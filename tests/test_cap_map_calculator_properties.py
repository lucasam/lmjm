"""Property-based tests for CAP/MAP calculator.

Feature: batch-financial-result, Property 3: CAP/MAP formula correctness

**Validates: Requirements 10.1–10.8**
"""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from lmjm.cap_map_calculator import compute_cap_map

Q = Decimal("0.0001")


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to 4 decimal places."""
    return value.quantize(Q)


# --- Strategies ---

car_st = st.decimals(min_value=Decimal("1.5"), max_value=Decimal("3.0"), places=4, allow_nan=False, allow_infinity=False)
mar_st = st.decimals(min_value=Decimal("1.0"), max_value=Decimal("5.0"), places=4, allow_nan=False, allow_infinity=False)
avg_slaughter_weight_st = st.decimals(
    min_value=Decimal("70"), max_value=Decimal("120"), places=2, allow_nan=False, allow_infinity=False
)
avg_piglet_weight_st = st.decimals(
    min_value=Decimal("15"), max_value=Decimal("30"), places=2, allow_nan=False, allow_infinity=False
)
average_age_st = st.integers(min_value=80, max_value=130)


# --- Property Tests ---


# Feature: batch-financial-result, Property 3: CAP/MAP formula correctness
@given(
    car=car_st,
    mar=mar_st,
    avg_slaughter_weight=avg_slaughter_weight_st,
    avg_piglet_weight=avg_piglet_weight_st,
    average_age=average_age_st,
)
@settings(max_examples=200)
def test_cap_map_formula_correctness(
    car: Decimal,
    mar: Decimal,
    avg_slaughter_weight: Decimal,
    avg_piglet_weight: Decimal,
    average_age: int,
) -> None:
    """Property 3: CAP/MAP formula correctness.

    For any valid CAP/MAP inputs, calling compute_cap_map SHALL produce
    results where every variant matches the independent recomputation
    of the formula from the design document.

    **Validates: Requirements 10.1–10.8**
    """
    result = compute_cap_map(car, mar, avg_slaughter_weight, avg_piglet_weight, average_age)

    # Req 10.1: cap_1 = CAR - (avg_slaughter_weight - 85) * 0.0095 - (avg_piglet_weight - 22) * 0.0125
    expected_cap_1 = _q(
        car
        - (avg_slaughter_weight - Decimal("85")) * Decimal("0.0095")
        - (avg_piglet_weight - Decimal("22")) * Decimal("0.0125")
    )
    assert result["cap_1"] == expected_cap_1, f"cap_1: {result['cap_1']} != {expected_cap_1}"

    # Req 10.2: cap_2 = cap_1 - 0.03
    expected_cap_2 = _q(expected_cap_1 - Decimal("0.03"))
    assert result["cap_2"] == expected_cap_2, f"cap_2: {result['cap_2']} != {expected_cap_2}"

    # Req 10.3: cap_3 = cap_2 - 0.015
    expected_cap_3 = _q(expected_cap_2 - Decimal("0.015"))
    assert result["cap_3"] == expected_cap_3, f"cap_3: {result['cap_3']} != {expected_cap_3}"

    # Req 10.4: cap_4 = cap_1 - 0.015
    expected_cap_4 = _q(expected_cap_1 - Decimal("0.015"))
    assert result["cap_4"] == expected_cap_4, f"cap_4: {result['cap_4']} != {expected_cap_4}"

    # Req 10.5: map_1 = (130 - average_age) * 0.0183 + mar
    expected_map_1 = _q(Decimal(130 - average_age) * Decimal("0.0183") + mar)
    assert result["map_1"] == expected_map_1, f"map_1: {result['map_1']} != {expected_map_1}"

    # Req 10.6: map_2 = map_1 - 0.4
    expected_map_2 = _q(expected_map_1 - Decimal("0.4"))
    assert result["map_2"] == expected_map_2, f"map_2: {result['map_2']} != {expected_map_2}"

    # Req 10.7: All output Decimals have at most 4 decimal places
    for key, value in result.items():
        _, _, exponent = value.as_tuple()
        assert isinstance(exponent, int) and exponent >= -4, (
            f"{key} has more than 4 decimal places: {value}"
        )

    # Req 10.8: Determinism — calling twice with same inputs produces identical results
    result_2 = compute_cap_map(car, mar, avg_slaughter_weight, avg_piglet_weight, average_age)
    assert result == result_2, f"Non-deterministic: {result} != {result_2}"
