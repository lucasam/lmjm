"""Import FeedConsumptionTemplate entries from a CSV file into DynamoDB.

CSV format: sequence;expected_piglet_weight;expected_kg_per_animal
- Field separator: ;
- Decimal separator: , (comma)

Usage:
    python scripts/import_feed_consumption_template.py /Users/lucasam/Downloads/pesos.csv
"""

import csv
import sys
from decimal import Decimal

import boto3


def parse_decimal(value: str) -> Decimal:
    """Parse a decimal string using comma as the decimal separator."""
    return Decimal(value.strip().replace(",", "."))


def main(csv_path: str) -> None:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    table = dynamodb.Table("lmjm")

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        items = []
        for row in reader:
            if not row or not row[0].strip():
                continue
            sequence = int(row[0].strip())
            expected_piglet_weight = parse_decimal(row[1])
            expected_kg_per_animal = parse_decimal(row[2])
            items.append(
                {
                    "pk": "FEED_CONSUMPTION_TEMPLATE",
                    "sk": f"FeedConsumptionTemplate|{sequence}",
                    "sequence": sequence,
                    "expected_piglet_weight": expected_piglet_weight,
                    "expected_kg_per_animal": expected_kg_per_animal,
                }
            )

    print(f"Parsed {len(items)} entries from {csv_path}")
    print(f"  First: seq={items[0]['sequence']}, weight={items[0]['expected_piglet_weight']}, kg={items[0]['expected_kg_per_animal']}")
    print(f"  Last:  seq={items[-1]['sequence']}, weight={items[-1]['expected_piglet_weight']}, kg={items[-1]['expected_kg_per_animal']}")

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    print(f"Successfully inserted {len(items)} FeedConsumptionTemplate entries into DynamoDB.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <csv_path>")
        sys.exit(1)
    main(sys.argv[1])
