import dataclasses
import json
import logging
import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import AnimalRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)


@dataclasses.dataclass
class PutEarTagRequest:
    new_ear_tag: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Replace an animal's ear_tag.

    The ear_tag is a GSI-indexed attribute (not the primary key), and related
    records (inseminations, diagnostics, weights) are keyed by the animal's pk,
    so replacing it is a single attribute update that leaves history intact.
    """
    current_ear_tag = unquote(event["pathParameters"]["animal_id"])
    request = load_data_class_from_dict(json.loads(event["body"]), PutEarTagRequest)

    new_ear_tag = (request.new_ear_tag or "").strip()
    if not new_ear_tag:
        return respond(status_code=400, error="new_ear_tag must be non-empty")

    animal = animal_repo.get_by_ear_tag(current_ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")

    # No-op when the tag is unchanged.
    if new_ear_tag == animal.ear_tag:
        return respond(status_code=200, body=serialize_to_dict(animal))

    # Reject if another animal already uses the target ear_tag (GSI lookups assume uniqueness).
    existing = animal_repo.get_by_ear_tag(new_ear_tag)
    if existing and existing.pk != animal.pk:
        return respond(status_code=409, error=f"Ear tag {new_ear_tag} is already in use")

    old_ear_tag = animal.ear_tag
    animal.ear_tag = new_ear_tag
    animal_repo.update(animal)
    logger.info("Replaced ear_tag %s -> %s (pk=%s)", old_ear_tag, new_ear_tag, animal.pk)

    return respond(status_code=200, body=serialize_to_dict(animal))
