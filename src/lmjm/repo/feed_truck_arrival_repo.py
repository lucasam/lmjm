from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import FeedTruckArrival
from lmjm.util.marshmallow_serializer import load_data_class_from_dict_list, serialize_to_dict


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
