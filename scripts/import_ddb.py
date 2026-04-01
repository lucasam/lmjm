"""Import items from a JSON file into DynamoDB table using env credentials.

Usage:
    python scripts/import_ddb.py
"""

import json
from decimal import Decimal

import boto3

REGION = "sa-east-1"
TABLE_NAME = "lmjm"
INPUT_FILE = "scripts/lmjm_backup.json"


def convert_floats(obj: object) -> object:
    """Convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


session = boto3.Session(region_name=REGION)
table = session.resource("dynamodb").Table(TABLE_NAME)

with open(INPUT_FILE) as f:
    items = json.load(f)

items = [convert_floats(item) for item in items]

with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)

print(f"Imported {len(items)} items into {TABLE_NAME}")
