"""Migrate legacy date-only records to datetime format.

Scans the DynamoDB lmjm table and upgrades:
- FeedTruckArrival.receive_date: YYYY-MM-DD → YYYY-MM-DDT00:00
- FeedBalance.measurement_date: YYYY-MM-DD → YYYY-MM-DDT00:00

Usage:
    TABLE_NAME=lmjm python scripts/migrate_datetime.py
"""

import logging
import os
import re

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LEGACY_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def migrate_date_value(value: str) -> str | None:
    """Return the migrated datetime string, or None if already migrated.

    For a legacy date string matching YYYY-MM-DD (no 'T'), appends T00:00.
    Strings already containing 'T' are considered already migrated and return None.

    Args:
        value: The date or datetime string to evaluate.

    Returns:
        The migrated string (YYYY-MM-DDT00:00) if migration is needed, or None.
    """
    if "T" in value:
        return None
    if LEGACY_DATE_RE.match(value):
        return f"{value}T00:00"
    return None


def main() -> None:
    table_name = os.environ.get("TABLE_NAME", "lmjm")
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    table = dynamodb.Table(table_name)

    scanned = 0
    arrival_updated = 0
    balance_updated = 0
    scan_kwargs: dict[str, object] = {}

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        scanned += len(items)

        for item in items:
            pk = item["pk"]
            sk = item["sk"]

            if sk.startswith("FeedTruckArrival|"):
                receive_date = item.get("receive_date", "")
                new_value = migrate_date_value(receive_date)
                if new_value is not None:
                    logger.info("Migrating FeedTruckArrival pk=%s sk=%s: %s → %s", pk, sk, receive_date, new_value)
                    table.update_item(
                        Key={"pk": pk, "sk": sk},
                        UpdateExpression="SET receive_date = :v",
                        ExpressionAttributeValues={":v": new_value},
                    )
                    arrival_updated += 1

            elif sk.startswith("FeedBalance|"):
                measurement_date = item.get("measurement_date", "")
                new_value = migrate_date_value(measurement_date)
                if new_value is not None:
                    logger.info("Migrating FeedBalance pk=%s sk=%s: %s → %s", pk, sk, measurement_date, new_value)
                    table.update_item(
                        Key={"pk": pk, "sk": sk},
                        UpdateExpression="SET measurement_date = :v",
                        ExpressionAttributeValues={":v": new_value},
                    )
                    balance_updated += 1

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    logger.info("Scan complete: %d records scanned", scanned)
    logger.info("FeedTruckArrival records updated: %d", arrival_updated)
    logger.info("FeedBalance records updated: %d", balance_updated)


if __name__ == "__main__":
    main()
