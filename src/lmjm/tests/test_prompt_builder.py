# Feature: feed-schedule-suggestions, Property 2: Prompt contains all required context and business rules
"""Property test for prompt completeness.

Validates: Requirements 2.4, 3.1, 3.2, 4.1, 4.2, 5.1
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model.feed_schedule import FeedSchedule, FeedScheduleStatus
from lmjm.model.feed_schedule_suggestion import (
    DailyBalance,
    FeedTypeGroup,
    SuggestionContext,
)
from lmjm.suggestion_engine.prompt_builder import build_prompt

# ── Strategies ──────────────────────────────────────────────────────────────

date_strategy = st.dates(
    min_value=__import__("datetime").date(2025, 1, 1),
    max_value=__import__("datetime").date(2025, 12, 31),
).map(lambda d: d.strftime("%Y-%m-%d"))

daily_balance_strategy = st.builds(
    DailyBalance,
    date=date_strategy,
    projected_balance_kg=st.integers(min_value=0, max_value=200_000),
    consumption_kg=st.integers(min_value=0, max_value=10_000),
    scheduled_delivery_kg=st.integers(min_value=0, max_value=50_000),
    arrival_kg=st.integers(min_value=0, max_value=50_000),
)

feed_type_strategy = st.sampled_from(["Feed A", "Feed B", "Feed C", "Ração Engorda"])

feed_schedule_entry_strategy = st.builds(
    FeedSchedule,
    pk=st.just("BATCH#test"),
    sk=st.uuids().map(lambda u: f"FeedSchedule|{u}"),
    feed_type=feed_type_strategy,
    planned_date=date_strategy,
    expected_amount_kg=st.integers(min_value=100, max_value=50_000),
    status=st.just(FeedScheduleStatus.scheduled),
)

weekday_strategy = st.lists(
    st.integers(min_value=0, max_value=6),
    min_size=1,
    max_size=5,
    unique=True,
).map(sorted)

feed_type_group_strategy = st.builds(
    FeedTypeGroup,
    feed_type=feed_type_strategy,
    entries=st.just([]),  # entries list not used by build_prompt
    production_weekdays=weekday_strategy,
    first_date=date_strategy,
    last_date=date_strategy,
)

suggestion_context_strategy = st.builds(
    SuggestionContext,
    batch_id=st.just("BATCH#test"),
    min_threshold=st.integers(min_value=1000, max_value=20_000),
    max_threshold=st.just(80_000),
    daily_balances=st.lists(daily_balance_strategy, min_size=1, max_size=10),
    scheduled_entries=st.lists(feed_schedule_entry_strategy, min_size=1, max_size=10),
    feed_type_groups=st.lists(feed_type_group_strategy, min_size=1, max_size=5),
)


# ── Property test ───────────────────────────────────────────────────────────


@settings(max_examples=100, deadline=None)
@given(context=suggestion_context_strategy)
def test_prompt_contains_all_required_context_and_business_rules(context: SuggestionContext):
    """**Validates: Requirements 2.4, 3.1, 3.2, 4.1, 4.2, 5.1**

    For any valid SuggestionContext, the prompt produced by build_prompt()
    must contain:
    - A representation of each daily balance date
    - Each scheduled delivery's planned_date, feed_type, and expected_amount_kg
    - The min_threshold value as a string
    - The max threshold value (80,000)
    - Grouping/ordering constraint rules
    - Production weekday data for each feed type group
    - The output format instruction
    """
    prompt = build_prompt(context)

    # 1. Contains each daily balance date
    for db in context.daily_balances:
        assert db.date in prompt, f"Daily balance date '{db.date}' not found in prompt"

    # 2. Contains each scheduled delivery's planned_date, feed_type, and expected_amount_kg
    for entry in context.scheduled_entries:
        assert (
            entry.planned_date in prompt
        ), f"Scheduled delivery planned_date '{entry.planned_date}' not found in prompt"
        assert entry.feed_type in prompt, f"Scheduled delivery feed_type '{entry.feed_type}' not found in prompt"
        assert (
            str(entry.expected_amount_kg) in prompt
        ), f"Scheduled delivery expected_amount_kg '{entry.expected_amount_kg}' not found in prompt"

    # 3. Contains the min_threshold value as a string
    assert str(context.min_threshold) in prompt, f"min_threshold '{context.min_threshold}' not found in prompt"

    # 4. Contains "80000" or "80,000" or "80_000" (the max threshold)
    assert any(
        s in prompt for s in ("80000", "80,000", "80_000")
    ), "Max threshold (80000 / 80,000 / 80_000) not found in prompt"

    # 5. Contains grouping/ordering rule text
    assert any(
        phrase in prompt.lower() for phrase in ("relative order", "cannot change", "order of groups")
    ), "Grouping/ordering constraint rule text not found in prompt"

    # 6. Contains production weekday data for each feed type group
    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    for group in context.feed_type_groups:
        for wd in group.production_weekdays:
            assert weekday_names[wd] in prompt, (
                f"Production weekday '{weekday_names[wd]}' for feed type " f"'{group.feed_type}' not found in prompt"
            )

    # 7. Contains the output format instruction
    assert "Move schedule from" in prompt, "Output format instruction 'Move schedule from' not found in prompt"


# ── Unit tests for prompt builder (Task 6.3) ────────────────────────────────
# Snapshot / structural tests to catch unintended prompt regressions.
# Requirements: 2.4, 3.1, 3.2


from lmjm.model.feed_schedule import (  # noqa: E402 (already imported above, safe re-import)
    FeedSchedule,
    FeedScheduleStatus,
)


class TestBuildPromptSnapshot:
    """Structural snapshot tests for build_prompt with known inputs."""

    @staticmethod
    def _make_snapshot_context() -> SuggestionContext:
        """Build a concrete SuggestionContext used by snapshot tests."""
        daily_balances = [
            DailyBalance(
                date="2025-07-01",
                projected_balance_kg=12_000,
                consumption_kg=3_000,
                scheduled_delivery_kg=10_000,
                arrival_kg=0,
            ),
            DailyBalance(
                date="2025-07-02",
                projected_balance_kg=19_000,
                consumption_kg=3_000,
                scheduled_delivery_kg=0,
                arrival_kg=10_000,
            ),
        ]

        scheduled_entries = [
            FeedSchedule(
                pk="BATCH#snapshot",
                sk="FeedSchedule|entry-1",
                feed_type="Ração Engorda",
                planned_date="2025-07-01",
                expected_amount_kg=10_000,
                status=FeedScheduleStatus.scheduled,
            ),
            FeedSchedule(
                pk="BATCH#snapshot",
                sk="FeedSchedule|entry-2",
                feed_type="Feed B",
                planned_date="2025-07-05",
                expected_amount_kg=15_000,
                status=FeedScheduleStatus.scheduled,
            ),
        ]

        feed_type_groups = [
            FeedTypeGroup(
                feed_type="Ração Engorda",
                entries=[],
                production_weekdays=[0, 2, 4],  # Monday, Wednesday, Friday
                first_date="2025-07-01",
                last_date="2025-07-03",
            ),
            FeedTypeGroup(
                feed_type="Feed B",
                entries=[],
                production_weekdays=[1, 3],  # Tuesday, Thursday
                first_date="2025-07-05",
                last_date="2025-07-10",
            ),
        ]

        return SuggestionContext(
            batch_id="BATCH#snapshot",
            min_threshold=5_000,
            max_threshold=80_000,
            daily_balances=daily_balances,
            scheduled_entries=scheduled_entries,
            feed_type_groups=feed_type_groups,
        )

    def test_prompt_starts_with_system_context(self):
        """The prompt must begin with the system context / role description."""
        prompt = build_prompt(self._make_snapshot_context())
        assert prompt.startswith("You are a feed schedule optimization assistant")

    def test_prompt_contains_daily_projected_balances_header(self):
        prompt = build_prompt(self._make_snapshot_context())
        assert "## Daily Projected Balances" in prompt

    def test_prompt_contains_scheduled_deliveries_header(self):
        prompt = build_prompt(self._make_snapshot_context())
        assert "## Scheduled Deliveries" in prompt

    def test_prompt_contains_business_rules_header(self):
        prompt = build_prompt(self._make_snapshot_context())
        assert "## Business Rules" in prompt

    def test_prompt_contains_output_format_header(self):
        prompt = build_prompt(self._make_snapshot_context())
        assert "## Output Format" in prompt

    def test_prompt_contains_threshold_values(self):
        """Min (5000) and max (80000) thresholds must appear in the prompt."""
        prompt = build_prompt(self._make_snapshot_context())
        assert "5000" in prompt
        assert any(v in prompt for v in ("80000", "80,000", "80_000"))

    def test_prompt_contains_feed_type_names(self):
        prompt = build_prompt(self._make_snapshot_context())
        assert "Ração Engorda" in prompt
        assert "Feed B" in prompt

    def test_prompt_contains_specific_dates(self):
        """All dates from balances and entries must appear in the prompt."""
        prompt = build_prompt(self._make_snapshot_context())
        for date in ("2025-07-01", "2025-07-02", "2025-07-05"):
            assert date in prompt, f"Date '{date}' not found in prompt"

    def test_prompt_contains_no_changes_needed_instruction(self):
        prompt = build_prompt(self._make_snapshot_context())
        assert "No changes needed" in prompt


class TestBuildPromptEmptyData:
    """Verify the prompt retains all required sections even with empty data."""

    @staticmethod
    def _make_empty_context() -> SuggestionContext:
        return SuggestionContext(
            batch_id="BATCH#empty",
            min_threshold=5_000,
            max_threshold=80_000,
            daily_balances=[],
            scheduled_entries=[],
            feed_type_groups=[],
        )

    def test_empty_prompt_has_daily_projected_balances_section(self):
        prompt = build_prompt(self._make_empty_context())
        assert "## Daily Projected Balances" in prompt

    def test_empty_prompt_has_scheduled_deliveries_section(self):
        prompt = build_prompt(self._make_empty_context())
        assert "## Scheduled Deliveries" in prompt

    def test_empty_prompt_has_business_rules_section(self):
        prompt = build_prompt(self._make_empty_context())
        assert "## Business Rules" in prompt

    def test_empty_prompt_has_output_format_section(self):
        prompt = build_prompt(self._make_empty_context())
        assert "## Output Format" in prompt

    def test_empty_prompt_has_threshold_values(self):
        prompt = build_prompt(self._make_empty_context())
        assert "5000" in prompt
        assert any(v in prompt for v in ("80000", "80,000", "80_000"))

    def test_empty_prompt_has_no_changes_needed_instruction(self):
        prompt = build_prompt(self._make_empty_context())
        assert "No changes needed" in prompt
