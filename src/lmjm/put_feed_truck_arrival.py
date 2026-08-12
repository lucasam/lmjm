import dataclasses
import json
import os
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.repo import BatchRepo, FeedScheduleRepo, FeedTruckArrivalRepo
from lmjm.util.datetime_util import parse_datetime_input
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_truck_arrival_repo = FeedTruckArrivalRepo(table)
feed_schedule_repo = FeedScheduleRepo(table)


@dataclasses.dataclass
class PutFeedTruckArrivalRequest:
    receive_date: Optional[str] = None
    fiscal_document_number: Optional[str] = None
    actual_amount_kg: Optional[int] = None
    feed_type: Optional[str] = None
    feed_description: Optional[str] = None
    feed_schedule_id: Optional[str] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Update an existing feed truck arrival.

    Only fields present in the request body are modified. The sort key (and its
    embedded date) is left unchanged since it is the record's identity.
    """
    batch_id = unquote(event["pathParameters"]["batch_id"])
    arrival_sk = unquote(event["pathParameters"]["arrival_sk"])

    if not batch_repo.get(batch_id):
        return respond(status_code=404, error="Batch not found")

    arrival = feed_truck_arrival_repo.get(batch_id, arrival_sk)
    if not arrival:
        return respond(status_code=404, error="FeedTruckArrival not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PutFeedTruckArrivalRequest)

    if request.receive_date is not None:
        try:
            receive_date_stored, _ = parse_datetime_input(request.receive_date)
        except (ValueError, TypeError):
            return respond(status_code=400, error="receive_date must be in YYYYMMDDHHmm or YYYYMMDD format")
        arrival.receive_date = receive_date_stored

    if request.fiscal_document_number is not None:
        if not request.fiscal_document_number.strip():
            return respond(status_code=400, error="fiscal_document_number must be non-empty")
        arrival.fiscal_document_number = request.fiscal_document_number

    if request.actual_amount_kg is not None:
        if request.actual_amount_kg <= 0:
            return respond(status_code=400, error="actual_amount_kg must be a positive number")
        arrival.actual_amount_kg = request.actual_amount_kg

    if request.feed_type is not None:
        if not request.feed_type.strip():
            return respond(status_code=400, error="feed_type must be non-empty")
        arrival.feed_type = request.feed_type

    if request.feed_description is not None:
        arrival.feed_description = request.feed_description

    if request.feed_schedule_id is not None:
        if request.feed_schedule_id:
            schedule_sks = {s.sk for s in feed_schedule_repo.list(batch_id)}
            if request.feed_schedule_id not in schedule_sks:
                return respond(status_code=404, error="FeedSchedule not found")
            arrival.feed_schedule_id = request.feed_schedule_id
        else:
            arrival.feed_schedule_id = None

    feed_truck_arrival_repo.update(arrival)

    return respond(body=serialize_to_dict(arrival))
