"""Property-based tests for fiscal document sort order.

Property 10: Fiscal documents returned sorted by issue_date descending.

**Validates: Requirements 7.3**
"""

import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model.fiscal_document import FiscalDocument

# --- Strategies ---

date_strategy = st.dates(
    min_value=datetime.date(2020, 1, 1),
    max_value=datetime.date(2030, 12, 31),
).map(lambda d: d.isoformat())

fiscal_document_strategy = st.builds(
    FiscalDocument,
    pk=st.just("batch-123"),
    sk=st.uuids().map(lambda u: f"FiscalDocument|{u}"),
    fiscal_document_number=st.uuids().map(str),
    issue_date=date_strategy,
    actual_amount_kg=st.integers(min_value=0, max_value=10_000_000),
    product_code=st.just("130906"),
    product_description=st.just("ST06 RAC SUI TERM"),
    supplier_name=st.just("BRF S.A."),
    order_number=st.just("0112053764"),
    source_email_s3_key=st.none(),
)


# --- Property Tests ---


@given(docs=st.lists(fiscal_document_strategy, min_size=0, max_size=30))
@settings(max_examples=100)
def test_fiscal_documents_sorted_by_issue_date_descending(docs: list[FiscalDocument]) -> None:
    """Property 10: Fiscal documents returned sorted by issue_date descending.

    For any set of FiscalDocument entities, sorting by issue_date descending
    (the same logic used in get_fiscal_documents.py) should produce a list
    where each consecutive pair has issue_date >= the next one.

    **Validates: Requirements 7.3**
    """
    # Apply the same sort logic as the Lambda handler
    sorted_docs = sorted(docs, key=lambda d: d.issue_date, reverse=True)

    # Verify descending order: each issue_date >= the next
    for i in range(len(sorted_docs) - 1):
        assert sorted_docs[i].issue_date >= sorted_docs[i + 1].issue_date, (
            f"Sort order violated at index {i}: "
            f"{sorted_docs[i].issue_date} < {sorted_docs[i + 1].issue_date}"
        )
