import os
from typing import Any

import boto3

from lmjm.repo import FeedConsumptionTemplateRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

feed_consumption_template_repo = FeedConsumptionTemplateRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    entries = feed_consumption_template_repo.list_all()
    return respond(body=serialize_to_dict_list(entries))
