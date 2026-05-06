"""Unit tests for post_procedure Lambda handler.

Feature: cattle-procedure

**Validates: Requirements 1.1, 1.2**
"""

import importlib
import json
import re
from typing import Any

import boto3
import pytest
from moto import mock_aws

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


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


def _apigw_event(body: dict[str, Any]) -> dict[str, Any]:
    return {"body": json.dumps(body)}


@mock_aws
def test_valid_date_creates_procedure_with_correct_fields() -> None:
    """Requirement 1.1: Valid YYYYMMDD date creates a Procedure with correct pk, date, and status."""
    _create_table()

    import lmjm.post_procedure as mod

    importlib.reload(mod)

    event = _apigw_event({"procedure_date": "20250715"})
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 201

    body = json.loads(result["body"])

    # pk matches "Procedure|{uuid}" pattern
    assert body["pk"].startswith("Procedure|")
    uuid_part = body["pk"].split("|", 1)[1]
    assert UUID_RE.match(uuid_part), f"UUID portion is invalid: {uuid_part}"

    # Date stored in YYYY-MM-DD format
    assert body["procedure_date"] == "2025-07-15"

    # Status is "open"
    assert body["status"] == "open"


@mock_aws
def test_invalid_date_format_returns_400() -> None:
    """Requirement 1.2: Invalid date format returns 400 with descriptive message."""
    _create_table()

    import lmjm.post_procedure as mod

    importlib.reload(mod)

    event = _apigw_event({"procedure_date": "not-a-date"})
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400

    body = json.loads(result["body"])
    assert "YYYYMMDD" in body["message"]


@mock_aws
def test_missing_date_returns_400() -> None:
    """Requirement 1.2: Missing procedure_date returns 400."""
    _create_table()

    import lmjm.post_procedure as mod

    importlib.reload(mod)

    event = _apigw_event({})
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400
