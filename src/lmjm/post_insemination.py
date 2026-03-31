import dataclasses
import json
import os
from datetime import datetime
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.model import Insemination
from lmjm.repo import AnimalRepo, InseminationRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)
insemination_repo = InseminationRepo(table)


@dataclasses.dataclass
class PostInseminationRequest:
    insemination_date: str
    semen: str
    note: Optional[str] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ear_tag = unquote(event["pathParameters"]["animal_id"])
    request = load_data_class_from_dict(json.loads(event["body"]), PostInseminationRequest)

    try:
        parsed = datetime.strptime(request.insemination_date, "%Y%m%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="insemination_date must be in YYYYMMDD format")

    animal = animal_repo.get_by_ear_tag(ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")

    insemination = Insemination(
        pk=animal.pk,
        sk=f"Insemination|{parsed.strftime('%Y%m%d')}",
        insemination_date=parsed.strftime("%Y-%m-%d"),
        semen=request.semen,
    )
    insemination_repo.put(insemination)

    animal.inseminated = True
    animal.implanted = False
    animal.pregnant = False
    animal.transferred = False

    default_note = f"{parsed.strftime('%d-%m-%Y')}: Inseminated {request.semen}"

    if not animal.notes:
        animal.notes = []
    animal.notes.append(default_note)
    if request.note:
        animal.notes.append(request.note)

    animal_repo.update(animal)

    return respond(status_code=201, body={"message": "Insemination created"})
