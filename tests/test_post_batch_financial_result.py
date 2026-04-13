"""Unit tests for PostBatchFinancialResult handler.

Validates:
- Requirement 4.1: Valid payload persists record with correct pk/sk, returns 201
- Requirement 4.2: Missing required fields returns 400 listing missing fields
- Requirement 4.3: Calculator invoked to compute derived fields
- Requirement 4.4: Overwrite existing record of same type
- Requirement 4.5: Missing fields error is descriptive
- Requirement 4.6: Batch not found returns 404
- Requirement 4.7: Calculator validation error returns 400
- Requirement 6.6: Actual type deletes existing simulation
"""

import importlib
import json
import os
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lmjm.model import Batch

os.environ.setdefault("TABLE_NAME", "lmjm")


def _make_event(batch_id: str = "batch-1", body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a minimal API Gateway proxy event."""
    if body is None:
        body = _valid_body()
    return {
        "pathParameters": {"batch_id": batch_id},
        "body": json.dumps(body, default=str),
    }


def _valid_body() -> dict[str, Any]:
    """Return a body dict with all required fields and valid values."""
    return {
        "type": "simulation",
        "housed_count": 1000,
        "mortality_count": 50,
        "total_feed": 50000,
        "piglet_weight": 22,
        "pig_weight": 100,
        "days_housed": 120,
        "cap": 2.5,
        "map_value": 3.0,
        "price_per_kg": 5.5,
        "piglet_adjustment": 0.01,
        "carcass_adjustment": -0.02,
    }


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABLE_NAME", "lmjm")



@patch("lmjm.post_batch_financial_result.batch_financial_result_repo")
@patch("lmjm.post_batch_financial_result.batch_repo")
def test_valid_submission_returns_201(mock_batch_repo: MagicMock, mock_bfr_repo: MagicMock) -> None:
    """Requirement 4.1, 4.3: Valid payload → 201 with computed fields."""
    mock_batch_repo.get.return_value = Batch(pk="batch-1")

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        result = mod.lambda_handler(_make_event(), None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])

    # Verify computed fields are present
    assert body["pig_count"] == 950  # 1000 - 50
    assert "carcass_yield_factor" in body
    assert "gross_income" in body
    assert "integrator_pct" in body
    assert "daily_weight_gain" in body
    assert body["type"] == "simulation"
    assert body["pk"] == "batch-1"
    assert body["sk"] == "BatchFinancialResult|simulation"

    # Verify repo.put was called
    mock_bfr_repo.put.assert_called_once()


@patch("lmjm.post_batch_financial_result.batch_financial_result_repo")
@patch("lmjm.post_batch_financial_result.batch_repo")
def test_missing_fields_returns_400(mock_batch_repo: MagicMock, mock_bfr_repo: MagicMock) -> None:
    """Requirement 4.2, 4.5: Missing required field → 400 listing missing fields."""
    mock_batch_repo.get.return_value = Batch(pk="batch-1")

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    body = _valid_body()
    del body["pig_weight"]

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        result = mod.lambda_handler(_make_event(body=body), None)

    assert result["statusCode"] == 400
    error = json.loads(result["body"])
    assert "pig_weight" in error["message"]
    mock_bfr_repo.put.assert_not_called()


@patch("lmjm.post_batch_financial_result.batch_financial_result_repo")
@patch("lmjm.post_batch_financial_result.batch_repo")
def test_batch_not_found_returns_404(mock_batch_repo: MagicMock, mock_bfr_repo: MagicMock) -> None:
    """Requirement 4.6: Non-existent batch → 404."""
    mock_batch_repo.get.return_value = None

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        result = mod.lambda_handler(_make_event(), None)

    assert result["statusCode"] == 404
    error = json.loads(result["body"])
    assert error["message"] == "Batch not found"
    mock_bfr_repo.put.assert_not_called()


@patch("lmjm.post_batch_financial_result.batch_financial_result_repo")
@patch("lmjm.post_batch_financial_result.batch_repo")
def test_calculator_error_returns_400(mock_batch_repo: MagicMock, mock_bfr_repo: MagicMock) -> None:
    """Requirement 4.7: Calculator ValueError (housed_count=0) → 400."""
    mock_batch_repo.get.return_value = Batch(pk="batch-1")

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    body = _valid_body()
    body["housed_count"] = 0

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        result = mod.lambda_handler(_make_event(body=body), None)

    assert result["statusCode"] == 400
    error = json.loads(result["body"])
    assert "Housed count must be greater than zero" in error["message"]
    mock_bfr_repo.put.assert_not_called()


@patch("lmjm.post_batch_financial_result.batch_financial_result_repo")
@patch("lmjm.post_batch_financial_result.batch_repo")
def test_actual_type_deletes_simulation(mock_batch_repo: MagicMock, mock_bfr_repo: MagicMock) -> None:
    """Requirement 6.6: Saving actual deletes existing simulation."""
    mock_batch_repo.get.return_value = Batch(pk="batch-1")

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    body = _valid_body()
    body["type"] = "actual"

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        result = mod.lambda_handler(_make_event(body=body), None)

    assert result["statusCode"] == 201
    mock_bfr_repo.delete.assert_called_once_with("batch-1", "simulation")
    mock_bfr_repo.put.assert_called_once()


@patch("lmjm.post_batch_financial_result.batch_financial_result_repo")
@patch("lmjm.post_batch_financial_result.batch_repo")
def test_overwrite_existing_record(mock_batch_repo: MagicMock, mock_bfr_repo: MagicMock) -> None:
    """Requirement 4.4: PUT overwrites existing record of same type."""
    mock_batch_repo.get.return_value = Batch(pk="batch-1")

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        # First submission
        mod.lambda_handler(_make_event(), None)
        # Second submission (overwrite)
        result = mod.lambda_handler(_make_event(), None)

    assert result["statusCode"] == 201
    # put is called twice — once per submission (overwrite semantics)
    assert mock_bfr_repo.put.call_count == 2


@patch("lmjm.post_batch_financial_result.batch_financial_result_repo")
@patch("lmjm.post_batch_financial_result.batch_repo")
def test_invalid_type_returns_400(mock_batch_repo: MagicMock, mock_bfr_repo: MagicMock) -> None:
    """Requirement 4.1: type must be 'simulation' or 'actual', else 400."""
    mock_batch_repo.get.return_value = Batch(pk="batch-1")

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    body = _valid_body()
    body["type"] = "invalid_type"

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        result = mod.lambda_handler(_make_event(body=body), None)

    assert result["statusCode"] == 400
    error = json.loads(result["body"])
    assert "simulation" in error["message"]
    assert "actual" in error["message"]
    mock_bfr_repo.put.assert_not_called()


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


REQUIRED_FIELDS = [
    "type",
    "housed_count",
    "mortality_count",
    "total_feed",
    "piglet_weight",
    "pig_weight",
    "days_housed",
    "cap",
    "map_value",
    "price_per_kg",
    "piglet_adjustment",
    "carcass_adjustment",
]


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    fields_to_remove=st.lists(
        st.sampled_from(REQUIRED_FIELDS),
        min_size=1,
        max_size=len(REQUIRED_FIELDS),
        unique=True,
    )
)
def test_missing_required_fields_returns_400_property(fields_to_remove: list[str]) -> None:
    """Property 6: Missing required fields validation.

    **Validates: Requirements 4.2, 4.5**

    For any non-empty subset of required fields that is removed from a valid body,
    the handler returns 400 and the error message lists every missing field.

    Tag: Feature: batch-financial-result, Property 6: Missing required fields validation
    """
    import importlib

    import lmjm.post_batch_financial_result as mod

    importlib.reload(mod)

    mock_batch_repo = MagicMock()
    mock_batch_repo.get.return_value = Batch(pk="batch-1")
    mock_bfr_repo = MagicMock()

    body = _valid_body()
    for field in fields_to_remove:
        del body[field]

    event = _make_event(body=body)

    with (
        patch.object(mod, "batch_repo", mock_batch_repo),
        patch.object(mod, "batch_financial_result_repo", mock_bfr_repo),
    ):
        result = mod.lambda_handler(event, None)

    assert result["statusCode"] == 400, (
        f"Expected 400 when removing {fields_to_remove}, got {result['statusCode']}"
    )

    error_body = json.loads(result["body"])
    error_message = error_body["message"]

    for field in fields_to_remove:
        assert field in error_message, (
            f"Missing field '{field}' not mentioned in error: {error_message}"
        )

    mock_bfr_repo.put.assert_not_called()
