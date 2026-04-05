"""Unit tests for NF-e XML parser.

Validates: Requirements 2.1, 2.2, 2.4, 6.1
"""

import pytest

from lmjm.fiscal.nfe_parser import ParsedNfe, parse_nfe_xml

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


def _build_nfe_xml(
    nNF: str = "833871",
    dhEmi: str = "2026-03-26T12:10:26-03:00",
    xNome: str = "BRF S.A.",
    det_items: list[dict[str, str]] | None = None,
    include_rastro: bool = False,
    rastro_nLote: str = "LOT001",
    rastro_dVal: str = "2027-01-15",
) -> bytes:
    """Build a minimal NF-e XML for testing."""
    if det_items is None:
        det_items = [{"cProd": "130906", "xProd": "ST06 RAC SUI TERM", "qCom": "15980.0000", "xPed": "0112053764"}]

    det_xml = ""
    for i, item in enumerate(det_items, start=1):
        rastro_xml = ""
        if include_rastro and i == 1:
            rastro_xml = f"""
                <rastro>
                    <nLote>{rastro_nLote}</nLote>
                    <dVal>{rastro_dVal}</dVal>
                </rastro>"""

        xPed_xml = f"<xPed>{item.get('xPed', '')}</xPed>" if item.get("xPed") else ""
        det_xml += f"""
        <det nItem="{i}">
            <prod>
                <cProd>{item['cProd']}</cProd>
                <xProd>{item['xProd']}</xProd>
                <qCom>{item['qCom']}</qCom>
                {xPed_xml}{rastro_xml}
            </prod>
        </det>"""

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
            </emit>{det_xml}
        </infNFe>
    </NFe>
</nfeProc>"""
    return xml.encode("utf-8")


def test_parse_basic_nfe() -> None:
    xml_bytes = _build_nfe_xml()
    result = parse_nfe_xml(xml_bytes)

    assert result.fiscal_document_number == "833871"
    assert result.issue_date == "2026-03-26"
    assert result.actual_amount_kg == 15980
    assert result.product_code == "130906"
    assert result.product_description == "ST06 RAC SUI TERM"
    assert result.supplier_name == "BRF S.A."
    assert result.order_number == "0112053764"
    assert result.lot_number == ""
    assert result.expiration_date == ""


def test_parse_with_rastro() -> None:
    xml_bytes = _build_nfe_xml(include_rastro=True)
    result = parse_nfe_xml(xml_bytes)

    assert result.lot_number == "LOT001"
    assert result.expiration_date == "2027-01-15"


def test_parse_multiple_det_sums_qcom() -> None:
    items = [
        {"cProd": "130906", "xProd": "ST06 RAC SUI TERM", "qCom": "8000.5000", "xPed": "0112053764"},
        {"cProd": "130906", "xProd": "ST06 RAC SUI TERM", "qCom": "7979.5000"},
    ]
    xml_bytes = _build_nfe_xml(det_items=items)
    result = parse_nfe_xml(xml_bytes)

    assert result.actual_amount_kg == 15980


def test_parse_qcom_rounds_to_int() -> None:
    items = [
        {"cProd": "130906", "xProd": "ST06 RAC SUI TERM", "qCom": "100.4999"},
    ]
    xml_bytes = _build_nfe_xml(det_items=items)
    result = parse_nfe_xml(xml_bytes)
    assert result.actual_amount_kg == 100

    items2 = [
        {"cProd": "130906", "xProd": "ST06 RAC SUI TERM", "qCom": "100.5001"},
    ]
    xml_bytes2 = _build_nfe_xml(det_items=items2)
    result2 = parse_nfe_xml(xml_bytes2)
    assert result2.actual_amount_kg == 101


def test_parse_dhEmi_extracts_date_only() -> None:
    xml_bytes = _build_nfe_xml(dhEmi="2026-03-26T12:10:26-03:00")
    result = parse_nfe_xml(xml_bytes)
    assert result.issue_date == "2026-03-26"


def test_parse_missing_nNF_raises() -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="{NFE_NS}">
    <NFe><infNFe>
        <ide><dhEmi>2026-03-26T12:10:26-03:00</dhEmi></ide>
        <emit><xNome>BRF</xNome></emit>
        <det nItem="1"><prod>
            <cProd>130906</cProd><xProd>ST06</xProd><qCom>100</qCom>
        </prod></det>
    </infNFe></NFe>
</nfeProc>""".encode("utf-8")
    with pytest.raises(ValueError, match="nNF"):
        parse_nfe_xml(xml)


def test_parse_missing_xNome_raises() -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="{NFE_NS}">
    <NFe><infNFe>
        <ide><nNF>123</nNF><dhEmi>2026-03-26T12:10:26-03:00</dhEmi></ide>
        <emit></emit>
        <det nItem="1"><prod>
            <cProd>130906</cProd><xProd>ST06</xProd><qCom>100</qCom>
        </prod></det>
    </infNFe></NFe>
</nfeProc>""".encode("utf-8")
    with pytest.raises(ValueError, match="xNome"):
        parse_nfe_xml(xml)


def test_parse_malformed_xml_raises() -> None:
    with pytest.raises(ValueError, match="Malformed XML"):
        parse_nfe_xml(b"<not valid xml")


def test_parse_missing_infNFe_raises() -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="{NFE_NS}">
    <NFe></NFe>
</nfeProc>""".encode("utf-8")
    with pytest.raises(ValueError, match="infNFe"):
        parse_nfe_xml(xml)


def test_parse_xPed_from_first_det() -> None:
    """xPed should be taken from the first det that has it."""
    items = [
        {"cProd": "130906", "xProd": "ST06", "qCom": "100", "xPed": "ORDER1"},
        {"cProd": "130906", "xProd": "ST06", "qCom": "200", "xPed": "ORDER2"},
    ]
    xml_bytes = _build_nfe_xml(det_items=items)
    result = parse_nfe_xml(xml_bytes)
    assert result.order_number == "ORDER1"
