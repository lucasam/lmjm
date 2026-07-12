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
class PostTagRequest:
    tag: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Append a tag to an animal (verbatim, deduplicated)."""
    ear_tag = unquote(event["pathParameters"]["animal_id"])
    request = load_data_class_from_dict(json.loads(event["body"]), PostTagRequest)

    tag_value = (request.tag or "").strip()
    if not tag_value:
        return respond(status_code=400, error="tag must be non-empty")

    animal = animal_repo.get_by_ear_tag(ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")

    if not animal.tags:
        animal.tags = []
    if tag_value not in animal.tags:
        animal.tags.append(tag_value)
        animal_repo.update(animal)
        logger.info("Added tag %s to animal ear_tag=%s pk=%s", tag_value, ear_tag, animal.pk)

    return respond(status_code=201, body=serialize_to_dict(animal))
