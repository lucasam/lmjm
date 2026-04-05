"""Unit tests for modified PostFeedTruckArrival Lambda.

Validates: Requirements 9.1, 9.2, 9.3
"""

import importlib
import json
from decimal import Decimal
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.model import Batch, FeedSchedule, FeedScheduleFiscalDocument
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize

BATCH_PK = "batch-123"
SUPPLY_ID = 112053764
FISCAL_DOC_NUMBER = "833871"


def _decimal_safe_serialize(obj: object, schema: Any = None) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj, schema)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    for repo_mod in [
        "lmjm.repo.batch_repo",
        "lmjm.repo.feed_truck_arrival_repo",
        "lmjm.repo.feed_schedule_repo",
        "lmjm.repo.feed_schedule_fiscal_document_repo",
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


def _seed_batch(table: Any) -> None:
    _put(table, Batch(pk=BATCH_PK, sk="Batch", status="created", supply_id=SUPPLY_ID, module_id="MODULE#1"))


def _seed_feed_schedule(table: Any) -> None:
    _put(
        table,
        FeedSchedule(
            pk=BATCH_PK,
            sk="FeedSchedule|sched-1",
            feed_type="130906",
            planned_date="2026-03-28",
            expected_amount_kg=16000,
            status="scheduled",
        ),
    )


def _seed_pending_fsfd(table: Any) -> None:
    _put(
        table,
        FeedScheduleFiscalDocument(
            pk=BATCH_PK,
            sk=f"FeedScheduleFiscalDocument|{FISCAL_DOC_NUMBER}",
            fiscal_document_number=FISCAL_DOC_NUMBER,
            feed_schedule_id="FeedSchedule|sched-1",
            status="pending",
            product_code="130906",
            actual_amount_kg=15980,
            issue_date="2026-03-26",
        ),
    )


def _seed_used_fsfd(table: Any) -> None:
    _put(
        table,
        FeedScheduleFiscalDocument(
            pk=BATCH_PK,
            sk=f"FeedScheduleFiscalDocument|{FISCAL_DOC_NUMBER}",
            fiscal_document_number=FISCAL_DOC_NUMBER,
            feed_schedule_id="FeedSchedule|sched-1",
            status="used",
            product_code="130906",
            actual_amount_kg=15980,
            issue_date="2026-03-26",
        ),
    )


def _apigw_event(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "pathParameters": {"batch_id": BATCH_PK},
        "body": json.dumps(body),
    }


def _query_items(table: Any, pk: str, sk_prefix: str) -> list[dict[str, Any]]:
    from boto3.dynamodb.conditions import Key

    resp = table.query(KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(sk_prefix))
    return resp["Items"]


# ── Test 1: Pending FeedScheduleFiscalDocument → status updated to "used" ────


@mock_aws
def test_pending_fsfd_updated_to_used_after_arrival() -> None:
    """Requirement 9.1: Pending FeedScheduleFiscalDocument status updated to 'used' on FeedTruckArrival creation."""
    table = _create_table()
    _seed_batch(table)
    _seed_feed_schedule(table)
    _seed_pending_fsfd(table)

    import lmjm.post_feed_truck_arrival as mod

    importlib.reload(mod)

    event = _apigw_event(
        {
            "receive_date": "20260326",
            "fiscal_document_number": FISCAL_DOC_NUMBER,
            "actual_amount_kg": 15980,
            "feed_type": "130906",
            "feed_schedule_id": "FeedSchedule|sched-1",
        }
    )
    result = mod.lambda_handler(event, None)
    assert result["statusCode"] == 201

    # FeedTruckArrival created
    arrivals = _query_items(table, BATCH_PK, "FeedTruckArrival|")
    assert len(arrivals) == 1

    # FeedScheduleFiscalDocument status updated to "used"
    fsfds = _query_items(table, BATCH_PK, "FeedScheduleFiscalDocument|")
    assert len(fsfds) == 1
    assert fsfds[0]["status"] == "used"


# ── Test 2: No FeedScheduleFiscalDocument → FeedTruckArrival still created ───


@mock_aws
def test_arrival_created_when_no_fsfd_exists() -> None:
    """Requirement 9.3: FeedTruckArrival created even when no FeedScheduleFiscalDocument exists."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_feed_truck_arrival as mod

    importlib.reload(mod)

    event = _apigw_event(
        {
            "receive_date": "20260326",
            "fiscal_document_number": "999999",
            "actual_amount_kg": 10000,
            "feed_type": "130906",
        }
    )
    result = mod.lambda_handler(event, None)
    assert result["statusCode"] == 201

    # FeedTruckArrival created
    arrivals = _query_items(table, BATCH_PK, "FeedTruckArrival|")
    assert len(arrivals) == 1
    assert arrivals[0]["fiscal_document_number"] == "999999"

    # No FeedScheduleFiscalDocument items
    fsfds = _query_items(table, BATCH_PK, "FeedScheduleFiscalDocument|")
    assert len(fsfds) == 0


# ── Test 3: Non-pending FeedScheduleFiscalDocument → status NOT changed ──────


@mock_aws
def test_arrival_created_fsfd_not_pending_status_unchanged() -> None:
    """Requirement 9.3: FeedTruckArrival created, non-pending FeedScheduleFiscalDocument status not changed."""
    table = _create_table()
    _seed_batch(table)
    _seed_feed_schedule(table)
    _seed_used_fsfd(table)

    import lmjm.post_feed_truck_arrival as mod

    importlib.reload(mod)

    event = _apigw_event(
        {
            "receive_date": "20260326",
            "fiscal_document_number": FISCAL_DOC_NUMBER,
            "actual_amount_kg": 15980,
            "feed_type": "130906",
            "feed_schedule_id": "FeedSchedule|sched-1",
        }
    )
    result = mod.lambda_handler(event, None)
    assert result["statusCode"] == 201

    # FeedTruckArrival created
    arrivals = _query_items(table, BATCH_PK, "FeedTruckArrival|")
    assert len(arrivals) == 1

    # FeedScheduleFiscalDocument status remains "used" (not changed)
    fsfds = _query_items(table, BATCH_PK, "FeedScheduleFiscalDocument|")
    assert len(fsfds) == 1
    assert fsfds[0]["status"] == "used"
