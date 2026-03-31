import os
from typing import Any

import boto3

from lmjm.repo import FeedConsumptionPlanRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

feed_consumption_plan_repo = FeedConsumptionPlanRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = event["pathParameters"]["batch_id"]
    plans = feed_consumption_plan_repo.list(batch_id)
    return respond(body=serialize_to_dict_list(plans))
