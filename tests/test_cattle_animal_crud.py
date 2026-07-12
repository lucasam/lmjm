"""Unit tests for cattle animal create (POST) and update (PUT) Lambdas."""

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


def _seed_animal(table: Any, pk: str, ear_tag: str, **extra: Any) -> None:
    item = {"pk": pk, "sk": "Animal", "ear_tag": ear_tag, "species": "cattle"}
    item.update(extra)
    table.put_item(Item=item)


def _by_ear_tag(table: Any, ear_tag: str) -> list[dict[str, Any]]:
    resp = table.query(
        IndexName="ear_tag-sk-index",
        KeyConditionExpression=Key("ear_tag").eq(ear_tag) & Key("sk").eq("Animal"),
    )
    return resp["Items"]


# ── Create (POST /cattle/animals) ───────────────────────────────────────────


@mock_aws
def test_create_animal_success() -> None:
    table = _create_table()

    import lmjm.post_cattle_animal as mod

    importlib.reload(mod)

    event = {
        "body": json.dumps(
            {"ear_tag": "6", "breed": "Nelore", "sex": "F", "status": "Ativa", "inseminated": True, "tags": ["lote1"]}
        )
    }
    result = mod.lambda_handler(event, None)
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["ear_tag"] == "6"
    assert body["species"] == "cattle"
    assert body["inseminated"] is True
    assert body["pk"]  # a generated uuid

    records = _by_ear_tag(table, "6")
    assert len(records) == 1


@mock_aws
def test_create_animal_conflict_when_ear_tag_exists() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6")

    import lmjm.post_cattle_animal as mod

    importlib.reload(mod)

    result = mod.lambda_handler({"body": json.dumps({"ear_tag": "6"})}, None)
    assert result["statusCode"] == 409


@mock_aws
def test_create_animal_400_when_ear_tag_empty() -> None:
    _create_table()

    import lmjm.post_cattle_animal as mod

    importlib.reload(mod)

    result = mod.lambda_handler({"body": json.dumps({"ear_tag": "   "})}, None)
    assert result["statusCode"] == 400


# ── Update (PUT /cattle/animals/{animal_id}) ────────────────────────────────


@mock_aws
def test_update_animal_success() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6", breed="Nelore", status="Ativa")

    import lmjm.put_cattle_animal as mod

    importlib.reload(mod)

    event = {
        "pathParameters": {"animal_id": "6"},
        "body": json.dumps({"breed": "Angus", "status": "Inativa", "pregnant": True}),
    }
    result = mod.lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["breed"] == "Angus"
    assert body["status"] == "Inativa"
    assert body["pregnant"] is True
    assert body["ear_tag"] == "6"


@mock_aws
def test_update_animal_preserves_unsent_fields() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6", breed="Nelore", notes=["nota antiga"])

    import lmjm.put_cattle_animal as mod

    importlib.reload(mod)

    # Body omits notes -> they must be preserved.
    event = {"pathParameters": {"animal_id": "6"}, "body": json.dumps({"breed": "Angus"})}
    result = mod.lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["breed"] == "Angus"
    assert body["notes"] == ["nota antiga"]


@mock_aws
def test_update_animal_ignores_ear_tag_change() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "6")

    import lmjm.put_cattle_animal as mod

    importlib.reload(mod)

    event = {"pathParameters": {"animal_id": "6"}, "body": json.dumps({"ear_tag": "999", "breed": "Angus"})}
    result = mod.lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["ear_tag"] == "6"  # unchanged

    assert _by_ear_tag(table, "999") == []
    assert len(_by_ear_tag(table, "6")) == 1


@mock_aws
def test_update_animal_404_when_missing() -> None:
    _create_table()

    import lmjm.put_cattle_animal as mod

    importlib.reload(mod)

    event = {"pathParameters": {"animal_id": "NOPE"}, "body": json.dumps({"breed": "Angus"})}
    assert mod.lambda_handler(event, None)["statusCode"] == 404
