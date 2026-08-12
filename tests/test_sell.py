"""Unit tests for cattle Sell create (POST) and list (GET) Lambdas."""

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


def _seed_animal(table: Any, pk: str, ear_tag: str, status: str = "Ativa") -> None:
    table.put_item(Item={"pk": pk, "sk": "Animal", "ear_tag": ear_tag, "species": "cattle", "status": status})


def _animal_by_ear_tag(table: Any, ear_tag: str) -> dict[str, Any]:
    resp = table.query(
        IndexName="ear_tag-sk-index",
        KeyConditionExpression=Key("ear_tag").eq(ear_tag) & Key("sk").eq("Animal"),
    )
    return resp["Items"][0]


def _event(body: dict[str, Any]) -> dict[str, Any]:
    return {"body": json.dumps(body)}


def _base_body(**overrides: Any) -> dict[str, Any]:
    body = {
        "sell_date": "20250115",
        "number_of_animals": 10,
        "animal_age": 24,
        "sex": "M",
        "batch": "L1",
        "buyer": "Frigorifico X",
        "description": "venda gordo",
        "average_weight": 18.5,
        "unit_value": 5000,
        "total_value": 50000,
        "total_commission": 1000,
        "total_transportation": 2000,
        "price_per_arroba": 320.5,
    }
    body.update(overrides)
    return body


@mock_aws
def test_create_sell_success_computes_net_value() -> None:
    _create_table()

    import lmjm.post_sell as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event(_base_body()), None)
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["sell_date"] == "2025-01-15"
    assert body["number_of_animals"] == 10
    assert body["sex"] == "M"  # Sex serialized by value
    assert body["unit_value"] == 5000
    assert body["net_value"] == 47000  # 50000 - 1000 - 2000
    assert body["pk"].startswith("Sell|")


@mock_aws
def test_create_sell_400_on_invalid_sex() -> None:
    _create_table()

    import lmjm.post_sell as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event(_base_body(sex="Male")), None)["statusCode"] == 400


@mock_aws
def test_create_sell_flips_associated_animals_to_vendida() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "BR001", status="Ativa")
    _seed_animal(table, "uuid-2", "BR002", status="Ativa")

    import lmjm.post_sell as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event(_base_body(associated_ear_tags=["BR001", "BR002"])), None)
    assert result["statusCode"] == 201

    assert _animal_by_ear_tag(table, "BR001")["status"] == "Vendida"
    assert _animal_by_ear_tag(table, "BR002")["status"] == "Vendida"

    body = json.loads(result["body"])
    assert body["associated_ear_tags"] == ["BR001", "BR002"]


@mock_aws
def test_create_sell_ignores_missing_associated_animal() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "BR001", status="Ativa")

    import lmjm.post_sell as mod

    importlib.reload(mod)

    # BR999 does not exist; sell should still be created and BR001 flipped.
    result = mod.lambda_handler(_event(_base_body(associated_ear_tags=["BR001", "BR999"])), None)
    assert result["statusCode"] == 201
    assert _animal_by_ear_tag(table, "BR001")["status"] == "Vendida"


@mock_aws
def test_create_sell_400_on_invalid_date() -> None:
    _create_table()

    import lmjm.post_sell as mod

    importlib.reload(mod)

    assert mod.lambda_handler(_event(_base_body(sell_date="2025-01-15")), None)["statusCode"] == 400


@mock_aws
def test_create_sell_minimal_without_associations() -> None:
    _create_table()

    import lmjm.post_sell as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_event({"sell_date": "20250110", "number_of_animals": 5}), None)
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["net_value"] == 0
    assert "associated_ear_tags" not in body  # None omitted by skip_none_values


def _sell_id(create_result: dict[str, Any]) -> str:
    return json.loads(create_result["body"])["pk"].split("|", 1)[1]


@mock_aws
def test_get_sell_returns_record() -> None:
    _create_table()

    import lmjm.post_sell as post_mod
    import lmjm.get_sell as get_mod

    importlib.reload(post_mod)
    importlib.reload(get_mod)

    created = post_mod.lambda_handler(_event(_base_body()), None)
    sid = _sell_id(created)

    result = get_mod.lambda_handler({"pathParameters": {"sell_id": sid}}, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["buyer"] == "Frigorifico X"
    assert body["net_value"] == 47000


@mock_aws
def test_get_sell_404_when_missing() -> None:
    _create_table()

    import lmjm.get_sell as get_mod

    importlib.reload(get_mod)

    result = get_mod.lambda_handler({"pathParameters": {"sell_id": "nope"}}, None)
    assert result["statusCode"] == 404


@mock_aws
def test_update_sell_changes_values_and_recomputes_net() -> None:
    _create_table()

    import lmjm.post_sell as post_mod
    import lmjm.put_sell as put_mod

    importlib.reload(post_mod)
    importlib.reload(put_mod)

    created = post_mod.lambda_handler(_event(_base_body()), None)
    sid = _sell_id(created)

    event = {
        "pathParameters": {"sell_id": sid},
        "body": json.dumps(
            _base_body(total_value=60000, total_commission=1500, total_transportation=2500, buyer="Novo Comprador")
        ),
    }
    result = put_mod.lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["buyer"] == "Novo Comprador"
    assert body["net_value"] == 56000  # 60000 - 1500 - 2500
    assert body["pk"] == f"Sell|{sid}"


@mock_aws
def test_update_sell_404_when_missing() -> None:
    _create_table()

    import lmjm.put_sell as put_mod

    importlib.reload(put_mod)

    event = {"pathParameters": {"sell_id": "nope"}, "body": json.dumps(_base_body())}
    assert put_mod.lambda_handler(event, None)["statusCode"] == 404


@mock_aws
def test_update_sell_does_not_fail_on_missing_associated_animal() -> None:
    table = _create_table()
    _seed_animal(table, "uuid-1", "BR001", status="Ativa")

    import lmjm.post_sell as post_mod
    import lmjm.put_sell as put_mod

    importlib.reload(post_mod)
    importlib.reload(put_mod)

    created = post_mod.lambda_handler(_event(_base_body()), None)
    sid = _sell_id(created)

    # BR999 doesn't exist; save must still succeed and BR001 must be flipped.
    event = {
        "pathParameters": {"sell_id": sid},
        "body": json.dumps(_base_body(associated_ear_tags=["BR001", "BR999"])),
    }
    result = put_mod.lambda_handler(event, None)
    assert result["statusCode"] == 200
    assert _animal_by_ear_tag(table, "BR001")["status"] == "Vendida"


@mock_aws
def test_list_sells_sorted_desc() -> None:
    _create_table()

    import lmjm.post_sell as post_mod
    import lmjm.get_sells as get_mod

    importlib.reload(post_mod)
    importlib.reload(get_mod)

    post_mod.lambda_handler(_event(_base_body(sell_date="20250110")), None)
    post_mod.lambda_handler(_event(_base_body(sell_date="20250115")), None)
    post_mod.lambda_handler(_event(_base_body(sell_date="20250101")), None)

    result = get_mod.lambda_handler({}, None)
    assert result["statusCode"] == 200
    sells = json.loads(result["body"])
    assert [s["sell_date"] for s in sells] == ["2025-01-15", "2025-01-10", "2025-01-01"]
