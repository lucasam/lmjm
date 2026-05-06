"""Property-based tests for Procedure list ordering.

# Feature: cattle-procedure, Property 9: Procedure list is sorted with correct metadata

For any set of Procedures in the system, the list endpoint SHALL return them sorted by
procedure_date in descending order, and each entry SHALL include the correct status and
action_count (equal to the number of ProcedureAction records under that Procedure's pk).

**Validates: Requirements 9.1, 9.2**
"""

import datetime
import importlib
import json
import uuid
from typing import Any

import boto3
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from lmjm.model import ProcedureActionType, ProcedureStatus

# --- Strategies ---

# Generate dates in YYYY-MM-DD format (stored format)
date_st = st.dates(
    min_value=datetime.date(2020, 1, 1),
    max_value=datetime.date(2030, 12, 31),
).map(lambda d: d.isoformat())

status_st = st.sampled_from(list(ProcedureStatus))

action_type_st = st.sampled_from(list(ProcedureActionType))


@st.composite
def procedure_with_actions_st(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a Procedure with a random number of actions."""
    procedure_id = str(uuid.uuid4())
    pk = f"Procedure|{procedure_id}"
    procedure_date = draw(date_st)
    status = draw(status_st)
    num_actions = draw(st.integers(min_value=0, max_value=10))

    actions: list[dict[str, Any]] = []
    for _ in range(num_actions):
        action_type = draw(action_type_st)
        action_id = str(uuid.uuid4())
        action_item: dict[str, Any] = {
            "pk": pk,
            "sk": f"Action|{action_id}",
            "action_type": str(action_type),
            "ear_tag": f"BR{draw(st.integers(min_value=1, max_value=999)):03d}",
        }

        if action_type == ProcedureActionType.weight:
            action_item["weighing_date"] = "2025-01-15"
            action_item["weight_kg"] = draw(st.integers(min_value=1, max_value=1000))
        elif action_type == ProcedureActionType.insemination:
            action_item["insemination_date"] = "2025-01-15"
            action_item["semen"] = "Bull A"
        elif action_type == ProcedureActionType.diagnostic:
            action_item["diagnostic_date"] = "2025-01-15"
            action_item["pregnant"] = draw(st.booleans())
        elif action_type == ProcedureActionType.observation:
            action_item["note"] = "Some observation"
        # inspected has no extra fields

        actions.append(action_item)

    return {
        "pk": pk,
        "procedure_date": procedure_date,
        "status": str(status),
        "actions": actions,
    }


procedures_list_st = st.lists(procedure_with_actions_st(), min_size=1, max_size=10)


# --- Helpers ---


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
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return table


# --- Property Tests ---


# Feature: cattle-procedure, Property 9: Procedure list is sorted with correct metadata
@given(procedures=procedures_list_st)
@settings(max_examples=100, deadline=None)
@mock_aws
def test_procedure_list_sorted_with_correct_metadata(procedures: list[dict[str, Any]]) -> None:
    """Property 9: Procedure list is sorted with correct metadata.

    For any set of Procedures in the system, the list endpoint SHALL return them sorted by
    procedure_date in descending order, and each entry SHALL include the correct status and
    action_count (equal to the number of ProcedureAction records under that Procedure's pk).

    **Validates: Requirements 9.1, 9.2**
    """
    table = _create_table()

    # Insert all Procedures and their actions into DynamoDB
    expected: dict[str, dict[str, Any]] = {}
    for proc in procedures:
        table.put_item(
            Item={
                "pk": proc["pk"],
                "sk": "Procedure",
                "procedure_date": proc["procedure_date"],
                "status": proc["status"],
            }
        )
        for action in proc["actions"]:
            table.put_item(Item=action)

        expected[proc["pk"]] = {
            "pk": proc["pk"],
            "procedure_date": proc["procedure_date"],
            "status": proc["status"],
            "action_count": len(proc["actions"]),
        }

    # Call the handler
    import lmjm.get_procedures as mod

    importlib.reload(mod)

    result = mod.lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])

    # Verify the result contains all procedures
    assert len(body) == len(procedures)

    # Verify sorted by procedure_date descending
    dates = [entry["procedure_date"] for entry in body]
    assert dates == sorted(dates, reverse=True), (
        f"List not sorted by procedure_date descending: {dates}"
    )

    # Verify each entry has correct status and action_count
    for entry in body:
        pk = entry["pk"]
        assert pk in expected, f"Unexpected pk in response: {pk}"
        exp = expected[pk]
        assert entry["procedure_date"] == exp["procedure_date"], (
            f"Wrong procedure_date for {pk}: got {entry['procedure_date']}, expected {exp['procedure_date']}"
        )
        assert entry["status"] == exp["status"], (
            f"Wrong status for {pk}: got {entry['status']}, expected {exp['status']}"
        )
        assert entry["action_count"] == exp["action_count"], (
            f"Wrong action_count for {pk}: got {entry['action_count']}, expected {exp['action_count']}"
        )
