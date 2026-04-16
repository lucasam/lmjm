import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import FeedConsumptionPlan
from lmjm.repo import BatchRepo, FeedConsumptionPlanRepo, FeedConsumptionTemplateRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_consumption_plan_repo = FeedConsumptionPlanRepo(table)
feed_consumption_template_repo = FeedConsumptionTemplateRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    # Parse optional body parameters
    body: dict[str, Any] = {}
    if event.get("body"):
        body = json.loads(event["body"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    # Use body overrides if provided, otherwise fall back to batch values
    average_start_date: str | None = body.get("average_start_date") or batch.average_start_date
    initial_animal_weight_raw: Any = body.get("initial_animal_weight")
    initial_animal_weight: Decimal | None = (
        Decimal(str(initial_animal_weight_raw))
        if initial_animal_weight_raw is not None
        else batch.initial_animal_weight
    )

    if not average_start_date:
        return respond(status_code=400, error="average_start_date is required — generate the batch start summary first")

    if not initial_animal_weight:
        return respond(
            status_code=400, error="initial_animal_weight is required — generate the batch start summary first"
        )

    templates = feed_consumption_template_repo.list_all()

    # Find first template where expected_piglet_weight >= initial_animal_weight
    start_index: int | None = None
    for i, t in enumerate(templates):
        if t.expected_piglet_weight >= initial_animal_weight:
            start_index = i
            break

    if start_index is None:
        return respond(
            status_code=400,
            error=f"No template entry found with expected_piglet_weight >= {initial_animal_weight}",
        )

    # Delete existing plan entries
    feed_consumption_plan_repo.delete_all(batch_id)

    # Generate new plan entries from the matched template onward
    receive_date = datetime.strptime(average_start_date, "%Y-%m-%d")
    new_plans: list[FeedConsumptionPlan] = []

    for j, template in enumerate(templates[start_index:], start=1):
        plan_date = receive_date + timedelta(days=j)
        plan = FeedConsumptionPlan(
            pk=batch_id,
            sk=f"FeedConsumptionPlan|{j}",
            day_number=j,
            expected_kg_per_animal=Decimal(str(template.expected_kg_per_animal)),
            expected_piglet_weight=Decimal(str(template.expected_piglet_weight)),
            date=plan_date.strftime("%Y-%m-%d"),
        )
        new_plans.append(plan)

    feed_consumption_plan_repo.put_all(new_plans)

    return respond(body=serialize_to_dict_list(new_plans))
