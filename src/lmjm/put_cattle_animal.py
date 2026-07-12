import json
import logging
import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import AnimalRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)

# Fields editable through this endpoint. ear_tag is intentionally excluded: it is
# a GSI key with uniqueness rules and has a dedicated replace endpoint.
UPDATABLE_FIELDS = {
    "breed",
    "sex",
    "birth_date",
    "mother",
    "batch",
    "status",
    "pregnant",
    "implanted",
    "inseminated",
    "lactating",
    "transferred",
    "tags",
    "notes",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Update an existing cattle animal.

    Only fields present in the request body are modified, so attributes not sent
    by the caller (e.g. notes managed elsewhere) are preserved.
    """
    ear_tag = unquote(event["pathParameters"]["animal_id"])
    body = json.loads(event["body"] or "{}")

    animal = animal_repo.get_by_ear_tag(ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")

    for field in UPDATABLE_FIELDS:
        if field in body:
            setattr(animal, field, body[field])

    animal_repo.update(animal)
    logger.info("Updated Animal ear_tag=%s pk=%s", ear_tag, animal.pk)

    return respond(status_code=200, body=serialize_to_dict(animal))
