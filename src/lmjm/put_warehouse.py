import dataclasses
import json
import os
from typing import Any

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
class PutWarehouseRequest:
    name: str = ""
    area: float = 0.0
    supported_animal_count: int = 0
    silo_capacity: float = 0.0


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    module_id = event["pathParameters"]["module_id"]
    warehouse_id = event["pathParameters"]["warehouse_id"]
    request = load_data_class_from_dict(json.loads(event["body"]), PutWarehouseRequest)

    warehouse = Warehouse(
        pk=module_id,
        sk=f"Warehouse|{warehouse_id}",
        name=request.name,
        area=request.area,
        supported_animal_count=request.supported_animal_count,
        silo_capacity=request.silo_capacity,
    )
    warehouse_repo.update(warehouse)

    return respond(body=serialize_to_dict(warehouse))
