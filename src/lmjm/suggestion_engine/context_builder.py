"""Context builder for feed schedule suggestions.

Pure function that assembles the data needed for the AI prompt by filtering
scheduled entries, computing projected balances, and grouping entries by
feed description.
"""

from datetime import datetime

from lmjm.model.batch import Batch
from lmjm.model.feed_balance import FeedBalance
from lmjm.model.feed_consumption_plan import FeedConsumptionPlan
from lmjm.model.feed_schedule import FeedSchedule, FeedScheduleStatus
from lmjm.model.feed_schedule_suggestion import (
    MAX_FEED_STOCK_THRESHOLD,
    FeedTypeGroup,
    SuggestionContext,
)
from lmjm.model.feed_truck_arrival import FeedTruckArrival
from lmjm.model.mortality import Mortality
from lmjm.suggestion_engine.forecast import compute_projected_balances


def _feed_label(entry: FeedSchedule) -> str:
    """Return the human-readable feed label: feed_description if set, otherwise feed_type."""
    return entry.feed_description or entry.feed_type


def build_suggestion_context(
    batch: Batch,
    scheduled_entries: list[FeedSchedule],
    consumption_plan: list[FeedConsumptionPlan],
    truck_arrivals: list[FeedTruckArrival],
    balances: list[FeedBalance],
    mortalities: list[Mortality],
) -> SuggestionContext:
    """Build the context needed for the AI suggestion prompt.

    1. Filters entries to only those with status == "scheduled".
    2. Sorts filtered entries by planned_date.
    3. Groups contiguous entries by feed description (preserving order).
    4. Derives production weekdays per feed description from all scheduled entries.
    5. Computes projected daily balances via compute_projected_balances().
    6. Returns a populated SuggestionContext.
    """
    # Step 1: Separate entries for different purposes
    # All non-canceled entries are used for balance projection (includes delivered)
    all_active = [entry for entry in scheduled_entries if entry.status != FeedScheduleStatus.canceled]
    # Only scheduled entries can be moved by suggestions
    movable = [entry for entry in scheduled_entries if entry.status == FeedScheduleStatus.scheduled]

    # Step 2: Sort by planned_date
    all_active.sort(key=lambda e: e.planned_date)
    movable.sort(key=lambda e: e.planned_date)

    # Step 3: Group contiguous movable entries by feed description
    groups: list[FeedTypeGroup] = []
    for entry in movable:
        label = _feed_label(entry)
        if groups and groups[-1].feed_type == label:
            groups[-1].entries.append(entry)
            if entry.planned_date > groups[-1].last_date:
                groups[-1].last_date = entry.planned_date
            if entry.planned_date < groups[-1].first_date:
                groups[-1].first_date = entry.planned_date
        else:
            groups.append(
                FeedTypeGroup(
                    feed_type=label,
                    entries=[entry],
                    production_weekdays=[],
                    first_date=entry.planned_date,
                    last_date=entry.planned_date,
                )
            )

    # Step 4: Derive production weekdays per feed description from ALL movable entries
    weekdays_by_desc: dict[str, set[int]] = {}
    for entry in movable:
        weekday = datetime.strptime(entry.planned_date, "%Y-%m-%d").weekday()
        weekdays_by_desc.setdefault(_feed_label(entry), set()).add(weekday)

    # Assign production_weekdays to each group
    for group in groups:
        group.production_weekdays = sorted(weekdays_by_desc.get(group.feed_type, set()))

    # Step 5: Compute projected daily balances using ALL non-canceled entries
    total_animal_count = batch.total_animal_count if batch.total_animal_count else 0
    average_start_date = batch.average_start_date or ""
    daily_balances = compute_projected_balances(
        consumption_plan=consumption_plan,
        scheduled_entries=all_active,
        balances=balances,
        total_animal_count=total_animal_count,
        average_start_date=average_start_date,
        mortalities=mortalities,
    )

    # Step 6: Return populated SuggestionContext (movable entries for suggestions)
    return SuggestionContext(
        batch_id=batch.pk,
        min_threshold=batch.min_feed_stock_threshold,
        max_threshold=MAX_FEED_STOCK_THRESHOLD,
        daily_balances=daily_balances,
        scheduled_entries=movable,
        feed_type_groups=groups,
    )
