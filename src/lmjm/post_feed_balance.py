import dataclasses
import json
import os
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import FeedBalance
from lmjm.repo import BatchRepo, FeedBalanceRepo
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
    balance_kg: float


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PostFeedBalanceRequest)

    # Validate measurement_date
    try:
        parsed_date = datetime.strptime(request.measurement_date, "%Y%m%d")
        measurement_date_stored = parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="measurement_date must be in YYYYMMDD format")

    # Validate balance_kg non-negative
    if request.balance_kg < 0:
        return respond(status_code=400, error="balance_kg must be non-negative")

    date_str = parsed_date.strftime("%Y%m%d")

    feed_balance = FeedBalance(
        pk=batch_id,
        sk=f"FeedBalance|{date_str}",
        measurement_date=measurement_date_stored,
        balance_kg=request.balance_kg,
    )
    feed_balance_repo.put(feed_balance)

    return respond(status_code=201, body=serialize_to_dict(feed_balance))
