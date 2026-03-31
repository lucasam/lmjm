"""Unit tests for pig write Lambda handlers.

Validates:
- Requirement 8.1: POST /pigs/modules/{module_id}/warehouses creates warehouse with 201
- Requirement 8.2: POST warehouse returns 400 for empty name
- Requirement 8.3: POST warehouse returns 400 for non-positive supported_animal_count
- Requirement 8.4: PUT /pigs/modules/{module_id}/warehouses/{warehouse_id} updates warehouse with 200
- Requirement 8.5: POST /pigs/batches creates batch with status "created" and returns 201
- Requirement 8.6: POST batch returns 404 when module not found
- Requirement 8.7: POST batch returns 400 when warehouse not in module
- Requirement 8.8: POST /pigs/batches/{batch_id}/feed-truck-arrivals creates arrival with 201
- Requirement 8.9: POST feed-truck-arrival returns 404 when batch not found
- Requirement 8.10: POST feed-truck-arrival returns 400 for invalid data
- Requirement 8.11: PUT /pigs/batches/{batch_id}/feed-schedule replaces schedule with 200
- Requirement 8.12: PUT feed-schedule returns 404 when batch not found
- Requirement 8.13: POST /pigs/batches/{batch_id}/pig-truck-arrivals creates arrival with 201
- Requirement 8.14: POST pig-truck-arrival returns 400 for invalid sex
- Requirement 8.15: POST pig-truck-arrival returns 400 for invalid origin_type
- Requirement 8.19: POST /pigs/batches/{batch_id}/mortalities creates mortality with 201
- Requirement 8.20: POST mortality returns 404 when batch not found
- Requirement 8.21: POST mortality returns 400 for invalid data
- Requirement 8.22: POST /pigs/batches/{batch_id}/medications creates medication with 201
- Requirement 8.23: POST medication returns 400 for empty medication_name
- Requirement 8.24: POST medication returns 400 for empty part_number
- Requirement 8.25: POST /pigs/batches/{batch_id}/medication-shots creates shot with 201
- Requirement 8.26: POST medication-shot returns 400 for non-existent medication
- Requirement 8.28: PUT /pigs/batches/{batch_id}/feed-consumption-plan replaces plan with 200
- Requirement 8.29: PUT feed-consumption-plan returns 400 for invalid day_number
- Requirement 8.31: POST /pigs/batches/{batch_id}/feed-balances creates balance with 201
- Requirement 8.32: POST feed-balance returns 400 for negative balance_kg
"""

import importlib
import json
from decimal import Decimal
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.model import Batch, FeedSchedule, Medication, Module, Warehouse
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize


def _decimal_safe_serialize(obj: object) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    # Patch serialize_to_dict in all repo modules that write to DynamoDB
    monkeypatch.setattr("lmjm.repo.batch_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.warehouse_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_schedule_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_truck_arrival_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.pig_truck_arrival_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.mortality_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.medication_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.medication_shot_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_consumption_plan_repo.serialize_to_dict", _decimal_safe_serialize)
    monkeypatch.setattr("lmjm.repo.feed_balance_repo.serialize_to_dict", _decimal_safe_serialize)


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


def _seed_module_with_warehouses(table: Any) -> None:
    _put(table, Module(pk="MODULE#1", sk="Module", module_number=1, name="Module 1"))
    _put(
        table,
        Warehouse(
            pk="MODULE#1", sk="Warehouse|w1", name="Barn A", area=100.0, supported_animal_count=50, silo_capacity=5000.0
        ),
    )


def _seed_batch(table: Any) -> None:
    _put(
        table,
        Batch(
            pk="batch-1",
            sk="Batch",
            status="created",
            supply_id=100,
            module_id="MODULE#1",
            pig_count=500,
            receive_date="2025-01-01",
        ),
    )


def _seed_batch_with_medication(table: Any) -> None:
    _seed_batch(table)
    _put(
        table,
        Medication(
            pk="batch-1",
            sk="Medication|med1",
            medication_name="Amoxicillin",
            expiration_date="2026-01-01",
            part_number="P001",
        ),
    )


# ── post_warehouse tests ────────────────────────────────────────────────────────


@mock_aws
def test_post_warehouse_returns_201_on_success() -> None:
    """Requirement 8.1: POST warehouse creates record and returns 201."""
    table = _create_table()
    _put(table, Module(pk="MODULE#1", sk="Module", module_number=1, name="Module 1"))

    import lmjm.post_warehouse as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"module_id": "MODULE#1"},
        "body": json.dumps({"name": "Barn C", "area": 150.0, "supported_animal_count": 60, "silo_capacity": 7000.0}),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["name"] == "Barn C"
    assert body["pk"] == "MODULE#1"
    assert body["supported_animal_count"] == 60


@mock_aws
def test_post_warehouse_returns_400_for_empty_name() -> None:
    """Requirement 8.2: POST warehouse returns 400 when name is empty."""
    _create_table()

    import lmjm.post_warehouse as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"module_id": "MODULE#1"},
        "body": json.dumps({"name": "", "supported_animal_count": 10}),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "name" in body["message"].lower()


@mock_aws
def test_post_warehouse_returns_400_for_non_positive_animal_count() -> None:
    """Requirement 8.3: POST warehouse returns 400 when supported_animal_count is not positive."""
    _create_table()

    import lmjm.post_warehouse as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"module_id": "MODULE#1"},
        "body": json.dumps({"name": "Barn D", "supported_animal_count": 0}),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "supported_animal_count" in body["message"]


# ── put_warehouse tests ─────────────────────────────────────────────────────────


@mock_aws
def test_put_warehouse_returns_200_on_success() -> None:
    """Requirement 8.4: PUT warehouse updates record and returns 200."""
    table = _create_table()
    _seed_module_with_warehouses(table)

    import lmjm.put_warehouse as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"module_id": "MODULE#1", "warehouse_id": "w1"},
        "body": json.dumps(
            {"name": "Barn A Updated", "area": 200.0, "supported_animal_count": 80, "silo_capacity": 9000.0}
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["name"] == "Barn A Updated"
    assert body["sk"] == "Warehouse|w1"


# ── post_batch tests ────────────────────────────────────────────────────────────


@mock_aws
def test_post_batch_returns_201_on_success() -> None:
    """Requirement 8.5: POST batch creates batch with status 'created' and returns 201."""
    table = _create_table()
    _seed_module_with_warehouses(table)

    import lmjm.post_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "body": json.dumps(
            {
                "supply_id": 100,
                "module_id": "MODULE#1",
                "warehouse_ids": ["Warehouse|w1"],
                "pig_count": 500,
                "receive_date": "20250101",
                "min_feed_stock_threshold": 1000.0,
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["status"] == "created"
    assert body["supply_id"] == 100
    assert body["receive_date"] == "2025-01-01"


@mock_aws
def test_post_batch_returns_404_for_missing_module() -> None:
    """Requirement 8.6: POST batch returns 404 when module_id does not exist."""
    _create_table()

    import lmjm.post_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "body": json.dumps(
            {
                "supply_id": 100,
                "module_id": "MODULE#99",
                "warehouse_ids": [],
                "pig_count": 500,
                "receive_date": "20250101",
                "min_feed_stock_threshold": 1000.0,
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Module not found"


@mock_aws
def test_post_batch_returns_400_for_invalid_warehouse() -> None:
    """Requirement 8.7: POST batch returns 400 when warehouse_id not in module."""
    table = _create_table()
    _seed_module_with_warehouses(table)

    import lmjm.post_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "body": json.dumps(
            {
                "supply_id": 100,
                "module_id": "MODULE#1",
                "warehouse_ids": ["Warehouse|nonexistent"],
                "pig_count": 500,
                "receive_date": "20250101",
                "min_feed_stock_threshold": 1000.0,
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "not found in module" in body["message"]


# ── post_feed_truck_arrival tests ────────────────────────────────────────────────


@mock_aws
def test_post_feed_truck_arrival_returns_201_on_success() -> None:
    """Requirement 8.8: POST feed-truck-arrival creates record and returns 201."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_feed_truck_arrival as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "receive_date": "20250115",
                "fiscal_document_number": "NF001",
                "actual_amount_kg": 1000.0,
                "feed_type": "starter",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["receive_date"] == "2025-01-15"
    assert body["feed_type"] == "starter"


@mock_aws
def test_post_feed_truck_arrival_returns_404_for_missing_batch() -> None:
    """Requirement 8.9: POST feed-truck-arrival returns 404 when batch not found."""
    _create_table()

    import lmjm.post_feed_truck_arrival as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "nonexistent"},
        "body": json.dumps(
            {
                "receive_date": "20250115",
                "fiscal_document_number": "NF001",
                "actual_amount_kg": 1000.0,
                "feed_type": "starter",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Batch not found"


@mock_aws
def test_post_feed_truck_arrival_returns_400_for_invalid_data() -> None:
    """Requirement 8.10: POST feed-truck-arrival returns 400 for empty fiscal_document_number."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_feed_truck_arrival as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "receive_date": "20250115",
                "fiscal_document_number": "",
                "actual_amount_kg": 1000.0,
                "feed_type": "starter",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "fiscal_document_number" in body["message"]


# ── put_feed_schedule tests ──────────────────────────────────────────────────────


@mock_aws
def test_put_feed_schedule_returns_200_on_success() -> None:
    """Requirement 8.11: PUT feed-schedule replaces all entries and returns 200."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.put_feed_schedule as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            [
                {"feed_type": "starter", "planned_date": "2025-01-10", "expected_amount_kg": 1000.0},
                {"feed_type": "grower", "planned_date": "2025-01-20", "expected_amount_kg": 2000.0},
            ]
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2


@mock_aws
def test_put_feed_schedule_returns_404_for_missing_batch() -> None:
    """Requirement 8.12: PUT feed-schedule returns 404 when batch not found."""
    _create_table()

    import lmjm.put_feed_schedule as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "nonexistent"},
        "body": json.dumps([]),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Batch not found"


# ── post_pig_truck_arrival tests ─────────────────────────────────────────────────


@mock_aws
def test_post_pig_truck_arrival_returns_201_on_success() -> None:
    """Requirement 8.13: POST pig-truck-arrival creates record and returns 201."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_pig_truck_arrival as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "animal_count": 100,
                "sex": "Male",
                "arrival_date": "20250201",
                "pig_age_days": 30,
                "origin_name": "Farm A",
                "origin_type": "UPL",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["animal_count"] == 100
    assert body["sex"] == "Male"
    assert body["arrival_date"] == "2025-02-01"


@mock_aws
def test_post_pig_truck_arrival_returns_400_for_invalid_sex() -> None:
    """Requirement 8.14: POST pig-truck-arrival returns 400 for invalid sex value."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_pig_truck_arrival as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "animal_count": 100,
                "sex": "Unknown",
                "arrival_date": "20250201",
                "pig_age_days": 30,
                "origin_name": "Farm A",
                "origin_type": "UPL",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "sex" in body["message"].lower()


@mock_aws
def test_post_pig_truck_arrival_returns_400_for_invalid_origin_type() -> None:
    """Requirement 8.15: POST pig-truck-arrival returns 400 for invalid origin_type."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_pig_truck_arrival as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "animal_count": 100,
                "sex": "Male",
                "arrival_date": "20250201",
                "pig_age_days": 30,
                "origin_name": "Farm A",
                "origin_type": "InvalidType",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "origin_type" in body["message"]


# ── post_mortality tests ─────────────────────────────────────────────────────────


@mock_aws
def test_post_mortality_returns_201_on_success() -> None:
    """Requirement 8.19: POST mortality creates record and returns 201."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_mortality as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "mortality_date": "20250301",
                "sex": "Male",
                "origin": "Farm A",
                "death_reason": "Disease",
                "reported_by": "user1",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["mortality_date"] == "2025-03-01"
    assert body["sex"] == "Male"
    assert body["death_reason"] == "Disease"


@mock_aws
def test_post_mortality_returns_404_for_missing_batch() -> None:
    """Requirement 8.20: POST mortality returns 404 when batch not found."""
    _create_table()

    import lmjm.post_mortality as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "nonexistent"},
        "body": json.dumps(
            {
                "mortality_date": "20250301",
                "sex": "Male",
                "origin": "Farm A",
                "death_reason": "Disease",
                "reported_by": "user1",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Batch not found"


@mock_aws
def test_post_mortality_returns_400_for_invalid_data() -> None:
    """Requirement 8.21: POST mortality returns 400 for empty death_reason."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_mortality as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "mortality_date": "20250301",
                "sex": "Male",
                "origin": "Farm A",
                "death_reason": "",
                "reported_by": "user1",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "death_reason" in body["message"]


# ── post_medication tests ────────────────────────────────────────────────────────


@mock_aws
def test_post_medication_returns_201_on_success() -> None:
    """Requirement 8.22: POST medication creates record and returns 201."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_medication as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "medication_name": "Amoxicillin",
                "expiration_date": "20260101",
                "part_number": "P001",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["medication_name"] == "Amoxicillin"
    assert body["expiration_date"] == "2026-01-01"


@mock_aws
def test_post_medication_returns_400_for_empty_name() -> None:
    """Requirement 8.23: POST medication returns 400 for empty medication_name."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_medication as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "medication_name": "",
                "expiration_date": "20260101",
                "part_number": "P001",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "medication_name" in body["message"]


@mock_aws
def test_post_medication_returns_400_for_empty_part_number() -> None:
    """Requirement 8.24: POST medication returns 400 for empty part_number."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_medication as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "medication_name": "Amoxicillin",
                "expiration_date": "20260101",
                "part_number": "",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "part_number" in body["message"]


# ── post_medication_shot tests ───────────────────────────────────────────────────


@mock_aws
def test_post_medication_shot_returns_201_on_success() -> None:
    """Requirement 8.25: POST medication-shot creates record and returns 201."""
    table = _create_table()
    _seed_batch_with_medication(table)

    import lmjm.post_medication_shot as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "medication_name": "Amoxicillin",
                "shot_count": 10,
                "date": "20250301",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["medication_name"] == "Amoxicillin"
    assert body["shot_count"] == 10
    assert body["date"] == "2025-03-01"


@mock_aws
def test_post_medication_shot_returns_400_for_nonexistent_medication() -> None:
    """Requirement 8.26: POST medication-shot returns 400 when medication_name doesn't exist."""
    table = _create_table()
    _seed_batch(table)  # No medications seeded

    import lmjm.post_medication_shot as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "medication_name": "NonExistent",
                "shot_count": 10,
                "date": "20250301",
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "medication_name" in body["message"]


# ── put_feed_consumption_plan tests ──────────────────────────────────────────────


@mock_aws
def test_put_feed_consumption_plan_returns_200_on_success() -> None:
    """Requirement 8.28: PUT feed-consumption-plan replaces all entries and returns 200."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.put_feed_consumption_plan as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            [
                {"day_number": 1, "expected_grams_per_animal": 300.0},
                {"day_number": 2, "expected_grams_per_animal": 320.0},
            ]
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2
    assert body[0]["day_number"] == 1
    assert body[1]["day_number"] == 2


@mock_aws
def test_put_feed_consumption_plan_returns_400_for_invalid_day_number() -> None:
    """Requirement 8.29: PUT feed-consumption-plan returns 400 for day_number out of range."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.put_feed_consumption_plan as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            [
                {"day_number": 0, "expected_grams_per_animal": 300.0},
            ]
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "day_number" in body["message"]


# ── post_feed_balance tests ──────────────────────────────────────────────────────


@mock_aws
def test_post_feed_balance_returns_201_on_success() -> None:
    """Requirement 8.31: POST feed-balance creates record and returns 201."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_feed_balance as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "measurement_date": "20250315",
                "balance_kg": 5000.0,
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["measurement_date"] == "2025-03-15"
    assert body["balance_kg"] == 5000.0


@mock_aws
def test_post_feed_balance_returns_400_for_negative_balance() -> None:
    """Requirement 8.32: POST feed-balance returns 400 for negative balance_kg."""
    table = _create_table()
    _seed_batch(table)

    import lmjm.post_feed_balance as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"batch_id": "batch-1"},
        "body": json.dumps(
            {
                "measurement_date": "20250315",
                "balance_kg": -100.0,
            }
        ),
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "balance_kg" in body["message"]
