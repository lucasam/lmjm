from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Warehouse
from lmjm.util.marshmallow_serializer import serialize_to_dict


class WarehouseRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, warehouse: Warehouse) -> None:
        self.table.put_item(Item=serialize_to_dict(warehouse))

    def update(self, warehouse: Warehouse) -> None:
        self.table.put_item(Item=serialize_to_dict(warehouse))
