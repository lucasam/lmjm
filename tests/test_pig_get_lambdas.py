"""Unit tests for pig GET Lambda handlers.

Validates:
- Requirement 6.1: GET /pigs/modules returns all modules
- Requirement 6.2: GET /pigs/modules/{module_id} returns module
- Requirement 6.3: GET /pigs/modules/{module_id} returns 404 if not found
- Requirement 6.4: GET /pigs/batches returns all batches
- Requirement 6.5: GET /pigs/batches/{batch_id} returns batch with status
- Requirement 6.6: GET /pigs/batches/{batch_id} returns 404 if not found
- Requirement 6.7: GET /pigs/batches/{batch_id}/feed-schedule returns feed schedule entries
- Requirement 6.8: GET /pigs/batches/{batch_id}/pig-truck-arrivals sorted by arrival_date asc
- Requirement 6.9: GET /pigs/batches/{batch_id}/feed-truck-arrivals sorted by receive_date asc
- Requirement 6.10: GET /pigs/batches/{batch_id} includes start summary fields if computed
- Requirement 6.11: GET /pigs/batches/{batch_id} returns start summary fields absent if not computed
- Requirement 6.12: GET /pigs/batches/{batch_id}/mortalities sorted by mortality_date desc
- Requirement 6.13: GET /pigs/batches/{batch_id}/medications returns medications for batch
- Requirement 6.14: GET /pigs/batches/{batch_id}/medication-shots with optional month filter
- Requirement 6.15: GET /pigs/batches/{batch_id}/feed-consumption-plan sorted by day_number asc
- Requirement 6.16: GET /pigs/batches/{batch_id}/feed-balances sorted by measurement_date asc
"""

import importlib
import json
from decimal import Decimal
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")


def _serialize_decimal_safe(obj: object) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


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
    """Put a dataclass item into DynamoDB with Decimal-safe serialization."""
    table.put_item(Item=_serialize_decimal_safe(obj))


# ── Seed helpers ────────────────────────────────────────────────────────────────

from lmjm.model import (
    Batch,
    FeedBalance,
    FeedConsumptionPlan,
    FeedSchedule,
    FeedTruckArrival,
    Medication,
    MedicationShot,
    Module,
    Mortality,
    PigTruckArrival,
)


def _seed_modules(table: Any) -> None:
    _put(table, Module(pk="MODULE#1", sk="Module", module_number=1, name="Module 1"))
    _put(table, Module(pk="MODULE#2", sk="Module", module_number=2, name="Module 2"))


def _seed_batches(table: Any) -> None:
    _put(table, Batch(pk="batch-1", sk="Batch", status="created", supply_id=100, module_id="MODULE#1", pig_count=500))
    _put(
        table, Batch(pk="batch-2", sk="Batch", status="in_progress", supply_id=200, module_id="MODULE#2", pig_count=300)
    )


def _seed_batch_with_start_summary(table: Any) -> None:
    _put(
        table,
        Batch(
            pk="batch-summary",
            sk="Batch",
            status="in_progress",
            supply_id=300,
            module_id="MODULE#1",
            pig_count=400,
            total_animal_count=250,
            average_start_date="2025-02-05",
            distinct_origin_count=2,
            origin_types=["UPL", "Creche"],
        ),
    )


def _seed_feed_schedule(table: Any) -> None:
    _put(
        table,
        FeedSchedule(
            pk="batch-1",
            sk="FeedSchedule|fs1",
            feed_type="starter",
            planned_date="2025-01-10",
            expected_amount_kg=1000.0,
        ),
    )
    _put(
        table,
        FeedSchedule(
            pk="batch-1",
            sk="FeedSchedule|fs2",
            feed_type="grower",
            planned_date="2025-01-20",
            expected_amount_kg=2000.0,
        ),
    )


def _seed_feed_truck_arrivals(table: Any) -> None:
    _put(
        table,
        FeedTruckArrival(
            pk="batch-1",
            sk="FeedTruckArrival|2025-01-15|001",
            receive_date="2025-01-15",
            fiscal_document_number="NF001",
            actual_amount_kg=1000.0,
            feed_type="starter",
        ),
    )
    _put(
        table,
        FeedTruckArrival(
            pk="batch-1",
            sk="FeedTruckArrival|2025-01-10|001",
            receive_date="2025-01-10",
            fiscal_document_number="NF002",
            actual_amount_kg=2000.0,
            feed_type="grower",
        ),
    )
    _put(
        table,
        FeedTruckArrival(
            pk="batch-1",
            sk="FeedTruckArrival|2025-01-20|001",
            receive_date="2025-01-20",
            fiscal_document_number="NF003",
            actual_amount_kg=1500.0,
            feed_type="finisher",
        ),
    )


def _seed_pig_truck_arrivals(table: Any) -> None:
    _put(
        table,
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|2025-02-05|001",
            animal_count=100,
            sex="Male",
            arrival_date="2025-02-05",
            pig_age_days=30,
            origin_name="Farm A",
            origin_type="UPL",
        ),
    )
    _put(
        table,
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|2025-02-01|001",
            animal_count=150,
            sex="Female",
            arrival_date="2025-02-01",
            pig_age_days=28,
            origin_name="Farm B",
            origin_type="Creche",
        ),
    )
    _put(
        table,
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|2025-02-10|001",
            animal_count=80,
            sex="Male",
            arrival_date="2025-02-10",
            pig_age_days=35,
            origin_name="Farm C",
            origin_type="UPL",
        ),
    )


def _seed_mortalities(table: Any) -> None:
    _put(
        table,
        Mortality(
            pk="batch-1",
            sk="Mortality|2025-03-01|001",
            mortality_date="2025-03-01",
            sex="Male",
            origin="Farm A",
            death_reason="Disease",
            reported_by="user1",
        ),
    )
    _put(
        table,
        Mortality(
            pk="batch-1",
            sk="Mortality|2025-03-10|001",
            mortality_date="2025-03-10",
            sex="Female",
            origin="Farm B",
            death_reason="Injury",
            reported_by="user2",
        ),
    )
    _put(
        table,
        Mortality(
            pk="batch-1",
            sk="Mortality|2025-03-05|001",
            mortality_date="2025-03-05",
            sex="Male",
            origin="Farm A",
            death_reason="Unknown",
            reported_by="user1",
        ),
    )


def _seed_medications(table: Any) -> None:
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
    _put(
        table,
        Medication(
            pk="batch-1",
            sk="Medication|med2",
            medication_name="Ivermectin",
            expiration_date="2026-06-01",
            part_number="P002",
        ),
    )


def _seed_medication_shots(table: Any) -> None:
    _put(
        table,
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-03-01|med1",
            medication_name="Amoxicillin",
            shot_count=10,
            date="2025-03-01",
        ),
    )
    _put(
        table,
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-03-15|med1",
            medication_name="Amoxicillin",
            shot_count=8,
            date="2025-03-15",
        ),
    )
    _put(
        table,
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-04-01|med1",
            medication_name="Amoxicillin",
            shot_count=5,
            date="2025-04-01",
        ),
    )


def _seed_feed_consumption_plan(table: Any) -> None:
    _put(
        table,
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|3", day_number=3, expected_grams_per_animal=350.0, date="2025-01-04"
        ),
    )
    _put(
        table,
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|1", day_number=1, expected_grams_per_animal=300.0, date="2025-01-02"
        ),
    )
    _put(
        table,
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|2", day_number=2, expected_grams_per_animal=320.0, date="2025-01-03"
        ),
    )


def _seed_feed_balances(table: Any) -> None:
    _put(table, FeedBalance(pk="batch-1", sk="FeedBalance|20250315", measurement_date="2025-03-15", balance_kg=5000.0))
    _put(table, FeedBalance(pk="batch-1", sk="FeedBalance|20250310", measurement_date="2025-03-10", balance_kg=8000.0))
    _put(table, FeedBalance(pk="batch-1", sk="FeedBalance|20250320", measurement_date="2025-03-20", balance_kg=3000.0))


# ── get_modules tests ───────────────────────────────────────────────────────────


@mock_aws
def test_get_modules_returns_all_modules() -> None:
    """Requirement 6.1: GET /pigs/modules returns JSON array of all modules."""
    table = _create_table()
    _seed_modules(table)

    import lmjm.get_modules as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2
    names = {m["name"] for m in body}
    assert names == {"Module 1", "Module 2"}


@mock_aws
def test_get_modules_returns_empty_list_when_no_modules() -> None:
    """Requirement 6.1: Returns empty array when no modules exist."""
    _create_table()

    import lmjm.get_modules as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == []


# ── get_module tests ────────────────────────────────────────────────────────────


@mock_aws
def test_get_module_returns_module() -> None:
    """Requirement 6.2: GET /pigs/modules/{module_id} returns module."""
    table = _create_table()
    _seed_modules(table)

    import lmjm.get_module as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"module_id": "MODULE#1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["name"] == "Module 1"
    assert body["module_number"] == 1


@mock_aws
def test_get_module_returns_404_when_not_found() -> None:
    """Requirement 6.3: Returns 404 with message when module_id not found."""
    _create_table()

    import lmjm.get_module as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"module_id": "MODULE#99"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Module not found"


# ── get_batches tests ───────────────────────────────────────────────────────────


@mock_aws
def test_get_batches_returns_all_batches() -> None:
    """Requirement 6.4: GET /pigs/batches returns JSON array of all batches."""
    table = _create_table()
    _seed_batches(table)

    import lmjm.get_batches as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2
    pks = {b["pk"] for b in body}
    assert pks == {"batch-1", "batch-2"}


@mock_aws
def test_get_batches_returns_empty_list_when_no_batches() -> None:
    """Requirement 6.4: Returns empty array when no batches exist."""
    _create_table()

    import lmjm.get_batches as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == []


# ── get_batch tests ─────────────────────────────────────────────────────────────


@mock_aws
def test_get_batch_returns_batch_by_id() -> None:
    """Requirement 6.5: GET /pigs/batches/{batch_id} returns batch record."""
    table = _create_table()
    _seed_batches(table)

    import lmjm.get_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["pk"] == "batch-1"
    assert body["status"] == "created"
    assert body["supply_id"] == 100


@mock_aws
def test_get_batch_returns_404_when_not_found() -> None:
    """Requirement 6.6: Returns 404 with message when batch_id not found."""
    _create_table()

    import lmjm.get_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "nonexistent"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Batch not found"


@mock_aws
def test_get_batch_includes_start_summary_when_computed() -> None:
    """Requirement 6.10: Batch includes start summary fields if they have been computed."""
    table = _create_table()
    _seed_batch_with_start_summary(table)

    import lmjm.get_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-summary"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["total_animal_count"] == 250
    assert body["average_start_date"] == "2025-02-05"
    assert body["distinct_origin_count"] == 2
    assert set(body["origin_types"]) == {"UPL", "Creche"}


@mock_aws
def test_get_batch_omits_start_summary_when_not_computed() -> None:
    """Requirement 6.11: Batch returns start summary fields absent when not computed."""
    table = _create_table()
    _seed_batches(table)

    import lmjm.get_batch as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "total_animal_count" not in body or body.get("total_animal_count") is None
    assert "average_start_date" not in body or body.get("average_start_date") is None


# ── get_feed_schedule tests ─────────────────────────────────────────────────────


@mock_aws
def test_get_feed_schedule_returns_entries() -> None:
    """Requirement 6.7: GET /pigs/batches/{batch_id}/feed-schedule returns feed schedule entries."""
    table = _create_table()
    _seed_feed_schedule(table)

    import lmjm.get_feed_schedule as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2
    feed_types = {e["feed_type"] for e in body}
    assert feed_types == {"starter", "grower"}


@mock_aws
def test_get_feed_schedule_returns_empty_when_none() -> None:
    """Requirement 6.7: Returns empty array when no feed schedule entries exist."""
    _create_table()

    import lmjm.get_feed_schedule as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == []


# ── get_feed_truck_arrivals tests ───────────────────────────────────────────────


@mock_aws
def test_get_feed_truck_arrivals_sorted_by_receive_date_asc() -> None:
    """Requirement 6.9: GET feed-truck-arrivals returns sorted by receive_date ascending."""
    table = _create_table()
    _seed_feed_truck_arrivals(table)

    import lmjm.get_feed_truck_arrivals as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3
    dates = [a["receive_date"] for a in body]
    assert dates == ["2025-01-10", "2025-01-15", "2025-01-20"]


# ── get_pig_truck_arrivals tests ────────────────────────────────────────────────


@mock_aws
def test_get_pig_truck_arrivals_sorted_by_arrival_date_asc() -> None:
    """Requirement 6.8: GET pig-truck-arrivals returns sorted by arrival_date ascending."""
    table = _create_table()
    _seed_pig_truck_arrivals(table)

    import lmjm.get_pig_truck_arrivals as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3
    dates = [a["arrival_date"] for a in body]
    assert dates == ["2025-02-01", "2025-02-05", "2025-02-10"]


# ── get_mortalities tests ───────────────────────────────────────────────────────


@mock_aws
def test_get_mortalities_sorted_by_date_desc() -> None:
    """Requirement 6.12: GET mortalities returns sorted by mortality_date descending."""
    table = _create_table()
    _seed_mortalities(table)

    import lmjm.get_mortalities as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3
    dates = [m["mortality_date"] for m in body]
    assert dates == ["2025-03-10", "2025-03-05", "2025-03-01"]


# ── get_medications tests ───────────────────────────────────────────────────────


@mock_aws
def test_get_medications_returns_medications_for_batch() -> None:
    """Requirement 6.13: GET medications returns all medications for the batch."""
    table = _create_table()
    _seed_medications(table)

    import lmjm.get_medications as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2
    names = {m["medication_name"] for m in body}
    assert names == {"Amoxicillin", "Ivermectin"}


# ── get_medication_shots tests ──────────────────────────────────────────────────


@mock_aws
def test_get_medication_shots_returns_all_shots() -> None:
    """Requirement 6.14: GET medication-shots returns all shots when no month filter."""
    table = _create_table()
    _seed_medication_shots(table)

    import lmjm.get_medication_shots as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}, "queryStringParameters": None}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3


@mock_aws
def test_get_medication_shots_filters_by_month() -> None:
    """Requirement 6.14: GET medication-shots filters by month query param."""
    table = _create_table()
    _seed_medication_shots(table)

    import lmjm.get_medication_shots as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}, "queryStringParameters": {"month": "2025-03"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2
    assert all(s["date"].startswith("2025-03") for s in body)


# ── get_feed_consumption_plan tests ─────────────────────────────────────────────


@mock_aws
def test_get_feed_consumption_plan_sorted_by_day_number_asc() -> None:
    """Requirement 6.15: GET feed-consumption-plan returns sorted by day_number ascending."""
    table = _create_table()
    _seed_feed_consumption_plan(table)

    import lmjm.get_feed_consumption_plan as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3
    day_numbers = [p["day_number"] for p in body]
    assert day_numbers == [1, 2, 3]


@mock_aws
def test_get_feed_consumption_plan_returns_empty_when_none() -> None:
    """Requirement 6.15: Returns empty array when no plan entries exist."""
    _create_table()

    import lmjm.get_feed_consumption_plan as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == []


# ── get_feed_balances tests ─────────────────────────────────────────────────────


@mock_aws
def test_get_feed_balances_sorted_by_measurement_date_asc() -> None:
    """Requirement 6.16: GET feed-balances returns sorted by measurement_date ascending."""
    table = _create_table()
    _seed_feed_balances(table)

    import lmjm.get_feed_balances as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3
    dates = [b["measurement_date"] for b in body]
    assert dates == ["2025-03-10", "2025-03-15", "2025-03-20"]


@mock_aws
def test_get_feed_balances_returns_empty_when_none() -> None:
    """Requirement 6.16: Returns empty array when no feed balances exist."""
    _create_table()

    import lmjm.get_feed_balances as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"batch_id": "batch-1"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == []
