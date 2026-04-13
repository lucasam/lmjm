from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import IntegratorWeeklyData
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class IntegratorWeeklyDataRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, data: IntegratorWeeklyData) -> None:
        self.table.put_item(Item=serialize_to_dict(data))

    def list(self) -> list[IntegratorWeeklyData]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq("INTEGRATOR_WEEKLY_DATA"),
            ScanIndexForward=False,
        )
        return load_data_class_from_dict_list(response["Items"], IntegratorWeeklyData)

    def get(self, date_generated: str) -> Optional[IntegratorWeeklyData]:
        response = self.table.get_item(
            Key={"pk": "INTEGRATOR_WEEKLY_DATA", "sk": f"IntegratorWeeklyData|{date_generated}"}
        )
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, IntegratorWeeklyData)
