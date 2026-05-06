"""Unit tests for delete_procedure_action Lambda handler.

Tests cover:
- Delete from open Procedure returns 204 and action is removed
- Delete from confirmed Procedure returns 409
- Delete non-existent action returns 404

Requirements: 10.1, 10.2
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
    sk = f"Action|{action_id}"
    item: dict[str, Any] = {
        "pk": pk,
        "sk": sk,
        "action_type": action_type,
        "ear_tag": ear_tag,
    }
    item.update(extra)
    table.put_item(Item=item)
    return sk


def _get_actions(table: Any, pk: str) -> list[dict[str, Any]]:
    """Query all Action| items for a given procedure pk."""
    response = table.query(
        KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
        ExpressionAttributeValues={":pk": pk, ":prefix": "Action|"},
    )
    return response["Items"]


# --- delete_procedure_action tests ---


@mock_aws
def test_delete_from_open_procedure_returns_204_and_removes_action() -> None:
    """Validates: Requirement 10.1 — delete staged action from open Procedure."""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    pk = _put_procedure(table, procedure_id, "2025-01-15")

    # Stage two actions
    action_sk_to_delete = _put_action(table, pk, "weight", "BR001", weighing_date="2025-01-15", weight_kg=350)
    action_sk_to_keep = _put_action(table, pk, "insemination", "BR002", insemination_date="2025-01-15", semen="Bull A")

    import lmjm.delete_procedure_action as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {
            "procedure_id": procedure_id,
            "action_sk": action_sk_to_delete,
        }
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 204

    # Verify the deleted action is gone and the other remains
    remaining = _get_actions(table, pk)
    remaining_sks = [item["sk"] for item in remaining]
    assert action_sk_to_delete not in remaining_sks
    assert action_sk_to_keep in remaining_sks
    assert len(remaining) == 1


@mock_aws
def test_delete_from_confirmed_procedure_returns_409() -> None:
    """Validates: Requirement 10.2 — cannot delete from confirmed Procedure."""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    pk = _put_procedure(table, procedure_id, "2025-01-15", status="confirmed")

    action_sk = _put_action(table, pk, "weight", "BR001", weighing_date="2025-01-15", weight_kg=350)

    import lmjm.delete_procedure_action as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {
            "procedure_id": procedure_id,
            "action_sk": action_sk,
        }
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 409
    body = json.loads(result["body"])
    assert "message" in body

    # Verify the action was NOT deleted
    remaining = _get_actions(table, pk)
    assert len(remaining) == 1
    assert remaining[0]["sk"] == action_sk


@mock_aws
def test_delete_nonexistent_action_returns_404() -> None:
    """Validates: Requirement 10.1 — action not found returns 404."""
    table = _create_table()
    procedure_id = str(uuid.uuid4())
    _put_procedure(table, procedure_id, "2025-01-15")

    fake_action_sk = f"Action|{uuid.uuid4()}"

    import lmjm.delete_procedure_action as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {
            "procedure_id": procedure_id,
            "action_sk": fake_action_sk,
        }
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "message" in body


@mock_aws
def test_delete_from_nonexistent_procedure_returns_404() -> None:
    """Validates: Requirement 10.1 — procedure not found returns 404."""
    _create_table()
    fake_procedure_id = str(uuid.uuid4())
    fake_action_sk = f"Action|{uuid.uuid4()}"

    import lmjm.delete_procedure_action as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {
            "procedure_id": fake_procedure_id,
            "action_sk": fake_action_sk,
        }
    }
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "message" in body
