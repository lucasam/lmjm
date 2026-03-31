from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Module
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, load_data_class_from_dict_list


class ModuleRepo:
    def __init__(self, table: Table):
        self.table = table

    def get(self, pk: str) -> Optional[Module]:
        response = self.table.get_item(Key={"pk": pk, "sk": "Module"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, Module)

    def list(self) -> List[Module]:
        items: list[dict] = []  # type: ignore[type-arg]
        filter_expr = Key("sk").eq("Module") & Key("pk").begins_with("MODULE#")
        response = self.table.scan(FilterExpression=filter_expr)
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(FilterExpression=filter_expr, ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return load_data_class_from_dict_list(items, Module)
