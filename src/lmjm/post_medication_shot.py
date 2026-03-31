import dataclasses
import json
import os
from datetime import datetime
from typing import Any

import boto3

from lmjm.model import MedicationShot
from lmjm.repo import BatchRepo, MedicationRepo, MedicationShotRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
medication_repo = MedicationRepo(table)
medication_shot_repo = MedicationShotRepo(table)


@dataclasses.dataclass
class PostMedicationShotRequest:
    medication_name: str
    shot_count: int
    date: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = event["pathParameters"]["batch_id"]

    batch = batch_repo.get(batch_id)
    if not batch:
        return {"statusCode": 404, "body": json.dumps({"message": "Batch not found"})}

    request = load_data_class_from_dict(json.loads(event["body"]), PostMedicationShotRequest)

    # Validate medication_name references an existing Medication for this batch
    medications = medication_repo.list(batch_id)
    matching = [m for m in medications if m.medication_name == request.medication_name]
    if not matching:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "medication_name does not reference an existing medication in this batch"}),
        }

    # Validate shot_count is a positive integer
    if not isinstance(request.shot_count, int) or request.shot_count <= 0:
        return {"statusCode": 400, "body": json.dumps({"message": "shot_count must be a positive integer"})}

    # Validate date
    try:
        parsed_date = datetime.strptime(request.date, "%Y%m%d")
    except (ValueError, TypeError):
        return {"statusCode": 400, "body": json.dumps({"message": "date must be in YYYYMMDD format"})}

    date_str = parsed_date.strftime("%Y%m%d")
    medication_id = matching[0].sk.split("|")[1]

    medication_shot = MedicationShot(
        pk=batch_id,
        sk=f"MedicationShot|{date_str}|{medication_id}",
        medication_name=request.medication_name,
        shot_count=request.shot_count,
        date=parsed_date.strftime("%Y-%m-%d"),
    )
    medication_shot_repo.put(medication_shot)

    return {"statusCode": 201, "body": json.dumps(serialize_to_dict(medication_shot))}
