from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Attr, Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Procedure
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class ProcedureRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, procedure: Procedure) -> None:
        self.table.put_item(Item=serialize_to_dict(procedure))

    def get(self, pk: str) -> Optional[Procedure]:
        response = self.table.get_item(Key={"pk": pk, "sk": "Procedure"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, Procedure)

    def list_all(self) -> list[Procedure]:
        items: list[dict] = []  # type: ignore[type-arg]
        filter_expr = Key("sk").eq("Procedure") & Attr("pk").begins_with("Procedure|")
        response = self.table.scan(FilterExpression=filter_expr)
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(FilterExpression=filter_expr, ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return load_data_class_from_dict_list(items, Procedure)
