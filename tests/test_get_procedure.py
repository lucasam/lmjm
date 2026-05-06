"""Unit tests for get_procedure and get_procedures Lambda handlers.

Tests cover:
- get_procedure returns summary with correct counts
- get_procedure with no actions returns zero counts
- get_procedure for non-existent Procedure returns 404
- get_procedures returns sorted list with action counts

Requirements: 7.1, 7.2, 7.5, 9.1, 9.2
"""

import importlib
import json
import uuid
from typing import Any

import boto3
import pytest
from moto import mock_aws


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


# --- get_procedure tests ---


@mock_aws
def test_get_procedure_returns_summary_with_correct_counts() -> None:
    """Validates: Requirements 7.1, 7.2, 7.5"""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    pk = _put_procedure(table, procedure_id, "2025-01-15")

    # Stage actions of various types
    _put_action(table, pk, "weight", "BR001", weighing_date="2025-01-15", weight_kg=350)
    _put_action(table, pk, "weight", "BR002", weighing_date="2025-01-15", weight_kg=400)
    _put_action(table, pk, "insemination", "BR001", insemination_date="2025-01-15", semen="Bull A")
    _put_action(table, pk, "diagnostic", "BR003", diagnostic_date="2025-01-15", pregnant=True)
    _put_action(table, pk, "observation", "BR004", note="Limping slightly")
    _put_action(table, pk, "inspected", "BR005")

    import lmjm.get_procedure as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    # Verify structure
    assert "procedure" in body
    assert "actions" in body
    assert "summary" in body

    summary = body["summary"]

    # Verify counts by type
    assert summary["weight_count"] == 2
    assert summary["insemination_count"] == 1
    assert summary["diagnostic_count"] == 1
    assert summary["observation_count"] == 1
    assert summary["inspected_count"] == 1
    assert summary["total_actions"] == 6

    # Verify processed animal count (5 distinct ear_tags: BR001-BR005)
    assert summary["processed_animal_count"] == 5

    # Verify animals list has one entry per distinct ear_tag
    animals = summary["animals"]
    assert len(animals) == 5
    returned_ear_tags = {a["ear_tag"] for a in animals}
    assert returned_ear_tags == {"BR001", "BR002", "BR003", "BR004", "BR005"}

    # BR001 has 2 actions (weight + insemination)
    br001_animal = next(a for a in animals if a["ear_tag"] == "BR001")
    assert len(br001_animal["actions"]) == 2

    # Verify procedure data is returned
    assert body["procedure"]["pk"] == pk
    assert body["procedure"]["procedure_date"] == "2025-01-15"
    assert body["procedure"]["status"] == "open"

    # Verify actions list matches total
    assert len(body["actions"]) == 6


@mock_aws
def test_get_procedure_with_no_actions_returns_zero_counts() -> None:
    """Validates: Requirements 7.1, 7.2"""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    _put_procedure(table, procedure_id, "2025-02-10")

    import lmjm.get_procedure as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    summary = body["summary"]
    assert summary["weight_count"] == 0
    assert summary["insemination_count"] == 0
    assert summary["diagnostic_count"] == 0
    assert summary["observation_count"] == 0
    assert summary["inspected_count"] == 0
    assert summary["total_actions"] == 0
    assert summary["processed_animal_count"] == 0
    assert summary["animals"] == []

    assert body["actions"] == []


@mock_aws
def test_get_procedure_not_found_returns_404() -> None:
    """Validates: Requirements 7.1"""
    _create_table()
    fake_id = str(uuid.uuid4())

    import lmjm.get_procedure as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": fake_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "message" in body


# --- get_procedures tests ---


@mock_aws
def test_get_procedures_returns_sorted_list_with_action_counts() -> None:
    """Validates: Requirements 9.1, 9.2"""
    table = _create_table()

    # Create 3 procedures with different dates
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    id3 = str(uuid.uuid4())

    pk1 = _put_procedure(table, id1, "2025-01-10")
    pk2 = _put_procedure(table, id2, "2025-01-20")
    pk3 = _put_procedure(table, id3, "2025-01-15", status="confirmed")

    # Add actions: proc1 has 2, proc2 has 0, proc3 has 3
    _put_action(table, pk1, "weight", "BR001", weighing_date="2025-01-10", weight_kg=300)
    _put_action(table, pk1, "inspected", "BR002")

    _put_action(table, pk3, "weight", "BR010", weighing_date="2025-01-15", weight_kg=350)
    _put_action(table, pk3, "insemination", "BR011", insemination_date="2025-01-15", semen="Bull B")
    _put_action(table, pk3, "observation", "BR012", note="Healthy")

    import lmjm.get_procedures as mod

    importlib.reload(mod)

    event: dict[str, Any] = {}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    assert len(body) == 3

    # Verify sorted by procedure_date descending
    dates = [p["procedure_date"] for p in body]
    assert dates == sorted(dates, reverse=True)
    assert dates == ["2025-01-20", "2025-01-15", "2025-01-10"]

    # Verify each entry has the expected fields
    for entry in body:
        assert "pk" in entry
        assert "procedure_date" in entry
        assert "status" in entry
        assert "action_count" in entry

    # Verify action counts
    proc_by_date = {p["procedure_date"]: p for p in body}
    assert proc_by_date["2025-01-10"]["action_count"] == 2
    assert proc_by_date["2025-01-10"]["status"] == "open"
    assert proc_by_date["2025-01-20"]["action_count"] == 0
    assert proc_by_date["2025-01-20"]["status"] == "open"
    assert proc_by_date["2025-01-15"]["action_count"] == 3
    assert proc_by_date["2025-01-15"]["status"] == "confirmed"
