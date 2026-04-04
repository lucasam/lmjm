from __future__ import annotations

from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Weight
from lmjm.util.marshmallow_serializer import load_data_class_from_dict_list, serialize_to_dict


class WeightRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, weight: Weight) -> None:
        self.table.put_item(Item=serialize_to_dict(weight))

    def list(self, pk: str) -> list[Weight]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("Peso|"),
            ScanIndexForward=False,
        )
        return load_data_class_from_dict_list(response["Items"], Weight)
