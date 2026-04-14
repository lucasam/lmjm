import json
import logging
import os
from typing import Any
from urllib.parse import unquote

import boto3

from lmjm.model import FiscalDocument
from lmjm.process_fiscal_email import _handle_feed_product, _handle_medicine_product
from lmjm.repo import (
    FeedScheduleFiscalDocumentRepo,
    FiscalDocumentRepo,
    RawMaterialTypeRepo,
)
from lmjm.util.marshmallow_serializer import load_data_class_from_dict
from lmjm.util.response import respond

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)

fiscal_document_repo = FiscalDocumentRepo(table)
feed_schedule_fiscal_document_repo = FeedScheduleFiscalDocumentRepo(table)
raw_material_type_repo = RawMaterialTypeRepo(table)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Reprocess a FiscalDocument: delete old linking records and re-classify."""
    body = json.loads(event.get("body", "{}"))
    pk: str = body.get("pk", "")
    fiscal_document_number: str = body.get("fiscal_document_number", "")

    if not pk or not fiscal_document_number:
        return respond(status_code=400, error="pk and fiscal_document_number are required")

    doc = fiscal_document_repo.get(pk, fiscal_document_number)
    if doc is None:
        return respond(status_code=404, error="FiscalDocument not found")

    # Delete existing FeedScheduleFiscalDocument if any
    existing_fsfd = feed_schedule_fiscal_document_repo.get(pk, fiscal_document_number)
    if existing_fsfd is not None:
        feed_schedule_fiscal_document_repo.delete(pk, existing_fsfd.sk)

    # Re-classify via RawMaterialType
    raw_material = raw_material_type_repo.get(doc.product_code)
    if raw_material is None:
        logger.info("No RawMaterialType for product_code %s, auto-creating", doc.product_code)
        from lmjm.model import RawMaterialType

        new_type = RawMaterialType(
            pk="RAW_MATERIAL_TYPE",
            sk=f"RawMaterialType|{doc.product_code}",
            code=doc.product_code,
            description=doc.product_description,
            category="",
        )
        raw_material_type_repo.put(new_type)
        return respond(body={"message": "reprocessed", "classification": "unknown (created RawMaterialType)"})

    # Build a minimal ParsedNfe-like object for the handlers
    from lmjm.fiscal.nfe_parser import ParsedNfe

    parsed = ParsedNfe(
        fiscal_document_number=doc.fiscal_document_number,
        issue_date=doc.issue_date,
        actual_amount_kg=doc.actual_amount_kg,
        product_code=doc.product_code,
        product_description=doc.product_description,
        supplier_name=doc.supplier_name,
        order_number=doc.order_number,
        item_number=doc.item_number,
    )

    if raw_material.category == "feed":
        _handle_feed_product(parsed, pk)
        return respond(body={"message": "reprocessed", "classification": "feed"})
    elif raw_material.category == "medicine":
        _handle_medicine_product(parsed, pk, raw_material.description)
        return respond(body={"message": "reprocessed", "classification": "medicine"})

    return respond(body={"message": "reprocessed", "classification": raw_material.category})
