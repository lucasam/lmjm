import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any

import boto3

from lmjm.model import Medication
from lmjm.repo import BatchRepo, MedicationRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

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
    batch_id = event["pathParameters"]["batch_id"]

    batch = batch_repo.get(batch_id)
    if not batch:
        return {"statusCode": 404, "body": json.dumps({"message": "Batch not found"})}

    request = load_data_class_from_dict(json.loads(event["body"]), PostMedicationRequest)

    # Validate medication_name
    if not request.medication_name or not request.medication_name.strip():
        return {"statusCode": 400, "body": json.dumps({"message": "medication_name must be non-empty"})}

    # Validate expiration_date
    try:
        parsed_date = datetime.strptime(request.expiration_date, "%Y%m%d")
    except (ValueError, TypeError):
        return {"statusCode": 400, "body": json.dumps({"message": "expiration_date must be in YYYYMMDD format"})}

    # Validate part_number
    if not request.part_number or not request.part_number.strip():
        return {"statusCode": 400, "body": json.dumps({"message": "part_number must be non-empty"})}

    medication_id = str(uuid.uuid4())

    medication = Medication(
        pk=batch_id,
        sk=f"Medication|{medication_id}",
        medication_name=request.medication_name,
        expiration_date=parsed_date.strftime("%Y-%m-%d"),
        part_number=request.part_number,
    )
    medication_repo.put(medication)

    return {"statusCode": 201, "body": json.dumps(serialize_to_dict(medication))}
