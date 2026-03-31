import json
import os
from datetime import date, datetime
from typing import Any

import boto3

from lmjm.repo import BatchRepo, PigTruckArrivalRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
pig_truck_arrival_repo = PigTruckArrivalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = event["pathParameters"]["batch_id"]

    batch = batch_repo.get(batch_id)
    if not batch:
        return {"statusCode": 404, "body": json.dumps({"message": "Batch not found"})}

    arrivals = pig_truck_arrival_repo.list(batch_id)
    if not arrivals:
        return {"statusCode": 400, "body": json.dumps({"message": "No pig truck arrivals recorded for this batch"})}

    # Compute total_animal_count
    total_animal_count: int = sum(a.animal_count for a in arrivals)

    # Compute average_start_date (mean of ordinal days)
    ordinals: list[int] = []
    for a in arrivals:
        parsed: date = datetime.strptime(a.arrival_date, "%Y-%m-%d").date()
        ordinals.append(parsed.toordinal())
    avg_ordinal: int = round(sum(ordinals) / len(ordinals))
    average_start_date: str = date.fromordinal(avg_ordinal).strftime("%Y-%m-%d")

    # Compute distinct_origin_count and origin_types
    origin_names: set[str] = {a.origin_name for a in arrivals}
    distinct_origin_count: int = len(origin_names)
    origin_types: list[str] = sorted({a.origin_type for a in arrivals})

    # Update batch
    batch.total_animal_count = total_animal_count
    batch.average_start_date = average_start_date
    batch.distinct_origin_count = distinct_origin_count
    batch.origin_types = origin_types
    batch.status = "in_progress"
    batch_repo.update(batch)

    return {"statusCode": 201, "body": json.dumps(serialize_to_dict(batch))}
