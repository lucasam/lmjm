"""Property-based tests for post_procedure_action Lambda handler.

# Feature: cattle-procedure, Property 3: Valid action staging creates correct Staged_Action

**Validates: Requirements 2.5, 3.1, 4.1, 5.1, 6.1**
"""

import calendar
import importlib
import json
import re
import uuid
from typing import Any

import boto3
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from lmjm.model import Insemination
from lmjm.util.marshmallow_serializer import serialize_to_dict

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


positive_weight_st = st.integers(min_value=1, max_value=2000)
non_empty_str_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"), blacklist_characters="\x00"),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

action_type_st = st.sampled_from(["weight", "insemination", "diagnostic", "observation", "inspected"])


@st.composite
def valid_action_request_st(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a valid action request for any of the 5 action types."""
    action_type = draw(action_type_st)
    ear_tag = "TEST-001"
    body: dict[str, Any] = {"action_type": action_type, "ear_tag": ear_tag}

    if action_type == "weight":
        body["weighing_date"] = draw(valid_yyyymmdd_st())
        body["weight_kg"] = draw(positive_weight_st)
    elif action_type == "insemination":
        body["insemination_date"] = draw(valid_yyyymmdd_st())
        body["semen"] = draw(non_empty_str_st)
        if draw(st.booleans()):
            body["note"] = draw(non_empty_str_st)
    elif action_type == "diagnostic":
        body["diagnostic_date"] = draw(valid_yyyymmdd_st())
        body["pregnant"] = draw(st.booleans())
        if draw(st.booleans()):
            body["note"] = draw(non_empty_str_st)
        if draw(st.booleans()):
            body["tags"] = draw(non_empty_str_st)
    elif action_type == "observation":
        body["note"] = draw(non_empty_str_st)
    # inspected: no additional fields

    return body


# --- Helpers ---

PK_RE = re.compile(
    r"^Procedure\|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
ACTION_SK_RE = re.compile(
    r"^Action\|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

PROCEDURE_PK = f"Procedure|{uuid.uuid4()}"
ANIMAL_PK = f"Animal|{uuid.uuid4()}"
EAR_TAG = "TEST-001"


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


def _seed_procedure_and_animal(table: Any) -> None:
    """Create an open Procedure and an Animal record in the table."""
    table.put_item(
        Item={
            "pk": PROCEDURE_PK,
            "sk": "Procedure",
            "procedure_date": "2024-06-15",
            "status": "open",
        }
    )
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
    """Create an Insemination record for the animal (needed for diagnostic actions)."""
    insemination = Insemination(
        pk=ANIMAL_PK,
        sk="Insemination|20240601",
        insemination_date="2024-06-01",
        semen="Bull-A",
    )
    table.put_item(Item=serialize_to_dict(insemination))


def _apigw_event(body: dict[str, Any], procedure_id: str) -> dict[str, Any]:
    return {
        "body": json.dumps(body),
        "pathParameters": {"procedure_id": procedure_id},
    }


def _yyyymmdd_to_stored(date_str: str) -> str:
    """Convert YYYYMMDD to YYYY-MM-DD storage format."""
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"


# --- Property Test ---


# Feature: cattle-procedure, Property 3: Valid action staging creates correct Staged_Action
@mock_aws
@given(action_request=valid_action_request_st())
@settings(max_examples=100, deadline=None)
def test_valid_action_staging_creates_correct_staged_action(action_request: dict[str, Any]) -> None:
    """Property 3: Valid action staging creates correct Staged_Action.

    For any valid action request (weight with valid date and positive kg,
    insemination with valid date and non-empty semen, diagnostic with valid date
    and boolean pregnant, observation with non-empty note, or inspected with
    valid ear_tag), the system SHALL create a ProcedureAction with the correct
    action_type, ear_tag, and type-specific fields stored under the Procedure's pk.

    **Validates: Requirements 2.5, 3.1, 4.1, 5.1, 6.1**
    """
    table = _ensure_table()
    _seed_procedure_and_animal(table)
    _seed_insemination(table)

    import lmjm.post_procedure_action as mod

    importlib.reload(mod)

    procedure_id = PROCEDURE_PK.split("|", 1)[1]
    event = _apigw_event(action_request, procedure_id)
    result = mod.lambda_handler(event, None)

    # Verify 201 status code
    assert result["statusCode"] == 201, (
        f"Expected 201 for action_type={action_request['action_type']}, "
        f"got {result['statusCode']}: {result['body']}"
    )

    body = json.loads(result["body"])

    # Verify pk matches the Procedure pk
    assert body["pk"] == PROCEDURE_PK, (
        f"Expected pk={PROCEDURE_PK}, got {body['pk']}"
    )

    # Verify sk matches Action|{uuid} pattern
    assert ACTION_SK_RE.match(body["sk"]), (
        f"sk does not match Action|{{uuid}} pattern: {body['sk']}"
    )

    # Verify action_type matches request
    assert body["action_type"] == action_request["action_type"], (
        f"Expected action_type={action_request['action_type']}, got {body['action_type']}"
    )

    # Verify ear_tag matches request
    assert body["ear_tag"] == action_request["ear_tag"], (
        f"Expected ear_tag={action_request['ear_tag']}, got {body['ear_tag']}"
    )

    # Verify type-specific fields
    action_type = action_request["action_type"]

    if action_type == "weight":
        expected_date = _yyyymmdd_to_stored(action_request["weighing_date"])
        assert body["weighing_date"] == expected_date, (
            f"Expected weighing_date={expected_date}, got {body.get('weighing_date')}"
        )
        assert body["weight_kg"] == action_request["weight_kg"], (
            f"Expected weight_kg={action_request['weight_kg']}, got {body.get('weight_kg')}"
        )

    elif action_type == "insemination":
        expected_date = _yyyymmdd_to_stored(action_request["insemination_date"])
        assert body["insemination_date"] == expected_date, (
            f"Expected insemination_date={expected_date}, got {body.get('insemination_date')}"
        )
        assert body["semen"] == action_request["semen"], (
            f"Expected semen={action_request['semen']}, got {body.get('semen')}"
        )
        if "note" in action_request:
            assert body.get("note") == action_request["note"], (
                f"Expected note={action_request['note']}, got {body.get('note')}"
            )

    elif action_type == "diagnostic":
        expected_date = _yyyymmdd_to_stored(action_request["diagnostic_date"])
        assert body["diagnostic_date"] == expected_date, (
            f"Expected diagnostic_date={expected_date}, got {body.get('diagnostic_date')}"
        )
        assert body["pregnant"] == action_request["pregnant"], (
            f"Expected pregnant={action_request['pregnant']}, got {body.get('pregnant')}"
        )
        if "note" in action_request:
            assert body.get("note") == action_request["note"], (
                f"Expected note={action_request['note']}, got {body.get('note')}"
            )
        if "tags" in action_request:
            assert body.get("tags") == action_request["tags"], (
                f"Expected tags={action_request['tags']}, got {body.get('tags')}"
            )

    elif action_type == "observation":
        assert body["note"] == action_request["note"], (
            f"Expected note={action_request['note']}, got {body.get('note')}"
        )

    # inspected: no type-specific fields to verify beyond action_type and ear_tag


# ---------------------------------------------------------------------------
# Feature: cattle-procedure, Property 2: Invalid input rejection
# ---------------------------------------------------------------------------

# --- Strategies for invalid inputs ---

# Strings that are NOT valid YYYYMMDD dates
invalid_date_st = st.one_of(
    # Random text that can't be a date
    st.text(min_size=1, max_size=20).filter(
        lambda s: not _is_valid_yyyymmdd(s)
    ),
    # Dates with wrong separators
    st.from_regex(r"\d{4}-\d{2}-\d{2}", fullmatch=True),
    # Too short / too long digit strings
    st.from_regex(r"\d{1,7}", fullmatch=True),
    st.from_regex(r"\d{9,12}", fullmatch=True),
    # Empty string
    st.just(""),
)

# Zero or negative weight
non_positive_weight_st = st.integers(max_value=0)

# Empty or whitespace-only semen
empty_semen_st = st.one_of(
    st.just(""),
    st.text(alphabet=" \t\n\r", min_size=1, max_size=10),
)

# Empty or whitespace-only note
empty_note_st = st.one_of(
    st.just(""),
    st.text(alphabet=" \t\n\r", min_size=1, max_size=10),
)


def _is_valid_yyyymmdd(s: str) -> bool:
    """Check if a string is a valid YYYYMMDD date."""
    try:
        from datetime import datetime

        datetime.strptime(s, "%Y%m%d")
        return True
    except (ValueError, TypeError):
        return False


def _count_actions(table: Any, procedure_pk: str) -> int:
    """Count ProcedureAction records under a Procedure pk."""
    resp = table.query(
        KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
        ExpressionAttributeValues={":pk": procedure_pk, ":prefix": "Action|"},
    )
    return len(resp.get("Items", []))


# --- Property 2 Tests ---


# Feature: cattle-procedure, Property 2: Invalid input rejection
@mock_aws
@given(bad_date=invalid_date_st)
@settings(max_examples=50, deadline=None)
def test_invalid_procedure_date_returns_400(bad_date: str) -> None:
    """Property 2a: Invalid procedure_date is rejected.

    For any string that is not a valid YYYYMMDD date, creating a Procedure
    SHALL return a 400 status code without creating any records.

    **Validates: Requirements 1.2**
    """
    import lmjm.post_procedure as proc_mod

    importlib.reload(proc_mod)

    _ensure_table()

    event: dict[str, Any] = {"body": json.dumps({"procedure_date": bad_date})}
    result = proc_mod.lambda_handler(event, None)

    assert result["statusCode"] == 400, (
        f"Expected 400 for invalid date '{bad_date}', got {result['statusCode']}"
    )


# Feature: cattle-procedure, Property 2: Invalid input rejection
@mock_aws
@given(bad_date=invalid_date_st)
@settings(max_examples=50, deadline=None)
def test_weight_invalid_date_returns_400(bad_date: str) -> None:
    """Property 2b: Weight with invalid weighing_date is rejected.

    For any string that is not a valid YYYYMMDD date, submitting a weight
    action SHALL return a 400 status code and create no ProcedureAction records.

    **Validates: Requirements 3.2**
    """
    table = _ensure_table()
    _seed_procedure_and_animal(table)

    import lmjm.post_procedure_action as mod

    importlib.reload(mod)

    procedure_id = PROCEDURE_PK.split("|", 1)[1]
    body = {
        "action_type": "weight",
        "ear_tag": EAR_TAG,
        "weighing_date": bad_date,
        "weight_kg": 500,
    }
    event = _apigw_event(body, procedure_id)
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400, (
        f"Expected 400 for invalid weighing_date '{bad_date}', got {result['statusCode']}"
    )
    assert _count_actions(table, PROCEDURE_PK) == 0, (
        "No ProcedureAction should be created for invalid weighing_date"
    )


# Feature: cattle-procedure, Property 2: Invalid input rejection
@mock_aws
@given(bad_weight=non_positive_weight_st)
@settings(max_examples=50, deadline=None)
def test_weight_non_positive_kg_returns_400(bad_weight: int) -> None:
    """Property 2c: Weight with non-positive weight_kg is rejected.

    For any weight_kg that is zero or negative, submitting a weight action
    SHALL return a 400 status code and create no ProcedureAction records.

    **Validates: Requirements 3.2**
    """
    table = _ensure_table()
    _seed_procedure_and_animal(table)

    import lmjm.post_procedure_action as mod

    importlib.reload(mod)

    procedure_id = PROCEDURE_PK.split("|", 1)[1]
    body = {
        "action_type": "weight",
        "ear_tag": EAR_TAG,
        "weighing_date": "20240615",
        "weight_kg": bad_weight,
    }
    event = _apigw_event(body, procedure_id)
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400, (
        f"Expected 400 for non-positive weight_kg={bad_weight}, got {result['statusCode']}"
    )
    assert _count_actions(table, PROCEDURE_PK) == 0, (
        "No ProcedureAction should be created for non-positive weight_kg"
    )


# Feature: cattle-procedure, Property 2: Invalid input rejection
@mock_aws
@given(bad_semen=empty_semen_st)
@settings(max_examples=50, deadline=None)
def test_insemination_empty_semen_returns_400(bad_semen: str) -> None:
    """Property 2d: Insemination with empty semen is rejected.

    For any semen identifier that is empty or whitespace-only, submitting an
    insemination action SHALL return a 400 status code and create no
    ProcedureAction records.

    **Validates: Requirements 4.2**
    """
    table = _ensure_table()
    _seed_procedure_and_animal(table)

    import lmjm.post_procedure_action as mod

    importlib.reload(mod)

    procedure_id = PROCEDURE_PK.split("|", 1)[1]
    body = {
        "action_type": "insemination",
        "ear_tag": EAR_TAG,
        "insemination_date": "20240615",
        "semen": bad_semen,
    }
    event = _apigw_event(body, procedure_id)
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400, (
        f"Expected 400 for empty semen '{bad_semen!r}', got {result['statusCode']}"
    )
    assert _count_actions(table, PROCEDURE_PK) == 0, (
        "No ProcedureAction should be created for empty semen"
    )


# Feature: cattle-procedure, Property 2: Invalid input rejection
@mock_aws
@given(bad_note=empty_note_st)
@settings(max_examples=50, deadline=None)
def test_observation_empty_note_returns_400(bad_note: str) -> None:
    """Property 2e: Observation with empty note is rejected.

    For any note that is empty or whitespace-only, submitting an observation
    action SHALL return a 400 status code and create no ProcedureAction records.

    **Validates: Requirements 6.2**
    """
    table = _ensure_table()
    _seed_procedure_and_animal(table)

    import lmjm.post_procedure_action as mod

    importlib.reload(mod)

    procedure_id = PROCEDURE_PK.split("|", 1)[1]
    body = {
        "action_type": "observation",
        "ear_tag": EAR_TAG,
        "note": bad_note,
    }
    event = _apigw_event(body, procedure_id)
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400, (
        f"Expected 400 for empty note '{bad_note!r}', got {result['statusCode']}"
    )
    assert _count_actions(table, PROCEDURE_PK) == 0, (
        "No ProcedureAction should be created for empty note"
    )
