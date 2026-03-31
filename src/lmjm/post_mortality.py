import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any

import boto3

from lmjm.model import Mortality
from lmjm.repo import BatchRepo, MortalityRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

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
    batch_id = event["pathParameters"]["batch_id"]

    batch = batch_repo.get(batch_id)
    if not batch:
        return {"statusCode": 404, "body": json.dumps({"message": "Batch not found"})}

    request = load_data_class_from_dict(json.loads(event["body"]), PostMortalityRequest)

    # Validate mortality_date
    try:
        parsed_date = datetime.strptime(request.mortality_date, "%Y%m%d")
        mortality_date_stored = parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return {"statusCode": 400, "body": json.dumps({"message": "mortality_date must be in YYYYMMDD format"})}

    # Validate sex
    if request.sex not in ("Male", "Female"):
        return {"statusCode": 400, "body": json.dumps({"message": "sex must be Male or Female"})}

    # Validate origin
    if not request.origin or not request.origin.strip():
        return {"statusCode": 400, "body": json.dumps({"message": "origin must be non-empty"})}

    # Validate death_reason
    if not request.death_reason or not request.death_reason.strip():
        return {"statusCode": 400, "body": json.dumps({"message": "death_reason must be non-empty"})}

    # Validate reported_by
    if not request.reported_by or not request.reported_by.strip():
        return {"statusCode": 400, "body": json.dumps({"message": "reported_by must be non-empty"})}

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

    return {"statusCode": 201, "body": json.dumps(serialize_to_dict(mortality))}
