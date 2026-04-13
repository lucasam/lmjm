import json
import os
from decimal import Decimal, InvalidOperation
from typing import Any

import boto3

from lmjm.cap_map_calculator import compute_cap_map
from lmjm.model import IntegratorWeeklyData
from lmjm.repo import IntegratorWeeklyDataRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

integrator_weekly_data_repo = IntegratorWeeklyDataRepo(table)

REQUIRED_FIELDS = [
    "date_generated",
    "validity_start",
    "validity_end",
    "source_data_start",
    "source_data_end",
    "car",
    "mar",
    "avg_piglet_weight",
    "avg_slaughter_weight",
    "average_age",
    "number_of_samples",
    "gdp",
]


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    body = json.loads(event["body"])

    # Validate required fields
    missing = [f for f in REQUIRED_FIELDS if f not in body or body[f] is None]
    if missing:
        return respond(status_code=400, error=f"Missing required fields: {', '.join(missing)}")

    try:
        car = Decimal(str(body["car"]))
        mar = Decimal(str(body["mar"]))
        avg_piglet_weight = Decimal(str(body["avg_piglet_weight"]))
        avg_slaughter_weight = Decimal(str(body["avg_slaughter_weight"]))
        average_age = Decimal(str(body["average_age"]))

        cap_map = compute_cap_map(
            car=car,
            mar=mar,
            avg_slaughter_weight=avg_slaughter_weight,
            avg_piglet_weight=avg_piglet_weight,
            average_age=average_age,
        )
    except (ValueError, InvalidOperation) as e:
        return respond(status_code=400, error=str(e))

    date_generated = body["date_generated"]

    record = IntegratorWeeklyData(
        pk="INTEGRATOR_WEEKLY_DATA",
        sk=f"IntegratorWeeklyData|{date_generated}",
        date_generated=date_generated,
        validity_start=body["validity_start"],
        validity_end=body["validity_end"],
        source_data_start=body["source_data_start"],
        source_data_end=body["source_data_end"],
        car=car,
        mar=mar,
        avg_piglet_weight=avg_piglet_weight,
        avg_slaughter_weight=avg_slaughter_weight,
        average_age=average_age,
        number_of_samples=int(body["number_of_samples"]),
        gdp=Decimal(str(body["gdp"])),
        cap_1=cap_map["cap_1"],
        cap_2=cap_map["cap_2"],
        cap_3=cap_map["cap_3"],
        cap_4=cap_map["cap_4"],
        map_1=cap_map["map_1"],
        map_2=cap_map["map_2"],
    )

    # put_item overwrites if same date_generated exists
    integrator_weekly_data_repo.put(record)

    return respond(status_code=201, body=serialize_to_dict(record))
