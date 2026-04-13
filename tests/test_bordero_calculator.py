"""Unit tests for Borderô calculator edge cases.

Requirements: 2.17, 2.18, 2.19
"""

from decimal import Decimal

import pytest

from lmjm.bordero_calculator import BorderoInput, calculate_bordero


def _make_input(**overrides: object) -> BorderoInput:
    """Create a valid BorderoInput with sensible defaults, applying overrides."""
    defaults = dict(
        housed_count=1000,
        mortality_count=30,
        piglet_weight=Decimal("22.5"),
        pig_weight=Decimal("105.0"),
        total_feed=Decimal("50000"),
        days_housed=120,
        cap=Decimal("2.35"),
        map_value=Decimal("3.5"),
        price_per_kg=Decimal("7.50"),
        piglet_adjustment=Decimal("-0.02"),
        carcass_adjustment=Decimal("0.01"),
    )
    defaults.update(overrides)
    return BorderoInput(**defaults)  # type: ignore[arg-type]


class TestBorderoValidationErrors:
    """Validates: Requirements 2.17, 2.18, 2.19"""

    def test_housed_count_zero_raises_value_error(self) -> None:
        inp = _make_input(housed_count=0)
        with pytest.raises(ValueError, match="Housed count must be greater than zero"):
            calculate_bordero(inp)

    def test_days_housed_zero_raises_value_error(self) -> None:
        inp = _make_input(days_housed=0)
        with pytest.raises(ValueError, match="Days housed must be positive"):
            calculate_bordero(inp)

    def test_total_carcass_produced_non_positive_raises_value_error(self) -> None:
        # pig_weight very close to piglet_weight → total_carcass_produced ≤ 0
        inp = _make_input(pig_weight=Decimal("22.5"), piglet_weight=Decimal("22.5"), mortality_count=30)
        with pytest.raises(ValueError, match="Total carcass produced must be positive"):
            calculate_bordero(inp)


class TestBorderoKnownExample:
    """Test a known spreadsheet example with expected outputs."""

    def test_known_spreadsheet_values(self) -> None:
        inp = _make_input()
        result = calculate_bordero(inp)

        assert result.pig_count == 970
        assert result.carcass_yield_factor == Decimal("76.3157")
        assert result.piglet_carcass_weight == Decimal("1717.1032")
        assert result.pig_carcass_weight == Decimal("8013.1485")
        assert result.total_piglet_carcass == Decimal("1717103.2000")
        assert result.total_pig_carcass == Decimal("7772754.0450")
        assert result.total_carcass_produced == Decimal("6055650.8450")
        assert result.real_conversion == Decimal("0.0083")
        assert result.adjusted_conversion == Decimal("-0.0017")
        assert result.real_mortality_pct == Decimal("3.0000")
        assert result.adjusted_mortality_pct == Decimal("3.0000")
        assert result.mortality_adjustment_pct == Decimal("0.5000")
        assert result.conversion_adjustment_pct == Decimal("2.3517")
        assert result.integrator_pct == Decimal("7.9517")
        assert result.gross_income == Decimal("3611453.9118")
        assert result.net_income == Decimal("3611453.9118")
        assert result.daily_weight_gain == Decimal("0.6875")
        assert result.daily_carcass_gain == Decimal("52.4670")
        assert result.gross_income_per_pig == Decimal("3723.1484")
        assert result.net_income_per_pig == Decimal("3723.1484")
