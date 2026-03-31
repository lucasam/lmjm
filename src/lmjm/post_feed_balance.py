import dataclasses
import json
import os
from datetime import datetime
from typing import Any

import boto3

from lmjm.model import FeedBalance
from lmjm.repo import BatchRepo, FeedBalanceRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

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
    batch_id = event["pathParameters"]["batch_id"]

    batch = batch_repo.get(batch_id)
    if not batch:
        return {"statusCode": 404, "body": json.dumps({"message": "Batch not found"})}

    request = load_data_class_from_dict(json.loads(event["body"]), PostFeedBalanceRequest)

    # Validate measurement_date
    try:
        parsed_date = datetime.strptime(request.measurement_date, "%Y%m%d")
        measurement_date_stored = parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return {"statusCode": 400, "body": json.dumps({"message": "measurement_date must be in YYYYMMDD format"})}

    # Validate balance_kg non-negative
    if request.balance_kg < 0:
        return {"statusCode": 400, "body": json.dumps({"message": "balance_kg must be non-negative"})}

    date_str = parsed_date.strftime("%Y%m%d")

    feed_balance = FeedBalance(
        pk=batch_id,
        sk=f"FeedBalance|{date_str}",
        measurement_date=measurement_date_stored,
        balance_kg=request.balance_kg,
    )
    feed_balance_repo.put(feed_balance)

    return {"statusCode": 201, "body": json.dumps(serialize_to_dict(feed_balance))}
