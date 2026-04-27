import dataclasses
import json
import os
import uuid
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.model import FeedTruckArrival
from lmjm.model.feed_schedule import FeedScheduleStatus
from lmjm.repo import (
    BatchRepo,
    FeedScheduleFiscalDocumentRepo,
    FeedScheduleRepo,
    FeedTruckArrivalRepo,
    RawMaterialTypeRepo,
)
from lmjm.util.datetime_util import parse_datetime_input
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_truck_arrival_repo = FeedTruckArrivalRepo(table)
feed_schedule_repo = FeedScheduleRepo(table)
feed_schedule_fiscal_document_repo = FeedScheduleFiscalDocumentRepo(table)
raw_material_type_repo = RawMaterialTypeRepo(table)


@dataclasses.dataclass
class PostFeedTruckArrivalRequest:
    receive_date: str
    fiscal_document_number: str
    actual_amount_kg: int
    feed_type: str
    feed_schedule_id: Optional[str] = None
    fiscal_document_sk: Optional[str] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PostFeedTruckArrivalRequest)

    # Validate receive_date
    try:
        receive_date_stored, sk_date_part = parse_datetime_input(request.receive_date)
    except (ValueError, TypeError):
        return respond(status_code=400, error="receive_date must be in YYYYMMDDHHmm or YYYYMMDD format")

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

    # Resolve feed_description from RawMaterialType
    feed_description = ""
    rmt = raw_material_type_repo.get(request.feed_type)
    if rmt:
        feed_description = rmt.description

    arrival = FeedTruckArrival(
        pk=batch_id,
        sk=f"FeedTruckArrival|{sk_date_part}|{sequence}",
        receive_date=receive_date_stored,
        fiscal_document_number=request.fiscal_document_number,
        actual_amount_kg=request.actual_amount_kg,
        feed_type=request.feed_type,
        feed_description=feed_description,
        feed_schedule_id=request.feed_schedule_id,
    )
    feed_truck_arrival_repo.put(arrival)

    # Update FeedScheduleFiscalDocument status to "used" if pending
    fiscal_doc = None
    if request.fiscal_document_sk:
        response = table.get_item(Key={"pk": batch_id, "sk": request.fiscal_document_sk})
        item = response.get("Item")
        if item and item.get("status") == "pending":
            feed_schedule_fiscal_document_repo.update_status(batch_id, request.fiscal_document_sk, "used")
    else:
        fiscal_doc = feed_schedule_fiscal_document_repo.get(batch_id, request.fiscal_document_number)
        if fiscal_doc and fiscal_doc.status == "pending":
            feed_schedule_fiscal_document_repo.update_status(fiscal_doc.pk, fiscal_doc.sk, "used")

    # Update FeedSchedule status to "delivered" if feed_schedule_id provided
    if request.feed_schedule_id:
        feed_schedule_repo.update_status_and_fulfilled_by(
            batch_id, request.feed_schedule_id, FeedScheduleStatus.delivered, arrival.sk
        )

    return respond(status_code=201, body=serialize_to_dict(arrival))
