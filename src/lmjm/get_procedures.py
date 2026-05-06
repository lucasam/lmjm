import os
from typing import Any

import boto3

from lmjm.repo import ProcedureActionRepo, ProcedureRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

procedure_repo = ProcedureRepo(table)
procedure_action_repo = ProcedureActionRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    procedures = procedure_repo.list_all()

    result: list[dict[str, Any]] = []
    for procedure in procedures:
        actions = procedure_action_repo.list_for_procedure(procedure.pk)
        entry = serialize_to_dict(procedure)
        entry["action_count"] = len(actions)
        result.append(
            {
                "pk": entry["pk"],
                "procedure_date": entry["procedure_date"],
                "status": entry["status"],
                "action_count": len(actions),
            }
        )

    result.sort(key=lambda p: p["procedure_date"], reverse=True)

    return respond(body=result)
