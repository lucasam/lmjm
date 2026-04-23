"""Unit tests for Bedrock client.

Validates: Requirements 8.1, 8.3, 8.4
"""

import io
import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from lmjm.suggestion_engine.bedrock_client import invoke_bedrock


class TestInvokeBedrockHappyPath:
    """Happy path: invoke_model returns a valid response with text content."""

    def test_returns_text_from_valid_response(self):
        response_body_dict = {"content": [{"text": "Move schedule from 2025-01-01 with Feed A to 2025-01-05"}]}
        response_bytes = json.dumps(response_body_dict).encode("utf-8")
        body_stream = io.BytesIO(response_bytes)

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": body_stream}

        with patch(
            "lmjm.suggestion_engine.bedrock_client.boto3.client",
            return_value=mock_client,
        ):
            result = invoke_bedrock("Test prompt")

        assert result == "Move schedule from 2025-01-01 with Feed A to 2025-01-05"


class TestInvokeBedrockTimeoutErrors:
    """Timeout errors propagate to the caller."""

    def test_read_timeout_error_propagates(self):
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = botocore.exceptions.ReadTimeoutError(
            endpoint_url="https://bedrock.us-east-1.amazonaws.com"
        )

        with patch(
            "lmjm.suggestion_engine.bedrock_client.boto3.client",
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ReadTimeoutError):
                invoke_bedrock("Test prompt")

    def test_connect_timeout_error_propagates(self):
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = botocore.exceptions.ConnectTimeoutError(
            endpoint_url="https://bedrock.us-east-1.amazonaws.com"
        )

        with patch(
            "lmjm.suggestion_engine.bedrock_client.boto3.client",
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ConnectTimeoutError):
                invoke_bedrock("Test prompt")


class TestInvokeBedrockServiceError:
    """Service errors (ClientError) propagate to the caller."""

    def test_client_error_propagates(self):
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = botocore.exceptions.ClientError(
            error_response={
                "Error": {
                    "Code": "ThrottlingException",
                    "Message": "Rate exceeded",
                }
            },
            operation_name="InvokeModel",
        )

        with patch(
            "lmjm.suggestion_engine.bedrock_client.boto3.client",
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                invoke_bedrock("Test prompt")
