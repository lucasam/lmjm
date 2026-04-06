import dataclasses
import json
import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import FeedBalance
from lmjm.repo import BatchRepo, FeedBalanceRepo
from lmjm.util.datetime_util import parse_datetime_input
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_balance_repo = FeedBalanceRepo(table)


@dataclasses.dataclass
class PostFeedBalanceRequest:
    measurement_date: str
    balance_kg: int


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PostFeedBalanceRequest)

    # Validate measurement_date
    try:
        measurement_date_stored, sk_date_part = parse_datetime_input(request.measurement_date)
    except (ValueError, TypeError):
        return respond(status_code=400, error="measurement_date must be in YYYYMMDDHHmm or YYYYMMDD format")

    # Validate balance_kg non-negative
    if request.balance_kg < 0:
        return respond(status_code=400, error="balance_kg must be non-negative")

    feed_balance = FeedBalance(
        pk=batch_id,
        sk=f"FeedBalance|{sk_date_part}",
        measurement_date=measurement_date_stored,
        balance_kg=request.balance_kg,
    )
    feed_balance_repo.put(feed_balance)

    return respond(status_code=201, body=serialize_to_dict(feed_balance))
