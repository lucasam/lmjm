"""Property-based tests for FeedScheduleFiscalDocument structural invariants.

**Validates: Requirements 12.1, 12.2**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model.feed_schedule_fiscal_document import FeedScheduleFiscalDocument

# --- Strategies ---

non_empty_safe_text = st.text(
    alphabet=st.characters(
        categories=("L", "N", "P", "S", "Z"),
        exclude_characters="\x00",
    ),
    min_size=1,
    max_size=50,
)

safe_text = st.text(
    alphabet=st.characters(
        categories=("L", "N", "P", "S", "Z"),
        exclude_characters="\x00",
    ),
    min_size=0,
    max_size=50,
)

VALID_STATUSES = ["pending", "used", "discarded"]


def build_fsfd(
    pk: str,
    fiscal_document_number: str,
    feed_schedule_id: str | None,
    status: str,
    product_code: str,
    actual_amount_kg: int,
    issue_date: str,
) -> FeedScheduleFiscalDocument:
    """Build a FeedScheduleFiscalDocument with the correct sk pattern."""
    return FeedScheduleFiscalDocument(
        pk=pk,
        sk=f"FeedScheduleFiscalDocument|{fiscal_document_number}",
        fiscal_document_number=fiscal_document_number,
        feed_schedule_id=feed_schedule_id,
        status=status,
        product_code=product_code,
        actual_amount_kg=actual_amount_kg,
        issue_date=issue_date,
    )


fsfd_strategy = st.builds(
    build_fsfd,
    pk=non_empty_safe_text,
    fiscal_document_number=non_empty_safe_text,
    feed_schedule_id=st.none() | safe_text,
    status=st.sampled_from(VALID_STATUSES),
    product_code=safe_text,
    actual_amount_kg=st.integers(min_value=0, max_value=10_000_000),
    issue_date=safe_text,
)


# --- Property Tests ---


@given(fsfd=fsfd_strategy)
@settings(max_examples=200)
def test_fsfd_sk_matches_fiscal_document_number(fsfd: FeedScheduleFiscalDocument) -> None:
    """Property 6 (part 1): FeedScheduleFiscalDocument sort key pattern.

    For any FeedScheduleFiscalDocument entity, the sort key should match
    the pattern "FeedScheduleFiscalDocument|{fiscal_document_number}"
    where fiscal_document_number equals the entity's fiscal_document_number field.

    **Validates: Requirements 12.1, 12.2**
    """
    expected_sk = f"FeedScheduleFiscalDocument|{fsfd.fiscal_document_number}"
    assert fsfd.sk == expected_sk, (
        f"sk '{fsfd.sk}' does not match expected pattern "
        f"'FeedScheduleFiscalDocument|{fsfd.fiscal_document_number}'"
    )


@given(fsfd=fsfd_strategy)
@settings(max_examples=200)
def test_fsfd_status_is_valid(fsfd: FeedScheduleFiscalDocument) -> None:
    """Property 6 (part 2): FeedScheduleFiscalDocument status invariant.

    For any FeedScheduleFiscalDocument entity, the status field should be
    one of "pending", "used", or "discarded".

    **Validates: Requirements 12.1, 12.2**
    """
    assert fsfd.status in VALID_STATUSES, (
        f"status '{fsfd.status}' is not one of {VALID_STATUSES}"
    )
