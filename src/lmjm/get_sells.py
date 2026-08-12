import os
from typing import Any

import boto3

from lmjm.repo import SellRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

sell_repo = SellRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    sells = sell_repo.list_all()
    sells.sort(key=lambda s: s.sell_date, reverse=True)
    return respond(body=serialize_to_dict_list(sells))
