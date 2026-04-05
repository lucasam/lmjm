from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import FeedScheduleFiscalDocument
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class FeedScheduleFiscalDocumentRepo:
    def __init__(self, table: Table):
        self.table = table

    def list(self, pk: str) -> list[FeedScheduleFiscalDocument]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("FeedScheduleFiscalDocument|"),
        )
        return load_data_class_from_dict_list(response["Items"], FeedScheduleFiscalDocument)

    def get(self, pk: str, fiscal_document_number: str) -> Optional[FeedScheduleFiscalDocument]:
        response = self.table.get_item(Key={"pk": pk, "sk": f"FeedScheduleFiscalDocument|{fiscal_document_number}"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, FeedScheduleFiscalDocument)

    def put(self, doc: FeedScheduleFiscalDocument) -> None:
        self.table.put_item(Item=serialize_to_dict(doc))

    def update_status(self, pk: str, sk: str, new_status: str) -> None:
        self.table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": new_status},
        )

    def delete(self, pk: str, sk: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": sk})
