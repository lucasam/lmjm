import json
import os
import uuid
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import FeedSchedule
from lmjm.model.feed_schedule import FeedScheduleStatus
from lmjm.repo import BatchRepo, FeedScheduleRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_schedule_repo = FeedScheduleRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    entries: list[dict[str, Any]] = json.loads(event["body"])

    # Build set of incoming sks to know which existing ones to keep
    incoming_sks: set[str] = set()
    for entry_dict in entries:
        sk = entry_dict.get("sk", "")
        if sk:
            incoming_sks.add(sk)

    # Delete existing entries not present in the incoming list
    existing = feed_schedule_repo.list(batch_id)
    for ex in existing:
        if ex.sk not in incoming_sks:
            feed_schedule_repo.delete(batch_id, ex.sk)

    # Upsert: update existing entries, create new ones
    result: list[FeedSchedule] = []
    for entry_dict in entries:
        sk = entry_dict.get("sk", "")
        if not sk:
            sk = f"FeedSchedule|{uuid.uuid4()}"

        schedule = FeedSchedule(
            pk=batch_id,
            sk=sk,
            feed_type=entry_dict.get("feed_type", ""),
            planned_date=entry_dict.get("planned_date", ""),
            expected_amount_kg=int(entry_dict.get("expected_amount_kg", 0)),
            status=FeedScheduleStatus(entry_dict.get("status", "scheduled")),
            fulfilled_by=entry_dict.get("fulfilled_by"),
        )
        feed_schedule_repo.put(schedule)
        result.append(schedule)

    return respond(body=serialize_to_dict_list(result))
