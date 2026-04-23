import logging
import os
from typing import Any
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError

from lmjm.model import FeedScheduleStatus
from lmjm.repo import (
    BatchRepo,
    FeedBalanceRepo,
    FeedConsumptionPlanRepo,
    FeedScheduleRepo,
    FeedTruckArrivalRepo,
    MortalityRepo,
)
from lmjm.suggestion_engine.bedrock_client import invoke_bedrock
from lmjm.suggestion_engine.context_builder import build_suggestion_context
from lmjm.suggestion_engine.prompt_builder import build_prompt
from lmjm.suggestion_engine.response_parser import parse_suggestions
from lmjm.util.response import respond

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
feed_schedule_repo = FeedScheduleRepo(table)
feed_consumption_plan_repo = FeedConsumptionPlanRepo(table)
feed_truck_arrival_repo = FeedTruckArrivalRepo(table)
feed_balance_repo = FeedBalanceRepo(table)
mortality_repo = MortalityRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    feed_schedule = feed_schedule_repo.list(batch_id)
    consumption_plan = feed_consumption_plan_repo.list(batch_id)
    truck_arrivals = feed_truck_arrival_repo.list(batch_id)
    balances = feed_balance_repo.list(batch_id)
    mortalities = mortality_repo.list(batch_id)

    # Filter: exclude canceled, only include entries on or after the latest balance date
    latest_balance_date = ""
    if balances:
        latest_balance_date = max(b.measurement_date for b in balances)

    scheduled_entries = [
        entry
        for entry in feed_schedule
        if entry.status != FeedScheduleStatus.canceled and entry.planned_date >= latest_balance_date
    ]

    if not scheduled_entries:
        return respond(
            body={
                "suggestions": [],
                "message": "No scheduled deliveries to optimize",
            }
        )

    suggestion_context = build_suggestion_context(
        batch=batch,
        scheduled_entries=scheduled_entries,
        consumption_plan=consumption_plan,
        truck_arrivals=truck_arrivals,
        balances=balances,
        mortalities=mortalities,
    )

    prompt = build_prompt(suggestion_context)
    logger.info(prompt)

    try:
        response_text = invoke_bedrock(prompt)
    except (ReadTimeoutError, ConnectTimeoutError):
        return respond(status_code=504, error="AI service timed out")
    except ClientError as e:
        return respond(status_code=502, error=f"AI service error: {str(e)}")
    except Exception:
        return respond(status_code=500, error="Could not parse AI suggestions")

    try:
        suggestions = parse_suggestions(response_text)
    except Exception:
        return respond(status_code=500, error="Could not parse AI suggestions")

    return respond(
        body={
            "suggestions": [
                {
                    "planned_date": s.planned_date,
                    "feed_description": s.feed_type,
                    "new_planned_date": s.new_planned_date,
                    "description": s.description,
                }
                for s in suggestions
            ],
            "message": (
                "No changes needed — all balances within thresholds"
                if not suggestions
                else f"{len(suggestions)} suggestion(s) generated"
            ),
        }
    )
