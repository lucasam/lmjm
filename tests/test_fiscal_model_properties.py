"""Property-based tests for fiscal document model serialization round-trips.

Validates: Requirements 3.1, 3.2, 11.1, 11.2, 12.1, 12.2
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.model.fiscal_document import FiscalDocument
from lmjm.model.feed_schedule_fiscal_document import FeedScheduleFiscalDocument
from lmjm.model.raw_material_type import RawMaterialType
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

# --- Strategies ---

safe_text = st.text(
    alphabet=st.characters(
        categories=("L", "N", "P", "S", "Z"),
        exclude_characters="\x00",
    ),
    min_size=0,
    max_size=50,
)

non_empty_safe_text = st.text(
    alphabet=st.characters(
        categories=("L", "N", "P", "S", "Z"),
        exclude_characters="\x00",
    ),
    min_size=1,
    max_size=50,
)


fiscal_document_strategy = st.builds(
    FiscalDocument,
    pk=non_empty_safe_text,
    sk=non_empty_safe_text,
    fiscal_document_number=safe_text,
    issue_date=safe_text,
    actual_amount_kg=st.integers(min_value=0, max_value=10_000_000),
    product_code=safe_text,
    product_description=safe_text,
    supplier_name=safe_text,
    order_number=safe_text,
    source_email_s3_key=st.none() | safe_text,
)


raw_material_type_strategy = st.builds(
    RawMaterialType,
    pk=st.just("RAW_MATERIAL_TYPE"),
    sk=non_empty_safe_text,
    code=safe_text,
    description=safe_text,
    category=st.sampled_from(["feed", "medicine"]),
)

feed_schedule_fiscal_document_strategy = st.builds(
    FeedScheduleFiscalDocument,
    pk=non_empty_safe_text,
    sk=non_empty_safe_text,
    fiscal_document_number=safe_text,
    feed_schedule_id=st.none() | safe_text,
    status=st.sampled_from(["pending", "used", "discarded"]),
    product_code=safe_text,
    actual_amount_kg=st.integers(min_value=0, max_value=10_000_000),
    issue_date=safe_text,
)


# --- Property Tests ---


@given(doc=fiscal_document_strategy)
@settings(max_examples=100)
def test_fiscal_document_serialization_round_trip(doc: FiscalDocument) -> None:
    """Property 1: FiscalDocument serialization round-trip.

    For any valid FiscalDocument, serializing to dict and deserializing back
    should produce an equivalent object with all fields preserved.

    **Validates: Requirements 3.1, 3.2**
    """
    serialized = serialize_to_dict(doc)
    deserialized = load_data_class_from_dict(serialized, FiscalDocument)

    assert deserialized.pk == doc.pk
    assert deserialized.sk == doc.sk
    assert deserialized.fiscal_document_number == doc.fiscal_document_number
    assert deserialized.issue_date == doc.issue_date
    assert deserialized.actual_amount_kg == doc.actual_amount_kg
    assert deserialized.product_code == doc.product_code
    assert deserialized.product_description == doc.product_description
    assert deserialized.supplier_name == doc.supplier_name
    assert deserialized.order_number == doc.order_number
    assert deserialized.source_email_s3_key == doc.source_email_s3_key


@given(rmt=raw_material_type_strategy)
@settings(max_examples=100)
def test_raw_material_type_serialization_round_trip(rmt: RawMaterialType) -> None:
    """Property 15: RawMaterialType serialization round-trip.

    For any valid RawMaterialType, serializing to dict and deserializing back
    should produce an equivalent object with all fields preserved.

    **Validates: Requirements 11.1, 11.2**
    """
    serialized = serialize_to_dict(rmt)
    deserialized = load_data_class_from_dict(serialized, RawMaterialType)

    assert deserialized.pk == rmt.pk
    assert deserialized.sk == rmt.sk
    assert deserialized.code == rmt.code
    assert deserialized.description == rmt.description
    assert deserialized.category == rmt.category


@given(fsfd=feed_schedule_fiscal_document_strategy)
@settings(max_examples=100)
def test_feed_schedule_fiscal_document_serialization_round_trip(fsfd: FeedScheduleFiscalDocument) -> None:
    """Property 16: FeedScheduleFiscalDocument serialization round-trip.

    For any valid FeedScheduleFiscalDocument, serializing to dict and
    deserializing back should produce an equivalent object with all fields preserved.

    **Validates: Requirements 12.1, 12.2**
    """
    serialized = serialize_to_dict(fsfd)
    deserialized = load_data_class_from_dict(serialized, FeedScheduleFiscalDocument)

    assert deserialized.pk == fsfd.pk
    assert deserialized.sk == fsfd.sk
    assert deserialized.fiscal_document_number == fsfd.fiscal_document_number
    assert deserialized.feed_schedule_id == fsfd.feed_schedule_id
    assert deserialized.status == fsfd.status
    assert deserialized.product_code == fsfd.product_code
    assert deserialized.actual_amount_kg == fsfd.actual_amount_kg
    assert deserialized.issue_date == fsfd.issue_date
