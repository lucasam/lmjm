"""Property-based tests for Procedure delete action.

# Feature: cattle-procedure, Property 10: Delete from open Procedure removes action

For any open Procedure and any staged action within it, deleting that action SHALL remove it
from the Procedure's actions such that it no longer appears in queries, while all other actions
remain unchanged.

**Validates: Requirements 10.1**
"""

import importlib
import uuid
from typing import Any

import boto3
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from lmjm.model import ProcedureActionType

# --- Strategies ---

action_type_st = st.sampled_from(list(ProcedureActionType))

ear_tag_st = st.text(
    alphabet=st.characters(categories=("L", "N"), exclude_characters="\x00"),
    min_size=1,
    max_size=10,
).map(lambda s: f"BR{s}")


@st.composite
def procedure_action_item_st(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a DynamoDB item representing a ProcedureAction."""
    action_type = draw(action_type_st)
    ear_tag = draw(ear_tag_st)
    action_id = str(uuid.uuid4())

    item: dict[str, Any] = {
        "pk": "__PLACEHOLDER__",
        "sk": f"Action|{action_id}",
        "action_type": str(action_type),
        "ear_tag": ear_tag,
    }

    if action_type == ProcedureActionType.weight:
        item["weighing_date"] = "2025-01-15"
        item["weight_kg"] = draw(st.integers(min_value=1, max_value=1000))
    elif action_type == ProcedureActionType.insemination:
        item["insemination_date"] = "2025-01-15"
        item["semen"] = "Bull A"
    elif action_type == ProcedureActionType.diagnostic:
        item["diagnostic_date"] = "2025-01-15"
        item["pregnant"] = draw(st.booleans())
    elif action_type == ProcedureActionType.observation:
        item["note"] = "Some observation"

    return item


# Generate a list of 2+ actions so there's always at least one remaining after deletion
actions_list_st = st.lists(procedure_action_item_st(), min_size=2, max_size=20)


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


# Feature: cattle-procedure, Property 10: Delete from open Procedure removes action
@given(actions=actions_list_st, delete_index=st.integers(min_value=0))
@settings(max_examples=100, deadline=None)
@mock_aws
def test_delete_from_open_procedure_removes_action(actions: list[dict[str, Any]], delete_index: int) -> None:
    """Property 10: Delete from open Procedure removes action.

    Stage random actions, delete one, verify it no longer appears in list while others remain.

    **Validates: Requirements 10.1**
    """
    table = _create_table()

    procedure_id = str(uuid.uuid4())
    pk = f"Procedure|{procedure_id}"

    # Create the Procedure record with status "open"
    table.put_item(
        Item={
            "pk": pk,
            "sk": "Procedure",
            "procedure_date": "2025-01-15",
            "status": "open",
        }
    )

    # Insert all actions and assign the correct pk
    for action in actions:
        action["pk"] = pk
        table.put_item(Item=action)

    # Pick which action to delete (use modulo to stay in bounds)
    target_index = delete_index % len(actions)
    target_action = actions[target_index]
    target_sk = target_action["sk"]

    # Collect the sk values of actions that should remain after deletion
    remaining_sks = {a["sk"] for i, a in enumerate(actions) if i != target_index}

    # Call the delete handler
    import lmjm.delete_procedure_action as del_mod

    importlib.reload(del_mod)

    event: dict[str, Any] = {
        "pathParameters": {
            "procedure_id": procedure_id,
            "action_sk": target_sk,
        }
    }
    result = del_mod.lambda_handler(event, None)

    # Verify delete returned 204
    assert result["statusCode"] == 204

    # Verify the deleted action no longer appears in the action list
    from lmjm.repo import ProcedureActionRepo

    repo = ProcedureActionRepo(table)
    remaining_actions = repo.list_for_procedure(pk)
    remaining_action_sks = {a.sk for a in remaining_actions}

    # The deleted action must not be present
    assert target_sk not in remaining_action_sks, (
        f"Deleted action {target_sk} still appears in the action list"
    )

    # All other actions must still be present
    assert remaining_action_sks == remaining_sks, (
        f"Expected remaining actions {remaining_sks}, got {remaining_action_sks}"
    )

    # Verify the count matches: original count minus 1
    assert len(remaining_actions) == len(actions) - 1
