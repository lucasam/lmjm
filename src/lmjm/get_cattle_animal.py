import os
from typing import Any

import boto3

from lmjm.repo import AnimalRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    animal_id: str = event["pathParameters"]["animal_id"]
    animal = animal_repo.get_by_ear_tag(animal_id)
    if not animal:
        return respond(status_code=404, error="Animal not found")
    return respond(body=serialize_to_dict(animal))
