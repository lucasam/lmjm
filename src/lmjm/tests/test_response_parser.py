# Feature: feed-schedule-suggestions, Property 4: Suggestion parsing round-trip
"""Property test for suggestion parsing round-trip.

Validates: Requirements 7.1, 6.2, 8.2
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from lmjm.suggestion_engine.response_parser import _MOVE_PATTERN, parse_suggestions

# Strategy: generate dates in YYYY-MM-DD format
date_strategy = st.dates().map(lambda d: d.strftime("%Y-%m-%d"))

# Strategy: generate non-empty feed_type strings without newlines.
# The regex uses (.+) (greedy) for feed_type and (\S+) for new_planned_date,
# so feed_type must not end with whitespace followed by a date-like token.
# We use printable characters filtered to exclude newlines.
feed_type_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Z"),
        blacklist_characters="\n\r",
    ),
    min_size=1,
    max_size=50,
).filter(
    # Ensure the greedy (.+) won't swallow part of " to <date>" by
    # rejecting strings that end with whitespace followed by a non-space token
    # that looks like a date (YYYY-MM-DD).
    lambda s: not __import__("re").search(r"\s\d{4}-\d{2}-\d{2}$", s)
)


@settings(max_examples=100, deadline=None)
@given(
    planned_date=date_strategy,
    feed_type=feed_type_strategy,
    new_planned_date=date_strategy,
)
def test_suggestion_parsing_round_trip(planned_date, feed_type, new_planned_date):
    """**Validates: Requirements 7.1, 6.2, 8.2**

    For any valid (planned_date, feed_type, new_planned_date) tuple,
    formatting into the move pattern and parsing back should recover
    the original values.
    """
    line = f"Move schedule from {planned_date} with {feed_type} to {new_planned_date}"

    suggestions = parse_suggestions(line)

    assert len(suggestions) == 1, f"Expected 1 suggestion, got {len(suggestions)}"
    suggestion = suggestions[0]
    assert suggestion.planned_date == planned_date
    assert suggestion.feed_type == feed_type
    assert suggestion.new_planned_date == new_planned_date


# Feature: feed-schedule-suggestions, Property 5: No-moves response returns empty suggestions
"""Property test for no-moves response.

Validates: Requirements 3.3
"""


@settings(max_examples=100, deadline=None)
@given(text=st.text(min_size=0, max_size=500))
def test_no_moves_response_returns_empty_suggestions(text):
    """**Validates: Requirements 3.3**

    For any string that does not contain the move pattern
    "Move schedule from ... with ... to ...",
    parse_suggestions() should return an empty list.
    """
    # Skip inputs that accidentally match the move pattern
    assume(not _MOVE_PATTERN.search(text))

    suggestions = parse_suggestions(text)

    assert suggestions == [], f"Expected empty list for text without move pattern, got {suggestions}"


# ── Unit tests for response parser edge cases (Task 2.4) ──────────────────────
# Validates: Requirements 7.1, 8.2


class TestParseEmptyInput:
    """Edge case: empty or whitespace-only input."""

    def test_empty_string_returns_empty_list(self):
        assert parse_suggestions("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert parse_suggestions("   \n\n  \t  ") == []


class TestParseSingleMove:
    """A response containing exactly one move line."""

    def test_single_move_parsed_correctly(self):
        text = "Move schedule from 2025-01-10 with Ração Engorda to 2025-01-15"
        result = parse_suggestions(text)

        assert len(result) == 1
        assert result[0].planned_date == "2025-01-10"
        assert result[0].feed_type == "Ração Engorda"
        assert result[0].new_planned_date == "2025-01-15"
        assert result[0].description == text.strip()

    def test_single_move_surrounded_by_non_matching_text(self):
        text = (
            "Here are my suggestions:\n"
            "Move schedule from 2025-03-01 with Feed A to 2025-03-05\n"
            "That should fix the balance issue."
        )
        result = parse_suggestions(text)

        assert len(result) == 1
        assert result[0].planned_date == "2025-03-01"
        assert result[0].feed_type == "Feed A"
        assert result[0].new_planned_date == "2025-03-05"


class TestParseMultipleMoves:
    """A response containing more than one move line."""

    def test_two_moves_parsed_in_order(self):
        text = (
            "Move schedule from 2025-02-01 with Feed X to 2025-02-03\n"
            "Move schedule from 2025-02-10 with Feed Y to 2025-02-12"
        )
        result = parse_suggestions(text)

        assert len(result) == 2
        assert result[0].planned_date == "2025-02-01"
        assert result[0].feed_type == "Feed X"
        assert result[0].new_planned_date == "2025-02-03"
        assert result[1].planned_date == "2025-02-10"
        assert result[1].feed_type == "Feed Y"
        assert result[1].new_planned_date == "2025-02-12"

    def test_multiple_moves_with_interleaved_text(self):
        text = (
            "Analysis complete. Suggested changes:\n"
            "1. Move schedule from 2025-04-01 with Milho to 2025-04-03\n"
            "This addresses the low balance on April 1st.\n"
            "2. Move schedule from 2025-04-10 with Soja to 2025-04-08\n"
            "This prevents the stock from exceeding the max threshold."
        )
        result = parse_suggestions(text)

        assert len(result) == 2
        assert result[0].feed_type == "Milho"
        assert result[1].feed_type == "Soja"


class TestParseSpecialCharactersInFeedType:
    """Feed type names with accented characters, symbols, or punctuation."""

    def test_accented_characters(self):
        text = "Move schedule from 2025-05-01 with Ração Inicial to 2025-05-04"
        result = parse_suggestions(text)

        assert len(result) == 1
        assert result[0].feed_type == "Ração Inicial"

    def test_hash_symbol_in_name(self):
        text = "Move schedule from 2025-06-01 with Feed Type #1 to 2025-06-05"
        result = parse_suggestions(text)

        assert len(result) == 1
        assert result[0].feed_type == "Feed Type #1"

    def test_parentheses_in_name(self):
        text = "Move schedule from 2025-07-01 with Premix (Vitaminas) to 2025-07-03"
        result = parse_suggestions(text)

        assert len(result) == 1
        assert result[0].feed_type == "Premix (Vitaminas)"

    def test_slash_in_name(self):
        text = "Move schedule from 2025-08-01 with Milho/Soja to 2025-08-04"
        result = parse_suggestions(text)

        assert len(result) == 1
        assert result[0].feed_type == "Milho/Soja"
