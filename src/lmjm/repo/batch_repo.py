from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Batch
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class BatchRepo:
    def __init__(self, table: Table):
        self.table = table

    def get(self, pk: str) -> Optional[Batch]:
        response = self.table.get_item(Key={"pk": pk, "sk": "Batch"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, Batch)

    def list(self) -> list[Batch]:
        items: list[dict] = []  # type: ignore[type-arg]
        filter_expr = Key("sk").eq("Batch")
        response = self.table.scan(FilterExpression=filter_expr)
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(FilterExpression=filter_expr, ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        # Filter out Module records that also have sk="Batch" (shouldn't exist, but be safe)
        return load_data_class_from_dict_list(
            [i for i in items if not str(i.get("pk", "")).startswith("MODULE#")], Batch
        )

    def update(self, batch: Batch) -> None:
        self.table.put_item(Item=serialize_to_dict(batch))
