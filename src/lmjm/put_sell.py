import json
import logging
import os
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
    """Update an existing cattle Sell.

    Recomputes net_value. Associated animals are flipped to "Vendida" on a
    best-effort basis so an animal deactivation problem never fails the save.
    """
    sell_id = event["pathParameters"]["sell_id"]
    pk = f"Sell|{sell_id}"

    if sell_repo.get(pk) is None:
        return respond(status_code=404, error="Sell not found")

    body = json.loads(event["body"] or "{}")

    sell, error = parse_sell_request(body, pk)
    if error is not None:
        return error
    assert sell is not None

    sell_repo.put(sell)
    flipped = flip_animals_to_vendida(animal_repo, sell.associated_ear_tags)
    logger.info("Updated Sell %s (%d associated animals flipped to Vendida)", sell.pk, len(flipped))

    return respond(status_code=200, body=serialize_to_dict(sell))
