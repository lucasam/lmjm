"""Shift FeedConsumptionPlan dates back by 1 day for specified batches.

This script:
1. Queries all FeedConsumptionPlan records for the given batch IDs
2. Subtracts 1 day from the `date` field of each record
3. Updates the records in DynamoDB

Usage:
    python scripts/shift_feed_plan_dates.py
"""

from datetime import datetime, timedelta

import boto3

TABLE_NAME = "lmjm"
REGION = "sa-east-1"

BATCH_IDS = [
    "293de398-0cca-4613-b528-7af1010c64eb",
    "a067b5e3-4fe4-498f-b1af-adbd8124cf0d",
]


def main() -> None:
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    for batch_id in BATCH_IDS:
        print(f"\nProcessing batch: {batch_id}")

        # Query all FeedConsumptionPlan records for this batch
        response = table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={
                ":pk": batch_id,
                ":prefix": "FeedConsumptionPlan|",
            },
        )
        items = response["Items"]

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
                ExpressionAttributeValues={
                    ":pk": batch_id,
                    ":prefix": "FeedConsumptionPlan|",
                },
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response["Items"])

        print(f"  Found {len(items)} FeedConsumptionPlan records")

        if not items:
            continue

        # Show sample before/after
        sample = items[0]
        old_date = sample.get("date", "")
        if old_date:
            new_date = (datetime.strptime(old_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"  Sample: {old_date} → {new_date}")

        # Update each record
        updated = 0
        for item in items:
            old_date = item.get("date", "")
            if not old_date:
                continue

            new_date = (datetime.strptime(old_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

            table.update_item(
                Key={"pk": item["pk"], "sk": item["sk"]},
                UpdateExpression="SET #d = :new_date",
                ExpressionAttributeNames={"#d": "date"},
                ExpressionAttributeValues={":new_date": new_date},
            )
            updated += 1

        print(f"  Updated {updated} records (date shifted back by 1 day)")

    print("\nDone.")


if __name__ == "__main__":
    main()
