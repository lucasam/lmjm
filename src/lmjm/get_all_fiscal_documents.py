import os
from typing import Any

import boto3

from lmjm.repo import FiscalDocumentRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

fiscal_document_repo = FiscalDocumentRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    entries = fiscal_document_repo.scan_all()
    entries.sort(key=lambda d: d.issue_date, reverse=True)
    return respond(body=serialize_to_dict_list(entries[:60]))
