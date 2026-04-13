import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.bordero_calculator import BorderoInput, calculate_bordero
from lmjm.repo import BatchFinancialResultRepo, BatchRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
batch_financial_result_repo = BatchFinancialResultRepo(table)

REQUIRED_FIELDS = [
    "type",
    "housed_count",
    "mortality_count",
    "total_feed",
    "piglet_weight",
    "pig_weight",
    "days_housed",
    "cap",
    "map_value",
    "price_per_kg",
    "piglet_adjustment",
    "carcass_adjustment",
]

VALID_TYPES = ("simulation", "actual")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    body = json.loads(event["body"])

    # Validate required fields
    missing = [f for f in REQUIRED_FIELDS if f not in body or body[f] is None]
    if missing:
        return respond(status_code=400, error=f"Missing required fields: {', '.join(missing)}")

    # Validate type
    result_type = body["type"]
    if result_type not in VALID_TYPES:
        return respond(status_code=400, error="type must be 'simulation' or 'actual'")

    # Build BorderoInput and calculate
    try:
        bordero_input = BorderoInput(
            housed_count=int(body["housed_count"]),
            mortality_count=int(body["mortality_count"]),
            piglet_weight=Decimal(str(body["piglet_weight"])),
            pig_weight=Decimal(str(body["pig_weight"])),
            total_feed=Decimal(str(body["total_feed"])),
            days_housed=int(body["days_housed"]),
            cap=Decimal(str(body["cap"])),
            map_value=Decimal(str(body["map_value"])),
            price_per_kg=Decimal(str(body["price_per_kg"])),
            piglet_adjustment=Decimal(str(body["piglet_adjustment"])),
            carcass_adjustment=Decimal(str(body["carcass_adjustment"])),
        )
        result = calculate_bordero(bordero_input)
    except (ValueError, InvalidOperation) as e:
        return respond(status_code=400, error=str(e))

    # If type=actual, delete existing simulation
    if result_type == "actual":
        batch_financial_result_repo.delete(batch_id, "simulation")

    # Set record metadata
    result.pk = batch_id
    result.sk = f"BatchFinancialResult|{result_type}"
    result.type = result_type
    result.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")

    # Persist (put_item overwrites existing record of same type)
    batch_financial_result_repo.put(result)

    return respond(status_code=201, body=serialize_to_dict(result))
