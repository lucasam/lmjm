import json
import os
from typing import Any

import boto3

from lmjm.repo import AnimalRepo, DiagnosticRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)
diagnostic_repo = DiagnosticRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ear_tag: str = event["pathParameters"]["animal_id"]
    animal = animal_repo.get_by_ear_tag(ear_tag)
    if not animal:
        return {"statusCode": 404, "body": json.dumps({"message": "Animal not found"})}
    diagnostics = diagnostic_repo.list(animal.pk)
    return {"statusCode": 200, "body": json.dumps(serialize_to_dict_list(diagnostics))}
