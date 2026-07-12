import email.parser
import email.policy
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Optional

import boto3

from lmjm.fiscal.email_parser import extract_xml_attachments
from lmjm.fiscal.nfe_parser import ParsedNfe, parse_nfe_xml
from lmjm.model import (
    Batch,
    FeedSchedule,
    FeedScheduleFiscalDocument,
    FiscalDocument,
    Medication,
    RawMaterialType,
)
from lmjm.model.feed_schedule import FeedScheduleStatus
from lmjm.repo import (
    BatchRepo,
    FeedScheduleFiscalDocumentRepo,
    FeedScheduleRepo,
    FiscalDocumentRepo,
    MedicationRepo,
    RawMaterialTypeRepo,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
EMAIL_BUCKET = os.environ["EMAIL_BUCKET"]

dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)
s3 = boto3.client("s3", region_name="sa-east-1")

batch_repo = BatchRepo(table)
fiscal_document_repo = FiscalDocumentRepo(table)
feed_schedule_fiscal_document_repo = FeedScheduleFiscalDocumentRepo(table)
feed_schedule_repo = FeedScheduleRepo(table)
raw_material_type_repo = RawMaterialTypeRepo(table)
medication_repo = MedicationRepo(table)


def _is_gmail_confirmation(subject: str) -> bool:
    """Check if the email is a Gmail forwarding confirmation."""
    lower = subject.lower()
    return "confirmation" in lower and "receive mail" in lower


def _extract_gmail_confirmation_link(raw_email: bytes) -> Optional[str]:
    """Extract Gmail confirmation link from email body."""
    parser = email.parser.BytesParser(policy=email.policy.default)
    msg = parser.parsebytes(raw_email)

    body_texts: list[str] = []
    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type in ("text/plain", "text/html"):
            payload = part.get_content()
            if isinstance(payload, str):
                body_texts.append(payload)

    full_body = "\n".join(body_texts)
    urls = re.findall(r"https?://[^\s<>\"]+", full_body)

    for url in urls:
        if "mail.google.com/mail" in url or "google.com/mail" in url:
            return url
    return None


def _find_batch_by_supply_id(order_number: str, batches: list[Batch]) -> Optional[Batch]:
    """Find a batch whose supply_id matches the order_number (compared as int)."""
    try:
        order_int = int(order_number)
    except (ValueError, TypeError):
        return None
    for batch in batches:
        if batch.supply_id == order_int:
            return batch
    return None


def _match_feed_schedule(
    product_code: str,
    schedules: list[FeedSchedule],
    scheduled_date_str: str = "",
    already_matched_ids: set[str] | None = None,
) -> tuple[Optional[str], str]:
    """Match a FeedSchedule by feed_type and exact scheduled_date.

    Only matches if scheduled_date_str is provided and equals a schedule's planned_date.
    Excludes schedules whose sk is in already_matched_ids.
    If multiple matches, returns the first and logs all.
    Returns (matched schedule sk or None, planned_date or "").
    """
    if not scheduled_date_str:
        logger.info("No scheduled_date (OCR), skipping schedule match for product_code=%s", product_code)
        return None, ""

    logger.info("Matching schedule: product_code=%s, scheduled_date=%s", product_code, scheduled_date_str)

    excluded = already_matched_ids or set()
    if excluded:
        logger.info("Excluding already-matched schedule ids: %s", excluded)

    matches: list[FeedSchedule] = []
    for schedule in schedules:
        if schedule.feed_type != product_code:
            continue
        if schedule.status != FeedScheduleStatus.scheduled:
            logger.info("  Skip %s: status=%s", schedule.sk, schedule.status)
            continue
        if schedule.sk in excluded:
            logger.info("  Skip %s: already matched", schedule.sk)
            continue
        if schedule.planned_date == scheduled_date_str:
            logger.info("  Match %s: planned_date=%s", schedule.sk, schedule.planned_date)
            matches.append(schedule)

    if len(matches) == 0:
        logger.info("No matching schedule for product_code=%s date=%s", product_code, scheduled_date_str)
        return None, ""

    if len(matches) > 1:
        logger.info(
            "Multiple matches (%d), returning first: %s. All: %s",
            len(matches),
            matches[0].sk,
            [m.sk for m in matches],
        )

    logger.info("Match found: %s (planned_date=%s)", matches[0].sk, matches[0].planned_date)
    return matches[0].sk, matches[0].planned_date


def _process_single_nfe(
    parsed: ParsedNfe,
    batch_pk: str,
    s3_key: str,
) -> Optional[str]:
    """Create the FiscalDocument, classify it, and handle medicine products.

    Returns the classification category ("feed", "medicine", or the raw
    material category) or None when the item is skipped (duplicate) or its
    product is not yet classified. Feed items are intentionally NOT written
    here: the caller aggregates feed items sharing the same product_code into a
    single FeedScheduleFiscalDocument via ``_handle_feed_product``.
    """
    # Build unique sk using item_number when present
    if parsed.item_number:
        doc_sk = f"FiscalDocument|{parsed.fiscal_document_number}|{parsed.item_number}"
    else:
        doc_sk = f"FiscalDocument|{parsed.fiscal_document_number}"

    # Check duplicate by sk
    existing = fiscal_document_repo.get_by_sk(batch_pk, doc_sk)
    if existing is not None:
        logger.warning("Duplicate fiscal document sk %s, skipping", doc_sk)
        return None

    # Create FiscalDocument
    fiscal_doc = FiscalDocument(
        pk=batch_pk,
        sk=doc_sk,
        fiscal_document_number=parsed.fiscal_document_number,
        issue_date=parsed.issue_date,
        actual_amount_kg=parsed.actual_amount_kg,
        product_code=parsed.product_code,
        product_description=parsed.product_description,
        supplier_name=parsed.supplier_name,
        order_number=parsed.order_number,
        source_email_s3_key=s3_key,
        item_number=parsed.item_number,
    )
    fiscal_document_repo.put(fiscal_doc)
    logger.info("Created FiscalDocument %s for batch %s", parsed.fiscal_document_number, batch_pk)

    # Classify via RawMaterialType
    raw_material = raw_material_type_repo.get(parsed.product_code)
    if raw_material is None:
        logger.info("No RawMaterialType found for product_code %s, auto-creating", parsed.product_code)
        new_type = RawMaterialType(
            pk="RAW_MATERIAL_TYPE",
            sk=f"RawMaterialType|{parsed.product_code}",
            code=parsed.product_code,
            description=parsed.product_description,
            category="",
        )
        raw_material_type_repo.put(new_type)
        return None

    if raw_material.category == "medicine":
        _handle_medicine_product(parsed, batch_pk, raw_material.description)

    return raw_material.category


def _handle_feed_product(items: list[ParsedNfe], batch_pk: str) -> None:
    """Create a single FeedScheduleFiscalDocument for a group of feed items.

    All items in ``items`` share the same product_code and fiscal document.
    Their delivered amounts (actual_amount_kg) are summed into one record so
    that a fiscal document listing the same feed code across multiple line
    items produces a single feed-schedule entry.
    """
    if not items:
        return

    first = items[0]
    total_amount_kg = sum(item.actual_amount_kg for item in items)

    feed_schedule_id: Optional[str] = None
    planned_date: str = ""

    if batch_pk != "UNMATCHED_FISCAL":
        schedules = feed_schedule_repo.list(batch_pk)
        # Exclude schedules already linked to a fiscal document
        existing_fsfds = feed_schedule_fiscal_document_repo.list(batch_pk)
        already_matched = {f.feed_schedule_id for f in existing_fsfds if f.feed_schedule_id}
        feed_schedule_id, planned_date = _match_feed_schedule(
            first.product_code, schedules, first.scheduled_date, already_matched
        )

    # A single fiscal document can carry several feed codes, so the sk is keyed
    # by product_code to keep distinct codes separate while merging duplicates.
    fsfd_sk = f"FeedScheduleFiscalDocument|{first.fiscal_document_number}|{first.product_code}"

    fsfd = FeedScheduleFiscalDocument(
        pk=batch_pk,
        sk=fsfd_sk,
        fiscal_document_number=first.fiscal_document_number,
        feed_schedule_id=feed_schedule_id,
        status="pending",
        product_code=first.product_code,
        actual_amount_kg=total_amount_kg,
        issue_date=first.issue_date,
        planned_date=planned_date,
    )
    feed_schedule_fiscal_document_repo.put(fsfd)
    logger.info(
        "Created FeedScheduleFiscalDocument %s code=%s amount=%d from %d item(s) (feed_schedule_id=%s) batch %s",
        first.fiscal_document_number,
        first.product_code,
        total_amount_kg,
        len(items),
        feed_schedule_id,
        batch_pk,
    )


def _handle_medicine_product(parsed: ParsedNfe, batch_pk: str, description: str) -> None:
    """Create a Medication record for medicine products."""
    medication = Medication(
        pk=batch_pk,
        sk=f"Medication|{uuid.uuid4()}",
        medication_name=description,
        raw_material_code=parsed.product_code,
        part_number=parsed.lot_number,
        expiration_date=parsed.expiration_date,
    )
    medication_repo.put(medication)
    logger.info("Created Medication for product_code %s in batch %s", parsed.product_code, batch_pk)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process incoming fiscal document emails from SES."""
    message_id: str = event["Records"][0]["ses"]["mail"]["messageId"]
    logger.info("Processing email message_id=%s", message_id)

    # Read raw email from S3
    s3_key = message_id
    response = s3.get_object(Bucket=EMAIL_BUCKET, Key=s3_key)
    raw_email: bytes = response["Body"].read()

    # Parse email subject
    parser = email.parser.BytesParser(policy=email.policy.default)
    msg = parser.parsebytes(raw_email)
    subject = msg.get("Subject", "") or ""

    # Gmail forwarding confirmation check
    if _is_gmail_confirmation(subject):
        link = _extract_gmail_confirmation_link(raw_email)
        if link:
            logger.info("Gmail forwarding confirmation link: %s", link)
        else:
            logger.info("Gmail forwarding confirmation email detected but no link found")
        return {"statusCode": 200, "body": "gmail confirmation handled"}

    # Extract XML attachments
    attachments = extract_xml_attachments(raw_email)
    if not attachments:
        logger.warning("No XML attachments found in email subject='%s'", subject)
        return {"statusCode": 200, "body": "no attachments"}

    # Load all batches once for supply_id matching
    all_batches = batch_repo.list()

    for attachment in attachments:
        try:
            parsed_items = parse_nfe_xml(attachment.content)
        except ValueError as exc:
            logger.error("Failed to parse XML %s: %s", attachment.filename, exc)
            continue

        # Identify batch from the first item's order_number (shared across all items)
        first_order = parsed_items[0].order_number if parsed_items else ""
        batch = _find_batch_by_supply_id(first_order, all_batches) if first_order else None
        if batch is not None:
            batch_pk = batch.pk
        else:
            batch_pk = "UNMATCHED_FISCAL"
            if first_order:
                logger.warning(
                    "No batch found for order_number (xPed) %s, using UNMATCHED_FISCAL",
                    first_order,
                )

        # Create FiscalDocuments and classify each item. Collect feed items,
        # grouped by product_code, so multiple line items with the same feed
        # code are aggregated into a single FeedScheduleFiscalDocument.
        feed_items_by_code: dict[str, list[ParsedNfe]] = {}
        for parsed in parsed_items:
            category = _process_single_nfe(parsed, batch_pk, s3_key)
            if category == "feed":
                feed_items_by_code.setdefault(parsed.product_code, []).append(parsed)

        for items in feed_items_by_code.values():
            _handle_feed_product(items, batch_pk)

    return {"statusCode": 200, "body": "processed"}
