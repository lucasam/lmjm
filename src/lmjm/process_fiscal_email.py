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
    issue_date_str: str,
    schedules: list[FeedSchedule],
) -> Optional[str]:
    """Attempt to match a single FeedSchedule by feed_type and date proximity.

    Returns the matched schedule's sk, or None if zero or multiple matches.
    """
    try:
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    matches: list[FeedSchedule] = []
    for schedule in schedules:
        if schedule.feed_type != product_code:
            continue
        if schedule.status != "scheduled":
            continue
        try:
            planned = datetime.strptime(schedule.planned_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue
        if abs((planned - issue_date).days) <= 7:
            matches.append(schedule)

    if len(matches) == 1:
        return matches[0].sk
    return None


def _process_single_nfe(
    parsed: ParsedNfe,
    batch_pk: str,
    s3_key: str,
) -> None:
    """Process a single parsed NF-e: create FiscalDocument, classify, and link."""
    # Check duplicate
    existing = fiscal_document_repo.get(batch_pk, parsed.fiscal_document_number)
    if existing is not None:
        logger.warning("Duplicate fiscal_document_number %s, skipping", parsed.fiscal_document_number)
        return

    # Create FiscalDocument
    fiscal_doc = FiscalDocument(
        pk=batch_pk,
        sk=f"FiscalDocument|{parsed.fiscal_document_number}",
        fiscal_document_number=parsed.fiscal_document_number,
        issue_date=parsed.issue_date,
        actual_amount_kg=parsed.actual_amount_kg,
        product_code=parsed.product_code,
        product_description=parsed.product_description,
        supplier_name=parsed.supplier_name,
        order_number=parsed.order_number,
        source_email_s3_key=s3_key,
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
        return

    if raw_material.category == "feed":
        _handle_feed_product(parsed, batch_pk)
    elif raw_material.category == "medicine":
        _handle_medicine_product(parsed, batch_pk, raw_material.description)


def _handle_feed_product(parsed: ParsedNfe, batch_pk: str) -> None:
    """Create FeedScheduleFiscalDocument, optionally matching a FeedSchedule."""
    feed_schedule_id: Optional[str] = None

    if batch_pk != "UNMATCHED_FISCAL":
        schedules = feed_schedule_repo.list(batch_pk)
        feed_schedule_id = _match_feed_schedule(parsed.product_code, parsed.issue_date, schedules)

    fsfd = FeedScheduleFiscalDocument(
        pk=batch_pk,
        sk=f"FeedScheduleFiscalDocument|{parsed.fiscal_document_number}",
        fiscal_document_number=parsed.fiscal_document_number,
        feed_schedule_id=feed_schedule_id,
        status="pending",
        product_code=parsed.product_code,
        actual_amount_kg=parsed.actual_amount_kg,
        issue_date=parsed.issue_date,
    )
    feed_schedule_fiscal_document_repo.put(fsfd)
    logger.info(
        "Created FeedScheduleFiscalDocument %s (feed_schedule_id=%s)",
        parsed.fiscal_document_number,
        feed_schedule_id,
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
            parsed = parse_nfe_xml(attachment.content)
        except ValueError as exc:
            logger.error("Failed to parse XML %s: %s", attachment.filename, exc)
            continue

        # Identify batch
        batch = _find_batch_by_supply_id(parsed.order_number, all_batches) if parsed.order_number else None
        if batch is not None:
            batch_pk = batch.pk
        else:
            batch_pk = "UNMATCHED_FISCAL"
            if parsed.order_number:
                logger.warning(
                    "No batch found for order_number (xPed) %s, using UNMATCHED_FISCAL",
                    parsed.order_number,
                )

        _process_single_nfe(parsed, batch_pk, s3_key)

    return {"statusCode": 200, "body": "processed"}
