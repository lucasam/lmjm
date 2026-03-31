import os
from typing import Any

import boto3

from lmjm.repo import MedicationShotRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

medication_shot_repo = MedicationShotRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = event["pathParameters"]["batch_id"]
    query_params: dict[str, str] | None = event.get("queryStringParameters")
    month: str | None = query_params.get("month") if query_params else None
    shots = medication_shot_repo.list(batch_id, month=month)
    return respond(body=serialize_to_dict_list(shots))
