import dataclasses
import json
import os
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.repo import ModuleRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

module_repo = ModuleRepo(table)


@dataclasses.dataclass
class PutModuleRequest:
    name: Optional[str] = None
    area: Optional[int] = None
    supported_animal_count: Optional[int] = None
    silo_capacity: Optional[int] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    module_id = unquote(event["pathParameters"]["module_id"])

    module = module_repo.get(module_id)
    if not module:
        return respond(status_code=404, error="Module not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PutModuleRequest)

    if request.name is not None:
        module.name = request.name
    if request.area is not None:
        module.area = request.area
    if request.supported_animal_count is not None:
        module.supported_animal_count = request.supported_animal_count
    if request.silo_capacity is not None:
        module.silo_capacity = request.silo_capacity

    module_repo.update(module)

    return respond(body=serialize_to_dict(module))
