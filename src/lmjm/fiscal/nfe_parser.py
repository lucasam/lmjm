import dataclasses
import xml.etree.ElementTree as ET

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


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


def parse_nfe_xml(xml_bytes: bytes) -> ParsedNfe:
    """Parse NF-e XML and extract required fields.

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

    total_qcom = 0.0
    product_code = ""
    product_description = ""
    order_number = ""
    lot_number = ""
    expiration_date = ""

    for det in det_elements:
        prod = det.find("nfe:prod", NS)
        if prod is None:
            prod = det.find("prod")
        if prod is None:
            continue

        qcom_text = _find_text(prod, "qCom")
        if qcom_text is not None:
            try:
                total_qcom += float(qcom_text)
            except ValueError:
                raise ValueError(f"Invalid qCom value: {qcom_text}")

        if not product_code:
            product_code = _find_text(prod, "cProd") or ""
        if not product_description:
            product_description = _find_text(prod, "xProd") or ""
        if not order_number:
            order_number = _find_text(prod, "xPed") or ""

        if not lot_number:
            rastro = prod.find("nfe:rastro", NS)
            if rastro is None:
                rastro = prod.find("rastro")
            if rastro is not None:
                lot_number = _find_text_el(rastro, "nLote") or ""
                expiration_date = _find_text_el(rastro, "dVal") or ""

    if not product_code:
        raise ValueError("Required field cProd not found in any <det> element")
    if not product_description:
        raise ValueError("Required field xProd not found in any <det> element")
    if total_qcom == 0.0:
        raise ValueError("Required field qCom not found or zero in all <det> elements")

    return ParsedNfe(
        fiscal_document_number=fiscal_document_number,
        issue_date=issue_date,
        actual_amount_kg=round(total_qcom),
        product_code=product_code,
        product_description=product_description,
        supplier_name=supplier_name,
        order_number=order_number,
        lot_number=lot_number,
        expiration_date=expiration_date,
    )


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
