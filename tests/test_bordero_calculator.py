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
        # carcass_yield_factor is now the dressing ratio (pig_carcass_weight / pig_weight)
        assert result.carcass_yield_factor == Decimal("0.7268")
        # piglet_carcass_weight = piglet_weight * 0.656807 - 1.315747
        assert result.piglet_carcass_weight == Decimal("13.4624")
        # pig_carcass_weight = (pig_weight - 6.629) / 1.289
        assert result.pig_carcass_weight == Decimal("76.3157")
        assert result.total_piglet_carcass == Decimal("13462.4105")
        assert result.total_pig_carcass == Decimal("74026.2762")
        assert result.total_carcass_produced == Decimal("60563.8657")
        assert result.real_conversion == Decimal("0.8256")
        # piglet_adjustment = (22 - piglet_weight) * 0.0125
        assert result.piglet_adjustment == Decimal("-0.0062")
        # carcass_adjustment = (85 - pig_carcass_weight) * 0.0095
        assert result.carcass_adjustment == Decimal("0.0825")
        assert result.adjusted_conversion == Decimal("0.9018")
        assert result.real_mortality_pct == Decimal("3.0000")
        # adjusted_mortality = (130 - days_housed) * 0.0183 + real_mortality_pct
        assert result.adjusted_mortality == Decimal("3.1830")
        # mortality_adjustment_pct = (map - adjusted_mortality) / 5
        assert result.mortality_adjustment_pct == Decimal("0.0634")
        # conversion_adjustment_pct = (cap - adjusted_conversion) * 10
        assert result.conversion_adjustment_pct == Decimal("14.4820")
        assert result.integrator_pct == Decimal("19.6454")
        assert result.gross_income == Decimal("89235.1025")
        # net_income = gross_income * 0.985
        assert result.net_income == Decimal("87896.5760")
        assert result.daily_weight_gain == Decimal("0.6875")
        assert result.daily_carcass_gain == Decimal("0.5238")
        assert result.gross_income_per_pig == Decimal("91.9950")
        assert result.net_income_per_pig == Decimal("90.6150")
