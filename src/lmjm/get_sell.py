import os
from typing import Any

import boto3

from lmjm.repo import SellRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

sell_repo = SellRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    sell_id = event["pathParameters"]["sell_id"]
    sell = sell_repo.get(f"Sell|{sell_id}")
    if not sell:
        return respond(status_code=404, error="Sell not found")
    return respond(body=serialize_to_dict(sell))
