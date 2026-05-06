from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import ProcedureAction
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class ProcedureActionRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, action: ProcedureAction) -> None:
        self.table.put_item(Item=serialize_to_dict(action))

    def get(self, pk: str, sk: str) -> Optional[ProcedureAction]:
        response = self.table.get_item(Key={"pk": pk, "sk": sk})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, ProcedureAction)

    def list_for_procedure(self, pk: str) -> list[ProcedureAction]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("Action|"),
        )
        return load_data_class_from_dict_list(response["Items"], ProcedureAction)

    def delete(self, pk: str, sk: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": sk})
