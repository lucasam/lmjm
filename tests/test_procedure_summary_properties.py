"""Property-based tests for Procedure summary counts.

# Feature: cattle-procedure, Property 5: Summary counts match staged actions

For any Procedure with a set of staged actions, the summary SHALL report counts where
weight_count + insemination_count + diagnostic_count + observation_count + inspected_count == total_actions,
and each count equals the number of actions with that action_type.

**Validates: Requirements 7.1, 7.2**
"""

import importlib
import json
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


actions_list_st = st.lists(procedure_action_item_st(), min_size=0, max_size=20)


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


# Feature: cattle-procedure, Property 5: Summary counts match staged actions
@given(actions=actions_list_st)
@settings(max_examples=100, deadline=None)
@mock_aws
def test_summary_counts_match_staged_actions(actions: list[dict[str, Any]]) -> None:
    """Property 5: Summary counts match staged actions.

    For any Procedure with a set of staged actions, the summary SHALL report counts where
    weight_count + insemination_count + diagnostic_count + observation_count + inspected_count == total_actions,
    and each count equals the number of actions with that action_type.

    **Validates: Requirements 7.1, 7.2**
    """
    table = _create_table()

    procedure_id = str(uuid.uuid4())
    pk = f"Procedure|{procedure_id}"

    # Create the Procedure record
    table.put_item(
        Item={
            "pk": pk,
            "sk": "Procedure",
            "procedure_date": "2025-01-15",
            "status": "open",
        }
    )

    # Compute expected counts from the generated actions
    expected_weight = 0
    expected_insemination = 0
    expected_diagnostic = 0
    expected_observation = 0
    expected_inspected = 0

    for action in actions:
        action["pk"] = pk
        table.put_item(Item=action)

        action_type = action["action_type"]
        if action_type == "weight":
            expected_weight += 1
        elif action_type == "insemination":
            expected_insemination += 1
        elif action_type == "diagnostic":
            expected_diagnostic += 1
        elif action_type == "observation":
            expected_observation += 1
        elif action_type == "inspected":
            expected_inspected += 1

    expected_total = expected_weight + expected_insemination + expected_diagnostic + expected_observation + expected_inspected

    # Call the handler
    import lmjm.get_procedure as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    summary = body["summary"]

    # Verify each count matches the number of actions with that type
    assert summary["weight_count"] == expected_weight
    assert summary["insemination_count"] == expected_insemination
    assert summary["diagnostic_count"] == expected_diagnostic
    assert summary["observation_count"] == expected_observation
    assert summary["inspected_count"] == expected_inspected

    # Verify the sum invariant: all type counts add up to total_actions
    actual_sum = (
        summary["weight_count"]
        + summary["insemination_count"]
        + summary["diagnostic_count"]
        + summary["observation_count"]
        + summary["inspected_count"]
    )
    assert actual_sum == summary["total_actions"]
    assert summary["total_actions"] == expected_total
    assert summary["total_actions"] == len(actions)


# --- Strategy for Property 6: actions with controlled ear_tag pool to force duplicates ---

# Use a small pool of ear_tags so duplicates are likely
_ear_tag_pool_st = st.sampled_from(["BR001", "BR002", "BR003", "BR004", "BR005"])


@st.composite
def procedure_action_with_pool_st(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a DynamoDB item with ear_tag drawn from a small pool to force duplicates."""
    action_type = draw(action_type_st)
    ear_tag = draw(_ear_tag_pool_st)
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


actions_with_duplicates_st = st.lists(procedure_action_with_pool_st(), min_size=1, max_size=25)


# Feature: cattle-procedure, Property 6: Processed animal count correctness
@given(actions=actions_with_duplicates_st)
@settings(max_examples=100, deadline=None)
@mock_aws
def test_processed_animal_count_equals_distinct_ear_tags(actions: list[dict[str, Any]]) -> None:
    """Property 6: Processed animal count correctness.

    For any set of staged actions within a Procedure, the processed_animal_count SHALL equal
    the number of distinct ear_tag values that appear in at least one staged action
    (including "inspected" type actions).

    **Validates: Requirements 2.3, 7.5**
    """
    table = _create_table()

    procedure_id = str(uuid.uuid4())
    pk = f"Procedure|{procedure_id}"

    # Create the Procedure record
    table.put_item(
        Item={
            "pk": pk,
            "sk": "Procedure",
            "procedure_date": "2025-01-15",
            "status": "open",
        }
    )

    # Insert actions and compute expected distinct ear_tags
    distinct_ear_tags: set[str] = set()

    for action in actions:
        action["pk"] = pk
        table.put_item(Item=action)
        distinct_ear_tags.add(action["ear_tag"])

    expected_processed_count = len(distinct_ear_tags)

    # Call the handler
    import lmjm.get_procedure as mod

    importlib.reload(mod)

    event: dict[str, Any] = {"pathParameters": {"procedure_id": procedure_id}}
    result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    summary = body["summary"]

    # Verify processed_animal_count equals distinct ear_tag count
    assert summary["processed_animal_count"] == expected_processed_count

    # Verify the animals list has one entry per distinct ear_tag
    animals = summary["animals"]
    assert len(animals) == expected_processed_count

    # Verify each distinct ear_tag appears exactly once in the animals list
    returned_ear_tags = {animal["ear_tag"] for animal in animals}
    assert returned_ear_tags == distinct_ear_tags
