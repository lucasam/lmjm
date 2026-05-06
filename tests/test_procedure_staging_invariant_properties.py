"""Property-based tests for Procedure staging invariant.

# Feature: cattle-procedure, Property 4: Staging invariant — Animal records unchanged until confirmation

For any set of staged actions in an open Procedure, the corresponding Animal records SHALL remain
unmodified (no changes to pregnant, inseminated, implanted, transferred, lactating, notes, or tags
fields) until the Procedure is confirmed.

**Validates: Requirements 3.3, 4.3, 5.3, 6.3**
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

# --- Constants ---

ANIMAL_INVARIANT_FIELDS = ("pregnant", "inseminated", "implanted", "transferred", "lactating", "notes", "tags")

# --- Strategies ---

action_type_st = st.sampled_from(list(ProcedureActionType))

# Small pool of ear_tags so we can reuse them across actions
_ear_tag_pool = ["BR100", "BR200", "BR300", "BR400", "BR500"]
ear_tag_st = st.sampled_from(_ear_tag_pool)


@st.composite
def staged_action_st(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a valid action request body for post_procedure_action."""
    action_type = draw(action_type_st)
    ear_tag = draw(ear_tag_st)

    body: dict[str, Any] = {
        "action_type": str(action_type),
        "ear_tag": ear_tag,
    }

    if action_type == ProcedureActionType.weight:
        body["weighing_date"] = "20250115"
        body["weight_kg"] = draw(st.integers(min_value=1, max_value=1000))
    elif action_type == ProcedureActionType.insemination:
        body["insemination_date"] = "20250115"
        body["semen"] = draw(st.text(min_size=1, max_size=10, alphabet="ABCDEFGHIJ"))
    elif action_type == ProcedureActionType.diagnostic:
        body["diagnostic_date"] = "20250115"
        body["pregnant"] = draw(st.booleans())
    elif action_type == ProcedureActionType.observation:
        body["note"] = draw(st.text(min_size=1, max_size=50, alphabet="abcdefghij "))

    # inspected: no extra fields

    return body


actions_list_st = st.lists(staged_action_st(), min_size=1, max_size=15)


# --- Helpers ---


def _create_table() -> Any:
    """Create the DynamoDB table with the ear_tag-sk-index GSI needed by AnimalRepo."""
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
    return table


def _create_animals(table: Any) -> dict[str, dict[str, Any]]:
    """Create Animal records for all ear_tags in the pool. Returns a map of ear_tag -> initial item."""
    initial_state: dict[str, dict[str, Any]] = {}
    for ear_tag in _ear_tag_pool:
        animal_pk = f"Animal|{uuid.uuid4()}"
        item: dict[str, Any] = {
            "pk": animal_pk,
            "sk": "Animal",
            "ear_tag": ear_tag,
            "breed": "Nelore",
            "sex": "F",
            "status": "Ativa",
            "species": "cattle",
            "pregnant": False,
            "inseminated": False,
            "implanted": False,
            "transferred": False,
            "lactating": False,
        }
        table.put_item(Item=item)
        initial_state[ear_tag] = item
    return initial_state


def _create_insemination_records(table: Any, initial_animals: dict[str, dict[str, Any]]) -> None:
    """Create a prior insemination record for every animal so diagnostic actions can pass validation."""
    for ear_tag, animal in initial_animals.items():
        table.put_item(
            Item={
                "pk": animal["pk"],
                "sk": "Insemination|20250101",
                "insemination_date": "2025-01-01",
                "semen": "Bull X",
            }
        )


def _read_animal_by_ear_tag(table: Any, ear_tag: str) -> dict[str, Any]:
    """Read an animal record back from DynamoDB using the GSI."""
    response = table.query(
        IndexName="ear_tag-sk-index",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("ear_tag").eq(ear_tag)
        & boto3.dynamodb.conditions.Key("sk").eq("Animal"),
        Limit=1,
    )
    items = response["Items"]
    assert items, f"Animal with ear_tag={ear_tag} not found"
    return items[0]


# --- Property Test ---


# Feature: cattle-procedure, Property 4: Staging invariant — Animal records unchanged until confirmation
@given(actions=actions_list_st)
@settings(max_examples=100, deadline=None)
@mock_aws
def test_staging_does_not_modify_animal_records(actions: list[dict[str, Any]]) -> None:
    """Property 4: Staging invariant — Animal records unchanged until confirmation.

    For any set of staged actions in an open Procedure, the corresponding Animal records SHALL
    remain unmodified (no changes to pregnant, inseminated, implanted, transferred, lactating,
    notes, or tags fields) until the Procedure is confirmed.

    **Validates: Requirements 3.3, 4.3, 5.3, 6.3**
    """
    table = _create_table()

    # 1. Create animals with known initial state
    initial_animals = _create_animals(table)

    # 2. Create insemination records so diagnostic actions pass validation
    _create_insemination_records(table, initial_animals)

    # 3. Snapshot the invariant fields BEFORE staging
    snapshots_before: dict[str, dict[str, Any]] = {}
    for ear_tag in _ear_tag_pool:
        animal_item = _read_animal_by_ear_tag(table, ear_tag)
        snapshots_before[ear_tag] = {field: animal_item.get(field) for field in ANIMAL_INVARIANT_FIELDS}

    # 4. Create an open Procedure
    procedure_id = str(uuid.uuid4())
    table.put_item(
        Item={
            "pk": f"Procedure|{procedure_id}",
            "sk": "Procedure",
            "procedure_date": "2025-01-15",
            "status": "open",
        }
    )

    # 5. Stage all generated actions via the post_procedure_action handler
    import lmjm.post_procedure_action as mod

    importlib.reload(mod)

    for action_body in actions:
        event: dict[str, Any] = {
            "pathParameters": {"procedure_id": procedure_id},
            "body": json.dumps(action_body),
        }
        result = mod.lambda_handler(event, None)
        # We only care about actions that were successfully staged (201).
        # Some may fail validation (400/404) — that's fine, the invariant still holds.

    # 6. After staging, read animal records back and verify invariant fields are UNCHANGED
    for ear_tag in _ear_tag_pool:
        animal_after = _read_animal_by_ear_tag(table, ear_tag)
        snapshot_after = {field: animal_after.get(field) for field in ANIMAL_INVARIANT_FIELDS}

        assert snapshot_after == snapshots_before[ear_tag], (
            f"Animal {ear_tag} was modified by staging! "
            f"Before: {snapshots_before[ear_tag]}, After: {snapshot_after}"
        )
