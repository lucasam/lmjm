from __future__ import annotations

from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import MedicationShot
from lmjm.util.marshmallow_serializer import load_data_class_from_dict_list, serialize_to_dict


class MedicationShotRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, shot: MedicationShot) -> None:
        self.table.put_item(Item=serialize_to_dict(shot))

    def list(self, pk: str, month: str | None = None) -> list[MedicationShot]:
        if month:
            # month comes as "YYYY-MM", sk uses YYYYMMDD format — strip the dash
            prefix = f"MedicationShot|{month.replace('-', '')}"
        else:
            prefix = "MedicationShot|"
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(prefix),
        )
        return load_data_class_from_dict_list(response["Items"], MedicationShot)
