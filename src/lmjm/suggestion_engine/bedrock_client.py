"""Bedrock client for feed schedule suggestions.

Wraps the boto3 Bedrock Runtime invoke_model call with timeout configuration.
Errors (ReadTimeoutError, ConnectTimeoutError, ClientError) propagate to the caller.
"""

import json

import boto3
from botocore.config import Config

from lmjm.model.feed_schedule_suggestion import BEDROCK_MODEL_ID, BEDROCK_TIMEOUT_SECONDS


def invoke_bedrock(
    prompt: str,
    model_id: str = BEDROCK_MODEL_ID,
    timeout_seconds: int = BEDROCK_TIMEOUT_SECONDS,
) -> str:
    """Invoke Amazon Bedrock with the given prompt and return the text response.

    Creates a Bedrock Runtime client with the specified timeout, sends the
    prompt using the Anthropic Claude messages format, and extracts the
    text content from the response.

    Args:
        prompt: The text prompt to send to the model.
        model_id: The Bedrock model identifier. Defaults to BEDROCK_MODEL_ID
            from feed_schedule_suggestion constants.
        timeout_seconds: Read and connect timeout in seconds. Defaults to 60.

    Returns:
        The text content from the model response.

    Raises:
        botocore.exceptions.ReadTimeoutError: If the read times out.
        botocore.exceptions.ConnectTimeoutError: If the connection times out.
        botocore.exceptions.ClientError: If the Bedrock service returns an error.
    """
    config = Config(
        read_timeout=timeout_seconds,
        connect_timeout=timeout_seconds,
    )

    client = boto3.client(
        "bedrock-runtime",
        region_name="sa-east-1",
        config=config,
    )

    request_body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
    )

    response = client.invoke_model(
        modelId=model_id,
        body=request_body,
        contentType="application/json",
        accept="application/json",
    )

    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"]
