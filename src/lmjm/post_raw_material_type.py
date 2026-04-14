import json
import os
from typing import Any

import boto3

from lmjm.model import RawMaterialType
from lmjm.repo import RawMaterialTypeRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

raw_material_type_repo = RawMaterialTypeRepo(table)

REQUIRED_FIELDS = ["code", "description", "category"]
VALID_CATEGORIES = {"feed", "medicine"}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    body = json.loads(event["body"])

    # Validate required fields
    missing = [f for f in REQUIRED_FIELDS if f not in body or body[f] is None]
    if missing:
        return respond(status_code=400, error=f"Missing required fields: {', '.join(missing)}")

    # Validate category
    if body["category"] not in VALID_CATEGORIES:
        return respond(status_code=400, error="Invalid category: must be 'feed' or 'medicine'")

    code = body["code"]

    record = RawMaterialType(
        pk="RAW_MATERIAL_TYPE",
        sk=f"RawMaterialType|{code}",
        code=code,
        description=body["description"],
        category=body["category"],
    )

    # put_item overwrites if same code exists
    raw_material_type_repo.put(record)

    return respond(status_code=201, body=serialize_to_dict(record))
