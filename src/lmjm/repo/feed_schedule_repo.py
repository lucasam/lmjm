from __future__ import annotations

from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import FeedSchedule
from lmjm.util.marshmallow_serializer import load_data_class_from_dict_list, serialize_to_dict


class FeedScheduleRepo:
    def __init__(self, table: Table):
        self.table = table

    def list(self, pk: str) -> list[FeedSchedule]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("FeedSchedule|"),
        )
        return load_data_class_from_dict_list(response["Items"], FeedSchedule)

    def put(self, feed_schedule: FeedSchedule) -> None:
        self.table.put_item(Item=serialize_to_dict(feed_schedule))

    def delete_all(self, pk: str) -> None:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("FeedSchedule|"),
            ProjectionExpression="pk, sk",
        )
        with self.table.batch_writer() as batch:
            for item in response["Items"]:
                batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
