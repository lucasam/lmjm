import dataclasses
import json
import os
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.model import PigTruckArrival
from lmjm.repo import BatchRepo, PigTruckArrivalRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

batch_repo = BatchRepo(table)
pig_truck_arrival_repo = PigTruckArrivalRepo(table)


@dataclasses.dataclass
class PutPigTruckArrivalRequest:
    animal_count: Optional[int] = None
    sex: Optional[str] = None
    pig_age_days: Optional[int] = None
    origin_name: Optional[str] = None
    origin_type: Optional[str] = None
    fiscal_document_number: Optional[str] = None
    animal_weight: Optional[Decimal] = None
    gta_number: Optional[str] = None
    mossa: Optional[str] = None
    suplier_code: Optional[int] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id = unquote(event["pathParameters"]["batch_id"])
    arrival_sk = unquote(event["pathParameters"]["arrival_sk"])

    batch = batch_repo.get(batch_id)
    if not batch:
        return respond(status_code=404, error="Batch not found")

    arrivals = pig_truck_arrival_repo.list(batch_id)
    arrival: Optional[PigTruckArrival] = None
    for a in arrivals:
        if a.sk == arrival_sk:
            arrival = a
            break

    if not arrival:
        return respond(status_code=404, error="PigTruckArrival not found")

    request = load_data_class_from_dict(json.loads(event["body"]), PutPigTruckArrivalRequest)

    if request.animal_count is not None:
        if request.animal_count <= 0:
            return respond(status_code=400, error="animal_count must be a positive integer")
        arrival.animal_count = request.animal_count

    if request.sex is not None:
        if request.sex not in ("Male", "Female"):
            return respond(status_code=400, error="sex must be Male or Female")
        arrival.sex = request.sex

    if request.pig_age_days is not None:
        if request.pig_age_days <= 0:
            return respond(status_code=400, error="pig_age_days must be a positive integer")
        arrival.pig_age_days = request.pig_age_days

    if request.origin_name is not None:
        if not request.origin_name.strip():
            return respond(status_code=400, error="origin_name must be non-empty")
        arrival.origin_name = request.origin_name

    if request.origin_type is not None:
        if request.origin_type not in ("UPL", "Creche"):
            return respond(status_code=400, error="origin_type must be UPL or Creche")
        arrival.origin_type = request.origin_type

    if request.fiscal_document_number is not None:
        arrival.fiscal_document_number = request.fiscal_document_number

    if request.animal_weight is not None:
        arrival.animal_weight = request.animal_weight

    if request.gta_number is not None:
        arrival.gta_number = request.gta_number

    if request.mossa is not None:
        arrival.mossa = request.mossa

    if request.suplier_code is not None:
        arrival.suplier_code = request.suplier_code

    pig_truck_arrival_repo.update(arrival)

    return respond(body=serialize_to_dict(arrival))
