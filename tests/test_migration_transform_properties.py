"""Property-based tests for migration datetime transform.

Feature: datetime-precision, Property 7: Migration transform appends T00:00 to legacy dates

**Validates: Requirements 7.1, 7.2, 7.3, 7.4**
"""

import calendar
import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# Add scripts directory to path so we can import the migration module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from migrate_datetime import migrate_date_value

# --- Strategies ---

year_st = st.integers(min_value=2000, max_value=2099)
month_st = st.integers(min_value=1, max_value=12)
hour_st = st.integers(min_value=0, max_value=23)
minute_st = st.integers(min_value=0, max_value=59)


@st.composite
def valid_legacy_date_st(draw: st.DrawFn) -> str:
    """Generate valid YYYY-MM-DD date strings."""
    year = draw(year_st)
    month = draw(month_st)
    max_day = calendar.monthrange(year, month)[1]
    day = draw(st.integers(min_value=1, max_value=max_day))
    return f"{year:04d}-{month:02d}-{day:02d}"


@st.composite
def already_migrated_datetime_st(draw: st.DrawFn) -> str:
    """Generate YYYY-MM-DDTHH:MM strings (already migrated)."""
    year = draw(year_st)
    month = draw(month_st)
    max_day = calendar.monthrange(year, month)[1]
    day = draw(st.integers(min_value=1, max_value=max_day))
    hour = draw(hour_st)
    minute = draw(minute_st)
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}"


# --- Property Tests ---


# Feature: datetime-precision, Property 7: Migration transform appends T00:00 to legacy dates
@given(date_str=valid_legacy_date_st())
@settings(max_examples=100)
def test_migration_transform_appends_t0000_to_legacy_dates(date_str: str) -> None:
    """Property 7: For any valid YYYY-MM-DD string, migration produces YYYY-MM-DDT00:00.

    The result preserves the original date components and sets time to 00:00.

    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """
    result = migrate_date_value(date_str)

    assert result is not None, f"Expected migration for legacy date: {date_str}"
    assert result == f"{date_str}T00:00", f"Expected {date_str}T00:00, got {result}"

    # Verify date components are preserved
    assert result[:10] == date_str, f"Date portion changed: {result[:10]} != {date_str}"
    # Verify time is 00:00
    assert result.endswith("T00:00"), f"Time should be T00:00: {result}"


# Feature: datetime-precision, Property 7: Migration transform appends T00:00 to legacy dates
@given(dt_str=already_migrated_datetime_st())
@settings(max_examples=100)
def test_migration_transform_skips_already_migrated(dt_str: str) -> None:
    """Property 7: Strings already containing T should not be modified.

    For any YYYY-MM-DDTHH:MM string, migrate_date_value returns None.

    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """
    result = migrate_date_value(dt_str)

    assert result is None, f"Expected None for already-migrated datetime: {dt_str}, got {result}"
