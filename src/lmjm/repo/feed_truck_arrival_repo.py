from __future__ import annotations

from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from typing import Optional

from lmjm.model import FeedTruckArrival
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class FeedTruckArrivalRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, arrival: FeedTruckArrival) -> None:
        self.table.put_item(Item=serialize_to_dict(arrival))

    def list(self, pk: str) -> list[FeedTruckArrival]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("FeedTruckArrival|"),
            ScanIndexForward=True,
        )
        return load_data_class_from_dict_list(response["Items"], FeedTruckArrival)

    def get(self, pk: str, sk: str) -> Optional[FeedTruckArrival]:
        response = self.table.get_item(Key={"pk": pk, "sk": sk})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, FeedTruckArrival)

    def update(self, arrival: FeedTruckArrival) -> None:
        self.table.put_item(Item=serialize_to_dict(arrival))

    def delete(self, pk: str, sk: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": sk})
