import json
from decimal import Decimal
from typing import Any, Optional


def _default_serializer(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def respond(
    status_code: int = 200,
    body: Optional[Any] = None,
    error: Optional[str] = None,
) -> dict[str, Any]:
    """Build an API Gateway proxy response with CORS headers."""
    if error:
        payload = json.dumps({"message": error})
    elif body is not None:
        payload = json.dumps(body, default=_default_serializer)
    else:
        payload = json.dumps({})

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": payload,
    }
