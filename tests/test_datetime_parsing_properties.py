"""Property-based tests for datetime parsing utility.

Feature: datetime-precision

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4**
"""

import calendar

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.util.datetime_util import parse_datetime_input

# --- Strategies ---

# Valid datetime components within year 2000-2099
year_st = st.integers(min_value=2000, max_value=2099)
month_st = st.integers(min_value=1, max_value=12)
hour_st = st.integers(min_value=0, max_value=23)
minute_st = st.integers(min_value=0, max_value=59)


@st.composite
def valid_datetime_st(draw: st.DrawFn) -> tuple[int, int, int, int, int]:
    """Generate valid (year, month, day, hour, minute) tuples."""
    year = draw(year_st)
    month = draw(month_st)
    max_day = calendar.monthrange(year, month)[1]
    day = draw(st.integers(min_value=1, max_value=max_day))
    hour = draw(hour_st)
    minute = draw(minute_st)
    return year, month, day, hour, minute


@st.composite
def valid_date_st(draw: st.DrawFn) -> tuple[int, int, int]:
    """Generate valid (year, month, day) tuples."""
    year = draw(year_st)
    month = draw(month_st)
    max_day = calendar.monthrange(year, month)[1]
    day = draw(st.integers(min_value=1, max_value=max_day))
    return year, month, day


# --- Property Tests ---


# Feature: datetime-precision, Property 1: Datetime parsing round trip
@given(dt=valid_datetime_st())
@settings(max_examples=100)
def test_datetime_parsing_round_trip_full(dt: tuple[int, int, int, int, int]) -> None:
    """Property 1: Datetime parsing round trip — full datetime (YYYYMMDDHHmm).

    For any valid datetime (year 2000-2099, valid month/day/hour/minute),
    formatting it as YYYYMMDDHHmm and passing it through parse_datetime_input
    should produce a stored_value equal to YYYY-MM-DDTHH:MM with the same
    date and time components, and a sk_date_part equal to the original
    YYYYMMDDHHmm string.

    **Validates: Requirements 1.1, 1.4, 2.1, 2.4**
    """
    year, month, day, hour, minute = dt
    raw = f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}"

    stored, sk_part = parse_datetime_input(raw)

    expected_stored = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}"
    assert stored == expected_stored, f"stored_value mismatch: {stored} != {expected_stored}"
    assert sk_part == raw, f"sk_date_part mismatch: {sk_part} != {raw}"


# Feature: datetime-precision, Property 1: Datetime parsing round trip
@given(d=valid_date_st())
@settings(max_examples=100)
def test_datetime_parsing_round_trip_date_only(d: tuple[int, int, int]) -> None:
    """Property 1: Datetime parsing round trip — date-only (YYYYMMDD).

    For any valid date formatted as YYYYMMDD, the stored_value should end
    with T00:00 and the sk_date_part should end with 0000.

    **Validates: Requirements 1.2, 1.4, 2.2, 2.4**
    """
    year, month, day = d
    raw = f"{year:04d}{month:02d}{day:02d}"

    stored, sk_part = parse_datetime_input(raw)

    expected_stored = f"{year:04d}-{month:02d}-{day:02d}T00:00"
    assert stored == expected_stored, f"stored_value mismatch: {stored} != {expected_stored}"
    assert stored.endswith("T00:00"), f"stored_value should end with T00:00: {stored}"
    assert sk_part.endswith("0000"), f"sk_date_part should end with 0000: {sk_part}"
    assert sk_part == f"{year:04d}{month:02d}{day:02d}0000"


# --- Invalid input strategies ---


@st.composite
def wrong_length_string_st(draw: st.DrawFn) -> str:
    """Generate strings that are not 8 or 12 characters long."""
    length = draw(st.integers(min_value=0, max_value=20).filter(lambda x: x not in (8, 12)))
    return draw(st.text(alphabet=st.characters(categories=("N", "L")), min_size=length, max_size=length))


@st.composite
def non_numeric_8_or_12_st(draw: st.DrawFn) -> str:
    """Generate 8 or 12 char strings that contain at least one non-digit."""
    length = draw(st.sampled_from([8, 12]))
    s = draw(
        st.text(
            alphabet=st.characters(categories=("N", "L", "P")),
            min_size=length,
            max_size=length,
        ).filter(lambda x: not x.isdigit())
    )
    return s


@st.composite
def invalid_date_values_st(draw: st.DrawFn) -> str:
    """Generate 8 or 12 digit strings with invalid date/time values."""
    choice = draw(st.sampled_from(["invalid_month", "invalid_day", "invalid_hour", "invalid_minute"]))
    year = draw(st.integers(min_value=2000, max_value=2099))

    if choice == "invalid_month":
        month = draw(st.sampled_from([0, 13, 14, 15, 99]))
        day = 1
        raw = f"{year:04d}{month:02d}{day:02d}"
        if draw(st.booleans()):
            raw += f"{0:02d}{0:02d}"
        return raw

    if choice == "invalid_day":
        month = draw(st.integers(min_value=1, max_value=12))
        max_valid = calendar.monthrange(year, month)[1]
        day = draw(st.integers(min_value=max_valid + 1, max_value=max_valid + 10))
        raw = f"{year:04d}{month:02d}{day:02d}"
        if draw(st.booleans()):
            raw += f"{0:02d}{0:02d}"
        return raw

    if choice == "invalid_hour":
        month = draw(st.integers(min_value=1, max_value=12))
        max_day = calendar.monthrange(year, month)[1]
        day = draw(st.integers(min_value=1, max_value=max_day))
        hour = draw(st.integers(min_value=24, max_value=99))
        minute = draw(st.integers(min_value=0, max_value=59))
        return f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}"

    # invalid_minute
    month = draw(st.integers(min_value=1, max_value=12))
    max_day = calendar.monthrange(year, month)[1]
    day = draw(st.integers(min_value=1, max_value=max_day))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=60, max_value=99))
    return f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}"


# Feature: datetime-precision, Property 2: Invalid datetime input rejection
@given(s=wrong_length_string_st())
@settings(max_examples=100)
def test_invalid_datetime_wrong_length(s: str) -> None:
    """Property 2: Invalid datetime input rejection — wrong length strings.

    For any string that is not 8 or 12 characters long, parse_datetime_input
    should raise a ValueError.

    **Validates: Requirements 1.3, 2.3**
    """
    try:
        parse_datetime_input(s)
        assert False, f"Expected ValueError for input of length {len(s)}: {s!r}"
    except ValueError:
        pass


# Feature: datetime-precision, Property 2: Invalid datetime input rejection
@given(s=non_numeric_8_or_12_st())
@settings(max_examples=100)
def test_invalid_datetime_non_numeric(s: str) -> None:
    """Property 2: Invalid datetime input rejection — non-numeric strings of valid length.

    For any 8 or 12 character string containing non-digit characters,
    parse_datetime_input should raise a ValueError.

    **Validates: Requirements 1.3, 2.3**
    """
    try:
        parse_datetime_input(s)
        assert False, f"Expected ValueError for non-numeric input: {s!r}"
    except ValueError:
        pass


# Feature: datetime-precision, Property 2: Invalid datetime input rejection
@given(s=invalid_date_values_st())
@settings(max_examples=100)
def test_invalid_datetime_bad_date_values(s: str) -> None:
    """Property 2: Invalid datetime input rejection — invalid date/time values.

    For strings with valid length (8 or 12 digits) but invalid date/time values
    (e.g., month 13, hour 25, minute 60), parse_datetime_input should raise ValueError.

    **Validates: Requirements 1.3, 2.3**
    """
    try:
        parse_datetime_input(s)
        assert False, f"Expected ValueError for invalid date values: {s!r}"
    except ValueError:
        pass
