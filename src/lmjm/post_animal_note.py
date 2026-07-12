import dataclasses
import json
import logging
import os
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import AnimalRepo
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict
from lmjm.util.response import respond

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

animal_repo = AnimalRepo(table)


@dataclasses.dataclass
class PostNoteRequest:
    note: str


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Append a note to an animal.

    The note is prefixed with today's date (DD-MM-YYYY) to match the format used
    by inseminations, diagnostics and procedures, so the note list reads as a
    chronological log.
    """
    ear_tag = unquote(event["pathParameters"]["animal_id"])
    request = load_data_class_from_dict(json.loads(event["body"]), PostNoteRequest)

    note_text = (request.note or "").strip()
    if not note_text:
        return respond(status_code=400, error="note must be non-empty")

    animal = animal_repo.get_by_ear_tag(ear_tag)
    if not animal:
        return respond(status_code=404, error="Animal not found")

    dated_note = f"{datetime.now().strftime('%d-%m-%Y')}: {note_text}"
    if not animal.notes:
        animal.notes = []
    animal.notes.append(dated_note)
    animal_repo.update(animal)
    logger.info("Added note to animal ear_tag=%s pk=%s", ear_tag, animal.pk)

    return respond(status_code=201, body=serialize_to_dict(animal))
