import dataclasses
import json
import os
import uuid
from typing import Any

import boto3

from lmjm.model import FeedSchedule
from lmjm.repo import BatchRepo, FeedScheduleRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_schedule_repo = FeedScheduleRepo(table)


@dataclasses.dataclass
class FeedScheduleEntry:
    feed_type: str = ""
    planned_date: str = ""
    expected_amount_kg: float = 0.0


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = event["pathParameters"]["batch_id"]

    batch = batch_repo.get(batch_id)
    if not batch:
        return {"statusCode": 404, "body": json.dumps({"message": "Batch not found"})}

    entries: list[dict[str, Any]] = json.loads(event["body"])

    # Delete all existing feed schedule entries for this batch
    feed_schedule_repo.delete_all(batch_id)

    # Create new FeedSchedule records
    new_schedules: list[FeedSchedule] = []
    for entry_dict in entries:
        schedule = FeedSchedule(
            pk=batch_id,
            sk=f"FeedSchedule|{uuid.uuid4()}",
            feed_type=entry_dict.get("feed_type", ""),
            planned_date=entry_dict.get("planned_date", ""),
            expected_amount_kg=float(entry_dict.get("expected_amount_kg", 0.0)),
        )
        feed_schedule_repo.put(schedule)
        new_schedules.append(schedule)

    return {"statusCode": 200, "body": json.dumps(serialize_to_dict_list(new_schedules))}
