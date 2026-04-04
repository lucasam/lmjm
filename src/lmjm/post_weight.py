import dataclasses
import json
import os
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import Weight
from lmjm.repo import AnimalRepo, WeightRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)
weight_repo = WeightRepo(table)


@dataclasses.dataclass
class PostWeightRequest:
    weighing_date: str
    weight_kg: int


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ear_tag = unquote(event["pathParameters"]["animal_id"])
    request = load_data_class_from_dict(json.loads(event["body"]), PostWeightRequest)

    animal = animal_repo.get_by_ear_tag(ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")

    try:
        parsed_date = datetime.strptime(request.weighing_date, "%Y%m%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="weighing_date must be in YYYYMMDD format")

    date_str = parsed_date.strftime("%Y%m%d")
    weight = Weight(
        pk=animal.pk,
        sk=f"Peso|{date_str}",
        weight_kg=request.weight_kg,
        weighing_date=parsed_date.strftime("%Y-%m-%d"),
    )
    weight_repo.put(weight)

    return respond(status_code=201, body=serialize_to_dict(weight))
