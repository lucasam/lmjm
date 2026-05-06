import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import boto3

from lmjm.model import ProcedureAction, ProcedureActionType, ProcedureStatus
from lmjm.repo import AnimalRepo, InseminationRepo, ProcedureActionRepo, ProcedureRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

procedure_repo = ProcedureRepo(table)
procedure_action_repo = ProcedureActionRepo(table)
animal_repo = AnimalRepo(table)
insemination_repo = InseminationRepo(table)


@dataclasses.dataclass
class PostProcedureActionRequest:
    action_type: str
    ear_tag: str
    weighing_date: Optional[str] = None
    weight_kg: Optional[int] = None
    insemination_date: Optional[str] = None
    semen: Optional[str] = None
    diagnostic_date: Optional[str] = None
    pregnant: Optional[bool] = None
    tags: Optional[str] = None
    note: Optional[str] = None


def _validate_date(value: Optional[str], field_name: str) -> Optional[datetime]:
    """Validate a YYYYMMDD date string. Returns parsed datetime or None on failure."""
    try:
        return datetime.strptime(value, "%Y%m%d")  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    procedure_id = event["pathParameters"]["procedure_id"]
    pk = f"Procedure|{procedure_id}"

    procedure = procedure_repo.get(pk)
    if not procedure:
        return respond(status_code=404, error="Procedure not found")

    if procedure.status != ProcedureStatus.open:
        return respond(status_code=409, error="Procedure is already confirmed")

    request = load_data_class_from_dict(json.loads(event["body"]), PostProcedureActionRequest)

    try:
        action_type = ProcedureActionType(request.action_type)
    except ValueError:
        return respond(status_code=400, error="Invalid action_type")

    animal = animal_repo.get_by_ear_tag(request.ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")

    action_fields: dict[str, Any] = {}

    if action_type == ProcedureActionType.weight:
        parsed = _validate_date(request.weighing_date, "weighing_date")
        if not parsed:
            return respond(status_code=400, error="weighing_date must be in YYYYMMDD format")
        if not request.weight_kg or request.weight_kg <= 0:
            return respond(status_code=400, error="weight_kg must be a positive integer")
        action_fields["weighing_date"] = parsed.strftime("%Y-%m-%d")
        action_fields["weight_kg"] = request.weight_kg

    elif action_type == ProcedureActionType.insemination:
        parsed = _validate_date(request.insemination_date, "insemination_date")
        if not parsed:
            return respond(status_code=400, error="insemination_date must be in YYYYMMDD format")
        if not request.semen or not request.semen.strip():
            return respond(status_code=400, error="semen is required")
        action_fields["insemination_date"] = parsed.strftime("%Y-%m-%d")
        action_fields["semen"] = request.semen
        if request.note:
            action_fields["note"] = request.note

    elif action_type == ProcedureActionType.diagnostic:
        parsed = _validate_date(request.diagnostic_date, "diagnostic_date")
        if not parsed:
            return respond(status_code=400, error="diagnostic_date must be in YYYYMMDD format")
        if request.pregnant is None or not isinstance(request.pregnant, bool):
            return respond(status_code=400, error="pregnant must be a boolean")
        insemination = insemination_repo.get_latest(animal.pk)
        if not insemination:
            return respond(status_code=404, error="No insemination found")
        action_fields["diagnostic_date"] = parsed.strftime("%Y-%m-%d")
        action_fields["pregnant"] = request.pregnant
        if request.note:
            action_fields["note"] = request.note
        if request.tags:
            action_fields["tags"] = request.tags

    elif action_type == ProcedureActionType.observation:
        if not request.note or not request.note.strip():
            return respond(status_code=400, error="note is required")
        action_fields["note"] = request.note

    # ProcedureActionType.inspected and ProcedureActionType.implant: no additional validation needed

    action = ProcedureAction(
        pk=pk,
        sk=f"Action|{uuid.uuid4()}",
        action_type=action_type,
        ear_tag=request.ear_tag,
        **action_fields,
    )
    procedure_action_repo.put(action)

    return respond(status_code=201, body=serialize_to_dict(action))
