from typing import Optional

from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Medication
from lmjm.util.marshmallow_serializer import (
    load_data_class_from_dict,
    load_data_class_from_dict_list,
    serialize_to_dict,
)


class MedicationRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, medication: Medication) -> None:
        self.table.put_item(Item=serialize_to_dict(medication))

    def list(self, pk: str) -> list[Medication]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("Medication|"),
        )
        items = [i for i in response["Items"] if not str(i.get("sk", "")).startswith("MedicationShot|")]
        return load_data_class_from_dict_list(items, Medication)

    def get(self, pk: str, sk: str) -> Optional[Medication]:
        response = self.table.get_item(Key={"pk": pk, "sk": sk})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, Medication)
