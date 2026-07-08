import os
from typing import Any

import boto3

from lmjm.repo import FeedTruckArrivalRepo, FiscalDocumentRepo
from lmjm.util.marshmallow_serializer import serialize_to_dict_list
from lmjm.util.response import respond

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

fiscal_document_repo = FiscalDocumentRepo(table)
feed_truck_arrival_repo = FeedTruckArrivalRepo(table)

UNMATCHED_FISCAL = "UNMATCHED_FISCAL"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    entries = fiscal_document_repo.scan_all()
    entries.sort(key=lambda d: d.issue_date, reverse=True)
    entries = entries[:60]

    # Determine which documents have been converted into a FeedTruckArrival.
    # A document is converted when an arrival in the same batch references its
    # fiscal_document_number. UNMATCHED_FISCAL documents can never have arrivals.
    converted: set[tuple[str, str]] = set()
    distinct_pks = {d.pk for d in entries if d.pk and d.pk != UNMATCHED_FISCAL}
    for pk in distinct_pks:
        for arrival in feed_truck_arrival_repo.list(pk):
            if arrival.fiscal_document_number:
                converted.add((pk, arrival.fiscal_document_number))

    result = serialize_to_dict_list(entries)
    for doc, item in zip(entries, result):
        item["is_converted"] = (doc.pk, doc.fiscal_document_number) in converted

    return respond(body=result)
