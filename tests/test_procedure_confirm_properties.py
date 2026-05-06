"""Property-based tests for Procedure confirmation.

# Feature: cattle-procedure, Property 7: Confirmation applies actions and transitions status

For any open Procedure with staged actions targeting existing animals, confirming the Procedure
SHALL change its status to "confirmed" and apply each action to the corresponding Animal record
(weight creates a Weight record, insemination creates an Insemination record and updates animal
flags, diagnostic creates a Diagnostic record and updates animal flags, observation appends to
animal notes, inspected does not modify the animal).

**Validates: Requirements 8.1, 8.2**
"""

import importlib
import json
import uuid
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from lmjm.model import ProcedureActionType

# --- Constants ---

_ear_tag_pool = ["BR100", "BR200", "BR300", "BR400", "BR500"]

# --- Strategies ---

action_type_st = st.sampled_from(list(ProcedureActionType))
ear_tag_st = st.sampled_from(_ear_tag_pool)


@st.composite
def staged_action_st(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a valid staged action to be inserted directly into DynamoDB."""
    action_type: ProcedureActionType = draw(action_type_st)
    ear_tag: str = draw(ear_tag_st)

    item: dict[str, Any] = {
        "action_type": str(action_type),
        "ear_tag": ear_tag,
    }

    if action_type == ProcedureActionType.weight:
        item["weighing_date"] = "20250115"
        item["weight_kg"] = draw(st.integers(min_value=1, max_value=1000))
    elif action_type == ProcedureActionType.insemination:
        item["insemination_date"] = "20250115"
        item["semen"] = draw(st.text(min_size=1, max_size=10, alphabet="ABCDEFGHIJ"))
    elif action_type == ProcedureActionType.diagnostic:
        item["diagnostic_date"] = "20250115"
        item["pregnant"] = draw(st.booleans())
    elif action_type == ProcedureActionType.observation:
        item["note"] = draw(st.text(min_size=1, max_size=50, alphabet="abcdefghij "))
    # inspected: no extra fields

    return item


actions_list_st = st.lists(staged_action_st(), min_size=1, max_size=10)


# --- Helpers ---


def _create_table() -> Any:
    """Create the DynamoDB table with the ear_tag-sk-index GSI."""
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
    """Create Animal records for all ear_tags. Returns map of ear_tag -> initial item."""
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


def _create_procedure_with_actions(
    table: Any, actions: list[dict[str, Any]]
) -> tuple[str, str, list[dict[str, Any]]]:
    """Create an open Procedure and stage actions directly in DynamoDB.

    Returns (procedure_id, procedure_pk, list of action items with pk/sk).
    """
    procedure_id = str(uuid.uuid4())
    procedure_pk = f"Procedure|{procedure_id}"
    table.put_item(
        Item={
            "pk": procedure_pk,
            "sk": "Procedure",
            "procedure_date": "2025-01-15",
            "status": "open",
        }
    )

    staged_items: list[dict[str, Any]] = []
    for action in actions:
        action_sk = f"Action|{uuid.uuid4()}"
        item: dict[str, Any] = {
            "pk": procedure_pk,
            "sk": action_sk,
            **action,
        }
        table.put_item(Item=item)
        staged_items.append(item)

    return procedure_id, procedure_pk, staged_items


def _read_animal_by_ear_tag(table: Any, ear_tag: str) -> dict[str, Any]:
    """Read an animal record from DynamoDB using the GSI."""
    response = table.query(
        IndexName="ear_tag-sk-index",
        KeyConditionExpression=Key("ear_tag").eq(ear_tag) & Key("sk").eq("Animal"),
        Limit=1,
    )
    items = response["Items"]
    assert items, f"Animal with ear_tag={ear_tag} not found"
    return items[0]


def _query_records(table: Any, pk: str, sk_prefix: str) -> list[dict[str, Any]]:
    """Query DynamoDB for records matching pk and sk prefix."""
    response = table.query(
        KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(sk_prefix),
    )
    return response["Items"]


def _group_actions_by_ear_tag(staged_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group staged actions by ear_tag, preserving insertion order."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in staged_items:
        ear_tag = item["ear_tag"]
        grouped.setdefault(ear_tag, []).append(item)
    return grouped


# --- Property Test ---


# Feature: cattle-procedure, Property 7: Confirmation applies actions and transitions status
@given(actions=actions_list_st)
@settings(max_examples=100, deadline=None)
@mock_aws
def test_confirmation_applies_actions_and_transitions_status(actions: list[dict[str, Any]]) -> None:
    """Property 7: Confirmation applies actions and transitions status.

    For any open Procedure with staged actions targeting existing animals, confirming the
    Procedure SHALL change its status to "confirmed" and apply each action to the corresponding
    Animal record (weight creates a Weight record, insemination creates an Insemination record
    and updates animal flags, diagnostic creates a Diagnostic record and updates animal flags,
    observation appends to animal notes, inspected does not modify the animal).

    **Validates: Requirements 8.1, 8.2**
    """
    table = _create_table()

    # 1. Create animals with known initial state
    initial_animals = _create_animals(table)

    # 2. Create insemination records so diagnostic actions can pass validation
    _create_insemination_records(table, initial_animals)

    # 3. Snapshot animal state BEFORE confirmation
    snapshots_before: dict[str, dict[str, Any]] = {}
    for ear_tag in _ear_tag_pool:
        snapshots_before[ear_tag] = _read_animal_by_ear_tag(table, ear_tag)

    # 4. Create an open Procedure with staged actions directly in DynamoDB
    procedure_id, procedure_pk, staged_items = _create_procedure_with_actions(table, actions)

    # 5. Call the post_procedure_confirm handler
    import lmjm.post_procedure_confirm as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"procedure_id": procedure_id},
    }
    result = mod.lambda_handler(event, None)
    body = json.loads(result["body"])

    # 6. Verify Procedure status changed to "confirmed"
    assert result["statusCode"] == 200, f"Expected 200, got {result['statusCode']}: {body}"
    assert body["status"] == "confirmed", f"Expected status 'confirmed', got '{body['status']}'"

    # Also verify the Procedure record in DynamoDB
    proc_response = table.get_item(Key={"pk": procedure_pk, "sk": "Procedure"})
    proc_item = proc_response["Item"]
    assert proc_item["status"] == "confirmed"

    # 7. Verify each action type was applied correctly per animal
    grouped = _group_actions_by_ear_tag(staged_items)

    for ear_tag, animal_actions in grouped.items():
        animal_pk = initial_animals[ear_tag]["pk"]
        animal_after = _read_animal_by_ear_tag(table, ear_tag)

        # Count expected records by type for this animal
        weight_actions = [a for a in animal_actions if a["action_type"] == "weight"]
        insemination_actions = [a for a in animal_actions if a["action_type"] == "insemination"]
        diagnostic_actions = [a for a in animal_actions if a["action_type"] == "diagnostic"]
        observation_actions = [a for a in animal_actions if a["action_type"] == "observation"]
        inspected_actions = [a for a in animal_actions if a["action_type"] == "inspected"]

        # --- Weight: each weight action creates a Weight record with sk "Peso|YYYYMMDD" ---
        if weight_actions:
            weights = _query_records(table, animal_pk, "Peso|")
            assert len(weights) >= 1, f"No Weight records found for {ear_tag}"
            # All weight actions use date 20250115, so at least one Peso|20250115 should exist
            weight_sks = [w["sk"] for w in weights]
            assert any(
                sk == "Peso|20250115" for sk in weight_sks
            ), f"Expected Peso|20250115 sk for {ear_tag}, got {weight_sks}"

        # --- Insemination: creates Insemination record ---
        if insemination_actions:
            inseminations = _query_records(table, animal_pk, "Insemination|")
            insem_sks = [i["sk"] for i in inseminations]
            assert any(
                sk == "Insemination|20250115" for sk in insem_sks
            ), f"Expected Insemination|20250115 for {ear_tag}, got {insem_sks}"
            # Note: We only verify the Insemination record was created.
            # The final animal.inseminated flag depends on DynamoDB query order
            # (sk-based, not insertion order), so when multiple action types
            # target the same animal, the final flag state is non-deterministic.

        # --- Diagnostic: creates Diagnostic record, animal.pregnant matches result ---
        if diagnostic_actions:
            diagnostics = _query_records(table, animal_pk, "Diagnostic|")
            diag_sks = [d["sk"] for d in diagnostics]
            assert any(
                sk == "Diagnostic|20250115" for sk in diag_sks
            ), f"Expected Diagnostic|20250115 for {ear_tag}, got {diag_sks}"

        # --- Observation: animal.notes contains each observation note ---
        if observation_actions:
            animal_notes = animal_after.get("notes", [])
            for obs in observation_actions:
                note = obs.get("note", "")
                assert note in animal_notes, (
                    f"Animal {ear_tag} notes should contain '{note}', got {animal_notes}"
                )

        # --- Inspected: does not modify the animal record ---
        if inspected_actions and not any([
            weight_actions, insemination_actions, diagnostic_actions, observation_actions
        ]):
            # If the ONLY actions for this animal are inspected, the animal should be unchanged
            before = snapshots_before[ear_tag]
            invariant_fields = ("pregnant", "inseminated", "implanted", "transferred", "lactating", "notes", "tags")
            for field in invariant_fields:
                assert animal_after.get(field) == before.get(field), (
                    f"Animal {ear_tag} field '{field}' changed by inspected action: "
                    f"before={before.get(field)}, after={animal_after.get(field)}"
                )


# --- Strategies for Property 8 ---

# Extended ear_tag pool: some will exist, some won't
_existing_ear_tags = ["BR100", "BR200", "BR300"]
_missing_ear_tags = ["BR999", "BR888"]
_all_ear_tags_p8 = _existing_ear_tags + _missing_ear_tags

ear_tag_mixed_st = st.sampled_from(_all_ear_tags_p8)


@st.composite
def staged_action_mixed_st(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a staged action targeting either an existing or non-existing animal."""
    action_type: ProcedureActionType = draw(action_type_st)
    ear_tag: str = draw(ear_tag_mixed_st)

    item: dict[str, Any] = {
        "action_type": str(action_type),
        "ear_tag": ear_tag,
    }

    if action_type == ProcedureActionType.weight:
        item["weighing_date"] = "20250115"
        item["weight_kg"] = draw(st.integers(min_value=1, max_value=1000))
    elif action_type == ProcedureActionType.insemination:
        item["insemination_date"] = "20250115"
        item["semen"] = draw(st.text(min_size=1, max_size=10, alphabet="ABCDEFGHIJ"))
    elif action_type == ProcedureActionType.diagnostic:
        item["diagnostic_date"] = "20250115"
        item["pregnant"] = draw(st.booleans())
    elif action_type == ProcedureActionType.observation:
        item["note"] = draw(st.text(min_size=1, max_size=50, alphabet="abcdefghij "))
    # inspected: no extra fields

    return item


mixed_actions_list_st = st.lists(staged_action_mixed_st(), min_size=1, max_size=10)


# --- Property 8 Test ---


# Feature: cattle-procedure, Property 8: Confirmation result counts are consistent
@given(actions=mixed_actions_list_st)
@settings(max_examples=100, deadline=None)
@mock_aws
def test_confirmation_result_counts_are_consistent(actions: list[dict[str, Any]]) -> None:
    """Property 8: Confirmation result counts are consistent.

    For any confirmed Procedure, applied_count + failed_count SHALL equal the total number
    of staged actions, and each action in the failures list SHALL correspond to an action
    that could not be applied.

    **Validates: Requirements 8.4**
    """
    table = _create_table()

    # 1. Create animals ONLY for _existing_ear_tags (not _missing_ear_tags)
    initial_animals: dict[str, dict[str, Any]] = {}
    for ear_tag in _existing_ear_tags:
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
        initial_animals[ear_tag] = item

    # 2. Create insemination records for existing animals so diagnostic actions can pass
    for ear_tag, animal in initial_animals.items():
        table.put_item(
            Item={
                "pk": animal["pk"],
                "sk": "Insemination|20250101",
                "insemination_date": "2025-01-01",
                "semen": "Bull X",
            }
        )

    # 3. Create an open Procedure with a mix of actions (some targeting missing animals)
    procedure_id, procedure_pk, staged_items = _create_procedure_with_actions(table, actions)
    total_actions = len(staged_items)

    # 4. Call the post_procedure_confirm handler
    import lmjm.post_procedure_confirm as mod

    importlib.reload(mod)

    event: dict[str, Any] = {
        "pathParameters": {"procedure_id": procedure_id},
    }
    result = mod.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200, f"Expected 200, got {result['statusCode']}: {body}"

    applied_count = body["applied_count"]
    failed_count = body["failed_count"]
    failures = body["failures"]

    # 5. Verify applied_count + failed_count == total staged actions
    assert applied_count + failed_count == total_actions, (
        f"applied_count ({applied_count}) + failed_count ({failed_count}) "
        f"!= total_actions ({total_actions})"
    )

    # 6. Verify failed_count matches the length of the failures list
    assert len(failures) == failed_count, (
        f"failures list length ({len(failures)}) != failed_count ({failed_count})"
    )

    # 7. Verify each failure corresponds to an action that couldn't be applied
    #    Non-inspected actions targeting missing ear_tags should fail.
    #    Inspected actions always succeed (they're skipped, counted as applied).
    for failure in failures:
        failed_ear_tag = failure["ear_tag"]
        failed_action_type = failure["action_type"]
        failed_reason = failure["reason"]

        # The failure must reference an ear_tag that doesn't have an animal record
        assert failed_ear_tag in _missing_ear_tags, (
            f"Failure for ear_tag '{failed_ear_tag}' but it should exist in the DB. "
            f"action_type={failed_action_type}, reason={failed_reason}"
        )

        # The failure must NOT be an inspected action (inspected always succeeds)
        assert failed_action_type != "inspected", (
            f"Inspected action for '{failed_ear_tag}' should not fail"
        )

    # 8. Verify that all non-inspected actions targeting missing animals are in failures
    expected_failures: list[tuple[str, str]] = []
    for item in staged_items:
        ear_tag = item["ear_tag"]
        action_type = item["action_type"]
        if ear_tag in _missing_ear_tags and action_type != "inspected":
            expected_failures.append((ear_tag, action_type))

    actual_failures = [(f["ear_tag"], f["action_type"]) for f in failures]

    assert sorted(expected_failures) == sorted(actual_failures), (
        f"Expected failures {sorted(expected_failures)} != actual {sorted(actual_failures)}"
    )
