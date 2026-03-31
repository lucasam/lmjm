import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import PigTruckArrival
from lmjm.repo import BatchRepo, PigTruckArrivalRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
pig_truck_arrival_repo = PigTruckArrivalRepo(table)


@dataclasses.dataclass
class PostPigTruckArrivalRequest:
    animal_count: int
    sex: str
    arrival_date: str
    pig_age_days: int
    origin_name: str
    origin_type: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PostPigTruckArrivalRequest)

    # Validate animal_count
    if request.animal_count <= 0:
        return respond(status_code=400, error="animal_count must be a positive integer")

    # Validate sex
    if request.sex not in ("Male", "Female"):
        return respond(status_code=400, error="sex must be Male or Female")

    # Validate arrival_date
    try:
        parsed_date = datetime.strptime(request.arrival_date, "%Y%m%d")
        arrival_date_stored = parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="arrival_date must be in YYYYMMDD format")

    # Validate pig_age_days
    if request.pig_age_days <= 0:
        return respond(status_code=400, error="pig_age_days must be a positive integer")

    # Validate origin_name
    if not request.origin_name or not request.origin_name.strip():
        return respond(status_code=400, error="origin_name must be non-empty")

    # Validate origin_type
    if request.origin_type not in ("UPL", "Creche"):
        return respond(status_code=400, error="origin_type must be UPL or Creche")

    sequence = str(uuid.uuid4())
    date_str = parsed_date.strftime("%Y%m%d")

    arrival = PigTruckArrival(
        pk=batch_id,
        sk=f"PigTruckArrival|{date_str}|{sequence}",
        animal_count=request.animal_count,
        sex=request.sex,
        arrival_date=arrival_date_stored,
        pig_age_days=request.pig_age_days,
        origin_name=request.origin_name,
        origin_type=request.origin_type,
    )
    pig_truck_arrival_repo.put(arrival)

    return respond(status_code=201, body=serialize_to_dict(arrival))
