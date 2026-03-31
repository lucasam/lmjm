"""Unit tests for cattle GET Lambda handlers.

Validates:
- Requirement 5.1: GET /cattle/animals returns all cattle animals
- Requirement 5.2: GET /cattle/animals/{animal_id} returns animal by ear_tag
- Requirement 5.3: GET /cattle/animals/{animal_id} returns 404 if not found
- Requirement 5.4: GET /cattle/animals/{animal_id}/inseminations returns history sorted desc
- Requirement 5.5: GET /cattle/animals/{animal_id}/diagnostics returns history sorted desc
"""

import importlib
import json
import os
from typing import Any

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")


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


def _seed_cattle(table: Any) -> None:
    """Seed two cattle animals with species attribute for list_cattle scan filter."""
    table.put_item(
        Item={
            "pk": "animal-uuid-1",
            "sk": "Animal",
            "ear_tag": "BR001",
            "breed": "Nelore",
            "sex": "Female",
            "status": "active",
            "species": "cattle",
        }
    )
    table.put_item(
        Item={
            "pk": "animal-uuid-2",
            "sk": "Animal",
            "ear_tag": "BR002",
            "breed": "Angus",
            "sex": "Male",
            "status": "active",
            "species": "cattle",
        }
    )


def _seed_inseminations(table: Any) -> None:
    """Seed insemination records for animal-uuid-1 in non-chronological insert order."""
    table.put_item(
        Item={"pk": "animal-uuid-1", "sk": "Insemination|20250110", "insemination_date": "2025-01-10", "semen": "Bull A"}
    )
    table.put_item(
        Item={"pk": "animal-uuid-1", "sk": "Insemination|20250301", "insemination_date": "2025-03-01", "semen": "Bull B"}
    )
    table.put_item(
        Item={"pk": "animal-uuid-1", "sk": "Insemination|20250215", "insemination_date": "2025-02-15", "semen": "Bull C"}
    )


def _seed_diagnostics(table: Any) -> None:
    """Seed diagnostic records for animal-uuid-1 in non-chronological insert order."""
    table.put_item(
        Item={
            "pk": "animal-uuid-1",
            "sk": "Diagnostic|20250120",
            "diagnostic_date": "2025-01-20",
            "pregnant": True,
            "semen": "Bull A",
        }
    )
    table.put_item(
        Item={
            "pk": "animal-uuid-1",
            "sk": "Diagnostic|20250320",
            "diagnostic_date": "2025-03-20",
            "pregnant": False,
        }
    )
    table.put_item(
        Item={
            "pk": "animal-uuid-1",
            "sk": "Diagnostic|20250225",
            "diagnostic_date": "2025-02-25",
            "pregnant": True,
            "expected_delivery_date": "2025-12-10",
            "semen": "Bull C",
        }
    )


# ── get_cattle_animals tests ────────────────────────────────────────────────────


@mock_aws
def test_get_cattle_animals_returns_all_cattle() -> None:
    """Requirement 5.1: GET /cattle/animals returns JSON array of all cattle animals."""
    table = _create_table()
    _seed_cattle(table)

    import lmjm.get_cattle_animals as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 2
    ear_tags = {a["ear_tag"] for a in body}
    assert ear_tags == {"BR001", "BR002"}


@mock_aws
def test_get_cattle_animals_returns_empty_list_when_no_cattle() -> None:
    """Requirement 5.1: Returns empty array when no cattle exist."""
    _create_table()

    import lmjm.get_cattle_animals as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == []


# ── get_cattle_animal tests ─────────────────────────────────────────────────────


@mock_aws
def test_get_cattle_animal_returns_animal_by_ear_tag() -> None:
    """Requirement 5.2: GET /cattle/animals/{animal_id} returns full record by ear_tag."""
    table = _create_table()
    _seed_cattle(table)

    import lmjm.get_cattle_animal as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"animal_id": "BR001"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["ear_tag"] == "BR001"
    assert body["breed"] == "Nelore"


@mock_aws
def test_get_cattle_animal_returns_404_when_not_found() -> None:
    """Requirement 5.3: Returns 404 with message when ear_tag not found."""
    _create_table()

    import lmjm.get_cattle_animal as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"animal_id": "NONEXISTENT"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Animal not found"


# ── get_inseminations tests ─────────────────────────────────────────────────────


@mock_aws
def test_get_inseminations_returns_sorted_desc() -> None:
    """Requirement 5.4: GET inseminations returns history sorted by date descending."""
    table = _create_table()
    _seed_cattle(table)
    _seed_inseminations(table)

    import lmjm.get_inseminations as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"animal_id": "BR001"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3
    dates = [i["insemination_date"] for i in body]
    assert dates == ["2025-03-01", "2025-02-15", "2025-01-10"]


@mock_aws
def test_get_inseminations_returns_404_when_animal_not_found() -> None:
    """Requirement 5.4: Returns 404 when animal ear_tag not found."""
    _create_table()

    import lmjm.get_inseminations as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"animal_id": "NONEXISTENT"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Animal not found"


# ── get_diagnostics tests ───────────────────────────────────────────────────────


@mock_aws
def test_get_diagnostics_returns_sorted_desc() -> None:
    """Requirement 5.5: GET diagnostics returns history sorted by date descending."""
    table = _create_table()
    _seed_cattle(table)
    _seed_diagnostics(table)

    import lmjm.get_diagnostics as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"animal_id": "BR001"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 3
    dates = [d["diagnostic_date"] for d in body]
    assert dates == ["2025-03-20", "2025-02-25", "2025-01-20"]


@mock_aws
def test_get_diagnostics_returns_404_when_animal_not_found() -> None:
    """Requirement 5.5: Returns 404 when animal ear_tag not found."""
    _create_table()

    import lmjm.get_diagnostics as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"animal_id": "NONEXISTENT"}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert body["message"] == "Animal not found"
