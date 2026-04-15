import json
import os
from decimal import Decimal
from typing import Any

import boto3

from lmjm.model import FeedConsumptionTemplate
from lmjm.repo import FeedConsumptionTemplateRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

feed_consumption_template_repo = FeedConsumptionTemplateRepo(table)

REQUIRED_FIELDS = ["sequence", "expected_piglet_weight", "expected_kg_per_animal"]


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    body = json.loads(event["body"])

    # Validate required fields
    missing = [f for f in REQUIRED_FIELDS if f not in body or body[f] is None]
    if missing:
        return respond(status_code=400, error=f"Missing required fields: {', '.join(missing)}")

    # Validate sequence >= 0
    if body["sequence"] < 0:
        return respond(status_code=400, error="sequence must be >= 0")

    # Validate expected_kg_per_animal >= 0
    if body["expected_kg_per_animal"] < 0:
        return respond(status_code=400, error="expected_kg_per_animal must be >= 0")

    sequence = body["sequence"]

    record = FeedConsumptionTemplate(
        pk="FEED_CONSUMPTION_TEMPLATE",
        sk=f"FeedConsumptionTemplate|{sequence}",
        sequence=sequence,
        expected_piglet_weight=body["expected_piglet_weight"],
        expected_kg_per_animal=Decimal(str(body["expected_kg_per_animal"])),
    )

    feed_consumption_template_repo.put(record)

    return respond(status_code=201, body=serialize_to_dict(record))
