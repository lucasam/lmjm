import dataclasses
import email.parser
import email.policy


@dataclasses.dataclass
class EmailAttachment:
    filename: str
    content: bytes


def extract_xml_attachments(raw_email: bytes) -> list[EmailAttachment]:
    """Parse MIME email and return all XML attachments.

    Uses Python's email.parser module. Identifies XML attachments by:
    - Content-Type: text/xml or application/xml
    - Filename ending in .xml
    """
    parser = email.parser.BytesParser(policy=email.policy.default)
    msg = parser.parsebytes(raw_email)

    attachments: list[EmailAttachment] = []

    for part in msg.walk():
        content_type = part.get_content_type()
        filename = part.get_filename() or ""

        is_xml_content_type = content_type in ("text/xml", "application/xml")
        is_xml_filename = filename.lower().endswith(".xml")

        if not (is_xml_content_type or is_xml_filename):
            continue

        payload = part.get_content()
        if isinstance(payload, str):
            content = payload.encode("utf-8")
        elif isinstance(payload, bytes):
            content = payload
        else:
            continue

        if not filename:
            filename = "attachment.xml"

        attachments.append(EmailAttachment(filename=filename, content=content))

    return attachments
