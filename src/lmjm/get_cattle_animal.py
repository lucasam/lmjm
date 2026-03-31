import json
import os
from typing import Any

import boto3

from lmjm.repo import AnimalRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    animal_id: str = event["pathParameters"]["animal_id"]
    animal = animal_repo.get_by_ear_tag(animal_id)
    if not animal:
        return {"statusCode": 404, "body": json.dumps({"message": "Animal not found"})}
    return {"statusCode": 200, "body": json.dumps(serialize_to_dict(animal))}
