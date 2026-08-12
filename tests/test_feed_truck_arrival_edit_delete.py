"""Unit tests for the PUT (edit) and DELETE feed truck arrival Lambdas."""

import importlib
import json
from typing import Any

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_aws

BATCH_PK = "batch-123"
ARRIVAL_SK = "FeedTruckArrival|202603261200|abc"


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
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def _seed_batch(table: Any) -> None:
    table.put_item(Item={"pk": BATCH_PK, "sk": "Batch", "status": "created", "supply_id": 1, "module_id": "M#1"})


def _seed_arrival(table: Any, sk: str = ARRIVAL_SK, **extra: Any) -> None:
    item = {
        "pk": BATCH_PK,
        "sk": sk,
        "receive_date": "2026-03-26T12:00",
        "fiscal_document_number": "100",
        "actual_amount_kg": 5000,
        "feed_type": "130906",
        "feed_description": "ST06",
    }
    item.update(extra)
    table.put_item(Item=item)


def _get_arrival(table: Any, sk: str = ARRIVAL_SK) -> dict[str, Any]:
    return table.get_item(Key={"pk": BATCH_PK, "sk": sk})["Item"]


def _query_arrivals(table: Any) -> list[dict[str, Any]]:
    resp = table.query(KeyConditionExpression=Key("pk").eq(BATCH_PK) & Key("sk").begins_with("FeedTruckArrival|"))
    return resp["Items"]


def _put_event(body: dict[str, Any], sk: str = ARRIVAL_SK) -> dict[str, Any]:
    return {"pathParameters": {"batch_id": BATCH_PK, "arrival_sk": sk}, "body": json.dumps(body)}


# ── Update ───────────────────────────────────────────────────────────────────


@mock_aws
def test_update_feed_truck_arrival_success() -> None:
    table = _create_table()
    _seed_batch(table)
    _seed_arrival(table)

    import lmjm.put_feed_truck_arrival as mod

    importlib.reload(mod)

    result = mod.lambda_handler(
        _put_event({"actual_amount_kg": 7200, "fiscal_document_number": "200", "receive_date": "202604011030"}),
        None,
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["actual_amount_kg"] == 7200
    assert body["fiscal_document_number"] == "200"
    assert body["receive_date"] == "2026-04-01T10:30"
    # sk (identity) preserved
    assert body["sk"] == ARRIVAL_SK

    stored = _get_arrival(table)
    assert stored["actual_amount_kg"] == 7200


@mock_aws
def test_update_feed_truck_arrival_404_when_missing() -> None:
    table = _create_table()
    _seed_batch(table)

    import lmjm.put_feed_truck_arrival as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_put_event({"actual_amount_kg": 100}, sk="FeedTruckArrival|x|missing"), None)
    assert result["statusCode"] == 404


@mock_aws
def test_update_feed_truck_arrival_404_when_batch_missing() -> None:
    _create_table()

    import lmjm.put_feed_truck_arrival as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_put_event({"actual_amount_kg": 100}), None)
    assert result["statusCode"] == 404


@mock_aws
def test_update_feed_truck_arrival_400_on_invalid_amount() -> None:
    table = _create_table()
    _seed_batch(table)
    _seed_arrival(table)

    import lmjm.put_feed_truck_arrival as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_put_event({"actual_amount_kg": 0}), None)["statusCode"] == 400


# ── Delete ───────────────────────────────────────────────────────────────────


@mock_aws
def test_delete_feed_truck_arrival_success() -> None:
    table = _create_table()
    _seed_batch(table)
    _seed_arrival(table)

    import lmjm.delete_feed_truck_arrival as mod

    importlib.reload(mod)

    result = mod.lambda_handler({"pathParameters": {"batch_id": BATCH_PK, "arrival_sk": ARRIVAL_SK}}, None)
    assert result["statusCode"] == 200
    assert _query_arrivals(table) == []


@mock_aws
def test_delete_feed_truck_arrival_is_idempotent() -> None:
    table = _create_table()
    _seed_batch(table)

    import lmjm.delete_feed_truck_arrival as mod

    importlib.reload(mod)

    # Deleting a non-existent record does not error.
    result = mod.lambda_handler(
        {"pathParameters": {"batch_id": BATCH_PK, "arrival_sk": "FeedTruckArrival|x|none"}}, None
    )
    assert result["statusCode"] == 200
