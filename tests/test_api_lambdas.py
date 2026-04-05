"""Unit tests for API Lambdas (GetFiscalDocuments, GetFeedScheduleFiscalDocuments, GetRawMaterialTypes).

Validates: Requirements 7.1, 7.3, 11.4, 12.4
"""

import importlib
import json
from decimal import Decimal
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.model import FeedScheduleFiscalDocument, FiscalDocument, RawMaterialType
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize


def _decimal_safe_serialize(obj: object, schema: Any = None) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj, schema)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    for repo_mod in [
        "lmjm.repo.fiscal_document_repo",
        "lmjm.repo.feed_schedule_fiscal_document_repo",
        "lmjm.repo.raw_material_type_repo",
    ]:
        monkeypatch.setattr(f"{repo_mod}.serialize_to_dict", _decimal_safe_serialize)


def _create_table() -> Any:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    return dynamodb.create_table(
        TableName="lmjm",
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


def _put(table: Any, obj: object) -> None:
    table.put_item(Item=_decimal_safe_serialize(obj))


def _apigw_event(batch_id: str) -> dict[str, Any]:
    return {"pathParameters": {"batch_id": batch_id}}


# ── GetFiscalDocuments ───────────────────────────────────────────────────────────


@mock_aws
def test_get_fiscal_documents_sorted_descending() -> None:
    """Requirement 7.1, 7.3: Returns FiscalDocuments sorted by issue_date descending."""
    table = _create_table()
    batch_id = "batch-123"

    _put(table, FiscalDocument(pk=batch_id, sk="FiscalDocument|111", fiscal_document_number="111", issue_date="2026-01-10", actual_amount_kg=1000, product_code="130906", product_description="ST06", supplier_name="BRF", order_number="100"))
    _put(table, FiscalDocument(pk=batch_id, sk="FiscalDocument|222", fiscal_document_number="222", issue_date="2026-03-15", actual_amount_kg=2000, product_code="130906", product_description="ST06", supplier_name="BRF", order_number="100"))
    _put(table, FiscalDocument(pk=batch_id, sk="FiscalDocument|333", fiscal_document_number="333", issue_date="2026-02-20", actual_amount_kg=3000, product_code="130906", product_description="ST06", supplier_name="BRF", order_number="100"))

    import lmjm.get_fiscal_documents as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_apigw_event(batch_id), None)
    assert result["statusCode"] == 200

    body = json.loads(result["body"])
    assert len(body) == 3
    assert body[0]["fiscal_document_number"] == "222"  # 2026-03-15
    assert body[1]["fiscal_document_number"] == "333"  # 2026-02-20
    assert body[2]["fiscal_document_number"] == "111"  # 2026-01-10


@mock_aws
def test_get_fiscal_documents_empty_batch() -> None:
    """Requirement 7.1: Empty batch returns empty list."""
    _create_table()

    import lmjm.get_fiscal_documents as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_apigw_event("batch-empty"), None)
    assert result["statusCode"] == 200

    body = json.loads(result["body"])
    assert body == []


# ── GetFeedScheduleFiscalDocuments ───────────────────────────────────────────────


@mock_aws
def test_get_feed_schedule_fiscal_documents_returns_entries() -> None:
    """Requirement 12.4: Returns FeedScheduleFiscalDocument entries for a batch."""
    table = _create_table()
    batch_id = "batch-456"

    _put(table, FeedScheduleFiscalDocument(pk=batch_id, sk="FeedScheduleFiscalDocument|AAA", fiscal_document_number="AAA", status="pending", product_code="130906", actual_amount_kg=5000, issue_date="2026-04-01"))
    _put(table, FeedScheduleFiscalDocument(pk=batch_id, sk="FeedScheduleFiscalDocument|BBB", fiscal_document_number="BBB", status="used", product_code="130871", actual_amount_kg=8000, issue_date="2026-03-20"))

    import lmjm.get_feed_schedule_fiscal_documents as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_apigw_event(batch_id), None)
    assert result["statusCode"] == 200

    body = json.loads(result["body"])
    assert len(body) == 2
    # Sorted descending by issue_date
    assert body[0]["fiscal_document_number"] == "AAA"  # 2026-04-01
    assert body[1]["fiscal_document_number"] == "BBB"  # 2026-03-20


# ── GetRawMaterialTypes ──────────────────────────────────────────────────────────


@mock_aws
def test_get_raw_material_types_returns_all() -> None:
    """Requirement 11.4: Returns all RawMaterialType entries."""
    table = _create_table()

    _put(table, RawMaterialType(pk="RAW_MATERIAL_TYPE", sk="RawMaterialType|130906", code="130906", description="ST06", category="feed"))
    _put(table, RawMaterialType(pk="RAW_MATERIAL_TYPE", sk="RawMaterialType|130871", code="130871", description="ST02", category="feed"))
    _put(table, RawMaterialType(pk="RAW_MATERIAL_TYPE", sk="RawMaterialType|200001", code="200001", description="Amoxicillin", category="medicine"))

    import lmjm.get_raw_material_types as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)
    assert result["statusCode"] == 200

    body = json.loads(result["body"])
    assert len(body) == 3
    codes = {entry["code"] for entry in body}
    assert codes == {"130906", "130871", "200001"}
