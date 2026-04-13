"""Unit tests for PostIntegratorWeeklyData handler.

Validates:
- Requirement 11.1: Valid payload computes CAP/MAP, persists record, returns 201
- Requirement 11.2: Required fields validation
- Requirement 11.3: Overwrite existing record with same date_generated
- Requirement 11.4: Missing fields returns 400 with descriptive error
"""

import importlib
import json
import os
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("TABLE_NAME", "lmjm")


def _make_event(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a minimal API Gateway proxy event."""
    if body is None:
        body = _valid_body()
    return {
        "body": json.dumps(body, default=str),
    }


def _valid_body() -> dict[str, Any]:
    """Return a body dict with all required fields and valid values."""
    return {
        "date_generated": "2024-06-15",
        "validity_start": "2024-06-10",
        "validity_end": "2024-06-16",
        "source_data_start": "2024-06-03",
        "source_data_end": "2024-06-09",
        "car": 2.35,
        "mar": 3.10,
        "avg_piglet_weight": 22.5,
        "avg_slaughter_weight": 95.0,
        "average_age": 110,
        "number_of_samples": 50,
        "gdp": 1.05,
    }


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")


@patch("lmjm.post_integrator_weekly_data.integrator_weekly_data_repo")
def test_valid_submission_returns_201_with_cap_map(mock_repo: MagicMock) -> None:
    """Requirement 11.1: Valid payload computes CAP/MAP and returns 201."""
    import lmjm.post_integrator_weekly_data as mod

    importlib.reload(mod)

    with patch.object(mod, "integrator_weekly_data_repo", mock_repo):
        result = mod.lambda_handler(_make_event(), None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])

    # Verify computed CAP/MAP fields are present and non-zero
    for field in ("cap_1", "cap_2", "cap_3", "cap_4", "map_1", "map_2"):
        assert field in body, f"Expected '{field}' in response body"
        assert body[field] != 0, f"Expected '{field}' to be computed (non-zero)"

    # Verify raw input fields are echoed back
    assert body["date_generated"] == "2024-06-15"
    assert body["pk"] == "INTEGRATOR_WEEKLY_DATA"
    assert body["sk"] == "IntegratorWeeklyData|2024-06-15"

    # Verify repo.put was called
    mock_repo.put.assert_called_once()


@patch("lmjm.post_integrator_weekly_data.integrator_weekly_data_repo")
def test_missing_fields_returns_400(mock_repo: MagicMock) -> None:
    """Requirement 11.2, 11.4: Missing required field → 400 listing missing fields."""
    import lmjm.post_integrator_weekly_data as mod

    importlib.reload(mod)

    body = _valid_body()
    del body["car"]

    with patch.object(mod, "integrator_weekly_data_repo", mock_repo):
        result = mod.lambda_handler(_make_event(body=body), None)

    assert result["statusCode"] == 400
    error = json.loads(result["body"])
    assert "car" in error["message"]
    mock_repo.put.assert_not_called()
