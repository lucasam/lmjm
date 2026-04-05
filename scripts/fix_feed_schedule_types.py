"""Migrate FeedSchedule records for batch 293de398-0cca-4613-b528-7af1010c64eb.

For each FeedSchedule:
- Reverse-lookup the current feed_type (description like ST01) to find the code
- Set feed_type = code (e.g. "130867")
- Set feed_description = old feed_type value (e.g. "ST01")
"""

import boto3
from boto3.dynamodb.conditions import Key

BATCH_PK = "293de398-0cca-4613-b528-7af1010c64eb"
TABLE_NAME = "lmjm"
REGION = "sa-east-1"

# Reverse map: description -> code
FEED_TYPE_MAP = {
    "130867": "ST01",
    "130871": "ST02",
    "130887": "ST03",
    "130888": "ST04",
    "765668": "ST05",
    "130906": "ST06",
}
DESC_TO_CODE = {v: k for k, v in FEED_TYPE_MAP.items()}

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

response = table.query(
    KeyConditionExpression=Key("pk").eq(BATCH_PK) & Key("sk").begins_with("FeedSchedule|"),
)
items = response["Items"]
print(f"Found {len(items)} FeedSchedule records")

updated = 0
for item in items:
    old_feed_type = item.get("feed_type", "")
    sk = item["sk"]

    # If feed_type is already a code (numeric), look up description directly
    if old_feed_type in FEED_TYPE_MAP:
        code = old_feed_type
        description = FEED_TYPE_MAP[old_feed_type]
    # If feed_type is a description (like ST01), reverse-lookup the code
    elif old_feed_type in DESC_TO_CODE:
        code = DESC_TO_CODE[old_feed_type]
        description = old_feed_type
    else:
        print(f"  SKIP {sk}: unknown feed_type '{old_feed_type}'")
        continue

    print(f"  {sk}: '{old_feed_type}' -> feed_type='{code}', feed_description='{description}'")
    table.update_item(
        Key={"pk": BATCH_PK, "sk": sk},
        UpdateExpression="SET feed_type = :ft, feed_description = :fd",
        ExpressionAttributeValues={":ft": code, ":fd": description},
    )
    updated += 1

print(f"Updated {updated}/{len(items)} records")
