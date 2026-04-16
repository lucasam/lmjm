"""Unit tests for FeedConsumptionTemplate API handlers (POST edge cases, GET sorting)
and plan generation error cases.

Validates: Requirements 2.1, 2.4, 2.5, 4.4, 4.5, 4.6, 4.7
"""

import importlib
import json
from decimal import Decimal
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.model import Batch, FeedConsumptionPlan, FeedConsumptionTemplate
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize


def _decimal_default(o: Any) -> Any:
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def _decimal_safe_serialize(obj: object, schema: Any = None) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj, schema)
    return json.loads(json.dumps(d, default=_decimal_default), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    for repo_mod in [
        "lmjm.repo.feed_consumption_template_repo",
        "lmjm.repo.feed_consumption_plan_repo",
        "lmjm.repo.batch_repo",
    ]:
        monkeypatch.setattr(f"{repo_mod}.serialize_to_dict", _decimal_safe_serialize)


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


def _put(table: Any, obj: object) -> None:
    table.put_item(Item=_decimal_safe_serialize(obj))


def _post_event(body: dict[str, Any]) -> dict[str, Any]:
    return {"body": json.dumps(body)}


# ── POST: negative sequence returns 400 (Requirement 2.4) ───────────────────────


@mock_aws
def test_post_template_negative_sequence_returns_400() -> None:
    """Requirement 2.4: sequence < 0 returns HTTP 400."""
    _create_table()

    import lmjm.post_feed_consumption_template as mod

    importlib.reload(mod)

    result = mod.lambda_handler(
        _post_event({"sequence": -1, "expected_piglet_weight": 100, "expected_kg_per_animal": 0.5}),
        None,
    )

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "sequence" in body["message"]


# ── POST: negative expected_kg_per_animal returns 400 (Requirement 2.5) ──────────


@mock_aws
def test_post_template_negative_kg_returns_400() -> None:
    """Requirement 2.5: expected_kg_per_animal < 0 returns HTTP 400."""
    _create_table()

    import lmjm.post_feed_consumption_template as mod

    importlib.reload(mod)

    result = mod.lambda_handler(
        _post_event({"sequence": 1, "expected_piglet_weight": 100, "expected_kg_per_animal": -0.5}),
        None,
    )

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "expected_kg_per_animal" in body["message"]


# ── GET: returns entries sorted by sequence (Requirement 2.1) ────────────────────


@mock_aws
def test_get_templates_returns_sorted_by_sequence() -> None:
    """Requirement 2.1: GET returns all entries sorted by sequence (ascending)."""
    table = _create_table()

    # Insert entries out of order to verify sorting
    _put(
        table,
        FeedConsumptionTemplate(
            pk="FEED_CONSUMPTION_TEMPLATE",
            sk="FeedConsumptionTemplate|30",
            sequence=30,
            expected_piglet_weight=Decimal("8000"),
            expected_kg_per_animal=Decimal("1.200"),
        ),
    )
    _put(
        table,
        FeedConsumptionTemplate(
            pk="FEED_CONSUMPTION_TEMPLATE",
            sk="FeedConsumptionTemplate|10",
            sequence=10,
            expected_piglet_weight=Decimal("4000"),
            expected_kg_per_animal=Decimal("0.500"),
        ),
    )
    _put(
        table,
        FeedConsumptionTemplate(
            pk="FEED_CONSUMPTION_TEMPLATE",
            sk="FeedConsumptionTemplate|20",
            sequence=20,
            expected_piglet_weight=Decimal("6000"),
            expected_kg_per_animal=Decimal("0.800"),
        ),
    )

    import lmjm.get_feed_consumption_templates as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)
    assert result["statusCode"] == 200

    body = json.loads(result["body"])
    assert len(body) == 3
    # Verify ascending sequence order
    assert body[0]["sequence"] == 10
    assert body[1]["sequence"] == 20
    assert body[2]["sequence"] == 30


# ── Helpers for plan generation tests ────────────────────────────────────────────


def _generate_event(batch_id: str) -> dict[str, Any]:
    return {"pathParameters": {"batch_id": batch_id}}


def _seed_templates(table: Any) -> None:
    """Insert a small set of templates sorted by sequence."""
    for seq, weight, kg in [
        (1, "3000", "0.300"),
        (2, "5000", "0.500"),
        (3, "7000", "0.800"),
    ]:
        _put(
            table,
            FeedConsumptionTemplate(
                pk="FEED_CONSUMPTION_TEMPLATE",
                sk=f"FeedConsumptionTemplate|{seq}",
                sequence=seq,
                expected_piglet_weight=Decimal(weight),
                expected_kg_per_animal=Decimal(kg),
            ),
        )


# ── Generate plan: batch not found returns 404 ──────────────────────────────────


@mock_aws
def test_generate_plan_batch_not_found_returns_404() -> None:
    """Batch not found returns HTTP 404."""
    _create_table()

    import lmjm.post_generate_feed_plan as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_generate_event("nonexistent-batch"), None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "not found" in body["message"].lower()


# ── Generate plan: no average_start_date returns 400 (Requirement 4.5) ───────────


@mock_aws
def test_generate_plan_no_start_date_returns_400() -> None:
    """Requirement 4.5: Missing average_start_date returns HTTP 400."""
    table = _create_table()
    batch_id = "batch-no-date"

    _put(
        table,
        Batch(
            pk=batch_id,
            sk="Batch",
            average_start_date=None,
            initial_animal_weight=Decimal("4000"),
        ),
    )

    import lmjm.post_generate_feed_plan as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_generate_event(batch_id), None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "average_start_date" in body["message"]


# ── Generate plan: no initial_animal_weight returns 400 (Requirement 4.6) ────────


@mock_aws
def test_generate_plan_no_initial_weight_returns_400() -> None:
    """Requirement 4.6: Missing initial_animal_weight returns HTTP 400."""
    table = _create_table()
    batch_id = "batch-no-weight"

    _put(
        table,
        Batch(
            pk=batch_id,
            sk="Batch",
            average_start_date="2025-01-15",
            initial_animal_weight=None,
        ),
    )

    import lmjm.post_generate_feed_plan as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_generate_event(batch_id), None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "initial_animal_weight" in body["message"]


# ── Generate plan: no matching template entry returns 400 (Requirement 4.7) ──────


@mock_aws
def test_generate_plan_no_matching_template_returns_400() -> None:
    """Requirement 4.7: No template with expected_piglet_weight >= initial_animal_weight returns HTTP 400."""
    table = _create_table()
    batch_id = "batch-heavy"

    # Batch weight exceeds all template weights
    _put(
        table,
        Batch(
            pk=batch_id,
            sk="Batch",
            average_start_date="2025-01-15",
            initial_animal_weight=Decimal("99999"),
        ),
    )
    _seed_templates(table)

    import lmjm.post_generate_feed_plan as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_generate_event(batch_id), None)

    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "no template entry found" in body["message"].lower()


# ── Generate plan: existing entries deleted before writing (Requirement 4.4) ─────


@mock_aws
def test_generate_plan_deletes_existing_before_writing() -> None:
    """Requirement 4.4: Existing FeedConsumptionPlan entries are deleted before new ones are written."""
    table = _create_table()
    batch_id = "batch-regen"

    _put(
        table,
        Batch(
            pk=batch_id,
            sk="Batch",
            average_start_date="2025-03-01",
            initial_animal_weight=Decimal("4000"),
        ),
    )
    _seed_templates(table)

    # Pre-populate old plan entries that should be deleted
    for day in range(1, 6):
        _put(
            table,
            FeedConsumptionPlan(
                pk=batch_id,
                sk=f"FeedConsumptionPlan|{day}",
                day_number=day,
                expected_kg_per_animal=Decimal("0.100"),
                expected_piglet_weight=Decimal("1000"),
                date=f"2025-02-{day:02d}",
            ),
        )

    import lmjm.post_generate_feed_plan as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_generate_event(batch_id), None)
    assert result["statusCode"] == 200

    body = json.loads(result["body"])

    # Templates: weight 3000 < 4000, weight 5000 >= 4000 (match), weight 7000 >= 4000
    # So plan should start from template seq=2 (weight=5000), producing 2 entries
    assert len(body) == 2
    assert body[0]["day_number"] == 1
    assert body[0]["expected_piglet_weight"] == 5000
    assert body[1]["day_number"] == 2
    assert body[1]["expected_piglet_weight"] == 7000

    # Verify old entries are gone — query DynamoDB directly
    from boto3.dynamodb.conditions import Key

    resp = table.query(
        KeyConditionExpression=Key("pk").eq(batch_id) & Key("sk").begins_with("FeedConsumptionPlan|"),
    )
    items = resp["Items"]
    # Only the 2 new entries should exist, not the 5 old ones
    assert len(items) == 2
    day_numbers = sorted(int(item["day_number"]) for item in items)
    assert day_numbers == [1, 2]
