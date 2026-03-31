"""Unit tests for pig entity repositories.

Validates:
- Requirement 7.17: Repository layer queries batch sub-entities with sk begins_with prefix
- Requirement 7.18: Repository layer filters cattle by species attribute or sk=Animal
"""

import json
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

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
from lmjm.repo import (
    BatchRepo,
    FeedBalanceRepo,
    FeedConsumptionPlanRepo,
    FeedScheduleRepo,
    FeedTruckArrivalRepo,
    MedicationRepo,
    MedicationShotRepo,
    ModuleRepo,
    MortalityRepo,
    PigTruckArrivalRepo,
)
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize


def _serialize_decimal_safe(obj: object, schema: Any = None) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj, schema)
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


# Patch all repo modules that import serialize_to_dict so repo write methods work with moto
_SERIALIZE_PATCHES = [
    "lmjm.repo.batch_repo.serialize_to_dict",
    "lmjm.repo.feed_balance_repo.serialize_to_dict",
    "lmjm.repo.feed_consumption_plan_repo.serialize_to_dict",
    "lmjm.repo.feed_schedule_repo.serialize_to_dict",
    "lmjm.repo.feed_truck_arrival_repo.serialize_to_dict",
    "lmjm.repo.medication_repo.serialize_to_dict",
    "lmjm.repo.medication_shot_repo.serialize_to_dict",
    "lmjm.repo.mortality_repo.serialize_to_dict",
    "lmjm.repo.pig_truck_arrival_repo.serialize_to_dict",
]


@pytest.fixture(autouse=True)
def _patch_serialize() -> Any:
    """Patch serialize_to_dict in all repo modules to produce Decimal-safe dicts for moto."""
    patchers = [patch(target, side_effect=_serialize_decimal_safe) for target in _SERIALIZE_PATCHES]
    for p in patchers:
        p.start()
    yield
    for p in patchers:
        p.stop()


# ── ModuleRepo ──────────────────────────────────────────────────────────────────


@mock_aws
def test_module_repo_get_returns_module() -> None:
    """Requirement 7.16: ModuleRepo.get returns a Module by pk."""
    table = _create_table()
    _put(table, Module(pk="MODULE#1", sk="Module", module_number=1, name="Module 1"))

    repo = ModuleRepo(table)
    result = repo.get("MODULE#1")

    assert result is not None
    assert result.pk == "MODULE#1"
    assert result.module_number == 1
    assert result.name == "Module 1"


@mock_aws
def test_module_repo_get_returns_none_when_not_found() -> None:
    """Requirement 7.16: ModuleRepo.get returns None for missing module."""
    table = _create_table()
    repo = ModuleRepo(table)
    assert repo.get("MODULE#99") is None


@mock_aws
def test_module_repo_list_returns_all_modules() -> None:
    """Requirement 7.16: ModuleRepo.list returns all Module records."""
    table = _create_table()
    _put(table, Module(pk="MODULE#1", sk="Module", module_number=1, name="Module 1"))
    _put(table, Module(pk="MODULE#2", sk="Module", module_number=2, name="Module 2"))

    repo = ModuleRepo(table)
    result = repo.list()

    assert len(result) == 2
    names = {m.name for m in result}
    assert names == {"Module 1", "Module 2"}


# ── BatchRepo ───────────────────────────────────────────────────────────────────


@mock_aws
def test_batch_repo_get_returns_batch() -> None:
    """Requirement 7.17: BatchRepo.get returns a Batch by pk."""
    table = _create_table()
    _put(table, Batch(pk="batch-1", sk="Batch", status="created", supply_id=100, module_id="MODULE#1", pig_count=500))

    repo = BatchRepo(table)
    result = repo.get("batch-1")

    assert result is not None
    assert result.pk == "batch-1"
    assert result.status == "created"
    assert result.supply_id == 100


@mock_aws
def test_batch_repo_get_returns_none_when_not_found() -> None:
    """Requirement 7.17: BatchRepo.get returns None for missing batch."""
    table = _create_table()
    repo = BatchRepo(table)
    assert repo.get("nonexistent") is None


@mock_aws
def test_batch_repo_list_returns_all_batches() -> None:
    """Requirement 7.17: BatchRepo.list returns all Batch records via scan."""
    table = _create_table()
    _put(table, Batch(pk="batch-1", sk="Batch", status="created", supply_id=1))
    _put(table, Batch(pk="batch-2", sk="Batch", status="in_progress", supply_id=2))

    repo = BatchRepo(table)
    result = repo.list()

    assert len(result) == 2
    pks = {b.pk for b in result}
    assert pks == {"batch-1", "batch-2"}


@mock_aws
def test_batch_repo_update_persists_changes() -> None:
    """Requirement 7.17: BatchRepo.update overwrites the Batch record."""
    table = _create_table()
    batch = Batch(pk="batch-1", sk="Batch", status="created", supply_id=1)
    _put(table, batch)

    repo = BatchRepo(table)
    batch.status = "in_progress"
    batch.total_animal_count = 250
    repo.update(batch)

    result = repo.get("batch-1")
    assert result is not None
    assert result.status == "in_progress"
    assert result.total_animal_count == 250


# ── FeedScheduleRepo ────────────────────────────────────────────────────────────


@mock_aws
def test_feed_schedule_repo_list_uses_begins_with() -> None:
    """Requirement 7.17: FeedScheduleRepo.list queries with sk begins_with FeedSchedule|."""
    table = _create_table()
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
    # Different entity — should not appear
    _put(table, Batch(pk="batch-1", sk="Batch", status="created"))

    repo = FeedScheduleRepo(table)
    result = repo.list("batch-1")

    assert len(result) == 2
    assert all(isinstance(fs, FeedSchedule) for fs in result)


@mock_aws
def test_feed_schedule_repo_put_and_delete_all() -> None:
    """Requirement 7.17: FeedScheduleRepo.put creates and delete_all removes all schedules."""
    table = _create_table()
    repo = FeedScheduleRepo(table)

    fs = FeedSchedule(
        pk="batch-1", sk="FeedSchedule|fs1", feed_type="starter", planned_date="2025-01-10", expected_amount_kg=500.0
    )
    repo.put(fs)
    assert len(repo.list("batch-1")) == 1

    repo.delete_all("batch-1")
    assert len(repo.list("batch-1")) == 0


# ── FeedTruckArrivalRepo ────────────────────────────────────────────────────────


@mock_aws
def test_feed_truck_arrival_repo_list_sorted_by_receive_date() -> None:
    """Requirement 7.17: FeedTruckArrivalRepo.list returns items sorted by receive_date asc (ScanIndexForward=True)."""
    table = _create_table()
    repo = FeedTruckArrivalRepo(table)

    repo.put(
        FeedTruckArrival(
            pk="batch-1",
            sk="FeedTruckArrival|2025-01-15|001",
            receive_date="2025-01-15",
            fiscal_document_number="NF001",
            actual_amount_kg=1000.0,
            feed_type="starter",
        )
    )
    repo.put(
        FeedTruckArrival(
            pk="batch-1",
            sk="FeedTruckArrival|2025-01-10|001",
            receive_date="2025-01-10",
            fiscal_document_number="NF002",
            actual_amount_kg=2000.0,
            feed_type="grower",
        )
    )
    repo.put(
        FeedTruckArrival(
            pk="batch-1",
            sk="FeedTruckArrival|2025-01-20|001",
            receive_date="2025-01-20",
            fiscal_document_number="NF003",
            actual_amount_kg=1500.0,
            feed_type="finisher",
        )
    )

    result = repo.list("batch-1")

    assert len(result) == 3
    dates = [r.receive_date for r in result]
    assert dates == ["2025-01-10", "2025-01-15", "2025-01-20"]


# ── PigTruckArrivalRepo ─────────────────────────────────────────────────────────


@mock_aws
def test_pig_truck_arrival_repo_list_sorted_by_arrival_date() -> None:
    """Requirement 7.17: PigTruckArrivalRepo.list returns items sorted by arrival_date asc (ScanIndexForward=True)."""
    table = _create_table()
    repo = PigTruckArrivalRepo(table)

    repo.put(
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|2025-02-05|001",
            animal_count=100,
            sex="Male",
            arrival_date="2025-02-05",
            pig_age_days=30,
            origin_name="Farm A",
            origin_type="UPL",
        )
    )
    repo.put(
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|2025-02-01|001",
            animal_count=150,
            sex="Female",
            arrival_date="2025-02-01",
            pig_age_days=28,
            origin_name="Farm B",
            origin_type="Creche",
        )
    )
    repo.put(
        PigTruckArrival(
            pk="batch-1",
            sk="PigTruckArrival|2025-02-10|001",
            animal_count=80,
            sex="Male",
            arrival_date="2025-02-10",
            pig_age_days=35,
            origin_name="Farm C",
            origin_type="UPL",
        )
    )

    result = repo.list("batch-1")

    assert len(result) == 3
    dates = [r.arrival_date for r in result]
    assert dates == ["2025-02-01", "2025-02-05", "2025-02-10"]


# ── MortalityRepo ───────────────────────────────────────────────────────────────


@mock_aws
def test_mortality_repo_list_sorted_by_date_desc() -> None:
    """Requirement 7.17: MortalityRepo.list returns items sorted by date desc (ScanIndexForward=False)."""
    table = _create_table()
    repo = MortalityRepo(table)

    repo.put(
        Mortality(
            pk="batch-1",
            sk="Mortality|2025-03-01|001",
            mortality_date="2025-03-01",
            sex="Male",
            origin="Farm A",
            death_reason="Disease",
            reported_by="user1",
        )
    )
    repo.put(
        Mortality(
            pk="batch-1",
            sk="Mortality|2025-03-10|001",
            mortality_date="2025-03-10",
            sex="Female",
            origin="Farm B",
            death_reason="Injury",
            reported_by="user2",
        )
    )
    repo.put(
        Mortality(
            pk="batch-1",
            sk="Mortality|2025-03-05|001",
            mortality_date="2025-03-05",
            sex="Male",
            origin="Farm A",
            death_reason="Unknown",
            reported_by="user1",
        )
    )

    result = repo.list("batch-1")

    assert len(result) == 3
    dates = [r.mortality_date for r in result]
    assert dates == ["2025-03-10", "2025-03-05", "2025-03-01"]


# ── MedicationRepo ──────────────────────────────────────────────────────────────


@mock_aws
def test_medication_repo_put_and_list() -> None:
    """Requirement 7.17: MedicationRepo list returns Medication records using begins_with."""
    table = _create_table()
    repo = MedicationRepo(table)

    repo.put(
        Medication(
            pk="batch-1",
            sk="Medication|med1",
            medication_name="Amoxicillin",
            expiration_date="2026-01-01",
            part_number="P001",
        )
    )
    repo.put(
        Medication(
            pk="batch-1",
            sk="Medication|med2",
            medication_name="Ivermectin",
            expiration_date="2026-06-01",
            part_number="P002",
        )
    )

    result = repo.list("batch-1")

    assert len(result) == 2
    names = {m.medication_name for m in result}
    assert names == {"Amoxicillin", "Ivermectin"}


@mock_aws
def test_medication_repo_list_excludes_medication_shots() -> None:
    """Requirement 7.17: MedicationRepo.list filters out MedicationShot records that share the Medication| prefix."""
    table = _create_table()
    repo = MedicationRepo(table)

    repo.put(
        Medication(
            pk="batch-1",
            sk="Medication|med1",
            medication_name="Amoxicillin",
            expiration_date="2026-01-01",
            part_number="P001",
        )
    )
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

    result = repo.list("batch-1")

    assert len(result) == 1
    assert result[0].medication_name == "Amoxicillin"


@mock_aws
def test_medication_repo_get() -> None:
    """Requirement 7.17: MedicationRepo.get returns a single Medication by pk+sk."""
    table = _create_table()
    repo = MedicationRepo(table)

    repo.put(
        Medication(
            pk="batch-1",
            sk="Medication|med1",
            medication_name="Amoxicillin",
            expiration_date="2026-01-01",
            part_number="P001",
        )
    )

    result = repo.get("batch-1", "Medication|med1")
    assert result is not None
    assert result.medication_name == "Amoxicillin"

    assert repo.get("batch-1", "Medication|nonexistent") is None


# ── MedicationShotRepo ──────────────────────────────────────────────────────────


@mock_aws
def test_medication_shot_repo_list_all() -> None:
    """Requirement 7.17: MedicationShotRepo.list returns all shots when no month filter."""
    table = _create_table()
    repo = MedicationShotRepo(table)

    repo.put(
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-03-01|med1",
            medication_name="Amoxicillin",
            shot_count=10,
            date="2025-03-01",
        )
    )
    repo.put(
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-04-01|med1",
            medication_name="Amoxicillin",
            shot_count=5,
            date="2025-04-01",
        )
    )

    result = repo.list("batch-1")
    assert len(result) == 2


@mock_aws
def test_medication_shot_repo_list_with_month_filter() -> None:
    """Requirement 7.17: MedicationShotRepo.list filters by month prefix when month is provided."""
    table = _create_table()
    repo = MedicationShotRepo(table)

    repo.put(
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-03-01|med1",
            medication_name="Amoxicillin",
            shot_count=10,
            date="2025-03-01",
        )
    )
    repo.put(
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-03-15|med1",
            medication_name="Amoxicillin",
            shot_count=8,
            date="2025-03-15",
        )
    )
    repo.put(
        MedicationShot(
            pk="batch-1",
            sk="MedicationShot|2025-04-01|med1",
            medication_name="Amoxicillin",
            shot_count=5,
            date="2025-04-01",
        )
    )

    result = repo.list("batch-1", month="2025-03")
    assert len(result) == 2
    assert all(r.date.startswith("2025-03") for r in result)


# ── FeedConsumptionPlanRepo ──────────────────────────────────────────────────────


@mock_aws
def test_feed_consumption_plan_repo_put_all_and_list() -> None:
    """Requirement 7.17: FeedConsumptionPlanRepo.put_all batch-writes and list returns sorted by day_number."""
    table = _create_table()
    repo = FeedConsumptionPlanRepo(table)

    plans = [
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|3", day_number=3, expected_grams_per_animal=350.0, date="2025-01-04"
        ),
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|1", day_number=1, expected_grams_per_animal=300.0, date="2025-01-02"
        ),
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|2", day_number=2, expected_grams_per_animal=320.0, date="2025-01-03"
        ),
    ]
    repo.put_all(plans)

    result = repo.list("batch-1")
    assert len(result) == 3
    day_numbers = [p.day_number for p in result]
    assert day_numbers == [1, 2, 3]


@mock_aws
def test_feed_consumption_plan_repo_delete_all() -> None:
    """Requirement 7.17: FeedConsumptionPlanRepo.delete_all removes all plan entries for a batch."""
    table = _create_table()
    repo = FeedConsumptionPlanRepo(table)

    plans = [
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|1", day_number=1, expected_grams_per_animal=300.0, date="2025-01-02"
        ),
        FeedConsumptionPlan(
            pk="batch-1", sk="FeedConsumptionPlan|2", day_number=2, expected_grams_per_animal=320.0, date="2025-01-03"
        ),
    ]
    repo.put_all(plans)
    assert len(repo.list("batch-1")) == 2

    repo.delete_all("batch-1")
    assert len(repo.list("batch-1")) == 0


# ── FeedBalanceRepo ──────────────────────────────────────────────────────────────


@mock_aws
def test_feed_balance_repo_list_sorted_by_measurement_date() -> None:
    """Requirement 7.17: FeedBalanceRepo.list returns items sorted by measurement_date asc (ScanIndexForward=True)."""
    table = _create_table()
    repo = FeedBalanceRepo(table)

    repo.put(FeedBalance(pk="batch-1", sk="FeedBalance|20250315", measurement_date="2025-03-15", balance_kg=5000.0))
    repo.put(FeedBalance(pk="batch-1", sk="FeedBalance|20250310", measurement_date="2025-03-10", balance_kg=8000.0))
    repo.put(FeedBalance(pk="batch-1", sk="FeedBalance|20250320", measurement_date="2025-03-20", balance_kg=3000.0))

    result = repo.list("batch-1")

    assert len(result) == 3
    dates = [r.measurement_date for r in result]
    assert dates == ["2025-03-10", "2025-03-15", "2025-03-20"]
