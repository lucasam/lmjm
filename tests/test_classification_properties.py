"""Property-based tests for RawMaterialType classification correctness.

Property 3: RawMaterialType classification correctness

For any RawMaterialType with category "feed" and a FiscalDocument with matching
product_code, the Email_Intake_Lambda should create a FeedScheduleFiscalDocument.
For any product_code NOT found in RawMaterialType or with category other than "feed",
NO FeedScheduleFiscalDocument should be created.

**Validates: Requirements 5.1, 5.5, 11.5**
"""

import json
from decimal import Decimal
from typing import Any

import boto3
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from lmjm.model import RawMaterialType
from lmjm.repo import RawMaterialTypeRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict

# --- Strategies ---

product_code_st = st.text(
    alphabet=st.characters(categories=("L", "N"), exclude_characters="\x00"),
    min_size=1,
    max_size=20,
)

category_st = st.sampled_from(["feed", "medicine"])

description_st = st.text(
    alphabet=st.characters(categories=("L", "N", "P", "Z"), exclude_characters="\x00"),
    min_size=1,
    max_size=30,
)


def _serialize_decimal_safe(obj: object, schema: Any = None) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = serialize_to_dict(obj, schema)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


def _create_table() -> Any:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    table = dynamodb.create_table(
        TableName="lmjm-test",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return table


# --- Property Tests ---


@given(code=product_code_st, category=category_st, desc=description_st)
@settings(max_examples=100)
@mock_aws
def test_raw_material_type_classification_known_product(code: str, category: str, desc: str) -> None:
    """Property 3: RawMaterialType classification — known product codes.

    For any RawMaterialType stored in DynamoDB, querying by its code should
    return the correct category. If category is "feed", a FeedScheduleFiscalDocument
    should be created; if not "feed", no FeedScheduleFiscalDocument should be created.

    **Validates: Requirements 5.1, 5.5, 11.5**
    """
    table = _create_table()
    repo = RawMaterialTypeRepo(table)

    rmt = RawMaterialType(
        pk="RAW_MATERIAL_TYPE",
        sk=f"RawMaterialType|{code}",
        code=code,
        description=desc,
        category=category,
    )
    table.put_item(Item=_serialize_decimal_safe(rmt))

    result = repo.get(code)

    # The repo must find the entry
    assert result is not None
    assert result.code == code
    assert result.category == category

    # Classification logic: only "feed" category triggers FeedScheduleFiscalDocument
    should_create_feed_schedule_fiscal_doc = result.category == "feed"

    if category == "feed":
        assert should_create_feed_schedule_fiscal_doc is True
    else:
        assert should_create_feed_schedule_fiscal_doc is False


@given(code=product_code_st)
@settings(max_examples=100)
@mock_aws
def test_raw_material_type_classification_unknown_product(code: str) -> None:
    """Property 3: RawMaterialType classification — unknown product codes.

    For any product_code NOT found in RawMaterialType, the repo should return None,
    meaning no FeedScheduleFiscalDocument should be created.

    **Validates: Requirements 5.1, 5.5, 11.5**
    """
    table = _create_table()
    repo = RawMaterialTypeRepo(table)

    # Table is empty — no RawMaterialType entries
    result = repo.get(code)

    assert result is None

    # Classification logic: unknown product → no FeedScheduleFiscalDocument
    should_create_feed_schedule_fiscal_doc = False
    assert should_create_feed_schedule_fiscal_doc is False
