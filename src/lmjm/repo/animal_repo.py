from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Attr, Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Animal
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class AnimalRepo:
    def __init__(self, table: Table):
        self.table = table

    def get(self, pk: str) -> Optional[Animal]:
        response = self.table.get_item(Key={"pk": pk, "sk": "Animal"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, Animal)

    def get_by_ear_tag(self, ear_tag: str) -> Optional[Animal]:
        response = self.table.query(
            IndexName="ear_tag-sk-index",
            KeyConditionExpression=Key("ear_tag").eq(ear_tag) & Key("sk").eq("Animal"),
            Limit=1,
        )
        items = response["Items"]
        if not items:
            return None
        return load_data_class_from_dict(items[0], Animal)

    def list_cattle(self) -> list[Animal]:
        items: list[dict] = []  # type: ignore[type-arg]
        filter_expr = Key("sk").eq("Animal") & Attr("species").eq("cattle")
        response = self.table.scan(FilterExpression=filter_expr)
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(FilterExpression=filter_expr, ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return load_data_class_from_dict_list(items, Animal)

    def update(self, animal: Animal) -> None:
        self.table.put_item(Item=serialize_to_dict(animal))
