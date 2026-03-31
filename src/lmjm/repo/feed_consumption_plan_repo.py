from __future__ import annotations

from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import FeedConsumptionPlan
from lmjm.util.marshmallow_serializer import load_data_class_from_dict_list, serialize_to_dict


class FeedConsumptionPlanRepo:
    def __init__(self, table: Table):
        self.table = table

    def put_all(self, plans: list[FeedConsumptionPlan]) -> None:
        with self.table.batch_writer() as batch:
            for plan in plans:
                batch.put_item(Item=serialize_to_dict(plan))

    def delete_all(self, pk: str) -> None:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("FeedConsumptionPlan|"),
            ProjectionExpression="pk, sk",
        )
        with self.table.batch_writer() as batch:
            for item in response["Items"]:
                batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})

    def list(self, pk: str) -> list[FeedConsumptionPlan]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("FeedConsumptionPlan|"),
            ScanIndexForward=True,
        )
        return load_data_class_from_dict_list(response["Items"], FeedConsumptionPlan)
