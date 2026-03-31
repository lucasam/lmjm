import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import FeedBalanceRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

feed_balance_repo = FeedBalanceRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = unquote(event["pathParameters"]["batch_id"])
    balances = feed_balance_repo.list(batch_id)
    return respond(body=serialize_to_dict_list(balances))
