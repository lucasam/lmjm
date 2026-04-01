import json
import os
from datetime import datetime, timedelta
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

    # Filter: only keep entries with a positive expected_grams_per_animal
    valid_entries: list[dict[str, Any]] = []
    for entry in entries:
        day_number = entry.get("day_number")
        expected_grams = entry.get("expected_grams_per_animal")

        if not isinstance(day_number, int) or day_number < 1 or day_number > 130:
            return respond(
                status_code=400,
                error=f"day_number must be an integer between 1 and 130, got {day_number}",
            )

        # Skip entries with no value — they just won't be recorded
        if expected_grams is None or expected_grams == "" or expected_grams == 0:
            continue

        if not isinstance(expected_grams, (int, float)) or expected_grams <= 0:
            return respond(
                status_code=400,
                error=f"expected_grams_per_animal must be a positive number, got {expected_grams}",
            )

        valid_entries.append(entry)

    # Delete all existing feed consumption plan entries for this batch
    feed_consumption_plan_repo.delete_all(batch_id)

    # Compute date from batch receive_date + day_number (day 1 = receive_date + 1 day)
    receive_date = datetime.strptime(batch.receive_date, "%Y-%m-%d")

    # Create new FeedConsumptionPlan records
    new_plans: list[FeedConsumptionPlan] = []
    for entry_dict in valid_entries:
        day_number = entry_dict["day_number"]
        plan_date = receive_date + timedelta(days=day_number)
        plan = FeedConsumptionPlan(
            pk=batch_id,
            sk=f"FeedConsumptionPlan|{day_number}",
            day_number=day_number,
            expected_grams_per_animal=int(entry_dict["expected_grams_per_animal"]),
            date=plan_date.strftime("%Y-%m-%d"),
        )
        new_plans.append(plan)

    feed_consumption_plan_repo.put_all(new_plans)

    return respond(body=serialize_to_dict_list(new_plans))
