"""Export all items from DynamoDB table to a JSON file.

Usage:
    python scripts/export_ddb.py
"""

import json
from decimal import Decimal

import boto3

REGION = "sa-east-1"
TABLE_NAME = "lmjm"
SOURCE_PROFILE = "lucasam+appsec-test-Admin"
OUTPUT_FILE = "scripts/lmjm_backup.json"


class DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return int(o) if o == int(o) else float(o)
        return super().default(o)


session = boto3.Session(profile_name=SOURCE_PROFILE, region_name=REGION)
table = session.resource("dynamodb").Table(TABLE_NAME)

items = []
response = table.scan()
items.extend(response["Items"])
while "LastEvaluatedKey" in response:
    response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
    items.extend(response["Items"])

with open(OUTPUT_FILE, "w") as f:
    json.dump(items, f, cls=DecimalEncoder, indent=2)

print(f"Exported {len(items)} items to {OUTPUT_FILE}")
