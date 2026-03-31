import os
from typing import Any

import boto3

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    email: str = event["request"]["userAttributes"]["email"]

    response = table.get_item(Key={"pk": "EMAIL_ALLOWLIST", "sk": email})
    item = response.get("Item")

    if not item:
        raise Exception(f"Email {email} is not in the allowlist")

    event["response"]["autoConfirmUser"] = True
    event["response"]["autoVerifyEmail"] = True

    return event
