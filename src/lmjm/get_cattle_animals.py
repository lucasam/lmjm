import json
import os
from typing import Any

import boto3

from lmjm.repo import AnimalRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    animals = animal_repo.list_cattle()
    return {"statusCode": 200, "body": json.dumps(serialize_to_dict_list(animals))}
