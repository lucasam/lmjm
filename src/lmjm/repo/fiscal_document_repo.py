from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import FiscalDocument
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class FiscalDocumentRepo:
    def __init__(self, table: Table):
        self.table = table

    def list(self, pk: str) -> list[FiscalDocument]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("FiscalDocument|"),
        )
        return load_data_class_from_dict_list(response["Items"], FiscalDocument)

    def get(self, pk: str, fiscal_document_number: str) -> Optional[FiscalDocument]:
        response = self.table.get_item(Key={"pk": pk, "sk": f"FiscalDocument|{fiscal_document_number}"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, FiscalDocument)

    def get_by_sk(self, pk: str, sk: str) -> Optional[FiscalDocument]:
        response = self.table.get_item(Key={"pk": pk, "sk": sk})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, FiscalDocument)

    def scan_all(self) -> List[FiscalDocument]:
        items: List[dict] = []  # type: ignore[type-arg]
        filter_expr = Key("sk").begins_with("FiscalDocument|")
        response = self.table.scan(FilterExpression=filter_expr)
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(FilterExpression=filter_expr, ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return load_data_class_from_dict_list(items, FiscalDocument)

    def delete(self, pk: str, fiscal_document_number: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": f"FiscalDocument|{fiscal_document_number}"})

    def put(self, doc: FiscalDocument) -> None:
        self.table.put_item(Item=serialize_to_dict(doc))
