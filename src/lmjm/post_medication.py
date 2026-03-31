import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import Medication
from lmjm.repo import BatchRepo, MedicationRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
medication_repo = MedicationRepo(table)


@dataclasses.dataclass
class PostMedicationRequest:
    medication_name: str
    expiration_date: str
    part_number: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PostMedicationRequest)

    # Validate medication_name
    if not request.medication_name or not request.medication_name.strip():
        return respond(status_code=400, error="medication_name must be non-empty")

    # Validate expiration_date
    try:
        parsed_date = datetime.strptime(request.expiration_date, "%Y%m%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="expiration_date must be in YYYYMMDD format")

    # Validate part_number
    if not request.part_number or not request.part_number.strip():
        return respond(status_code=400, error="part_number must be non-empty")

    medication_id = str(uuid.uuid4())

    medication = Medication(
        pk=batch_id,
        sk=f"Medication|{medication_id}",
        medication_name=request.medication_name,
        expiration_date=parsed_date.strftime("%Y-%m-%d"),
        part_number=request.part_number,
    )
    medication_repo.put(medication)

    return respond(status_code=201, body=serialize_to_dict(medication))
