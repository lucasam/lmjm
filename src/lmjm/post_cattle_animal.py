import dataclasses
import json
import logging
import os
import uuid
from typing import Any, Optional

import boto3

from lmjm.model import Animal
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
class PostAnimalRequest:
    ear_tag: str
    breed: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[str] = None
    mother: Optional[str] = None
    batch: Optional[str] = None
    status: Optional[str] = None
    pregnant: Optional[bool] = None
    implanted: Optional[bool] = None
    inseminated: Optional[bool] = None
    lactating: Optional[bool] = None
    transferred: Optional[bool] = None
    tags: Optional[list[str]] = None
    notes: Optional[list[str]] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Create a new cattle animal from scratch."""
    request = load_data_class_from_dict(json.loads(event["body"]), PostAnimalRequest)

    ear_tag = (request.ear_tag or "").strip()
    if not ear_tag:
        return respond(status_code=400, error="ear_tag must be non-empty")

    # Ear tags must be unique (GSI lookups assume uniqueness).
    if animal_repo.get_by_ear_tag(ear_tag):
        return respond(status_code=409, error=f"Ear tag {ear_tag} is already in use")

    animal = Animal(
        pk=str(uuid.uuid4()),
        sk="Animal",
        species="cattle",
        ear_tag=ear_tag,
        breed=request.breed,
        sex=request.sex,
        birth_date=request.birth_date,
        mother=request.mother,
        batch=request.batch,
        status=request.status,
        pregnant=request.pregnant,
        implanted=request.implanted,
        inseminated=request.inseminated,
        lactating=request.lactating,
        transferred=request.transferred,
        tags=request.tags,
        notes=request.notes,
    )
    animal_repo.update(animal)
    logger.info("Created Animal ear_tag=%s pk=%s", ear_tag, animal.pk)

    return respond(status_code=201, body=serialize_to_dict(animal))
