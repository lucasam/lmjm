import json
import logging
import os
import uuid
from typing import Any

import boto3

from lmjm.repo import AnimalRepo, SellRepo
from lmjm.service.sell_service import flip_animals_to_vendida, parse_sell_request
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

sell_repo = SellRepo(table)
animal_repo = AnimalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Create a cattle Sell record.

    net_value is computed server-side. Associated animals (by ear_tag) are
    flipped to status "Vendida" on a best-effort basis (never fails the save).
    """
    body = json.loads(event["body"] or "{}")

    sell, error = parse_sell_request(body, f"Sell|{uuid.uuid4()}")
    if error is not None:
        return error
    assert sell is not None

    sell_repo.put(sell)
    flipped = flip_animals_to_vendida(animal_repo, sell.associated_ear_tags)
    logger.info("Created Sell %s (%d associated animals flipped to Vendida)", sell.pk, len(flipped))

    return respond(status_code=201, body=serialize_to_dict(sell))
