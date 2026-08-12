import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import FeedTruckArrivalRepo
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

feed_truck_arrival_repo = FeedTruckArrivalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])
    arrival_sk = unquote(event["pathParameters"]["arrival_sk"])

    feed_truck_arrival_repo.delete(batch_id, arrival_sk)

    return respond(status_code=200)
