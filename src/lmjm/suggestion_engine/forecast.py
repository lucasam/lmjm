"""Feed forecast calculator.

Pure function that computes daily projected balances from consumption plan,
scheduled deliveries, feed balance measurements, and mortalities.

Matches the frontend FeedBalanceForecastView calculation logic:
- Starts from the latest balance measurement date
- Projects forward 60 days
- Uses day_number relative to average_start_date for consumption lookup
- Accounts for mortalities reducing live animal count
- Includes scheduled and delivered feed schedules (excludes canceled)
"""

from datetime import datetime, timedelta

from lmjm.model.feed_balance import FeedBalance
from lmjm.model.feed_consumption_plan import FeedConsumptionPlan
from lmjm.model.feed_schedule import FeedSchedule
from lmjm.model.feed_schedule_suggestion import DailyBalance
from lmjm.model.mortality import Mortality


def _get_cumulative_deaths_up_to(mortalities: list[Mortality], date_str: str) -> int:
    """Count mortalities on or before the given date."""
    count = 0
    for m in mortalities:
        if m.mortality_date <= date_str:
            count += 1
    return count


def compute_projected_balances(
    consumption_plan: list[FeedConsumptionPlan],
    scheduled_entries: list[FeedSchedule],
    balances: list[FeedBalance],
    total_animal_count: int,
    average_start_date: str,
    mortalities: list[Mortality],
) -> list[DailyBalance]:
    """Compute daily projected feed balances.

    Starts from the latest balance measurement and projects forward 60 days.
    For each day:
    - consumption = plan's expected_kg_per_animal * live_animals for that day_number
    - scheduled_delivery = sum of expected_amount_kg from scheduled/delivered entries
    - projected_balance = previous balance + delivery - consumption

    Returns a list of DailyBalance sorted by date.
    """
    if total_animal_count == 0 or not balances:
        return []

    # Find latest balance measurement
    sorted_balances = sorted(balances, key=lambda b: b.measurement_date)
    latest_balance = sorted_balances[-1]

    # Index scheduled deliveries by planned_date (scheduled + delivered only)
    delivery_by_date: dict[str, int] = {}
    for entry in scheduled_entries:
        if entry.status in ("scheduled", "delivered"):
            delivery_by_date[entry.planned_date] = (
                delivery_by_date.get(entry.planned_date, 0) + entry.expected_amount_kg
            )

    # Index consumption plan by day_number
    plan_by_day: dict[int, float] = {}
    for p in consumption_plan:
        plan_by_day[p.day_number] = float(p.expected_kg_per_animal)

    receive_date = datetime.strptime(average_start_date[:10], "%Y-%m-%d")
    start_date = datetime.strptime(latest_balance.measurement_date[:10], "%Y-%m-%d")
    balance = latest_balance.balance_kg

    max_days = 60
    results: list[DailyBalance] = []

    for d in range(max_days + 1):
        current_date = start_date + timedelta(days=d)
        date_str = current_date.strftime("%Y-%m-%d")

        consumption = 0
        scheduled_delivery = delivery_by_date.get(date_str, 0)

        if d > 0:
            balance += scheduled_delivery

            days_since_receive = (current_date - receive_date).days
            day_number = days_since_receive + 1
            kg_per_animal = plan_by_day.get(day_number, 0)
            deaths = _get_cumulative_deaths_up_to(mortalities, date_str)
            live_animals = max(1, total_animal_count - deaths)
            consumption = int(kg_per_animal * live_animals)
            balance -= consumption

        results.append(
            DailyBalance(
                date=date_str,
                projected_balance_kg=balance,
                consumption_kg=consumption,
                scheduled_delivery_kg=scheduled_delivery,
                arrival_kg=0,
            )
        )

    return results
