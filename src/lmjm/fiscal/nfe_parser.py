import dataclasses
import logging
import xml.etree.ElementTree as ET

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclasses.dataclass
class ParsedNfe:
    fiscal_document_number: str
    issue_date: str  # YYYY-MM-DD
    actual_amount_kg: int  # from qCom, rounded to int
    product_code: str  # cProd (e.g., "130906")
    product_description: str  # xProd (e.g., "ST06 RAC SUI TERM")
    supplier_name: str
    order_number: str = ""  # xPed (purchase order)
    lot_number: str = ""  # rastro/nLote
    expiration_date: str = ""  # rastro/dVal (YYYY-MM-DD)
    scheduled_date: str = ""  # from infAdic/infCpl "Data OCR: DD MM YYYY" → YYYY-MM-DD
    item_number: str = ""  # nItem attribute from <det> element


def parse_nfe_xml(xml_bytes: bytes) -> list[ParsedNfe]:
    """Parse NF-e XML and extract one ParsedNfe per <det> item.

    Returns a list with one entry per <det> element. Each entry carries its own
    product_code, product_description, actual_amount_kg, lot_number, and
    expiration_date. Header-level fields (fiscal_document_number, issue_date,
    supplier_name, scheduled_date) and order_number (first xPed found) are
    shared across all items.

    Raises ValueError if required fields are missing or XML is malformed.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed XML: {exc}") from exc

    # Try with namespace first, fall back to no namespace
    inf_nfe = root.find(".//nfe:NFe/nfe:infNFe", NS)
    if inf_nfe is None:
        inf_nfe = root.find(".//NFe/infNFe")
    if inf_nfe is None:
        raise ValueError("Cannot find infNFe element in XML")

    fiscal_document_number = _required_text(inf_nfe, "ide/nNF", "nNF")
    dh_emi = _required_text(inf_nfe, "ide/dhEmi", "dhEmi")
    issue_date = dh_emi[:10]

    supplier_name = _required_text(inf_nfe, "emit/xNome", "emit/xNome")

    det_elements = inf_nfe.findall("nfe:det", NS)
    if not det_elements:
        det_elements = inf_nfe.findall("det")
    if not det_elements:
        raise ValueError("No <det> elements found in XML")

    # Extract scheduled_date from infAdic/infCpl "Data OCR: DD MM YYYY"
    scheduled_date = ""
    inf_adic = inf_nfe.find("nfe:infAdic", NS)
    if inf_adic is None:
        inf_adic = inf_nfe.find("infAdic")
        logger.info("Found infAdic: %s", inf_adic)
    if inf_adic is not None:
        inf_cpl = _find_text_el(inf_adic, "infCpl")
        logger.info("Found infCpl: %s", inf_cpl)

        if inf_cpl:
            import re

            m = re.search(r"Data OCR:\s*(\d{2})\s+(\d{2})\s+(\d{4})", inf_cpl)
            if m:
                scheduled_date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    # Collect order_number from the first det that has xPed
    order_number = ""
    for det in det_elements:
        prod = det.find("nfe:prod", NS)
        if prod is None:
            prod = det.find("prod")
        if prod is not None:
            xped = _find_text(prod, "xPed")
            if xped:
                order_number = xped
                break

    # Build one ParsedNfe per det element
    items: list[ParsedNfe] = []
    for det in det_elements:
        item_number = det.get("nItem", "")
        prod = det.find("nfe:prod", NS)
        if prod is None:
            prod = det.find("prod")
        if prod is None:
            continue

        product_code = _find_text(prod, "cProd") or ""
        product_description = _find_text(prod, "xProd") or ""
        qcom_text = _find_text(prod, "qCom")
        if not product_code or not product_description or qcom_text is None:
            logger.warning("Skipping det nItem=%s: missing cProd/xProd/qCom", item_number)
            continue

        try:
            actual_amount_kg = round(float(qcom_text))
        except ValueError:
            raise ValueError(f"Invalid qCom value: {qcom_text}")

        lot_number = ""
        expiration_date = ""
        rastro = prod.find("nfe:rastro", NS)
        if rastro is None:
            rastro = prod.find("rastro")
        if rastro is not None:
            lot_number = _find_text_el(rastro, "nLote") or ""
            expiration_date = _find_text_el(rastro, "dVal") or ""

        items.append(
            ParsedNfe(
                fiscal_document_number=fiscal_document_number,
                issue_date=issue_date,
                actual_amount_kg=actual_amount_kg,
                product_code=product_code,
                product_description=product_description,
                supplier_name=supplier_name,
                order_number=order_number,
                lot_number=lot_number,
                expiration_date=expiration_date,
                scheduled_date=scheduled_date,
                item_number=item_number,
            )
        )

    if not items:
        raise ValueError("No valid <det> elements found in XML")

    return items


def _required_text(parent: ET.Element, path: str, field_name: str) -> str:
    """Find element text using namespace, falling back to no namespace."""
    ns_path = path.replace("/", "/nfe:")
    ns_path = "nfe:" + ns_path
    el = parent.find(ns_path, NS)
    if el is None:
        el = parent.find(path)
    if el is None or el.text is None:
        raise ValueError(f"Required field {field_name} not found in XML")
    return el.text.strip()


def _find_text(parent: ET.Element, tag: str) -> str | None:
    """Find element text using namespace, falling back to no namespace."""
    el = parent.find(f"nfe:{tag}", NS)
    if el is None:
        el = parent.find(tag)
    if el is not None and el.text is not None:
        return el.text.strip()
    return None


def _find_text_el(parent: ET.Element, tag: str) -> str | None:
    """Find element text within a parent element."""
    el = parent.find(f"nfe:{tag}", NS)
    if el is None:
        el = parent.find(tag)
    if el is not None and el.text is not None:
        return el.text.strip()
    return None
