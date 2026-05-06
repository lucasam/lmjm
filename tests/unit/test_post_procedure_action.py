"""Unit tests for post_procedure_action Lambda handler.

Feature: cattle-procedure

**Validates: Requirements 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2**
"""

import importlib
import json
import re
import uuid
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.model import Insemination
from lmjm.util.marshmallow_serializer import serialize_to_dict

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
ACTION_SK_RE = re.compile(
    r"^Action\|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

PROCEDURE_ID = str(uuid.uuid4())
PROCEDURE_PK = f"Procedure|{PROCEDURE_ID}"
ANIMAL_PK = f"Animal|{uuid.uuid4()}"
EAR_TAG = "UNIT-001"


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


def _seed_open_procedure(table: Any) -> None:
    """Seed an open Procedure record."""
    table.put_item(
        Item={
            "pk": PROCEDURE_PK,
            "sk": "Procedure",
            "procedure_date": "2024-07-15",
            "status": "open",
        }
    )


def _seed_confirmed_procedure(table: Any) -> None:
    """Seed a confirmed Procedure record."""
    table.put_item(
        Item={
            "pk": PROCEDURE_PK,
            "sk": "Procedure",
            "procedure_date": "2024-07-15",
            "status": "confirmed",
        }
    )


def _seed_animal(table: Any) -> None:
    """Seed an Animal record with ear_tag."""
    table.put_item(
        Item={
            "pk": ANIMAL_PK,
            "sk": "Animal",
            "ear_tag": EAR_TAG,
            "species": "cattle",
            "status": "Ativa",
        }
    )


def _seed_insemination(table: Any) -> None:
    """Seed an Insemination record for the animal (needed for diagnostic tests)."""
    insemination = Insemination(
        pk=ANIMAL_PK,
        sk="Insemination|20240601",
        insemination_date="2024-06-01",
        semen="Bull-A",
    )
    table.put_item(Item=serialize_to_dict(insemination))


def _apigw_event(body: dict[str, Any], procedure_id: str = PROCEDURE_ID) -> dict[str, Any]:
    return {
        "body": json.dumps(body),
        "pathParameters": {"procedure_id": procedure_id},
    }


def _reload_handler() -> Any:
    import lmjm.post_procedure_action as mod

    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# Valid action types return 201
# ---------------------------------------------------------------------------


@mock_aws
def test_weight_valid_input_returns_201() -> None:
    """Requirement 3.1: Valid weight action creates a Staged_Action."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "weight",
        "ear_tag": EAR_TAG,
        "weighing_date": "20240715",
        "weight_kg": 450,
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["pk"] == PROCEDURE_PK
    assert ACTION_SK_RE.match(body["sk"])
    assert body["action_type"] == "weight"
    assert body["ear_tag"] == EAR_TAG
    assert body["weighing_date"] == "2024-07-15"
    assert body["weight_kg"] == 450


@mock_aws
def test_insemination_valid_input_returns_201() -> None:
    """Requirement 4.1: Valid insemination action creates a Staged_Action."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "insemination",
        "ear_tag": EAR_TAG,
        "insemination_date": "20240715",
        "semen": "Bull-X",
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["action_type"] == "insemination"
    assert body["insemination_date"] == "2024-07-15"
    assert body["semen"] == "Bull-X"


@mock_aws
def test_diagnostic_valid_input_returns_201() -> None:
    """Requirement 5.1: Valid diagnostic action creates a Staged_Action."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    _seed_insemination(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "diagnostic",
        "ear_tag": EAR_TAG,
        "diagnostic_date": "20240715",
        "pregnant": True,
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["action_type"] == "diagnostic"
    assert body["diagnostic_date"] == "2024-07-15"
    assert body["pregnant"] is True


@mock_aws
def test_observation_valid_input_returns_201() -> None:
    """Requirement 6.1: Valid observation action creates a Staged_Action."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "observation",
        "ear_tag": EAR_TAG,
        "note": "Animal looks healthy",
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["action_type"] == "observation"
    assert body["note"] == "Animal looks healthy"


@mock_aws
def test_inspected_valid_input_returns_201() -> None:
    """Requirement 2.5: Inspected action creates a Staged_Action with no extra fields."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "inspected",
        "ear_tag": EAR_TAG,
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["action_type"] == "inspected"
    assert body["ear_tag"] == EAR_TAG
    assert body["pk"] == PROCEDURE_PK
    # Inspected should have no type-specific fields
    assert "weighing_date" not in body
    assert "weight_kg" not in body
    assert "insemination_date" not in body
    assert "semen" not in body
    assert "diagnostic_date" not in body
    assert "pregnant" not in body
    assert "note" not in body
    assert "tags" not in body


# ---------------------------------------------------------------------------
# Validation errors return 400
# ---------------------------------------------------------------------------


@mock_aws
def test_weight_non_positive_weight_kg_returns_400() -> None:
    """Requirement 3.2: Non-positive weight_kg returns 400."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "weight",
        "ear_tag": EAR_TAG,
        "weighing_date": "20240715",
        "weight_kg": 0,
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "weight_kg" in body["message"]


@mock_aws
def test_insemination_empty_semen_returns_400() -> None:
    """Requirement 4.2: Empty semen identifier returns 400."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "insemination",
        "ear_tag": EAR_TAG,
        "insemination_date": "20240715",
        "semen": "",
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "semen" in body["message"]


@mock_aws
def test_observation_empty_note_returns_400() -> None:
    """Requirement 6.2: Empty observation note returns 400."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "observation",
        "ear_tag": EAR_TAG,
        "note": "",
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "note" in body["message"]


# ---------------------------------------------------------------------------
# Diagnostic without insemination returns 404
# ---------------------------------------------------------------------------


@mock_aws
def test_diagnostic_without_insemination_returns_404() -> None:
    """Requirement 5.2: Diagnostic for animal without insemination returns 404."""
    table = _create_table()
    _seed_open_procedure(table)
    _seed_animal(table)
    # Deliberately NOT seeding an insemination record
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "diagnostic",
        "ear_tag": EAR_TAG,
        "diagnostic_date": "20240715",
        "pregnant": False,
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "insemination" in body["message"].lower()


# ---------------------------------------------------------------------------
# Procedure not found returns 404
# ---------------------------------------------------------------------------


@mock_aws
def test_action_on_nonexistent_procedure_returns_404() -> None:
    """Action on a non-existent Procedure returns 404."""
    _create_table()
    mod = _reload_handler()

    non_existent_id = str(uuid.uuid4())
    event = _apigw_event(
        {"action_type": "inspected", "ear_tag": EAR_TAG},
        procedure_id=non_existent_id,
    )
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "procedure" in body["message"].lower()


# ---------------------------------------------------------------------------
# Confirmed Procedure returns 409
# ---------------------------------------------------------------------------


@mock_aws
def test_action_on_confirmed_procedure_returns_409() -> None:
    """Action on a confirmed Procedure returns 409."""
    table = _create_table()
    _seed_confirmed_procedure(table)
    _seed_animal(table)
    mod = _reload_handler()

    event = _apigw_event({
        "action_type": "inspected",
        "ear_tag": EAR_TAG,
    })
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 409
    body = json.loads(result["body"])
    assert "confirmed" in body["message"].lower()
