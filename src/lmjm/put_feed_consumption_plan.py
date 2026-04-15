import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import FeedConsumptionPlan
from lmjm.repo import BatchRepo, FeedConsumptionPlanRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_consumption_plan_repo = FeedConsumptionPlanRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    try:
        entries: list[dict[str, Any]] = json.loads(event["body"])
    except (json.JSONDecodeError, TypeError):
        return respond(status_code=400, error="Invalid JSON body")

    if not isinstance(entries, list):
        return respond(status_code=400, error="Body must be a JSON array")

    # Filter: only keep entries with a positive expected_kg_per_animal
    valid_entries: list[dict[str, Any]] = []
    for entry in entries:
        day_number = entry.get("day_number")
        expected_kg = entry.get("expected_kg_per_animal")

        if not isinstance(day_number, int) or day_number < 1 or day_number > 130:
            return respond(
                status_code=400,
                error=f"day_number must be an integer between 1 and 130, got {day_number}",
            )

        # Skip entries with no value — they just won't be recorded
        if expected_kg is None or expected_kg == "" or expected_kg == 0:
            continue

        if not isinstance(expected_kg, (int, float)) or expected_kg <= 0:
            return respond(
                status_code=400,
                error=f"expected_kg_per_animal must be a positive number, got {expected_kg}",
            )

        valid_entries.append(entry)

    # Delete all existing feed consumption plan entries for this batch
    feed_consumption_plan_repo.delete_all(batch_id)

    # Compute date from batch average_start_date + day_number (day 1 = average_start_date + 1 day)
    if batch.average_start_date is None:
        return respond(status_code=400, error="average_start_date is required — generate the batch start summary first")
    receive_date = datetime.strptime(batch.average_start_date, "%Y-%m-%d")

    # Create new FeedConsumptionPlan records
    new_plans: list[FeedConsumptionPlan] = []
    for entry_dict in valid_entries:
        day_number = entry_dict["day_number"]
        plan_date = receive_date + timedelta(days=day_number)
        plan = FeedConsumptionPlan(
            pk=batch_id,
            sk=f"FeedConsumptionPlan|{day_number}",
            day_number=day_number,
            expected_kg_per_animal=Decimal(str(entry_dict["expected_kg_per_animal"])),
            expected_piglet_weight=int(entry_dict.get("expected_piglet_weight", 0)),
            date=plan_date.strftime("%Y-%m-%d"),
        )
        new_plans.append(plan)

    feed_consumption_plan_repo.put_all(new_plans)

    return respond(body=serialize_to_dict_list(new_plans))
