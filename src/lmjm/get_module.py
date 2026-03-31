import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import ModuleRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

module_repo = ModuleRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    module_id: str = unquote(event["pathParameters"]["module_id"])
    module = module_repo.get(module_id)
    if not module:
        return respond(status_code=404, error="Module not found")
    return respond(body=serialize_to_dict(module))
