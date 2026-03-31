import dataclasses
import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import boto3

from lmjm.model import Batch
from lmjm.repo import BatchRepo, ModuleRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

module_repo = ModuleRepo(table)
batch_repo = BatchRepo(table)


@dataclasses.dataclass
class PostBatchRequest:
    supply_id: int
    module_id: str
    warehouse_ids: list[str]
    pig_count: int
    receive_date: str
    min_feed_stock_threshold: float
    expected_slaughter_date: Optional[str] = None


def _parse_date(value: str, field_name: str) -> Optional[str]:
    try:
        parsed = datetime.strptime(value, "%Y%m%d")
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request = load_data_class_from_dict(json.loads(event["body"]), PostBatchRequest)

    # Validate module exists
    module = module_repo.get(request.module_id)
    if not module:
        return respond(status_code=404, error="Module not found")

    # Validate warehouse_ids exist within the module
    warehouses = module_repo.query_warehouses(request.module_id)
    warehouse_sks = {w.sk for w in warehouses}
    for wid in request.warehouse_ids:
        if wid not in warehouse_sks:
            return respond(status_code=400, error=f"Warehouse {wid} not found in module")

    # Parse dates
    receive_date = _parse_date(request.receive_date, "receive_date")
    if not receive_date:
        return respond(status_code=400, error="receive_date must be in YYYYMMDD format")

    expected_slaughter_date: Optional[str] = None
    if request.expected_slaughter_date:
        expected_slaughter_date = _parse_date(request.expected_slaughter_date, "expected_slaughter_date")
        if not expected_slaughter_date:
            return respond(status_code=400, error="expected_slaughter_date must be in YYYYMMDD format")

    batch_pk = str(uuid.uuid4())
    batch = Batch(
        pk=batch_pk,
        sk="Batch",
        status="created",
        supply_id=request.supply_id,
        module_id=request.module_id,
        warehouse_ids=request.warehouse_ids,
        receive_date=receive_date,
        expected_slaughter_date=expected_slaughter_date,
        pig_count=request.pig_count,
        min_feed_stock_threshold=request.min_feed_stock_threshold,
    )
    batch_repo.update(batch)

    return respond(status_code=201, body=serialize_to_dict(batch))
