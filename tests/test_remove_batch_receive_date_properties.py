"""Property-based tests for removing Batch receive_date.

Feature: remove-batch-receive-date (bugfix)

**Validates: Requirements 1.1, 1.3, 2.1, 2.3**
"""

import importlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from lmjm.model import Batch, Module
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize


def _decimal_safe_serialize(obj: object) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj)
    return json.loads(json.dumps(d, default=str), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    monkeypatch.setattr("lmjm.repo.batch_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_consumption_plan_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_truck_arrival_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_schedule_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_schedule_fiscal_document_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.raw_material_type_repo.serialize_to_dict", _decimal_safe_serialize)


def _get_or_create_table() -> Any:
    """Get existing table or create it (safe for repeated calls within same mock context)."""
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    try:
        table = dynamodb.Table("lmjm")
        table.load()
        # Clear all items for a fresh state
        scan = table.scan()
        with table.batch_writer() as batch:
            for item in scan.get("Items", []):
                batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
        return table
    except Exception:
        pass
    table = dynamodb.create_table(
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
    return table


def _put(table: Any, obj: object) -> None:
    table.put_item(Item=_decimal_safe_serialize(obj))


# ── Strategies ───────────────────────────────────────────────────────────────────

# Valid supply_id (positive integers)
supply_id_st = st.integers(min_value=1, max_value=99999)

# Valid min_feed_stock_threshold (non-negative)
threshold_st = st.integers(min_value=0, max_value=100000)

# Day numbers for feed consumption plan (1–130)
day_number_st = st.integers(min_value=1, max_value=130)

# Valid date strings in YYYY-MM-DD format (for average_start_date)
date_st = st.dates(
    min_value=datetime(2020, 1, 1).date(),
    max_value=datetime(2030, 12, 31).date(),
).map(lambda d: d.strftime("%Y-%m-%d"))


# ── Property 1a: POST /batches without receive_date should return 201 ────────────
# Bug Condition: POST /batches requires receive_date (it shouldn't)
# On UNFIXED code this test FAILS because receive_date is a required field in PostBatchRequest


@mock_aws
@given(supply_id=supply_id_st, threshold=threshold_st)
@settings(max_examples=50, deadline=None)
def test_post_batch_without_receive_date_should_succeed(supply_id: int, threshold: int) -> None:
    """Property 1a: POST /batches without receive_date should return 201.

    For any valid batch creation payload that omits receive_date,
    POST /batches should return 201 with status 'created'.

    On UNFIXED code, this FAILS because receive_date is required in PostBatchRequest.

    **Validates: Requirements 1.1, 2.1**
    """
    table = _get_or_create_table()
    _put(table, Module(pk="MODULE#1", sk="Module", module_number=1, name="Module 1"))

    import lmjm.post_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "body": json.dumps(
            {
                "supply_id": supply_id,
                "module_id": "MODULE#1",
                "min_feed_stock_threshold": threshold,
                # NOTE: receive_date intentionally omitted
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201, (
        f"Expected 201 but got {result['statusCode']}. "
        f"POST /batches should succeed without receive_date. "
        f"Response: {result.get('body', '')}"
    )
    body = json.loads(result["body"])
    assert body["status"] == "created"
    assert "receive_date" not in body, "Batch response should not contain receive_date"


# ── Property 1b: PUT feed-consumption-plan should use average_start_date ─────────
# Bug Condition: plan_date is computed from batch.receive_date instead of batch.average_start_date
# On UNFIXED code this FAILS because the code reads batch.receive_date for date computation


@mock_aws
@given(day_number=day_number_st, avg_start_date=date_st)
@settings(max_examples=50)
def test_feed_consumption_plan_uses_average_start_date(day_number: int, avg_start_date: str) -> None:
    """Property 1b: PUT feed-consumption-plan should compute plan_date from average_start_date.

    For any batch with average_start_date set, the feed consumption plan
    should compute plan_date = average_start_date + timedelta(days=day_number),
    NOT from receive_date.

    On UNFIXED code, this FAILS because the code uses batch.receive_date
    for the date computation instead of batch.average_start_date.

    **Validates: Requirements 1.3, 2.3**
    """
    table = _get_or_create_table()

    # Seed a batch with average_start_date set
    _put(
        table,
        Batch(
            pk="batch-1",
            sk="Batch",
            status="created",
            supply_id=100,
            module_id="MODULE#1",
            average_start_date=avg_start_date,
        ),
    )

    import lmjm.put_feed_consumption_plan as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            [
                {"day_number": day_number, "expected_kg_per_animal": 0.300},
            ]
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200, (
        f"Expected 200 but got {result['statusCode']}. Response: {result.get('body', '')}"
    )

    body = json.loads(result["body"])
    assert len(body) == 1

    actual_date = body[0]["date"]
    expected_date = (datetime.strptime(avg_start_date, "%Y-%m-%d") + timedelta(days=day_number)).strftime("%Y-%m-%d")

    assert actual_date == expected_date, (
        f"plan_date should be average_start_date + {day_number} days = {expected_date}, "
        f"but got {actual_date}. "
        f"The code is likely using receive_date (2020-01-01) instead of average_start_date ({avg_start_date})."
    )


# ── Strategies for Preservation Tests ────────────────────────────────────────────

# Valid receive_date strings in YYYYMMDD format for FeedTruckArrival
receive_date_yyyymmdd_st = st.dates(
    min_value=datetime(2020, 1, 1).date(),
    max_value=datetime(2030, 12, 31).date(),
).map(lambda d: d.strftime("%Y%m%d"))

# Valid batch statuses
batch_status_st = st.sampled_from(["created", "in_progress", "delivered"])


# ── Property 2a: FeedTruckArrival receive_date preservation ──────────────────────
# Preservation: POST feed-truck-arrival with receive_date in YYYYMMDD format
# should return 201 and the response receive_date should match the parsed datetime.
# This must PASS on UNFIXED code (confirms baseline behavior to preserve).


@mock_aws
@given(receive_date_raw=receive_date_yyyymmdd_st)
@settings(max_examples=50, deadline=None)
def test_feed_truck_arrival_receive_date_preserved(receive_date_raw: str) -> None:
    """Property 2a: POST feed-truck-arrival preserves receive_date.

    For all valid FeedTruckArrival payloads with any receive_date string
    in YYYYMMDD format, POST feed-truck-arrival should return 201 and
    the response receive_date should match the parsed datetime.

    **Validates: Requirements 3.1**
    """
    table = _get_or_create_table()

    # Seed a batch (FeedTruckArrival requires an existing batch)
    _put(
        table,
        Batch(
            pk="batch-1",
            sk="Batch",
            status="created",
            supply_id=100,
            module_id="MODULE#1",
        ),
    )

    import lmjm.post_feed_truck_arrival as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "receive_date": receive_date_raw,
                "fiscal_document_number": "NF001",
                "actual_amount_kg": 500,
                "feed_type": "starter",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201, (
        f"Expected 201 but got {result['statusCode']}. "
        f"POST feed-truck-arrival should succeed with receive_date={receive_date_raw}. "
        f"Response: {result.get('body', '')}"
    )

    body = json.loads(result["body"])

    # parse_datetime_input for YYYYMMDD returns "YYYY-MM-DDTHH:MM" (with T00:00)
    expected_stored = datetime.strptime(receive_date_raw, "%Y%m%d").strftime("%Y-%m-%dT%H:%M")
    assert body["receive_date"] == expected_stored, (
        f"FeedTruckArrival receive_date should be '{expected_stored}' "
        f"but got '{body['receive_date']}' for input '{receive_date_raw}'"
    )


# ── Property 2b: Non-receive_date Batch update preservation ─────────────────────
# Preservation: PUT /batches/{id} with non-receive_date fields should return 200
# and the response should reflect the updated fields.
# This must PASS on UNFIXED code (confirms baseline behavior to preserve).


@mock_aws
@given(
    status=batch_status_st,
    supply_id=st.integers(min_value=1, max_value=99999),
    threshold=st.integers(min_value=0, max_value=100000),
)
@settings(max_examples=50, deadline=None)
def test_put_batch_non_receive_date_fields_preserved(status: str, supply_id: int, threshold: int) -> None:
    """Property 2b: PUT /batches/{id} preserves non-receive_date fields.

    For all valid non-receive_date Batch update payloads (status in
    {created, in_progress, delivered}, supply_id > 0,
    min_feed_stock_threshold >= 0), PUT /batches/{id} should return 200
    and the response should reflect the updated fields.

    **Validates: Requirements 3.3**
    """
    table = _get_or_create_table()

    # Seed a batch with initial values
    _put(
        table,
        Batch(
            pk="batch-1",
            sk="Batch",
            status="created",
            supply_id=1,
            module_id="MODULE#1",
            min_feed_stock_threshold=0,
        ),
    )

    import lmjm.put_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "status": status,
                "supply_id": supply_id,
                "min_feed_stock_threshold": threshold,
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200, (
        f"Expected 200 but got {result['statusCode']}. "
        f"PUT /batches should succeed for non-receive_date fields. "
        f"Response: {result.get('body', '')}"
    )

    body = json.loads(result["body"])
    assert body["status"] == status, f"Expected status '{status}' but got '{body['status']}'"
    assert body["supply_id"] == supply_id, f"Expected supply_id {supply_id} but got {body['supply_id']}"
    assert body["min_feed_stock_threshold"] == threshold, (
        f"Expected min_feed_stock_threshold {threshold} but got {body['min_feed_stock_threshold']}"
    )
