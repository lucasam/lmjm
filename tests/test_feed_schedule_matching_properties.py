"""Property-based tests for FeedSchedule matching correctness.

Property 8: FeedSchedule matching correctness

For any FeedScheduleFiscalDocument with a given product_code and issue_date,
and a set of FeedSchedule entities for the batch: if exactly one FeedSchedule
has a matching feed_type (equal to product_code), status "scheduled", and
planned_date within 7 days of the issue_date, then feed_schedule_id should be
set to that schedule's sk. If zero or more than one FeedSchedule matches,
feed_schedule_id should be None.

**Validates: Requirements 5.2, 5.3, 5.4**
"""

from datetime import datetime, timedelta
from typing import Optional

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model import FeedSchedule
from lmjm.process_fiscal_email import _match_feed_schedule

# --- Strategies ---

product_code_st = st.text(
    alphabet=st.characters(categories=("L", "N"), exclude_characters="\x00"),
    min_size=1,
    max_size=20,
)

# Dates within a reasonable range
date_st = st.dates(
    min_value=datetime(2020, 1, 1).date(),
    max_value=datetime(2030, 12, 31).date(),
)

status_st = st.sampled_from(["scheduled", "delivered", "cancelled", "pending"])

# Day offset for planned_date relative to issue_date
close_offset_st = st.integers(min_value=-7, max_value=7)
far_offset_st = st.one_of(
    st.integers(min_value=8, max_value=365),
    st.integers(min_value=-365, max_value=-8),
)

sk_st = st.text(
    alphabet=st.characters(categories=("L", "N"), exclude_characters="\x00"),
    min_size=1,
    max_size=30,
).map(lambda s: f"FeedSchedule|{s}")


def _make_schedule(
    sk: str,
    feed_type: str,
    planned_date: str,
    status: str = "scheduled",
) -> FeedSchedule:
    return FeedSchedule(
        pk="batch-pk",
        sk=sk,
        feed_type=feed_type,
        planned_date=planned_date,
        status=status,
    )


def _oracle(
    product_code: str,
    issue_date_str: str,
    schedules: list[FeedSchedule],
) -> Optional[str]:
    """Reference implementation of matching logic for property verification."""
    try:
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    matches: list[FeedSchedule] = []
    for s in schedules:
        if s.feed_type != product_code:
            continue
        if s.status != "scheduled":
            continue
        try:
            planned = datetime.strptime(s.planned_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue
        if abs((planned - issue_date).days) <= 7:
            matches.append(s)

    if len(matches) == 1:
        return matches[0].sk
    return None


# --- Property Tests ---


@given(
    product_code=product_code_st,
    issue_date=date_st,
    offset=close_offset_st,
    sk=sk_st,
)
@settings(max_examples=100)
def test_exactly_one_matching_schedule_returns_sk(
    product_code: str,
    issue_date: datetime,
    offset: int,
    sk: str,
) -> None:
    """Exactly one matching schedule → returns its sk.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    issue_date_str = issue_date.isoformat()
    planned_date = (issue_date + timedelta(days=offset)).isoformat()

    schedules = [_make_schedule(sk=sk, feed_type=product_code, planned_date=planned_date, status="scheduled")]

    result = _match_feed_schedule(product_code, issue_date_str, schedules)
    expected = _oracle(product_code, issue_date_str, schedules)

    assert result == expected
    assert result == sk


@given(
    product_code=product_code_st,
    other_code=product_code_st,
    issue_date=date_st,
    offset=close_offset_st,
    sk=sk_st,
    status=status_st,
)
@settings(max_examples=100)
def test_no_matching_schedules_returns_none(
    product_code: str,
    other_code: str,
    issue_date: datetime,
    offset: int,
    sk: str,
    status: str,
) -> None:
    """No matching schedules → returns None.

    Schedules that differ in feed_type, status, or date should not match.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    issue_date_str = issue_date.isoformat()
    planned_date = (issue_date + timedelta(days=offset)).isoformat()

    # Build schedules that should NOT match: wrong feed_type, wrong status, or far date
    schedules: list[FeedSchedule] = []

    # Wrong feed_type (ensure it differs)
    if other_code != product_code:
        schedules.append(
            _make_schedule(sk=f"{sk}_wrong_type", feed_type=other_code, planned_date=planned_date, status="scheduled")
        )

    # Wrong status
    if status != "scheduled":
        schedules.append(
            _make_schedule(sk=f"{sk}_wrong_status", feed_type=product_code, planned_date=planned_date, status=status)
        )

    result = _match_feed_schedule(product_code, issue_date_str, schedules)
    expected = _oracle(product_code, issue_date_str, schedules)

    assert result == expected
    assert result is None


@given(
    product_code=product_code_st,
    issue_date=date_st,
    offset1=close_offset_st,
    offset2=close_offset_st,
    sk1=sk_st,
    sk2=sk_st,
)
@settings(max_examples=100)
def test_multiple_matching_schedules_returns_none(
    product_code: str,
    issue_date: datetime,
    offset1: int,
    offset2: int,
    sk1: str,
    sk2: str,
) -> None:
    """Multiple matching schedules → returns None.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    # Ensure distinct sks
    if sk1 == sk2:
        sk2 = sk2 + "_2"

    issue_date_str = issue_date.isoformat()
    planned1 = (issue_date + timedelta(days=offset1)).isoformat()
    planned2 = (issue_date + timedelta(days=offset2)).isoformat()

    schedules = [
        _make_schedule(sk=sk1, feed_type=product_code, planned_date=planned1, status="scheduled"),
        _make_schedule(sk=sk2, feed_type=product_code, planned_date=planned2, status="scheduled"),
    ]

    result = _match_feed_schedule(product_code, issue_date_str, schedules)
    expected = _oracle(product_code, issue_date_str, schedules)

    assert result == expected
    assert result is None


@given(
    product_code=product_code_st,
    other_code=product_code_st,
    issue_date=date_st,
    offset=close_offset_st,
    sk=sk_st,
)
@settings(max_examples=100)
def test_wrong_feed_type_not_matched(
    product_code: str,
    other_code: str,
    issue_date: datetime,
    offset: int,
    sk: str,
) -> None:
    """Schedule with wrong feed_type → not matched.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    # Ensure codes differ
    if other_code == product_code:
        other_code = product_code + "_diff"

    issue_date_str = issue_date.isoformat()
    planned_date = (issue_date + timedelta(days=offset)).isoformat()

    schedules = [_make_schedule(sk=sk, feed_type=other_code, planned_date=planned_date, status="scheduled")]

    result = _match_feed_schedule(product_code, issue_date_str, schedules)
    assert result is None


@given(
    product_code=product_code_st,
    issue_date=date_st,
    offset=close_offset_st,
    sk=sk_st,
    status=st.sampled_from(["delivered", "cancelled", "pending"]),
)
@settings(max_examples=100)
def test_wrong_status_not_matched(
    product_code: str,
    issue_date: datetime,
    offset: int,
    sk: str,
    status: str,
) -> None:
    """Schedule with wrong status → not matched.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    issue_date_str = issue_date.isoformat()
    planned_date = (issue_date + timedelta(days=offset)).isoformat()

    schedules = [_make_schedule(sk=sk, feed_type=product_code, planned_date=planned_date, status=status)]

    result = _match_feed_schedule(product_code, issue_date_str, schedules)
    assert result is None


@given(
    product_code=product_code_st,
    issue_date=date_st,
    offset=far_offset_st,
    sk=sk_st,
)
@settings(max_examples=100)
def test_date_beyond_7_days_not_matched(
    product_code: str,
    issue_date: datetime,
    offset: int,
    sk: str,
) -> None:
    """Schedule with date > 7 days away → not matched.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    issue_date_str = issue_date.isoformat()
    planned_date = (issue_date + timedelta(days=offset)).isoformat()

    schedules = [_make_schedule(sk=sk, feed_type=product_code, planned_date=planned_date, status="scheduled")]

    result = _match_feed_schedule(product_code, issue_date_str, schedules)
    assert result is None


@given(
    product_code=product_code_st,
    issue_date=date_st,
    schedules_data=st.lists(
        st.tuples(
            product_code_st,  # feed_type
            st.integers(min_value=-30, max_value=30),  # day offset
            status_st,  # status
            sk_st,  # sk
        ),
        min_size=0,
        max_size=10,
    ),
)
@settings(max_examples=200)
def test_general_matching_agrees_with_oracle(
    product_code: str,
    issue_date: datetime,
    schedules_data: list[tuple[str, int, str, str]],
) -> None:
    """General property: _match_feed_schedule always agrees with the oracle.

    Generates random schedules with varying feed_types, offsets, and statuses,
    then verifies the function result matches the reference implementation.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    issue_date_str = issue_date.isoformat()

    schedules: list[FeedSchedule] = []
    seen_sks: set[str] = set()
    for feed_type, offset, status, sk in schedules_data:
        # Ensure unique sks
        if sk in seen_sks:
            sk = sk + f"_{len(seen_sks)}"
        seen_sks.add(sk)

        planned_date = (issue_date + timedelta(days=offset)).isoformat()
        schedules.append(_make_schedule(sk=sk, feed_type=feed_type, planned_date=planned_date, status=status))

    result = _match_feed_schedule(product_code, issue_date_str, schedules)
    expected = _oracle(product_code, issue_date_str, schedules)

    assert result == expected
