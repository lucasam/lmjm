import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.model import FeedTruckArrival
from lmjm.repo import BatchRepo, FeedScheduleRepo, FeedTruckArrivalRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_truck_arrival_repo = FeedTruckArrivalRepo(table)
feed_schedule_repo = FeedScheduleRepo(table)


@dataclasses.dataclass
class PostFeedTruckArrivalRequest:
    receive_date: str
    fiscal_document_number: str
    actual_amount_kg: float
    feed_type: str
    feed_schedule_id: Optional[str] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PostFeedTruckArrivalRequest)

    # Validate receive_date
    try:
        parsed_date = datetime.strptime(request.receive_date, "%Y%m%d")
        receive_date_stored = parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="receive_date must be in YYYYMMDD format")

    # Validate fiscal_document_number
    if not request.fiscal_document_number or not request.fiscal_document_number.strip():
        return respond(status_code=400, error="fiscal_document_number must be non-empty")

    # Validate actual_amount_kg
    if request.actual_amount_kg <= 0:
        return respond(status_code=400, error="actual_amount_kg must be a positive number")

    # Validate feed_type
    if not request.feed_type or not request.feed_type.strip():
        return respond(status_code=400, error="feed_type must be non-empty")

    # Validate feed_schedule_id if provided
    if request.feed_schedule_id:
        schedules = feed_schedule_repo.list(batch_id)
        schedule_sks = {s.sk for s in schedules}
        if request.feed_schedule_id not in schedule_sks:
            return respond(status_code=404, error="FeedSchedule not found")

    sequence = str(uuid.uuid4())
    date_str = parsed_date.strftime("%Y%m%d")

    arrival = FeedTruckArrival(
        pk=batch_id,
        sk=f"FeedTruckArrival|{date_str}|{sequence}",
        receive_date=receive_date_stored,
        fiscal_document_number=request.fiscal_document_number,
        actual_amount_kg=request.actual_amount_kg,
        feed_type=request.feed_type,
        feed_schedule_id=request.feed_schedule_id,
    )
    feed_truck_arrival_repo.put(arrival)

    return respond(status_code=201, body=serialize_to_dict(arrival))
