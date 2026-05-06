import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any

import boto3
from marshmallow import ValidationError

from lmjm.model import Procedure, ProcedureStatus
from lmjm.repo import ProcedureRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

procedure_repo = ProcedureRepo(table)


@dataclasses.dataclass
class PostProcedureRequest:
    procedure_date: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        request = load_data_class_from_dict(json.loads(event["body"]), PostProcedureRequest)
    except ValidationError:
        return respond(status_code=400, error="procedure_date must be in YYYYMMDD format")

    try:
        parsed = datetime.strptime(request.procedure_date, "%Y%m%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="procedure_date must be in YYYYMMDD format")

    procedure_id = str(uuid.uuid4())
    procedure = Procedure(
        pk=f"Procedure|{procedure_id}",
        procedure_date=parsed.strftime("%Y-%m-%d"),
        status=ProcedureStatus.open,
    )
    procedure_repo.put(procedure)

    return respond(status_code=201, body=serialize_to_dict(procedure))
