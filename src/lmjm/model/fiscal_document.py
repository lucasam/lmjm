import dataclasses
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class FiscalDocument:
    pk: str
    sk: str
    fiscal_document_number: str = ""
    issue_date: str = ""
    actual_amount_kg: int = 0
    product_code: str = ""
    product_description: str = ""
    supplier_name: str = ""
    order_number: str = ""
    source_email_s3_key: Optional[str] = None
