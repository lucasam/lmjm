"""Property-based tests for post_procedure Lambda handler.

Feature: cattle-procedure

**Validates: Requirements 1.1**
"""

import calendar
import importlib
import json
import re
from typing import Any

import boto3
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

# --- Strategies ---

year_st = st.integers(min_value=2000, max_value=2099)
month_st = st.integers(min_value=1, max_value=12)


@st.composite
def valid_yyyymmdd_st(draw: st.DrawFn) -> str:
    """Generate valid date strings in YYYYMMDD format."""
    year = draw(year_st)
    month = draw(month_st)
    max_day = calendar.monthrange(year, month)[1]
    day = draw(st.integers(min_value=1, max_value=max_day))
    return f"{year:04d}{month:02d}{day:02d}"


# --- Helpers ---

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
PK_RE = re.compile(
    r"^Procedure\|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
DATE_STORED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ensure_table() -> Any:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    try:
        table = dynamodb.Table("lmjm")
        table.load()
        return table
    except Exception:
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


# --- Property Tests ---


# Feature: cattle-procedure, Property 1: Procedure creation produces valid record
@mock_aws
@given(date_str=valid_yyyymmdd_st())
@settings(max_examples=100, deadline=None)
def test_procedure_creation_produces_valid_record(date_str: str) -> None:
    """Property 1: Procedure creation produces valid record.

    For any valid date string in YYYYMMDD format, creating a Procedure SHALL
    produce a record with a unique pk matching the pattern "Procedure|{uuid}",
    the date stored in YYYY-MM-DD format, and status "open".

    **Validates: Requirements 1.1**
    """
    _ensure_table()

    import lmjm.post_procedure as mod

    importlib.reload(mod)

    event = _apigw_event({"procedure_date": date_str})
    result = mod.lambda_handler(event, None)

    # Verify 201 status code
    assert result["statusCode"] == 201, (
        f"Expected 201, got {result['statusCode']}"
    )

    body = json.loads(result["body"])

    # Verify pk matches "Procedure|{uuid}" pattern
    assert PK_RE.match(body["pk"]), (
        f"pk does not match Procedure|{{uuid}} pattern: {body['pk']}"
    )

    # Verify the uuid portion is valid
    uuid_part = body["pk"].split("|", 1)[1]
    assert UUID_RE.match(uuid_part), f"UUID portion is invalid: {uuid_part}"

    # Verify procedure_date is stored in YYYY-MM-DD format
    assert DATE_STORED_RE.match(body["procedure_date"]), (
        f"procedure_date not in YYYY-MM-DD format: {body['procedure_date']}"
    )

    # Verify the stored date matches the input date
    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    expected_date = f"{year:04d}-{month:02d}-{day:02d}"
    assert body["procedure_date"] == expected_date, (
        f"Date mismatch: input={date_str}, "
        f"stored={body['procedure_date']}, expected={expected_date}"
    )

    # Verify status is "open"
    assert body["status"] == "open", (
        f"Expected status 'open', got '{body['status']}'"
    )
