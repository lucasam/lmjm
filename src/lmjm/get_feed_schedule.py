import json
import os
from typing import Any

import boto3

from lmjm.repo import FeedScheduleRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

feed_schedule_repo = FeedScheduleRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = event["pathParameters"]["batch_id"]
    entries = feed_schedule_repo.list(batch_id)
    return {"statusCode": 200, "body": json.dumps(serialize_to_dict_list(entries))}
