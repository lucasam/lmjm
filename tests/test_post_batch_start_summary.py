"""Unit tests for PostBatchStartSummaryLambda.

Validates:
- Requirement 8.16: Compute aggregation from PigTruckArrival records and update Batch
- Requirement 8.17: Update Batch status to "in_progress" and return 201
- Requirement 8.18: Return 400 if no pig truck arrivals exist
- Requirement 7.11: Start summary stored as attributes on Batch record
- Requirement 7.29: Compute total_animal_count, average_start_date, distinct_origin_count, origin_types
"""

import importlib
import json
from decimal import Decimal
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.model import Batch, PigTruckArrival
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize


def _decimal_safe_serialize(obj: object) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    # Patch serialize_to_dict in batch_repo to produce Decimal-safe output for moto
    monkeypatch.setattr("lmjm.repo.batch_repo.serialize_to_dict", _decimal_safe_serialize)


def _create_table() -> Any:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
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


def _seed_batch(table: Any) -> None:
    _put(
        table,
        Batch(pk="batch-1", sk="Batch", status="created", supply_id=100, module_id="MODULE#1"),
    )


def _seed_arrivals(table: Any) -> None:
    _put(
        table,
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|20250201|001",
            animal_count=100,
            sex="Male",
            arrival_date="2025-02-01",
            pig_age_days=30,
            origin_name="Farm A",
            origin_type="UPL",
        ),
    )
    _put(
        table,
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|20250205|001",
            animal_count=150,
            sex="Female",
            arrival_date="2025-02-05",
            pig_age_days=28,
            origin_name="Farm B",
            origin_type="Creche",
        ),
    )
    _put(
        table,
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|20250210|001",
            animal_count=80,
            sex="Male",
            arrival_date="2025-02-10",
            pig_age_days=35,
            origin_name="Farm A",
            origin_type="UPL",
        ),
    )


@mock_aws
def test_start_summary_computes_and_updates_batch() -> None:
    """Requirement 8.16, 8.17, 7.29: Compute summary from arrivals, set status in_progress, return 201."""
    table = _create_table()
    _seed_batch(table)
    _seed_arrivals(table)

    import lmjm.post_batch_start_summary as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])

    # total_animal_count = 100 + 150 + 80 = 330
    assert body["total_animal_count"] == 330

    # average_start_date: mean of 2025-02-01, 2025-02-05, 2025-02-10
    # ordinals: 738917, 738921, 738926 → avg = 738921.33 → round = 738921 → 2025-02-05
    assert body["average_start_date"] == "2025-02-05"

    # distinct_origin_count: Farm A, Farm B → 2
    assert body["distinct_origin_count"] == 2

    # origin_types: UPL, Creche (sorted)
    assert body["origin_types"] == ["Creche", "UPL"]

    # status updated to in_progress
    assert body["status"] == "in_progress"


@mock_aws
def test_start_summary_returns_400_when_no_arrivals() -> None:
    """Requirement 8.18: Return 400 if batch has no pig truck arrivals."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_batch_start_summary as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert body["message"] == "No pig truck arrivals recorded for this batch"


@mock_aws
def test_start_summary_returns_404_when_batch_not_found() -> None:
    """Return 404 when batch_id does not exist."""
    _create_table()

    import lmjm.post_batch_start_summary as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "nonexistent"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Batch not found"


@mock_aws
def test_start_summary_single_arrival() -> None:
    """Verify computation with a single arrival record."""
    table = _create_table()
    _seed_batch(table)
    _put(
        table,
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|20250301|001",
            animal_count=200,
            sex="Female",
            arrival_date="2025-03-01",
            pig_age_days=25,
            origin_name="Farm X",
            origin_type="Creche",
        ),
    )

    import lmjm.post_batch_start_summary as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["total_animal_count"] == 200
    assert body["average_start_date"] == "2025-03-01"
    assert body["distinct_origin_count"] == 1
    assert body["origin_types"] == ["Creche"]
    assert body["status"] == "in_progress"
