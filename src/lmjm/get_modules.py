import json
import os
from typing import Any

import boto3

from lmjm.repo import ModuleRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

module_repo = ModuleRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    modules = module_repo.list()
    return {"statusCode": 200, "body": json.dumps(serialize_to_dict_list(modules))}
