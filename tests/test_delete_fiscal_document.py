"""Unit tests for the DeleteFiscalDocument Lambda.

A fiscal document can only be deleted when it has NOT been converted into a
FeedTruckArrival (i.e. no arrival in the same batch references its
fiscal_document_number).
"""

import importlib
import json
from decimal import Decimal
from typing import Any

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_aws

from lmjm.model import FeedScheduleFiscalDocument, FeedTruckArrival, FiscalDocument
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize

BATCH_PK = "batch-123"
FISCAL_DOC_NUMBER = "833871"
DOC_SK = f"FiscalDocument|{FISCAL_DOC_NUMBER}"
FSFD_SK = f"FeedScheduleFiscalDocument|{FISCAL_DOC_NUMBER}"


def _decimal_safe_serialize(obj: object, schema: Any = None) -> dict[str, Any]:
    d = _original_serialize(obj, schema)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    for repo_mod in [
        "lmjm.repo.fiscal_document_repo",
        "lmjm.repo.feed_schedule_fiscal_document_repo",
        "lmjm.repo.feed_truck_arrival_repo",
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


def _seed_doc(table: Any, sk: str = DOC_SK) -> None:
    _put(
        table,
        FiscalDocument(
            pk=BATCH_PK,
            sk=sk,
            fiscal_document_number=FISCAL_DOC_NUMBER,
            issue_date="2026-03-26",
            actual_amount_kg=15980,
            product_code="130906",
            product_description="Feed",
            supplier_name="ACME",
            order_number="123",
        ),
    )


def _seed_fsfd(table: Any) -> None:
    _put(
        table,
        FeedScheduleFiscalDocument(
            pk=BATCH_PK,
            sk=FSFD_SK,
            fiscal_document_number=FISCAL_DOC_NUMBER,
            status="pending",
            product_code="130906",
            actual_amount_kg=15980,
            issue_date="2026-03-26",
        ),
    )


def _seed_arrival(table: Any) -> None:
    _put(
        table,
        FeedTruckArrival(
            pk=BATCH_PK,
            sk="FeedTruckArrival|202603261200|abc",
            receive_date="2026-03-26 12:00",
            fiscal_document_number=FISCAL_DOC_NUMBER,
            actual_amount_kg=15980,
            feed_type="130906",
        ),
    )


def _event(pk: str, sk: str) -> dict[str, Any]:
    return {"body": json.dumps({"pk": pk, "sk": sk})}


def _query(table: Any, pk: str, sk_prefix: str) -> list[dict[str, Any]]:
    resp = table.query(KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(sk_prefix))
    return resp["Items"]


@mock_aws
def test_delete_succeeds_when_not_converted() -> None:
    table = _create_table()
    _seed_doc(table)
    _seed_fsfd(table)

    import lmjm.delete_fiscal_document as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event(BATCH_PK, DOC_SK), None)
    assert result["statusCode"] == 200

    # Both the fiscal document and its linked FSFD are removed
    assert _query(table, BATCH_PK, "FiscalDocument|") == []
    assert _query(table, BATCH_PK, "FeedScheduleFiscalDocument|") == []


@mock_aws
def test_delete_blocked_when_converted_to_arrival() -> None:
    table = _create_table()
    _seed_doc(table)
    _seed_fsfd(table)
    _seed_arrival(table)

    import lmjm.delete_fiscal_document as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event(BATCH_PK, DOC_SK), None)
    assert result["statusCode"] == 409

    # Nothing removed
    assert len(_query(table, BATCH_PK, "FiscalDocument|")) == 1
    assert len(_query(table, BATCH_PK, "FeedScheduleFiscalDocument|")) == 1


@mock_aws
def test_delete_returns_404_when_missing() -> None:
    table = _create_table()

    import lmjm.delete_fiscal_document as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event(BATCH_PK, DOC_SK), None)
    assert result["statusCode"] == 404


@mock_aws
def test_delete_returns_400_when_pk_or_sk_missing() -> None:
    _create_table()

    import lmjm.delete_fiscal_document as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event("", DOC_SK), None)["statusCode"] == 400
    assert mod.lambda_handler(_event(BATCH_PK, ""), None)["statusCode"] == 400
