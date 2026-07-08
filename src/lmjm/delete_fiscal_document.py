import json
import logging
import os
from typing import Any

import boto3

from lmjm.repo import (
    FeedScheduleFiscalDocumentRepo,
    FeedTruckArrivalRepo,
    FiscalDocumentRepo,
)
from lmjm.util.response import respond

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

fiscal_document_repo = FiscalDocumentRepo(table)
feed_schedule_fiscal_document_repo = FeedScheduleFiscalDocumentRepo(table)
feed_truck_arrival_repo = FeedTruckArrivalRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Delete a FiscalDocument, but only if it has not been converted into a FeedTruckArrival.

    A fiscal document is considered "converted" when a FeedTruckArrival in the same batch (pk)
    references the same fiscal_document_number. Documents that are still pending (or unmatched)
    can be removed. Deleting a document also removes its linked FeedScheduleFiscalDocument.
    """
    body = json.loads(event.get("body") or "{}")
    pk: str = body.get("pk", "")
    sk: str = body.get("sk", "")

    if not pk or not sk:
        return respond(status_code=400, error="pk and sk are required")

    doc = fiscal_document_repo.get_by_sk(pk, sk)
    if doc is None:
        return respond(status_code=404, error="FiscalDocument not found")

    # Guard: block deletion when the document has been converted into a FeedTruckArrival.
    arrivals = feed_truck_arrival_repo.list(pk)
    if any(a.fiscal_document_number == doc.fiscal_document_number for a in arrivals):
        return respond(
            status_code=409,
            error="Fiscal document is linked to a feed truck arrival and cannot be deleted",
        )

    # Remove the linked FeedScheduleFiscalDocument (idempotent). Its sk mirrors the fiscal doc sk.
    fsfd_sk = "FeedScheduleFiscalDocument|" + sk.split("|", 1)[1]
    feed_schedule_fiscal_document_repo.delete(pk, fsfd_sk)

    fiscal_document_repo.delete_by_sk(pk, sk)
    logger.info("Deleted FiscalDocument pk=%s sk=%s", pk, sk)

    return respond(status_code=200, body={"message": "deleted"})
