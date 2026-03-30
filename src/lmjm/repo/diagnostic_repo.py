from mypy_boto3_dynamodb.service_resource import Table

from lmjm.model import Diagnostic
from lmjm.util.marshmallow_serializer import serialize_to_dict


class DiagnosticRepo:
    def __init__(self, table: Table):
        self.table = table

    def put(self, diagnostic: Diagnostic) -> None:
        self.table.put_item(Item=serialize_to_dict(diagnostic))
