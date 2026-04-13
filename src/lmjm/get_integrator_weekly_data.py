import os
from typing import Any

import boto3

from lmjm.repo import IntegratorWeeklyDataRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

integrator_weekly_data_repo = IntegratorWeeklyDataRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    results = integrator_weekly_data_repo.list()
    return respond(body=serialize_to_dict_list(results))
