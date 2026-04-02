"""Import feed schedule from PENEPRA HTML report into DynamoDB.

Batch pk: 293de398-0cca-4613-b528-7af1010c64eb
Source: PENEPRA GRANJA LUCAS ALVES M1.htm

Usage:
    python scripts/import_feed_schedule_m1.py
"""

import uuid

import boto3

REGION = "sa-east-1"
TABLE_NAME = "lmjm"
BATCH_PK = "293de398-0cca-4613-b528-7af1010c64eb"

# Material code → feed type name mapping
FEED_TYPE_MAP = {
    "130867": "ST01",
    "130871": "ST02",   # TODO: provide mapping
    "130887": "ST03",   # TODO: provide mapping
    "130888": "ST04",
    "765668": "ST05",
    "130906": "ST06",   # TODO: provide mapping
}

# Feed schedule data extracted from HTML (left column only, preserving same-day duplicates)
# Format: (planned_date YYYY-MM-DD, material_code, expected_amount_kg)
SCHEDULE_DATA = [
    ("2026-04-02", "130867", 16000),
    ("2026-04-06", "130867", 16000),
    ("2026-04-08", "130867", 16000),
    ("2026-04-11", "130867", 16000),
    ("2026-04-14", "130867", 16000),
    ("2026-04-17", "130867", 16000),
    ("2026-04-19", "130867", 16000),
    ("2026-04-24", "130871", 16000),
    ("2026-04-27", "130871", 16000),
    ("2026-04-29", "130871", 16000),
    ("2026-05-01", "130871", 16000),
    ("2026-05-01", "130871", 16000),
    ("2026-05-04", "130871", 16000),
    ("2026-05-06", "130871", 16000),
    ("2026-05-08", "130871", 16000),
    ("2026-05-08", "130871", 16000),
    ("2026-05-11", "130871", 16000),
    ("2026-05-13", "130871", 16000),
    ("2026-05-14", "130887", 16000),
    ("2026-05-16", "130887", 16000),
    ("2026-05-16", "130887", 16000),
    ("2026-05-19", "130887", 16000),
    ("2026-05-21", "130887", 16000),
    ("2026-05-23", "130887", 16000),
    ("2026-05-23", "130887", 16000),
    ("2026-05-26", "130887", 16000),
    ("2026-05-28", "130887", 16000),
    ("2026-05-30", "130887", 16000),
    ("2026-05-30", "130887", 16000),
    ("2026-06-02", "130888", 16000),
    ("2026-06-04", "130888", 16000),
    ("2026-06-05", "130888", 16000),
    ("2026-06-06", "130888", 16000),
    ("2026-06-08", "130888", 16000),
    ("2026-06-10", "130888", 16000),
    ("2026-06-11", "130888", 16000),
    ("2026-06-13", "130888", 16000),
    ("2026-06-14", "130888", 16000),
    ("2026-06-16", "130888", 16000),
    ("2026-06-18", "130888", 16000),
    ("2026-06-19", "130888", 16000),
    ("2026-06-21", "130888", 16000),
    ("2026-06-22", "130888", 16000),
    ("2026-06-28", "130888", 16000),
    ("2026-06-30", "130888", 16000),
    ("2026-07-01", "130888", 16000),
    ("2026-07-08", "765668", 16000),
    ("2026-07-09", "765668", 16000),
    ("2026-07-11", "765668", 16000),
    ("2026-07-12", "765668", 16000),
    ("2026-07-14", "765668", 16000),
    ("2026-07-15", "765668", 16000),
    ("2026-07-16", "765668", 2237),
    ("2026-07-17", "130906", 16000),
    ("2026-07-18", "130906", 16000),
    ("2026-07-19", "130906", 16000),
    ("2026-07-21", "130906", 16000),
    ("2026-07-22", "130906", 16000),
    ("2026-07-23", "130906", 16000),
    ("2026-07-24", "130906", 16000),
    ("2026-07-26", "130906", 16000),
    ("2026-07-27", "130906", 16000),
    ("2026-07-28", "130906", 16000),
    ("2026-07-30", "130906", 16000),
    ("2026-07-31", "130906", 16000),
    ("2026-08-01", "130906", 16000),
    ("2026-08-03", "130906", 16000),
    ("2026-08-04", "130906", 16000),
]

session = boto3.Session(region_name=REGION)
table = session.resource("dynamodb").Table(TABLE_NAME)

# First delete existing feed schedules for this batch
from boto3.dynamodb.conditions import Key

response = table.query(
    KeyConditionExpression=Key("pk").eq(BATCH_PK) & Key("sk").begins_with("FeedSchedule|"),
    ProjectionExpression="pk, sk",
)
existing = response["Items"]
if existing:
    with table.batch_writer() as batch:
        for item in existing:
            batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
    print(f"Deleted {len(existing)} existing feed schedule entries")

# Insert new entries
with table.batch_writer() as batch:
    for planned_date, material_code, amount_kg in SCHEDULE_DATA:
        feed_type = FEED_TYPE_MAP.get(material_code, material_code)
        item = {
            "pk": BATCH_PK,
            "sk": f"FeedSchedule|{uuid.uuid4()}",
            "feed_type": feed_type,
            "planned_date": planned_date,
            "expected_amount_kg": amount_kg,
            "status": "scheduled",
        }
        batch.put_item(Item=item)

print(f"Imported {len(SCHEDULE_DATA)} feed schedule entries for batch {BATCH_PK}")
print(f"  Dates with 2 deliveries: 2026-05-01, 2026-05-08, 2026-05-16, 2026-05-23, 2026-05-30")
