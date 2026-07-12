"""Unit tests for the PutEarTag Lambda (replace an animal's ear_tag)."""

import importlib
import json
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


def _seed_animal(table: Any, pk: str, ear_tag: str) -> None:
    table.put_item(Item={"pk": pk, "sk": "Animal", "ear_tag": ear_tag, "species": "cattle", "breed": "Nelore"})


def _event(animal_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return {"pathParameters": {"animal_id": animal_id}, "body": json.dumps(body)}


def _query_by_ear_tag(table: Any, ear_tag: str) -> list[dict[str, Any]]:
    resp = table.query(
        IndexName="ear_tag-sk-index",
        KeyConditionExpression=Key("ear_tag").eq(ear_tag) & Key("sk").eq("Animal"),
    )
    return resp["Items"]


@mock_aws
def test_replace_ear_tag_success() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "4188")

    import lmjm.put_ear_tag as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("4188", {"new_ear_tag": "9999"}), None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["ear_tag"] == "9999"
    assert body["pk"] == "uuid-1"

    # Old tag no longer resolves; new tag points to the same animal record
    assert _query_by_ear_tag(table, "4188") == []
    new_records = _query_by_ear_tag(table, "9999")
    assert len(new_records) == 1
    assert new_records[0]["pk"] == "uuid-1"


@mock_aws
def test_replace_ear_tag_trims_whitespace() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "4188")

    import lmjm.put_ear_tag as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("4188", {"new_ear_tag": "  777  "}), None)
    assert result["statusCode"] == 200
    assert json.loads(result["body"])["ear_tag"] == "777"


@mock_aws
def test_replace_ear_tag_returns_404_when_animal_missing() -> None:
    _create_table()

    import lmjm.put_ear_tag as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("NOPE", {"new_ear_tag": "9999"}), None)
    assert result["statusCode"] == 404


@mock_aws
def test_replace_ear_tag_returns_409_when_target_in_use() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "4188")
    _seed_animal(table, "uuid-2", "5000")

    import lmjm.put_ear_tag as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("4188", {"new_ear_tag": "5000"}), None)
    assert result["statusCode"] == 409

    # Nothing changed: 4188 still resolves to uuid-1
    records = _query_by_ear_tag(table, "4188")
    assert len(records) == 1
    assert records[0]["pk"] == "uuid-1"


@mock_aws
def test_replace_ear_tag_returns_400_when_empty() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "4188")

    import lmjm.put_ear_tag as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event("4188", {"new_ear_tag": "   "}), None)["statusCode"] == 400


@mock_aws
def test_replace_ear_tag_same_value_is_noop() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "4188")

    import lmjm.put_ear_tag as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event("4188", {"new_ear_tag": "4188"}), None)
    assert result["statusCode"] == 200
    assert json.loads(result["body"])["ear_tag"] == "4188"
