import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import Mortality
from lmjm.repo import BatchRepo, MortalityRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
mortality_repo = MortalityRepo(table)


@dataclasses.dataclass
class PostMortalityRequest:
    mortality_date: str
    sex: str
    origin: str
    death_reason: str
    reported_by: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PostMortalityRequest)

    # Validate mortality_date
    try:
        parsed_date = datetime.strptime(request.mortality_date, "%Y%m%d")
        mortality_date_stored = parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="mortality_date must be in YYYYMMDD format")

    # Validate sex
    if request.sex not in ("Male", "Female"):
        return respond(status_code=400, error="sex must be Male or Female")

    # Validate origin
    if not request.origin or not request.origin.strip():
        return respond(status_code=400, error="origin must be non-empty")

    # Validate death_reason
    if not request.death_reason or not request.death_reason.strip():
        return respond(status_code=400, error="death_reason must be non-empty")

    # Validate reported_by
    if not request.reported_by or not request.reported_by.strip():
        return respond(status_code=400, error="reported_by must be non-empty")

    sequence = str(uuid.uuid4())
    date_str = parsed_date.strftime("%Y%m%d")

    mortality = Mortality(
        pk=batch_id,
        sk=f"Mortality|{date_str}|{sequence}",
        mortality_date=mortality_date_stored,
        sex=request.sex,
        origin=request.origin,
        death_reason=request.death_reason,
        reported_by=request.reported_by,
    )
    mortality_repo.put(mortality)

    return respond(status_code=201, body=serialize_to_dict(mortality))
