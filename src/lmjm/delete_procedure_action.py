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
    action_id: str = event["pathParameters"]["action_sk"]
    pk = f"Procedure|{procedure_id}"
    # Support both full sk ("Action|{uuid}") and just the uuid
    action_sk = action_id if action_id.startswith("Action|") else f"Action|{action_id}"

    procedure = procedure_repo.get(pk)
    if not procedure:
        return respond(status_code=404, error="Procedure not found")

    if procedure.status == ProcedureStatus.confirmed:
        return respond(status_code=409, error="Procedure is already confirmed")

    action = procedure_action_repo.get(pk, action_sk)
    if not action:
        return respond(status_code=404, error="Action not found")

    procedure_action_repo.delete(pk, action_sk)

    return respond(status_code=204)
