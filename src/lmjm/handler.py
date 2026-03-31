from typing import Any

from lmjm.util.response import respond


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return respond(body={"message": "ok"})
