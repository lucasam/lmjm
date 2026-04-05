"""Property-based tests for NF-e XML parser.

**Validates: Requirements 2.1**
"""

import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.fiscal.nfe_parser import parse_nfe_xml

NFE_NS = "http://www.portalfiscal.inf.br/nfe"

# Strategy: safe XML text (no special chars like <, >, &, ', ")
xml_safe_text = st.from_regex(r"[A-Za-z0-9]{1,30}", fullmatch=True)

# Strategy: date string in YYYY-MM-DD format
date_strategy = st.dates(
    min_value=datetime.date(2000, 1, 1),
    max_value=datetime.date(2099, 12, 31),
).map(lambda d: d.isoformat())

# Strategy: positive integer for qCom (use integers to avoid float rounding)
positive_kg = st.integers(min_value=1, max_value=10_000_000)


def _build_nfe_xml(
    nNF: str,
    date_str: str,
    cProd: str,
    xProd: str,
    qCom: int,
    xNome: str,
    xPed: str,
) -> bytes:
    """Build a valid NF-e XML string from the given field values."""
    dhEmi = f"{date_str}T00:00:00-03:00"
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
                    <xPed>{xPed}</xPed>
                </prod>
            </det>
        </infNFe>
    </NFe>
</nfeProc>"""
    return xml.encode("utf-8")


@given(
    nNF=xml_safe_text,
    date_str=date_strategy,
    cProd=xml_safe_text,
    xProd=xml_safe_text,
    qCom=positive_kg,
    xNome=xml_safe_text,
    xPed=xml_safe_text,
)
@settings(max_examples=100)
def test_nfe_xml_parsing_extracts_all_required_fields(
    nNF: str,
    date_str: str,
    cProd: str,
    xProd: str,
    qCom: int,
    xNome: str,
    xPed: str,
) -> None:
    """Property 2: NF-e XML parsing extracts all required fields.

    For any valid NF-e XML document containing a fiscal document number,
    issue date, product quantity, product description, product code, and
    supplier name, the parse_nfe_xml function should return a ParsedNfe
    with all fields populated and matching the values in the XML.

    **Validates: Requirements 2.1**
    """
    xml_bytes = _build_nfe_xml(
        nNF=nNF,
        date_str=date_str,
        cProd=cProd,
        xProd=xProd,
        qCom=qCom,
        xNome=xNome,
        xPed=xPed,
    )

    result = parse_nfe_xml(xml_bytes)

    assert result.fiscal_document_number == nNF
    assert result.issue_date == date_str
    assert result.product_code == cProd
    assert result.product_description == xProd
    assert result.actual_amount_kg == qCom
    assert result.supplier_name == xNome
    assert result.order_number == xPed
