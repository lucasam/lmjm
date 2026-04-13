from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import BatchFinancialResult
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class BatchFinancialResultRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, result: BatchFinancialResult) -> None:
        self.table.put_item(Item=serialize_to_dict(result))

    def list(self, batch_id: str) -> list[BatchFinancialResult]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(batch_id) & Key("sk").begins_with("BatchFinancialResult|"),
            ScanIndexForward=True,
        )
        return load_data_class_from_dict_list(response["Items"], BatchFinancialResult)

    def get(self, batch_id: str, type: str) -> Optional[BatchFinancialResult]:
        response = self.table.get_item(Key={"pk": batch_id, "sk": f"BatchFinancialResult|{type}"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, BatchFinancialResult)

    def delete(self, batch_id: str, type: str) -> None:
        self.table.delete_item(Key={"pk": batch_id, "sk": f"BatchFinancialResult|{type}"})
