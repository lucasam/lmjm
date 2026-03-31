from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Insemination
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class InseminationRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, insemination: Insemination) -> None:
        self.table.put_item(Item=serialize_to_dict(insemination))

    def get_latest(self, pk: str) -> Optional[Insemination]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("Insemination|"),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response["Items"]
        if not items:
            return None
        return load_data_class_from_dict(items[0], Insemination)

    def list(self, pk: str) -> list[Insemination]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("Insemination|"),
            ScanIndexForward=False,
        )
        return load_data_class_from_dict_list(response["Items"], Insemination)
