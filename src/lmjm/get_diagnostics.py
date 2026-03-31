import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import AnimalRepo, DiagnosticRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)
diagnostic_repo = DiagnosticRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ear_tag: str = unquote(event["pathParameters"]["animal_id"])
    animal = animal_repo.get_by_ear_tag(ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")
    diagnostics = diagnostic_repo.list(animal.pk)
    return respond(body=serialize_to_dict_list(diagnostics))
