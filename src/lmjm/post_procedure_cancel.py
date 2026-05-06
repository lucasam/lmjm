import os
from typing import Any

import boto3

from lmjm.model import ProcedureStatus
from lmjm.repo import ProcedureActionRepo, ProcedureRepo
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

procedure_repo = ProcedureRepo(table)
procedure_action_repo = ProcedureActionRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    procedure_id: str = event["pathParameters"]["procedure_id"]
    pk = f"Procedure|{procedure_id}"

    procedure = procedure_repo.get(pk)
    if not procedure:
        return respond(status_code=404, error="Procedure not found")

    if procedure.status != ProcedureStatus.open:
        return respond(status_code=409, error="Only open Procedures can be cancelled")

    # Delete all staged actions
    actions = procedure_action_repo.list_for_procedure(pk)
    for action in actions:
        procedure_action_repo.delete(pk, action.sk)

    # Update status to cancelled
    procedure.status = ProcedureStatus.cancelled
    procedure_repo.put(procedure)

    return respond(body={"status": "cancelled"})
