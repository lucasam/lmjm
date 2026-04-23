# Feature: feed-schedule-suggestions, Property 1: Schedule filtering preserves only scheduled entries
"""Property test for schedule filtering.

Validates: Requirements 2.2, 2.3
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model.batch import Batch
from lmjm.model.feed_schedule import FeedSchedule, FeedScheduleStatus
from lmjm.suggestion_engine.context_builder import build_suggestion_context

# Strategy: generate a list of FeedSchedule entries with random statuses
feed_schedule_strategy = st.lists(
    st.tuples(
        st.sampled_from(["Feed A", "Feed B", "Feed C"]),
        st.dates(
            min_value=__import__("datetime").date(2025, 1, 1),
            max_value=__import__("datetime").date(2025, 12, 31),
        ).map(lambda d: d.strftime("%Y-%m-%d")),
        st.integers(min_value=100, max_value=50000),
        st.sampled_from(list(FeedScheduleStatus)),
    ),
    min_size=0,
    max_size=20,
)


def _build_entries(raw_list: list) -> list[FeedSchedule]:
    """Convert raw tuples into FeedSchedule objects with unique sk values."""
    return [
        FeedSchedule(
            pk="BATCH#test",
            sk=f"FeedSchedule|{i}",
            feed_type=feed_type,
            planned_date=planned_date,
            expected_amount_kg=amount,
            status=status,
        )
        for i, (feed_type, planned_date, amount, status) in enumerate(raw_list)
    ]


@settings(max_examples=100, deadline=None)
@given(raw_entries=feed_schedule_strategy)
def test_schedule_filtering_preserves_only_scheduled_entries(raw_entries):
    """**Validates: Requirements 2.2, 2.3**

    For any list of FeedSchedule entries with arbitrary statuses,
    build_suggestion_context() should include exactly those entries
    whose status is 'scheduled' and exclude all others.
    """
    entries = _build_entries(raw_entries)

    batch = Batch(pk="BATCH#test", min_feed_stock_threshold=5000, total_animal_count=100)

    context = build_suggestion_context(
        batch=batch,
        scheduled_entries=entries,
        consumption_plan=[],
        truck_arrivals=[],
        balances=[],
    )

    # Expected: only entries with status == scheduled
    expected_scheduled = [e for e in entries if e.status == FeedScheduleStatus.scheduled]

    # Assert count matches
    assert len(context.scheduled_entries) == len(expected_scheduled), (
        f"Expected {len(expected_scheduled)} scheduled entries, " f"got {len(context.scheduled_entries)}"
    )

    # Assert every entry in context.scheduled_entries has status == scheduled
    for entry in context.scheduled_entries:
        assert (
            entry.status == FeedScheduleStatus.scheduled
        ), f"Found entry with status {entry.status} in scheduled_entries"

    # Assert the filtered set contains exactly the right entries (by sk)
    expected_sks = {e.sk for e in expected_scheduled}
    actual_sks = {e.sk for e in context.scheduled_entries}
    assert actual_sks == expected_sks, f"Scheduled entry sk mismatch: expected {expected_sks}, got {actual_sks}"


# Feature: feed-schedule-suggestions, Property 3: Production weekday derivation matches actual schedule weekdays
"""Property test for production weekday derivation.

Validates: Requirements 5.2
"""

from datetime import datetime

# Strategy: generate a list of FeedSchedule entries with only scheduled status and random valid dates
feed_schedule_scheduled_strategy = st.lists(
    st.tuples(
        st.sampled_from(["Feed A", "Feed B", "Feed C"]),
        st.dates(
            min_value=__import__("datetime").date(2025, 1, 1),
            max_value=__import__("datetime").date(2025, 12, 31),
        ).map(lambda d: d.strftime("%Y-%m-%d")),
        st.integers(min_value=100, max_value=50000),
    ),
    min_size=1,
    max_size=20,
)


def _build_scheduled_entries(raw_list: list) -> list[FeedSchedule]:
    """Convert raw tuples into FeedSchedule objects with status=scheduled."""
    return [
        FeedSchedule(
            pk="BATCH#test",
            sk=f"FeedSchedule|{i}",
            feed_type=feed_type,
            planned_date=planned_date,
            expected_amount_kg=amount,
            status=FeedScheduleStatus.scheduled,
        )
        for i, (feed_type, planned_date, amount) in enumerate(raw_list)
    ]


@settings(max_examples=100, deadline=None)
@given(raw_entries=feed_schedule_scheduled_strategy)
def test_production_weekday_derivation_matches_actual_schedule_weekdays(raw_entries):
    """**Validates: Requirements 5.2**

    For any list of FeedSchedule entries with valid planned_date values,
    the derived production_weekdays for each feed type equals the sorted
    list of distinct weekdays from ALL entries of that feed type.
    """
    entries = _build_scheduled_entries(raw_entries)

    batch = Batch(pk="BATCH#test", min_feed_stock_threshold=5000, total_animal_count=100)

    context = build_suggestion_context(
        batch=batch,
        scheduled_entries=entries,
        consumption_plan=[],
        truck_arrivals=[],
        balances=[],
    )

    # Compute expected weekdays per feed type from ALL entries
    expected_weekdays_by_feed_type: dict[str, set[int]] = {}
    for entry in entries:
        weekday = datetime.strptime(entry.planned_date, "%Y-%m-%d").weekday()
        expected_weekdays_by_feed_type.setdefault(entry.feed_type, set()).add(weekday)

    # For each FeedTypeGroup in the context, verify production_weekdays
    for group in context.feed_type_groups:
        expected = sorted(expected_weekdays_by_feed_type.get(group.feed_type, set()))
        assert group.production_weekdays == expected, (
            f"Feed type '{group.feed_type}': expected production_weekdays {expected}, "
            f"got {group.production_weekdays}"
        )


# ── Unit tests for context builder ──────────────────────────────────────────
# Validates: Requirements 2.1, 2.2, 2.3, 5.2

import pytest

from lmjm.model.feed_schedule_suggestion import (
    MAX_FEED_STOCK_THRESHOLD,
    FeedTypeGroup,
    SuggestionContext,
)


def _make_entry(
    sk: str,
    feed_type: str,
    planned_date: str,
    expected_amount_kg: int = 1000,
    status: FeedScheduleStatus = FeedScheduleStatus.scheduled,
) -> FeedSchedule:
    """Helper to create a FeedSchedule with sensible defaults."""
    return FeedSchedule(
        pk="BATCH#test",
        sk=sk,
        feed_type=feed_type,
        planned_date=planned_date,
        expected_amount_kg=expected_amount_kg,
        status=status,
    )


def _default_batch(min_threshold: int = 5000) -> Batch:
    return Batch(
        pk="BATCH#test",
        min_feed_stock_threshold=min_threshold,
        total_animal_count=100,
    )


def _call_context(entries: list[FeedSchedule], batch: Batch | None = None) -> SuggestionContext:
    """Shortcut to call build_suggestion_context with empty ancillary data."""
    return build_suggestion_context(
        batch=batch or _default_batch(),
        scheduled_entries=entries,
        consumption_plan=[],
        truck_arrivals=[],
        balances=[],
    )


# ---------- 1. Feed type group identification (contiguous grouping) ----------


class TestFeedTypeGroupIdentification:
    """**Validates: Requirements 2.1, 2.2, 2.3**"""

    def test_contiguous_groups_not_merged(self):
        """Given entries [A, A, B, B, A] sorted by date, verify 3 contiguous
        groups are created: [A, B, A] — the two A runs are NOT merged."""
        entries = [
            _make_entry("FS|1", "Feed A", "2025-01-06"),  # Mon
            _make_entry("FS|2", "Feed A", "2025-01-07"),  # Tue
            _make_entry("FS|3", "Feed B", "2025-01-08"),  # Wed
            _make_entry("FS|4", "Feed B", "2025-01-09"),  # Thu
            _make_entry("FS|5", "Feed A", "2025-01-10"),  # Fri
        ]

        ctx = _call_context(entries)

        assert len(ctx.feed_type_groups) == 3
        assert ctx.feed_type_groups[0].feed_type == "Feed A"
        assert ctx.feed_type_groups[1].feed_type == "Feed B"
        assert ctx.feed_type_groups[2].feed_type == "Feed A"

        # Verify entry counts per group
        assert len(ctx.feed_type_groups[0].entries) == 2
        assert len(ctx.feed_type_groups[1].entries) == 2
        assert len(ctx.feed_type_groups[2].entries) == 1


# ---------- 2. Feed type group ordering ----------


class TestFeedTypeGroupOrdering:
    """**Validates: Requirements 2.1, 2.2**"""

    def test_groups_maintain_date_sorted_order(self):
        """Groups must appear in the order they first occur after sorting
        entries by planned_date."""
        entries = [
            _make_entry("FS|1", "Feed C", "2025-03-01"),
            _make_entry("FS|2", "Feed A", "2025-03-02"),
            _make_entry("FS|3", "Feed A", "2025-03-03"),
            _make_entry("FS|4", "Feed B", "2025-03-04"),
        ]

        ctx = _call_context(entries)

        group_types = [g.feed_type for g in ctx.feed_type_groups]
        assert group_types == ["Feed C", "Feed A", "Feed B"]

    def test_unsorted_entries_are_sorted_before_grouping(self):
        """Entries provided out of date order should still produce groups
        ordered by the earliest planned_date."""
        entries = [
            _make_entry("FS|1", "Feed B", "2025-02-10"),
            _make_entry("FS|2", "Feed A", "2025-02-01"),
            _make_entry("FS|3", "Feed A", "2025-02-05"),
            _make_entry("FS|4", "Feed B", "2025-02-15"),
        ]

        ctx = _call_context(entries)

        group_types = [g.feed_type for g in ctx.feed_type_groups]
        assert group_types == ["Feed A", "Feed B"]


# ---------- 3. Group first_date and last_date ----------


class TestGroupDateBoundaries:
    """**Validates: Requirements 2.1, 2.2**"""

    def test_single_entry_group_has_same_first_and_last(self):
        entries = [_make_entry("FS|1", "Feed A", "2025-04-15")]

        ctx = _call_context(entries)

        assert len(ctx.feed_type_groups) == 1
        assert ctx.feed_type_groups[0].first_date == "2025-04-15"
        assert ctx.feed_type_groups[0].last_date == "2025-04-15"

    def test_multi_entry_group_has_correct_boundaries(self):
        entries = [
            _make_entry("FS|1", "Feed A", "2025-05-01"),
            _make_entry("FS|2", "Feed A", "2025-05-05"),
            _make_entry("FS|3", "Feed A", "2025-05-10"),
            _make_entry("FS|4", "Feed B", "2025-05-12"),
        ]

        ctx = _call_context(entries)

        group_a = ctx.feed_type_groups[0]
        assert group_a.feed_type == "Feed A"
        assert group_a.first_date == "2025-05-01"
        assert group_a.last_date == "2025-05-10"

        group_b = ctx.feed_type_groups[1]
        assert group_b.feed_type == "Feed B"
        assert group_b.first_date == "2025-05-12"
        assert group_b.last_date == "2025-05-12"


# ---------- 4. Context thresholds ----------


class TestContextThresholds:
    """**Validates: Requirements 2.1, 2.3**"""

    def test_min_threshold_from_batch(self):
        batch = Batch(
            pk="BATCH#test",
            min_feed_stock_threshold=7500,
            total_animal_count=100,
        )
        ctx = _call_context([], batch)

        assert ctx.min_threshold == 7500

    def test_max_threshold_is_80000(self):
        ctx = _call_context([])

        assert ctx.max_threshold == 80_000
        assert ctx.max_threshold == MAX_FEED_STOCK_THRESHOLD


# ---------- 5. Empty entries ----------


class TestEmptyEntries:
    """**Validates: Requirements 2.2, 2.3**"""

    def test_empty_entries_produce_empty_groups(self):
        ctx = _call_context([])

        assert ctx.feed_type_groups == []
        assert ctx.scheduled_entries == []

    def test_empty_entries_still_populate_batch_id_and_thresholds(self):
        batch = Batch(
            pk="BATCH#farm42",
            min_feed_stock_threshold=3000,
            total_animal_count=50,
        )
        ctx = _call_context([], batch)

        assert ctx.batch_id == "BATCH#farm42"
        assert ctx.min_threshold == 3000
        assert ctx.max_threshold == 80_000


# ---------- 6. Mixed statuses ----------


class TestMixedStatuses:
    """**Validates: Requirements 2.2, 2.3**"""

    def test_only_scheduled_entries_appear_in_context(self):
        """Concrete example: 5 entries with mixed statuses. Only the 3
        scheduled ones should appear in the context."""
        entries = [
            _make_entry("FS|1", "Feed A", "2025-06-01", 1000, FeedScheduleStatus.scheduled),
            _make_entry("FS|2", "Feed A", "2025-06-02", 2000, FeedScheduleStatus.delivered),
            _make_entry("FS|3", "Feed B", "2025-06-03", 1500, FeedScheduleStatus.scheduled),
            _make_entry("FS|4", "Feed B", "2025-06-04", 3000, FeedScheduleStatus.canceled),
            _make_entry("FS|5", "Feed A", "2025-06-05", 2500, FeedScheduleStatus.scheduled),
        ]

        ctx = _call_context(entries)

        # Only 3 scheduled entries should be present
        assert len(ctx.scheduled_entries) == 3
        actual_sks = {e.sk for e in ctx.scheduled_entries}
        assert actual_sks == {"FS|1", "FS|3", "FS|5"}

        # All entries in context must be scheduled
        for entry in ctx.scheduled_entries:
            assert entry.status == FeedScheduleStatus.scheduled

        # Groups should reflect only the scheduled entries: [Feed A, Feed B, Feed A]
        group_types = [g.feed_type for g in ctx.feed_type_groups]
        assert group_types == ["Feed A", "Feed B", "Feed A"]
