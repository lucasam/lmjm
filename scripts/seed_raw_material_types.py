"""Seed initial RawMaterialType records into DynamoDB.

Inserts the 7 feed raw material types used by the fiscal document intake pipeline.

Usage:
    TABLE_NAME=lmjm python scripts/seed_raw_material_types.py
"""

import os

import boto3

REGION = "sa-east-1"
TABLE_NAME = os.environ.get("TABLE_NAME", "lmjm")

# Initial RawMaterialType records: (code, description, category)
RAW_MATERIAL_TYPES = [
    ("130867", "ST01", "feed"),
    ("130871", "ST02", "feed"),
    ("130887", "ST03", "feed"),
    ("130888", "ST04", "feed"),
    ("765668", "ST05", "feed"),
    ("130906", "ST06", "feed"),
    ("104278", "Super Plus", "feed"),
]

session = boto3.Session(region_name=REGION)
table = session.resource("dynamodb").Table(TABLE_NAME)

print(f"Seeding {len(RAW_MATERIAL_TYPES)} RawMaterialType records into '{TABLE_NAME}'...")

with table.batch_writer() as batch:
    for code, description, category in RAW_MATERIAL_TYPES:
        item = {
            "pk": "RAW_MATERIAL_TYPE",
            "sk": f"RawMaterialType|{code}",
            "code": code,
            "description": description,
            "category": category,
        }
        batch.put_item(Item=item)
        print(f"  {code} → {description} ({category})")

print(f"Done. {len(RAW_MATERIAL_TYPES)} records seeded.")
