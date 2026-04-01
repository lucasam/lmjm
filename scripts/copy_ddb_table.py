"""Copy all items from source DynamoDB table (profile) to destination table (env credentials).

Usage:
    python scripts/copy_ddb_table.py
"""

import boto3

REGION = "sa-east-1"
TABLE_NAME = "lmjm"
SOURCE_PROFILE = "lucasam+appsec-test-Admin"

# Source: from named profile
source_session = boto3.Session(profile_name=SOURCE_PROFILE, region_name=REGION)
source_table = source_session.resource("dynamodb").Table(TABLE_NAME)

# Destination: from environment credentials (default)
dest_session = boto3.Session(region_name=REGION)
dest_table = dest_session.resource("dynamodb").Table(TABLE_NAME)

# Scan all items from source
items = []
response = source_table.scan()
items.extend(response["Items"])
while "LastEvaluatedKey" in response:
    response = source_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
    items.extend(response["Items"])

print(f"Read {len(items)} items from source")

# Write to destination
with dest_table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)

print(f"Wrote {len(items)} items to destination")
