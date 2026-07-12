"""Unit tests for appending notes and tags to a cattle animal."""

import importlib
import json
from datetime import datetime
from typing import Any

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_aws


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")


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


def _seed_animal(table: Any, pk: str, ear_tag: str, **extra: Any) -> None:
    item = {"pk": pk, "sk": "Animal", "ear_tag": ear_tag, "species": "cattle"}
    item.update(extra)
    table.put_item(Item=item)


def _get_animal(table: Any, pk: str) -> dict[str, Any]:
    return table.get_item(Key={"pk": pk, "sk": "Animal"})["Item"]


def _event(animal_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return {"pathParameters": {"animal_id": animal_id}, "body": json.dumps(body)}


# ── Notes ────────────────────────────────────────────────────────────────────


@mock_aws
def test_add_note_success_prefixes_date_and_appends() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6", notes=["old note"])

    import lmjm.post_animal_note as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("6", {"note": "Comeu bem"}), None)
    assert result["statusCode"] == 201

    notes = _get_animal(table, "uuid-1")["notes"]
    assert len(notes) == 2
    assert notes[0] == "old note"  # preserved, appended at end
    today = datetime.now().strftime("%d-%m-%Y")
    assert notes[1] == f"{today}: Comeu bem"


@mock_aws
def test_add_note_creates_list_when_absent() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6")

    import lmjm.post_animal_note as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("6", {"note": "Primeira"}), None)
    assert result["statusCode"] == 201
    notes = _get_animal(table, "uuid-1")["notes"]
    assert len(notes) == 1
    assert notes[0].endswith(": Primeira")


@mock_aws
def test_add_note_400_when_empty() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6")

    import lmjm.post_animal_note as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event("6", {"note": "   "}), None)["statusCode"] == 400


@mock_aws
def test_add_note_404_when_missing() -> None:
    _create_table()

    import lmjm.post_animal_note as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event("NOPE", {"note": "x"}), None)["statusCode"] == 404


# ── Tags ─────────────────────────────────────────────────────────────────────


@mock_aws
def test_add_tag_success() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6", tags=["lote1"])

    import lmjm.post_animal_tag as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("6", {"tag": "vendida"}), None)
    assert result["statusCode"] == 201
    tags = _get_animal(table, "uuid-1")["tags"]
    assert tags == ["lote1", "vendida"]


@mock_aws
def test_add_tag_deduplicates() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6", tags=["lote1"])

    import lmjm.post_animal_tag as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("6", {"tag": "lote1"}), None)
    assert result["statusCode"] == 201
    tags = _get_animal(table, "uuid-1")["tags"]
    assert tags == ["lote1"]


@mock_aws
def test_add_tag_400_when_empty() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6")

    import lmjm.post_animal_tag as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event("6", {"tag": ""}), None)["statusCode"] == 400


@mock_aws
def test_add_tag_404_when_missing() -> None:
    _create_table()

    import lmjm.post_animal_tag as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event("NOPE", {"tag": "x"}), None)["statusCode"] == 404
