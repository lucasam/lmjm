"""Unit tests for post_procedure_confirm Lambda handler.

Tests cover:
- Confirm open Procedure applies all actions and returns counts
- Confirm already-confirmed Procedure returns 409
- Confirmation with missing animal records failure and continues
- Inspected actions are skipped (not applied to animal)
- Observation appends to animal notes

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import importlib
import json
import uuid
from typing import Any

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_aws


def _create_table() -> Any:
    """Create the DynamoDB table with the ear_tag-sk-index GSI."""
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
            {"AttributeName": "ear_tag", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "ear_tag-sk-index",
                "KeySchema": [
                    {"AttributeName": "ear_tag", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return table


def _put_procedure(table: Any, procedure_id: str, procedure_date: str, status: str = "open") -> str:
    pk = f"Procedure|{procedure_id}"
    table.put_item(
        Item={
            "pk": pk,
            "sk": "Procedure",
            "procedure_date": procedure_date,
            "status": status,
        }
    )
    return pk


def _put_animal(table: Any, ear_tag: str, **extra: Any) -> str:
    animal_pk = f"Animal|{uuid.uuid4()}"
    item: dict[str, Any] = {
        "pk": animal_pk,
        "sk": "Animal",
        "ear_tag": ear_tag,
        "breed": "Nelore",
        "sex": "F",
        "status": "Ativa",
        "species": "cattle",
        "pregnant": False,
        "inseminated": False,
        "implanted": False,
        "transferred": False,
        "lactating": False,
    }
    item.update(extra)
    table.put_item(Item=item)
    return animal_pk


def _put_insemination(table: Any, animal_pk: str, date: str = "20250101", semen: str = "Bull X") -> None:
    table.put_item(
        Item={
            "pk": animal_pk,
            "sk": f"Insemination|{date}",
            "insemination_date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
            "semen": semen,
        }
    )


def _put_action(table: Any, pk: str, action_type: str, ear_tag: str, **extra: Any) -> str:
    action_id = str(uuid.uuid4())
    item: dict[str, Any] = {
        "pk": pk,
        "sk": f"Action|{action_id}",
        "action_type": action_type,
        "ear_tag": ear_tag,
    }
    item.update(extra)
    table.put_item(Item=item)
    return item["sk"]


def _read_animal_by_ear_tag(table: Any, ear_tag: str) -> dict[str, Any]:
    response = table.query(
        IndexName="ear_tag-sk-index",
        KeyConditionExpression=Key("ear_tag").eq(ear_tag) & Key("sk").eq("Animal"),
        Limit=1,
    )
    items = response["Items"]
    assert items, f"Animal with ear_tag={ear_tag} not found"
    return items[0]


def _query_records(table: Any, pk: str, sk_prefix: str) -> list[dict[str, Any]]:
    response = table.query(
        KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(sk_prefix),
    )
    return response["Items"]


# --- Tests ---


@mock_aws
def test_confirm_open_procedure_applies_all_actions_and_returns_counts() -> None:
    """Validates: Requirements 8.1, 8.2, 8.4"""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    pk = _put_procedure(table, procedure_id, "2025-01-15")

    # Create animals
    animal_pk_1 = _put_animal(table, "BR001")
    animal_pk_2 = _put_animal(table, "BR002")
    animal_pk_3 = _put_animal(table, "BR003")

    # Create prior insemination for BR003 (needed for diagnostic)
    _put_insemination(table, animal_pk_3)

    # Stage actions
    _put_action(table, pk, "weight", "BR001", weighing_date="20250115", weight_kg=350)
    _put_action(table, pk, "insemination", "BR002", insemination_date="20250115", semen="Bull A")
    _put_action(table, pk, "diagnostic", "BR003", diagnostic_date="20250115", pregnant=True)
    _put_action(table, pk, "inspected", "BR001")

    import lmjm.post_procedure_confirm as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    # Status should be confirmed
    assert body["status"] == "confirmed"

    # All 4 actions should be applied (inspected counts as applied)
    assert body["applied_count"] == 4
    assert body["failed_count"] == 0
    assert body["failures"] == []

    # Verify Procedure record in DynamoDB is updated
    proc_item = table.get_item(Key={"pk": pk, "sk": "Procedure"})["Item"]
    assert proc_item["status"] == "confirmed"
    assert proc_item["applied_count"] == 4
    assert proc_item["failed_count"] == 0

    # Verify weight record was created for BR001
    weights = _query_records(table, animal_pk_1, "Peso|")
    assert len(weights) == 1
    assert weights[0]["sk"] == "Peso|20250115"
    assert weights[0]["weight_kg"] == 350

    # Verify insemination record was created for BR002
    inseminations = _query_records(table, animal_pk_2, "Insemination|")
    assert len(inseminations) == 1
    assert inseminations[0]["sk"] == "Insemination|20250115"
    animal_2 = _read_animal_by_ear_tag(table, "BR002")
    assert animal_2["inseminated"] is True

    # Verify diagnostic record was created for BR003
    diagnostics = _query_records(table, animal_pk_3, "Diagnostic|")
    assert len(diagnostics) == 1
    assert diagnostics[0]["sk"] == "Diagnostic|20250115"
    animal_3 = _read_animal_by_ear_tag(table, "BR003")
    assert animal_3["pregnant"] is True


@mock_aws
def test_confirm_already_confirmed_procedure_returns_409() -> None:
    """Validates: Requirements 8.5"""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    _put_procedure(table, procedure_id, "2025-01-15", status="confirmed")

    import lmjm.post_procedure_confirm as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 409
    body = json.loads(result["body"])
    assert "message" in body


@mock_aws
def test_confirmation_with_missing_animal_records_failure_and_continues() -> None:
    """Validates: Requirements 8.3, 8.4"""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    pk = _put_procedure(table, procedure_id, "2025-01-15")

    # Create only BR001, BR999 does not exist
    animal_pk_1 = _put_animal(table, "BR001")

    # Stage actions: one for existing animal, one for missing animal
    _put_action(table, pk, "weight", "BR001", weighing_date="20250115", weight_kg=400)
    _put_action(table, pk, "weight", "BR999", weighing_date="20250115", weight_kg=300)

    import lmjm.post_procedure_confirm as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    # One applied, one failed
    assert body["applied_count"] == 1
    assert body["failed_count"] == 1
    assert body["status"] == "confirmed"

    # Failures list should contain the missing animal action
    assert len(body["failures"]) == 1
    failure = body["failures"][0]
    assert failure["ear_tag"] == "BR999"
    assert failure["action_type"] == "weight"
    assert "reason" in failure

    # The existing animal's weight should still have been applied
    weights = _query_records(table, animal_pk_1, "Peso|")
    assert len(weights) == 1


@mock_aws
def test_inspected_actions_are_skipped() -> None:
    """Validates: Requirements 8.1 (inspected does not modify animal)"""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    pk = _put_procedure(table, procedure_id, "2025-01-15")

    # Create animal with known initial state
    animal_pk = _put_animal(table, "BR050")
    animal_before = _read_animal_by_ear_tag(table, "BR050")

    # Stage only an inspected action
    _put_action(table, pk, "inspected", "BR050")

    import lmjm.post_procedure_confirm as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    # Inspected counts as applied
    assert body["applied_count"] == 1
    assert body["failed_count"] == 0

    # Animal record should be completely unchanged
    animal_after = _read_animal_by_ear_tag(table, "BR050")
    invariant_fields = ("pregnant", "inseminated", "implanted", "transferred", "lactating", "notes", "tags")
    for field in invariant_fields:
        assert animal_after.get(field) == animal_before.get(field), (
            f"Field '{field}' changed: before={animal_before.get(field)}, after={animal_after.get(field)}"
        )

    # No extra records should have been created for this animal
    weights = _query_records(table, animal_pk, "Peso|")
    inseminations = _query_records(table, animal_pk, "Insemination|")
    diagnostics = _query_records(table, animal_pk, "Diagnostic|")
    assert len(weights) == 0
    assert len(inseminations) == 0
    assert len(diagnostics) == 0


@mock_aws
def test_observation_appends_to_animal_notes() -> None:
    """Validates: Requirements 8.1 (observation appends note)"""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    pk = _put_procedure(table, procedure_id, "2025-01-15")

    # Create animal with existing notes
    animal_pk = _put_animal(table, "BR060", notes=["Previous note"])

    # Stage an observation action
    _put_action(table, pk, "observation", "BR060", note="Limping on left rear leg")

    import lmjm.post_procedure_confirm as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    assert body["applied_count"] == 1
    assert body["failed_count"] == 0

    # Animal notes should contain both the previous note and the new observation
    animal_after = _read_animal_by_ear_tag(table, "BR060")
    notes = animal_after.get("notes", [])
    assert "Previous note" in notes, f"Previous note missing from {notes}"
    assert "Limping on left rear leg" in notes, f"Observation note missing from {notes}"
