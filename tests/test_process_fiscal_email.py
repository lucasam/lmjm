"""Unit tests for Email Intake Lambda (process_fiscal_email).

Validates: Requirements 2.5, 4.4, 5.1, 5.4, 5.5, 6.2, 6.3, 13.3, 13.4
"""

import importlib
import json
from decimal import Decimal
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import boto3
import pytest
from moto import mock_aws

from lmjm.model import Batch, FeedSchedule, RawMaterialType
from lmjm.util.marshmallow_serializer import serialize_to_dict as _original_serialize

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
BATCH_PK = "batch-abc-123"
SUPPLY_ID = 112053764
MESSAGE_ID = "test-message-id"


def _decimal_safe_serialize(obj: object, schema: Any = None) -> dict[str, Any]:
    """Wrap serialize_to_dict to convert floats to Decimal for moto compatibility."""
    d = _original_serialize(obj, schema)
    return json.loads(json.dumps(d), parse_float=Decimal)  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")
    monkeypatch.setenv("EMAIL_BUCKET", "lmjm-fiscal-emails")
    # Patch serialize_to_dict in all repo modules that write to DynamoDB
    for repo_mod in [
        "lmjm.repo.batch_repo",
        "lmjm.repo.fiscal_document_repo",
        "lmjm.repo.feed_schedule_fiscal_document_repo",
        "lmjm.repo.feed_schedule_repo",
        "lmjm.repo.raw_material_type_repo",
        "lmjm.repo.medication_repo",
    ]:
        monkeypatch.setattr(f"{repo_mod}.serialize_to_dict", _decimal_safe_serialize)



def _build_nfe_xml(
    nNF: str = "833871",
    dhEmi: str = "2026-03-26T12:10:26-03:00",
    xNome: str = "BRF S.A.",
    cProd: str = "130906",
    xProd: str = "ST06 RAC SUI TERM",
    qCom: str = "15980.0000",
    xPed: str = "0112053764",
    include_rastro: bool = False,
    rastro_nLote: str = "LOT001",
    rastro_dVal: str = "2027-01-15",
) -> bytes:
    """Build a minimal NF-e XML for testing."""
    rastro_xml = ""
    if include_rastro:
        rastro_xml = f"""
                <rastro>
                    <nLote>{rastro_nLote}</nLote>
                    <dVal>{rastro_dVal}</dVal>
                </rastro>"""

    xPed_xml = f"<xPed>{xPed}</xPed>" if xPed else ""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="{NFE_NS}">
    <NFe>
        <infNFe>
            <ide>
                <nNF>{nNF}</nNF>
                <dhEmi>{dhEmi}</dhEmi>
            </ide>
            <emit>
                <xNome>{xNome}</xNome>
            </emit>
            <det nItem="1">
                <prod>
                    <cProd>{cProd}</cProd>
                    <xProd>{xProd}</xProd>
                    <qCom>{qCom}</qCom>
                    {xPed_xml}{rastro_xml}
                </prod>
            </det>
        </infNFe>
    </NFe>
</nfeProc>"""
    return xml.encode("utf-8")


def _build_email_with_xml(xml_bytes: bytes, filename: str = "nfe.xml") -> bytes:
    """Build a MIME email with a single XML attachment."""
    msg = MIMEMultipart()
    msg["Subject"] = "NF-e Documents"
    msg["From"] = "supplier@example.com"
    msg["To"] = "fiscal@lmjm.net"
    msg.attach(MIMEText("See attached.", "plain"))

    part = MIMEBase("application", "xml")
    part.set_payload(xml_bytes)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)
    return msg.as_bytes()


def _build_plain_email(subject: str = "Hello", body: str = "No attachments here.") -> bytes:
    """Build a plain text email with no attachments."""
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = "someone@example.com"
    msg["To"] = "fiscal@lmjm.net"
    return msg.as_bytes()


def _ses_event(message_id: str = MESSAGE_ID) -> dict[str, Any]:
    """Build a minimal SES event."""
    return {"Records": [{"ses": {"mail": {"messageId": message_id}}}]}


def _create_table() -> Any:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    return dynamodb.create_table(
        TableName="lmjm",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def _create_bucket() -> Any:
    s3 = boto3.client("s3", region_name="sa-east-1")
    s3.create_bucket(
        Bucket="lmjm-fiscal-emails",
        CreateBucketConfiguration={"LocationConstraint": "sa-east-1"},
    )
    return s3


def _put(table: Any, obj: object) -> None:
    table.put_item(Item=_decimal_safe_serialize(obj))


def _seed_batch(table: Any) -> None:
    _put(table, Batch(pk=BATCH_PK, sk="Batch", status="created", supply_id=SUPPLY_ID, module_id="MODULE#1"))


def _seed_feed_raw_material(table: Any, code: str = "130906", description: str = "ST06") -> None:
    _put(table, RawMaterialType(pk="RAW_MATERIAL_TYPE", sk=f"RawMaterialType|{code}", code=code, description=description, category="feed"))


def _seed_medicine_raw_material(table: Any, code: str = "200001", description: str = "Amoxicillin") -> None:
    _put(table, RawMaterialType(pk="RAW_MATERIAL_TYPE", sk=f"RawMaterialType|{code}", code=code, description=description, category="medicine"))


def _seed_feed_schedule(table: Any, feed_type: str = "130906", planned_date: str = "2026-03-28") -> None:
    _put(table, FeedSchedule(pk=BATCH_PK, sk="FeedSchedule|sched-1", feed_type=feed_type, planned_date=planned_date, expected_amount_kg=16000, status="scheduled"))


def _upload_email(s3: Any, raw_email: bytes, key: str = MESSAGE_ID) -> None:
    s3.put_object(Bucket="lmjm-fiscal-emails", Key=key, Body=raw_email)


def _query_items(table: Any, pk: str, sk_prefix: str) -> list[dict[str, Any]]:
    """Query DynamoDB for items with given pk and sk prefix."""
    from boto3.dynamodb.conditions import Key

    resp = table.query(KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(sk_prefix))
    return resp["Items"]


# ── Happy path: feed product ────────────────────────────────────────────────────


@mock_aws
def test_happy_path_feed_creates_fiscal_doc_and_fsfd() -> None:
    """Requirement 5.1, 4.4: Feed product creates FiscalDocument and FeedScheduleFiscalDocument."""
    table = _create_table()
    s3 = _create_bucket()
    _seed_batch(table)
    _seed_feed_raw_material(table)
    _seed_feed_schedule(table)

    xml = _build_nfe_xml(xPed=str(SUPPLY_ID))
    email_bytes = _build_email_with_xml(xml)
    _upload_email(s3, email_bytes)

    import lmjm.process_fiscal_email as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_ses_event(), None)
    assert result["statusCode"] == 200

    # FiscalDocument created under batch pk
    fiscal_docs = _query_items(table, BATCH_PK, "FiscalDocument|")
    assert len(fiscal_docs) == 1
    assert fiscal_docs[0]["fiscal_document_number"] == "833871"
    assert fiscal_docs[0]["product_code"] == "130906"
    assert fiscal_docs[0]["actual_amount_kg"] == 15980

    # FeedScheduleFiscalDocument created
    fsfds = _query_items(table, BATCH_PK, "FeedScheduleFiscalDocument|")
    assert len(fsfds) == 1
    assert fsfds[0]["status"] == "pending"
    assert fsfds[0]["product_code"] == "130906"
    assert fsfds[0]["feed_schedule_id"] == "FeedSchedule|sched-1"


# ── Idempotent processing ───────────────────────────────────────────────────────


@mock_aws
def test_duplicate_fiscal_document_number_skipped() -> None:
    """Requirement 2.5: Processing same email twice creates only 1 FiscalDocument."""
    table = _create_table()
    s3 = _create_bucket()
    _seed_batch(table)
    _seed_feed_raw_material(table)

    xml = _build_nfe_xml(xPed=str(SUPPLY_ID))
    email_bytes = _build_email_with_xml(xml)
    _upload_email(s3, email_bytes)

    import lmjm.process_fiscal_email as mod

    importlib.reload(mod)

    # Process twice
    mod.lambda_handler(_ses_event(), None)
    mod.lambda_handler(_ses_event(), None)

    fiscal_docs = _query_items(table, BATCH_PK, "FiscalDocument|")
    assert len(fiscal_docs) == 1


# ── Batch identification ────────────────────────────────────────────────────────


@mock_aws
def test_no_batch_match_uses_unmatched_fiscal() -> None:
    """Requirement 6.3: No batch match stores with pk=UNMATCHED_FISCAL."""
    table = _create_table()
    s3 = _create_bucket()
    _seed_feed_raw_material(table)
    # No batch seeded — xPed won't match anything

    xml = _build_nfe_xml(xPed="9999999")
    email_bytes = _build_email_with_xml(xml)
    _upload_email(s3, email_bytes)

    import lmjm.process_fiscal_email as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_ses_event(), None)
    assert result["statusCode"] == 200

    fiscal_docs = _query_items(table, "UNMATCHED_FISCAL", "FiscalDocument|")
    assert len(fiscal_docs) == 1
    assert fiscal_docs[0]["fiscal_document_number"] == "833871"


@mock_aws
def test_batch_matched_by_supply_id() -> None:
    """Requirement 6.2: xPed matching supply_id associates FiscalDocument with batch."""
    table = _create_table()
    s3 = _create_bucket()
    _seed_batch(table)
    _seed_feed_raw_material(table)

    xml = _build_nfe_xml(xPed=str(SUPPLY_ID))
    email_bytes = _build_email_with_xml(xml)
    _upload_email(s3, email_bytes)

    import lmjm.process_fiscal_email as mod

    importlib.reload(mod)

    mod.lambda_handler(_ses_event(), None)

    fiscal_docs = _query_items(table, BATCH_PK, "FiscalDocument|")
    assert len(fiscal_docs) == 1


# ── Feed vs medicine classification ─────────────────────────────────────────────


@mock_aws
def test_medicine_product_creates_medication_not_fsfd() -> None:
    """Requirement 5.5, 13.3, 13.4: Medicine product creates Medication, no FeedScheduleFiscalDocument."""
    table = _create_table()
    s3 = _create_bucket()
    _seed_batch(table)
    _seed_medicine_raw_material(table)

    xml = _build_nfe_xml(
        cProd="200001",
        xProd="AMOXICILLIN 500MG",
        xPed=str(SUPPLY_ID),
        include_rastro=True,
        rastro_nLote="LOT-MED-001",
        rastro_dVal="2027-06-30",
    )
    email_bytes = _build_email_with_xml(xml)
    _upload_email(s3, email_bytes)

    import lmjm.process_fiscal_email as mod

    importlib.reload(mod)

    mod.lambda_handler(_ses_event(), None)

    # FiscalDocument created
    fiscal_docs = _query_items(table, BATCH_PK, "FiscalDocument|")
    assert len(fiscal_docs) == 1

    # No FeedScheduleFiscalDocument
    fsfds = _query_items(table, BATCH_PK, "FeedScheduleFiscalDocument|")
    assert len(fsfds) == 0

    # Medication created
    meds = _query_items(table, BATCH_PK, "Medication|")
    assert len(meds) == 1
    assert meds[0]["medication_name"] == "Amoxicillin"
    assert meds[0]["raw_material_code"] == "200001"
    assert meds[0]["part_number"] == "LOT-MED-001"
    assert meds[0]["expiration_date"] == "2027-06-30"


# ── FeedScheduleFiscalDocument without FeedSchedule match ────────────────────────


@mock_aws
def test_feed_product_without_feed_schedule_creates_fsfd_with_none() -> None:
    """Requirement 5.4: Feed product without FeedSchedule match creates FSFD with feed_schedule_id=None."""
    table = _create_table()
    s3 = _create_bucket()
    _seed_batch(table)
    _seed_feed_raw_material(table)
    # No FeedSchedule seeded

    xml = _build_nfe_xml(xPed=str(SUPPLY_ID))
    email_bytes = _build_email_with_xml(xml)
    _upload_email(s3, email_bytes)

    import lmjm.process_fiscal_email as mod

    importlib.reload(mod)

    mod.lambda_handler(_ses_event(), None)

    fsfds = _query_items(table, BATCH_PK, "FeedScheduleFiscalDocument|")
    assert len(fsfds) == 1
    assert fsfds[0]["status"] == "pending"
    # feed_schedule_id should be absent (None → skipped by serialization_config)
    assert fsfds[0].get("feed_schedule_id") is None


# ── No XML attachments ──────────────────────────────────────────────────────────


@mock_aws
def test_no_xml_attachments_returns_success_no_fiscal_doc() -> None:
    """Requirement 1.3: Email with no XML attachments logs warning, no FiscalDocument created."""
    table = _create_table()
    s3 = _create_bucket()

    email_bytes = _build_plain_email()
    _upload_email(s3, email_bytes)

    import lmjm.process_fiscal_email as mod

    importlib.reload(mod)

    result = mod.lambda_handler(_ses_event(), None)
    assert result["statusCode"] == 200

    # No FiscalDocument anywhere
    from boto3.dynamodb.conditions import Key

    resp = table.scan()
    fiscal_items = [i for i in resp["Items"] if str(i.get("sk", "")).startswith("FiscalDocument|")]
    assert len(fiscal_items) == 0
