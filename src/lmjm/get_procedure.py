import os
from collections import defaultdict
from typing import Any

import boto3

from lmjm.model import ProcedureActionType
from lmjm.repo import AnimalRepo, ProcedureActionRepo, ProcedureRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict, serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

procedure_repo = ProcedureRepo(table)
procedure_action_repo = ProcedureActionRepo(table)
animal_repo = AnimalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    procedure_id: str = event["pathParameters"]["procedure_id"]
    pk = f"Procedure|{procedure_id}"

    procedure = procedure_repo.get(pk)
    if not procedure:
        return respond(status_code=404, error="Procedure not found")

    actions = procedure_action_repo.list_for_procedure(pk)

    weight_count = 0
    insemination_count = 0
    diagnostic_count = 0
    observation_count = 0
    inspected_count = 0
    implant_count = 0

    actions_by_ear_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for action in actions:
        if action.action_type == ProcedureActionType.weight:
            weight_count += 1
        elif action.action_type == ProcedureActionType.insemination:
            insemination_count += 1
        elif action.action_type == ProcedureActionType.diagnostic:
            diagnostic_count += 1
        elif action.action_type == ProcedureActionType.observation:
            observation_count += 1
        elif action.action_type == ProcedureActionType.inspected:
            inspected_count += 1
        elif action.action_type == ProcedureActionType.implant:
            implant_count += 1

        actions_by_ear_tag[action.ear_tag].append(serialize_to_dict(action))

    total_actions = (
        weight_count + insemination_count + diagnostic_count + observation_count + inspected_count + implant_count
    )
    processed_animal_count = len(actions_by_ear_tag)

    # Diagnostic breakdown: confirmed (pregnant=True) vs failed (pregnant=False)
    diagnostic_confirmed = 0
    diagnostic_failed = 0
    # Pregnancy rate: only count diagnostics on animals that were "Inseminada"
    prenhez_confirmed = 0
    prenhez_total = 0

    for action in actions:
        if action.action_type == ProcedureActionType.diagnostic:
            if action.pregnant:
                diagnostic_confirmed += 1
            else:
                diagnostic_failed += 1

            # Check if the animal was inseminated at the time of diagnostic
            animal = animal_repo.get_by_ear_tag(action.ear_tag)
            if animal and animal.inseminated:
                prenhez_total += 1
                if action.pregnant:
                    prenhez_confirmed += 1

    prenhez_rate: float | None = None
    if prenhez_total > 0:
        prenhez_rate = round(prenhez_confirmed / prenhez_total * 100, 1)

    animals = [
        {"ear_tag": ear_tag, "actions": ear_tag_actions} for ear_tag, ear_tag_actions in actions_by_ear_tag.items()
    ]

    summary: dict[str, Any] = {
        "weight_count": weight_count,
        "insemination_count": insemination_count,
        "diagnostic_count": diagnostic_count,
        "diagnostic_confirmed": diagnostic_confirmed,
        "diagnostic_failed": diagnostic_failed,
        "prenhez_rate": prenhez_rate,
        "prenhez_confirmed": prenhez_confirmed,
        "prenhez_total": prenhez_total,
        "observation_count": observation_count,
        "inspected_count": inspected_count,
        "implant_count": implant_count,
        "total_actions": total_actions,
        "processed_animal_count": processed_animal_count,
        "animals": animals,
    }

    body: dict[str, Any] = {
        "procedure": serialize_to_dict(procedure),
        "actions": serialize_to_dict_list(actions),
        "summary": summary,
    }

    return respond(body=body)
