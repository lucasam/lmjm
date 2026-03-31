import json
import os
from typing import Any

import boto3

from lmjm.repo import ModuleRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict, serialize_to_dict_list

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

module_repo = ModuleRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    module_id: str = event["pathParameters"]["module_id"]
    module = module_repo.get(module_id)
    if not module:
        return {"statusCode": 404, "body": json.dumps({"message": "Module not found"})}
    warehouses = module_repo.query_warehouses(module_id)
    result = serialize_to_dict(module)
    result["warehouses"] = serialize_to_dict_list(warehouses)
    return {"statusCode": 200, "body": json.dumps(result)}
