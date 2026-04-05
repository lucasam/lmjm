"""Unit tests for email MIME parser.

Validates: Requirements 1.3, 1.4
"""

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from lmjm.fiscal.email_parser import extract_xml_attachments

SAMPLE_XML = b'<?xml version="1.0"?><nfeProc><NFe><infNFe></infNFe></NFe></nfeProc>'


def _build_email_with_attachments(
    attachments: list[tuple[str, str, bytes]],
    body: str = "See attached fiscal documents.",
) -> bytes:
    """Build a multipart MIME email with the given attachments.

    Each attachment is a tuple of (filename, content_type, content).
    """
    msg = MIMEMultipart()
    msg["Subject"] = "NF-e Documents"
    msg["From"] = "supplier@example.com"
    msg["To"] = "fiscal@lmjm.net"
    msg.attach(MIMEText(body, "plain"))

    for filename, content_type, content in attachments:
        maintype, subtype = content_type.split("/", 1)
        part = MIMEBase(maintype, subtype)
        part.set_payload(content)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    return msg.as_bytes()


def test_single_xml_attachment() -> None:
    """Single XML attachment (application/xml) returns 1 attachment."""
    raw = _build_email_with_attachments([
        ("nfe_833871.xml", "application/xml", SAMPLE_XML),
    ])
    result = extract_xml_attachments(raw)

    assert len(result) == 1
    assert result[0].filename == "nfe_833871.xml"
    assert result[0].content == SAMPLE_XML


def test_no_attachments_returns_empty() -> None:
    """Plain text email with no attachments returns empty list."""
    msg = MIMEText("Just a plain email, no attachments.", "plain")
    msg["Subject"] = "Hello"
    msg["From"] = "someone@example.com"
    msg["To"] = "fiscal@lmjm.net"

    result = extract_xml_attachments(msg.as_bytes())

    assert result == []


def test_multiple_xml_attachments() -> None:
    """Multiple XML attachments are all returned."""
    xml1 = b"<nfe>1</nfe>"
    xml2 = b"<nfe>2</nfe>"
    xml3 = b"<nfe>3</nfe>"
    raw = _build_email_with_attachments([
        ("nfe_001.xml", "application/xml", xml1),
        ("nfe_002.xml", "text/xml", xml2),
        ("nfe_003.xml", "application/xml", xml3),
    ])
    result = extract_xml_attachments(raw)

    assert len(result) == 3
    assert result[0].filename == "nfe_001.xml"
    assert result[0].content == xml1
    assert result[1].filename == "nfe_002.xml"
    assert result[1].content == xml2
    assert result[2].filename == "nfe_003.xml"
    assert result[2].content == xml3


def test_mixed_attachments_returns_only_xml() -> None:
    """Mixed attachments (XML + PDF + image) returns only XML ones."""
    xml_content = b"<nfe>data</nfe>"
    pdf_content = b"%PDF-1.4 fake pdf"
    img_content = b"\x89PNG fake image"

    raw = _build_email_with_attachments([
        ("nfe_100.xml", "application/xml", xml_content),
        ("invoice.pdf", "application/pdf", pdf_content),
        ("photo.png", "image/png", img_content),
    ])
    result = extract_xml_attachments(raw)

    assert len(result) == 1
    assert result[0].filename == "nfe_100.xml"
    assert result[0].content == xml_content


def test_xml_identified_by_filename_extension() -> None:
    """XML identified by .xml filename even with application/octet-stream Content-Type."""
    xml_content = b"<nfe>octet</nfe>"
    raw = _build_email_with_attachments([
        ("nfe_999.xml", "application/octet-stream", xml_content),
    ])
    result = extract_xml_attachments(raw)

    assert len(result) == 1
    assert result[0].filename == "nfe_999.xml"
    assert result[0].content == xml_content
