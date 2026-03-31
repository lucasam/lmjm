"""Unit tests for Pre Sign-up Lambda handler.

Validates:
- Requirement 32.1: Extract email from event request user attributes
- Requirement 32.3: Allowlisted email returns autoConfirmUser=True, autoVerifyEmail=True
- Requirement 32.4: Non-allowlisted email raises error rejecting sign-up
- Requirement 32.5: Handle external IdP (Google) trigger source
"""

import os
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")


def _create_table() -> Any:
    dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
    table = dynamodb.create_table(
        TableName="lmjm",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return table


def _make_event(email: str, trigger_source: str = "PreSignUp_SignUp") -> dict[str, Any]:
    return {
        "version": "1",
        "triggerSource": trigger_source,
        "region": "sa-east-1",
        "userPoolId": "sa-east-1_test",
        "userName": "test-user",
        "callerContext": {"awsSdkVersion": "1", "clientId": "test-client"},
        "request": {
            "userAttributes": {"email": email},
        },
        "response": {
            "autoConfirmUser": False,
            "autoVerifyEmail": False,
        },
    }


@mock_aws
def test_allowlisted_email_returns_auto_confirm_and_verify() -> None:
    """Requirement 32.3: Allowlisted email sets autoConfirmUser and autoVerifyEmail to True."""
    table = _create_table()
    table.put_item(Item={"pk": "EMAIL_ALLOWLIST", "sk": "allowed@gmail.com"})

    import importlib

    import lmjm.pre_signup as mod

    importlib.reload(mod)

    event = _make_event("allowed@gmail.com")
    result = mod.lambda_handler(event, None)

    assert result["response"]["autoConfirmUser"] is True
    assert result["response"]["autoVerifyEmail"] is True


@mock_aws
def test_non_allowlisted_email_raises_error() -> None:
    """Requirement 32.4: Non-allowlisted email raises error to reject sign-up."""
    _create_table()

    import importlib

    import lmjm.pre_signup as mod

    importlib.reload(mod)

    event = _make_event("notallowed@gmail.com")
    with pytest.raises(Exception, match="Email notallowed@gmail.com is not in the allowlist"):
        mod.lambda_handler(event, None)


@mock_aws
def test_external_idp_trigger_source_with_allowlisted_email() -> None:
    """Requirement 32.5: Handle external IdP (Google) Pre Sign-up trigger source."""
    table = _create_table()
    table.put_item(Item={"pk": "EMAIL_ALLOWLIST", "sk": "google@gmail.com"})

    import importlib

    import lmjm.pre_signup as mod

    importlib.reload(mod)

    event = _make_event("google@gmail.com", trigger_source="PreSignUp_ExternalProvider")
    result = mod.lambda_handler(event, None)

    assert result["response"]["autoConfirmUser"] is True
    assert result["response"]["autoVerifyEmail"] is True


@mock_aws
def test_external_idp_trigger_source_with_non_allowlisted_email() -> None:
    """Requirement 32.5: External IdP with non-allowlisted email still raises error."""
    _create_table()

    import importlib

    import lmjm.pre_signup as mod

    importlib.reload(mod)

    event = _make_event("unknown@gmail.com", trigger_source="PreSignUp_ExternalProvider")
    with pytest.raises(Exception, match="Email unknown@gmail.com is not in the allowlist"):
        mod.lambda_handler(event, None)


@mock_aws
def test_event_structure_preserved_on_success() -> None:
    """Requirement 32.1: Email extracted from event and full event returned."""
    table = _create_table()
    table.put_item(Item={"pk": "EMAIL_ALLOWLIST", "sk": "user@gmail.com"})

    import importlib

    import lmjm.pre_signup as mod

    importlib.reload(mod)

    event = _make_event("user@gmail.com")
    result = mod.lambda_handler(event, None)

    assert result["request"]["userAttributes"]["email"] == "user@gmail.com"
    assert result["userName"] == "test-user"
    assert result["triggerSource"] == "PreSignUp_SignUp"
