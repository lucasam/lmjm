import dataclasses
import json
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import unquote

import boto3

from lmjm.model import Diagnostic
from lmjm.repo import AnimalRepo, DiagnosticRepo, InseminationRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)
insemination_repo = InseminationRepo(table)
diagnostic_repo = DiagnosticRepo(table)


@dataclasses.dataclass
class PostDiagnosticRequest:
    diagnostic_date: str
    pregnant: bool
    note: Optional[str] = None
    tags: Optional[str] = None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ear_tag = unquote(event["pathParameters"]["animal_id"])
    request = load_data_class_from_dict(json.loads(event["body"]), PostDiagnosticRequest)

    animal = animal_repo.get_by_ear_tag(ear_tag)

    try:
        diagnostic_date = datetime.strptime(request.diagnostic_date, "%Y%m%d")
    except (ValueError, TypeError):
        return respond(status_code=400, error="diagnostic_date must be in YYYYMMDD format")

    if not animal:
        return respond(status_code=404, error="Animal not found")

    insemination = insemination_repo.get_latest(animal.pk)

    if not insemination:
        return respond(status_code=404, error="No insemination found")

    expected_delivery_date = (
        datetime.strptime(insemination.insemination_date, "%Y-%m-%d") + timedelta(days=292)
    ).strftime("%Y-%m-%d")

    diagnostic = Diagnostic(
        pk=animal.pk,
        sk=f"Diagnostic|{diagnostic_date.strftime('%Y%m%d')}",
        diagnostic_date=diagnostic_date.strftime("%Y-%m-%d"),
        breeding_date=insemination.insemination_date,
        pregnant=request.pregnant,
        expected_delivery_date=expected_delivery_date,
        semen=insemination.semen,
    )
    diagnostic_repo.put(diagnostic)

    if request.pregnant:
        animal.pregnant = True
        animal.implanted = False
        animal.inseminated = False
        animal.transferred = False

        edd_formatted = datetime.strptime(expected_delivery_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        default_note = (
            f"{diagnostic_date.strftime('%d-%m-%Y')}: Pregnancy Confirmed. {insemination.semen}. EDD: {edd_formatted}"
        )
    else:
        default_note = f"{diagnostic_date.strftime('%d-%m-%Y')}: IATF Failed"

    if not animal.notes:
        animal.notes = []
    animal.notes.append(default_note)
    if request.note:
        animal.notes.append(request.note)
    if request.tags:
        if not animal.tags:
            animal.tags = []
        animal.tags.append(request.tags)
    animal_repo.update(animal)

    return respond(status_code=201, body={"message": "Diagnostic created"})
