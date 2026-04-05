from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import RawMaterialType
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class RawMaterialTypeRepo:
    def __init__(self, table: Table):
        self.table = table

    def list_all(self) -> list[RawMaterialType]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq("RAW_MATERIAL_TYPE") & Key("sk").begins_with("RawMaterialType|"),
        )
        return load_data_class_from_dict_list(response["Items"], RawMaterialType)

    def get(self, code: str) -> Optional[RawMaterialType]:
        response = self.table.get_item(Key={"pk": "RAW_MATERIAL_TYPE", "sk": f"RawMaterialType|{code}"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, RawMaterialType)

    def put(self, item: RawMaterialType) -> None:
        self.table.put_item(Item=serialize_to_dict(item))
