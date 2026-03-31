import dataclasses
import json
import os
import uuid
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import Warehouse
from lmjm.repo import WarehouseRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

warehouse_repo = WarehouseRepo(table)


@dataclasses.dataclass
class PostWarehouseRequest:
    name: str
    area: float = 0.0
    supported_animal_count: int = 0
    silo_capacity: float = 0.0


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    module_id = unquote(event["pathParameters"]["module_id"])
    request = load_data_class_from_dict(json.loads(event["body"]), PostWarehouseRequest)

    if not request.name or not request.name.strip():
        return respond(status_code=400, error="name must be non-empty")

    if not isinstance(request.supported_animal_count, int) or request.supported_animal_count <= 0:
        return respond(status_code=400, error="supported_animal_count must be a positive integer")

    warehouse_id = str(uuid.uuid4())

    warehouse = Warehouse(
        pk=module_id,
        sk=f"Warehouse|{warehouse_id}",
        name=request.name,
        area=request.area,
        supported_animal_count=request.supported_animal_count,
        silo_capacity=request.silo_capacity,
    )
    warehouse_repo.put(warehouse)

    return respond(status_code=201, body=serialize_to_dict(warehouse))
