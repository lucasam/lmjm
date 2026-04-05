import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.repo import FeedScheduleFiscalDocumentRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

feed_schedule_fiscal_document_repo = FeedScheduleFiscalDocumentRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    batch_id: str = unquote(event["pathParameters"]["batch_id"])
    entries = feed_schedule_fiscal_document_repo.list(batch_id)
    entries.sort(key=lambda d: d.issue_date, reverse=True)
    return respond(body=serialize_to_dict_list(entries))
