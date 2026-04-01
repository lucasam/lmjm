import dataclasses
import json
import os
from datetime import datetime
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.repo import BatchRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)


@dataclasses.dataclass
class PutBatchRequest:
    status: Optional[str] = None
    supply_id: Optional[int] = None
    receive_date: Optional[str] = None
    expected_slaughter_date: Optional[str] = None
    min_feed_stock_threshold: Optional[int] = None
    total_animal_count: Optional[int] = None
    average_start_date: Optional[str] = None
    distinct_origin_count: Optional[int] = None
    origin_types: Optional[list[str]] = None


def _parse_date(value: str) -> Optional[str]:
    try:
        return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PutBatchRequest)

    if request.status is not None:
        batch.status = request.status
    if request.supply_id is not None:
        batch.supply_id = request.supply_id
    if request.receive_date is not None:
        parsed = _parse_date(request.receive_date)
        if not parsed:
            return respond(status_code=400, error="receive_date must be in YYYYMMDD format")
        batch.receive_date = parsed
    if request.expected_slaughter_date is not None:
        parsed = _parse_date(request.expected_slaughter_date)
        if not parsed:
            return respond(status_code=400, error="expected_slaughter_date must be in YYYYMMDD format")
        batch.expected_slaughter_date = parsed
    if request.min_feed_stock_threshold is not None:
        batch.min_feed_stock_threshold = request.min_feed_stock_threshold
    if request.total_animal_count is not None:
        batch.total_animal_count = request.total_animal_count
    if request.average_start_date is not None:
        parsed = _parse_date(request.average_start_date)
        if not parsed:
            return respond(status_code=400, error="average_start_date must be in YYYYMMDD format")
        batch.average_start_date = parsed
    if request.distinct_origin_count is not None:
        batch.distinct_origin_count = request.distinct_origin_count
    if request.origin_types is not None:
        batch.origin_types = request.origin_types

    batch_repo.update(batch)

    return respond(body=serialize_to_dict(batch))
