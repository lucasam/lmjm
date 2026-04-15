from __future__ import annotations

from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import FeedConsumptionTemplate
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class FeedConsumptionTemplateRepo:
    def __init__(self, table: Table):
        self.table = table

    def list_all(self) -> list[FeedConsumptionTemplate]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq("FEED_CONSUMPTION_TEMPLATE")
            & Key("sk").begins_with("FeedConsumptionTemplate|"),
            ScanIndexForward=True,
        )
        return load_data_class_from_dict_list(response["Items"], FeedConsumptionTemplate)

    def put(self, item: FeedConsumptionTemplate) -> None:
        self.table.put_item(Item=serialize_to_dict(item))
