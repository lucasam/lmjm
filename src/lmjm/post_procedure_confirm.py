import os
from typing import Any

import boto3

from lmjm.model import ProcedureStatus
from lmjm.repo import (
    AnimalRepo,
    DiagnosticRepo,
    InseminationRepo,
    ProcedureActionRepo,
    ProcedureRepo,
    WeightRepo,
)
from lmjm.service.procedure_confirm_service import ProcedureConfirmService
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

procedure_repo = ProcedureRepo(table)
procedure_action_repo = ProcedureActionRepo(table)

confirm_service = ProcedureConfirmService(
    animal_repo=AnimalRepo(table),
    insemination_repo=InseminationRepo(table),
    diagnostic_repo=DiagnosticRepo(table),
    weight_repo=WeightRepo(table),
)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    procedure_id: str = event["pathParameters"]["procedure_id"]
    pk = f"Procedure|{procedure_id}"

    procedure = procedure_repo.get(pk)
    if not procedure:
        return respond(status_code=404, error="Procedure not found")

    if procedure.status == ProcedureStatus.confirmed:
        return respond(status_code=409, error="Procedure is already confirmed")

    actions = procedure_action_repo.list_for_procedure(pk)
    applied_count, failed_count, failures = confirm_service.apply_actions(actions)

    procedure.status = ProcedureStatus.confirmed
    procedure.applied_count = applied_count
    procedure.failed_count = failed_count
    procedure.failures = failures if failures else None
    procedure_repo.put(procedure)

    return respond(
        status_code=200,
        body={
            "status": str(procedure.status),
            "applied_count": applied_count,
            "failed_count": failed_count,
            "failures": failures,
        },
    )
