import os
from typing import Any

import boto3

from lmjm.repo import BatchRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = event["pathParameters"]["batch_id"]
    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")
    return respond(body=serialize_to_dict(batch))
