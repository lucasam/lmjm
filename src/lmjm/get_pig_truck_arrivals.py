import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import PigTruckArrivalRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

pig_truck_arrival_repo = PigTruckArrivalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = unquote(event["pathParameters"]["batch_id"])
    arrivals = pig_truck_arrival_repo.list(batch_id)
    return respond(body=serialize_to_dict_list(arrivals))
