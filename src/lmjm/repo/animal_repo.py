from typing import Optional

from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Animal
from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict


class AnimalRepo:
    def __init__(self, table: Table):
        self.table = table

    def get(self, pk: str) -> Optional[Animal]:
        response = self.table.get_item(Key={"pk": pk, "sk": "Animal"})
        item = response.get("Item")
        if not item:
            return None
        return load_data_class_from_dict(item, Animal)

    def get_by_ear_tag(self, ear_tag: str) -> Optional[Animal]:
        response = self.table.query(
            IndexName="ear_tag-sk-index",
            KeyConditionExpression=Key("ear_tag").eq(ear_tag) & Key("sk").eq("Animal"),
            Limit=1,
        )
        items = response["Items"]
        if not items:
            return None
        return load_data_class_from_dict(items[0], Animal)

    def update(self, animal: Animal) -> None:
        self.table.put_item(Item=serialize_to_dict(animal))
