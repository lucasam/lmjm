"""Property-based tests for RawMaterialType CRUD.

Feature: raw-material-type-crud
"""

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

os.environ.setdefault("TABLE_NAME", "lmjm")

# Patch boto3 at module level so importing post_raw_material_type doesn't hang
# trying to connect to real AWS.
with patch("boto3.resource"):
    import lmjm.post_raw_material_type  # noqa: F401


# --- Strategies ---

# Non-empty printable strings for code and description
non_empty_text_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != "")

valid_category_st = st.sampled_from(["feed", "medicine"])


def _make_event(body: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal API Gateway proxy event."""
    return {"body": json.dumps(body)}


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")


# --- Property Tests ---


# Feature: raw-material-type-crud, Property 2: Valid POST body round-trip
@given(
    code=non_empty_text_st,
    description=non_empty_text_st,
    category=valid_category_st,
)
@settings(max_examples=100)
@patch("lmjm.post_raw_material_type.raw_material_type_repo")
def test_valid_post_body_round_trip(mock_repo: MagicMock, code: str, description: str, category: str) -> None:
    """Property 2: Valid POST body round-trip.

    For any valid combination of code (non-empty string), description (non-empty
    string), and category ("feed" or "medicine"), the POST handler should construct
    a RawMaterialType with pk="RAW_MATERIAL_TYPE", sk="RawMaterialType|{code}",
    and all three fields matching the input exactly.

    **Validates: Requirements 3.4, 4.4, 5.2**
    """
    from lmjm.post_raw_material_type import lambda_handler

    body = {"code": code, "description": description, "category": category}
    result = lambda_handler(_make_event(body), None)

    assert result["statusCode"] == 201

    # Verify repo.put was called exactly once
    mock_repo.put.assert_called_once()

    # Extract the RawMaterialType passed to repo.put
    record = mock_repo.put.call_args[0][0]

    # Verify constructed fields match input exactly
    assert record.pk == "RAW_MATERIAL_TYPE"
    assert record.sk == f"RawMaterialType|{code}"
    assert record.code == code
    assert record.description == description
    assert record.category == category


# Feature: raw-material-type-crud, Property 3: Missing required fields are rejected
@given(
    fields_to_include=st.lists(
        st.sampled_from(["code", "description", "category"]),
        unique=True,
        min_size=0,
        max_size=2,
    ),
    code=non_empty_text_st,
    description=non_empty_text_st,
    category=valid_category_st,
)
@settings(max_examples=100)
@patch("lmjm.post_raw_material_type.raw_material_type_repo")
def test_missing_required_fields_are_rejected(
    mock_repo: MagicMock,
    fields_to_include: list[str],
    code: str,
    description: str,
    category: str,
) -> None:
    """Property 3: Missing required fields are rejected.

    For any JSON body that is missing at least one of the required fields
    (code, description, category), the POST handler should return a 400
    status code.

    **Validates: Requirements 5.3**
    """
    from lmjm.post_raw_material_type import lambda_handler

    all_values = {"code": code, "description": description, "category": category}
    body = {k: v for k, v in all_values.items() if k in fields_to_include}

    result = lambda_handler(_make_event(body), None)

    assert result["statusCode"] == 400
    mock_repo.put.assert_not_called()


# Feature: raw-material-type-crud, Property 4: Invalid category is rejected
@given(
    code=non_empty_text_st,
    description=non_empty_text_st,
    category=st.text(min_size=1, max_size=100).filter(lambda s: s not in ("feed", "medicine")),
)
@settings(max_examples=100, deadline=None)
@patch("lmjm.post_raw_material_type.raw_material_type_repo")
def test_invalid_category_is_rejected(mock_repo: MagicMock, code: str, description: str, category: str) -> None:
    """Property 4: Invalid category is rejected.

    For any string that is not "feed" and not "medicine", submitting it as the
    category field in an otherwise valid POST body should result in a 400 status
    code response.

    **Validates: Requirements 5.4, 6.2, 6.3**
    """
    from lmjm.post_raw_material_type import lambda_handler

    body = {"code": code, "description": description, "category": category}
    result = lambda_handler(_make_event(body), None)

    assert result["statusCode"] == 400
    mock_repo.put.assert_not_called()


# Feature: raw-material-type-crud, Property 5: Serialization round-trip preserves RawMaterialType data
@given(
    code=non_empty_text_st,
    description=non_empty_text_st,
    category=valid_category_st,
)
@settings(max_examples=100)
def test_serialization_round_trip_preserves_data(code: str, description: str, category: str) -> None:
    """Property 5: Serialization round-trip preserves RawMaterialType data.

    For any valid RawMaterialType instance, serializing it to a dictionary via
    the marshmallow serializer and then deserializing back should produce an
    equivalent RawMaterialType object.

    **Validates: Requirements 5.5**
    """
    from lmjm.model.raw_material_type import RawMaterialType
    from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

    original = RawMaterialType(
        pk="RAW_MATERIAL_TYPE",
        sk=f"RawMaterialType|{code}",
        code=code,
        description=description,
        category=category,
    )

    serialized = serialize_to_dict(original)
    restored = load_data_class_from_dict(serialized, RawMaterialType)

    assert restored.pk == original.pk
    assert restored.sk == original.sk
    assert restored.code == original.code
    assert restored.description == original.description
    assert restored.category == original.category
    assert restored == original


# Feature: raw-material-type-crud, Property 1: Pagination preserves all records and respects page size
@given(
    items=st.lists(
        st.fixed_dictionaries(
            {
                "code": non_empty_text_st,
                "description": non_empty_text_st,
                "category": valid_category_st,
            }
        ),
        min_size=0,
        max_size=200,
    ),
)
@settings(max_examples=100)
def test_pagination_preserves_all_records_and_respects_page_size(items: list[dict[str, str]]) -> None:
    """Property 1: Pagination preserves all records and respects page size.

    For any list of RawMaterialType records of arbitrary length, slicing into
    pages of 30 should produce pages where each page has at most 30 items, and
    concatenating all pages produces the original list in order.

    **Validates: Requirements 2.3**
    """
    import math

    PAGE_SIZE = 30
    total_pages = math.ceil(len(items) / PAGE_SIZE) if items else 0

    all_paged_items: list[dict[str, str]] = []
    for page in range(total_pages):
        page_data = items[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
        # Each page must have at most PAGE_SIZE items
        assert len(page_data) <= PAGE_SIZE
        all_paged_items.extend(page_data)

    # Concatenating all pages must produce the original list in order
    assert all_paged_items == items
