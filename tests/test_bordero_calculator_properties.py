"""Property-based tests for Borderô calculator.

Feature: batch-financial-result

**Validates: Requirements 2.1–2.16, 2.20**
"""

from decimal import Decimal

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from lmjm.bordero_calculator import BorderoInput, calculate_bordero

Q = Decimal("0.0001")


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to 4 decimal places."""
    return value.quantize(Q)


# --- Strategies ---

housed_count_st = st.integers(min_value=100, max_value=5000)
pig_weight_st = st.decimals(min_value=80, max_value=130, places=2, allow_nan=False, allow_infinity=False)
piglet_weight_st = st.decimals(min_value=5, max_value=30, places=2, allow_nan=False, allow_infinity=False)
total_feed_st = st.decimals(min_value=10000, max_value=100000, places=2, allow_nan=False, allow_infinity=False)
days_housed_st = st.integers(min_value=90, max_value=180)
cap_st = st.decimals(min_value=Decimal("1.5"), max_value=Decimal("3.0"), places=4, allow_nan=False, allow_infinity=False)
map_value_st = st.decimals(min_value=Decimal("1.0"), max_value=Decimal("5.0"), places=4, allow_nan=False, allow_infinity=False)
price_per_kg_st = st.decimals(min_value=Decimal("3.0"), max_value=Decimal("10.0"), places=4, allow_nan=False, allow_infinity=False)
piglet_adj_st = st.decimals(min_value=Decimal("-0.5"), max_value=Decimal("0.5"), places=4, allow_nan=False, allow_infinity=False)
carcass_adj_st = st.decimals(min_value=Decimal("-0.5"), max_value=Decimal("0.5"), places=4, allow_nan=False, allow_infinity=False)


@st.composite
def bordero_input_st(draw: st.DrawFn) -> BorderoInput:
    """Generate a valid BorderoInput that will not trigger ValueError."""
    housed_count = draw(housed_count_st)
    # mortality_count must be 0..housed_count-1 so pig_count > 0
    mortality_count = draw(st.integers(min_value=0, max_value=housed_count - 1))
    piglet_weight = draw(piglet_weight_st)
    pig_weight = draw(pig_weight_st)
    total_feed = draw(total_feed_st)
    days_housed = draw(days_housed_st)
    cap = draw(cap_st)
    map_value = draw(map_value_st)
    price_per_kg = draw(price_per_kg_st)
    piglet_adjustment = draw(piglet_adj_st)
    carcass_adjustment = draw(carcass_adj_st)

    return BorderoInput(
        housed_count=housed_count,
        mortality_count=mortality_count,
        piglet_weight=piglet_weight,
        pig_weight=pig_weight,
        total_feed=total_feed,
        days_housed=days_housed,
        cap=cap,
        map_value=map_value,
        price_per_kg=price_per_kg,
        piglet_adjustment=piglet_adjustment,
        carcass_adjustment=carcass_adjustment,
    )


# --- Property Tests ---


# Feature: batch-financial-result, Property 1: Borderô formula correctness
@given(inp=bordero_input_st())
@settings(max_examples=200)
def test_bordero_formula_correctness(inp: BorderoInput) -> None:
    """Property 1: Borderô formula correctness.

    For any valid BorderoInput, calling calculate_bordero SHALL produce a
    BatchFinancialResult where every computed field matches the independent
    recomputation of the formula from the design document.

    **Validates: Requirements 2.1–2.16, 2.20**
    """
    # Pre-compute total_carcass_produced to filter out invalid inputs
    cyf = _q((inp.pig_weight - Decimal("6.629")) / Decimal("1.289"))
    pcw = _q(inp.piglet_weight * cyf)
    pig_cw = _q(inp.pig_weight * cyf)
    pig_count = inp.housed_count - inp.mortality_count
    tcp = _q(pig_cw * pig_count) - _q(pcw * inp.housed_count)
    assume(tcp > 0)

    result = calculate_bordero(inp)

    # Req 2.10: pig_count
    expected_pig_count = inp.housed_count - inp.mortality_count
    assert result.pig_count == expected_pig_count, (
        f"pig_count: {result.pig_count} != {expected_pig_count}"
    )

    # Req 2.1: carcass_yield_factor
    expected_cyf = _q((inp.pig_weight - Decimal("6.629")) / Decimal("1.289"))
    assert result.carcass_yield_factor == expected_cyf, (
        f"carcass_yield_factor: {result.carcass_yield_factor} != {expected_cyf}"
    )

    # Req 2.2: piglet_carcass_weight
    expected_pcw = _q(inp.piglet_weight * expected_cyf)
    assert result.piglet_carcass_weight == expected_pcw, (
        f"piglet_carcass_weight: {result.piglet_carcass_weight} != {expected_pcw}"
    )

    # Req 2.3: pig_carcass_weight
    expected_pig_cw = _q(inp.pig_weight * expected_cyf)
    assert result.pig_carcass_weight == expected_pig_cw, (
        f"pig_carcass_weight: {result.pig_carcass_weight} != {expected_pig_cw}"
    )

    # Req 2.4: total_piglet_carcass
    expected_tpc = _q(expected_pcw * inp.housed_count)
    assert result.total_piglet_carcass == expected_tpc, (
        f"total_piglet_carcass: {result.total_piglet_carcass} != {expected_tpc}"
    )

    # Req 2.5: total_pig_carcass
    expected_tpigc = _q(expected_pig_cw * expected_pig_count)
    assert result.total_pig_carcass == expected_tpigc, (
        f"total_pig_carcass: {result.total_pig_carcass} != {expected_tpigc}"
    )

    # Req 2.6: total_carcass_produced
    expected_tcp = _q(expected_tpigc - expected_tpc)
    assert result.total_carcass_produced == expected_tcp, (
        f"total_carcass_produced: {result.total_carcass_produced} != {expected_tcp}"
    )

    # Req 2.7: real_conversion
    expected_rc = _q(inp.total_feed / expected_tcp)
    assert result.real_conversion == expected_rc, (
        f"real_conversion: {result.real_conversion} != {expected_rc}"
    )

    # Req 2.8: adjusted_conversion
    expected_ac = _q(expected_rc + inp.piglet_adjustment + inp.carcass_adjustment)
    assert result.adjusted_conversion == expected_ac, (
        f"adjusted_conversion: {result.adjusted_conversion} != {expected_ac}"
    )

    # Req 2.9: real_mortality_pct
    expected_rmp = _q(Decimal(inp.mortality_count) / Decimal(inp.housed_count) * 100)
    assert result.real_mortality_pct == expected_rmp, (
        f"real_mortality_pct: {result.real_mortality_pct} != {expected_rmp}"
    )

    # Req 2.11: daily_weight_gain
    expected_dwg = _q((inp.pig_weight - inp.piglet_weight) / Decimal(inp.days_housed))
    assert result.daily_weight_gain == expected_dwg, (
        f"daily_weight_gain: {result.daily_weight_gain} != {expected_dwg}"
    )

    # Req 2.12: daily_carcass_gain
    expected_dcg = _q((expected_pig_cw - expected_pcw) / Decimal(inp.days_housed))
    assert result.daily_carcass_gain == expected_dcg, (
        f"daily_carcass_gain: {result.daily_carcass_gain} != {expected_dcg}"
    )

    # Req 2.13: integrator_pct
    expected_ip = _q(
        Decimal("5.1") + result.mortality_adjustment_pct + result.conversion_adjustment_pct
    )
    assert result.integrator_pct == expected_ip, (
        f"integrator_pct: {result.integrator_pct} != {expected_ip}"
    )

    # Req 2.14: gross_income
    expected_gi = _q(expected_tcp * inp.price_per_kg * expected_ip / 100)
    assert result.gross_income == expected_gi, (
        f"gross_income: {result.gross_income} != {expected_gi}"
    )

    # Req 2.20: All Decimal output fields have at most 4 decimal places
    decimal_fields = [
        result.carcass_yield_factor, result.piglet_carcass_weight,
        result.pig_carcass_weight, result.total_piglet_carcass,
        result.total_pig_carcass, result.total_carcass_produced,
        result.real_conversion, result.adjusted_conversion,
        result.real_mortality_pct, result.adjusted_mortality_pct,
        result.daily_weight_gain, result.daily_carcass_gain,
        result.mortality_adjustment_pct, result.conversion_adjustment_pct,
        result.integrator_pct, result.gross_income, result.net_income,
        result.gross_income_per_pig, result.net_income_per_pig,
    ]
    for field_val in decimal_fields:
        _, _, exponent = field_val.as_tuple()
        assert isinstance(exponent, int) and exponent >= -4, (
            f"Decimal field has more than 4 decimal places: {field_val}"
        )


# Feature: batch-financial-result, Property 2: Borderô round-trip serialization
@given(inp=bordero_input_st())
@settings(max_examples=200)
def test_bordero_round_trip_serialization(inp: BorderoInput) -> None:
    """Property 2: Borderô round-trip serialization.

    For any valid BorderoInput, computing the Borderô via calculate_bordero,
    then serializing with serialize_to_dict and deserializing with
    load_data_class_from_dict produces an equivalent BatchFinancialResult
    (all fields match).

    **Validates: Requirements 2.21**
    """
    from lmjm.model.batch_financial_result import BatchFinancialResult
    from lmjm.util.marshmallow_serializer import load_data_class_from_dict, serialize_to_dict

    # Filter out inputs where total_carcass_produced <= 0
    cyf = _q((inp.pig_weight - Decimal("6.629")) / Decimal("1.289"))
    pcw = _q(inp.piglet_weight * cyf)
    pig_cw = _q(inp.pig_weight * cyf)
    pig_count = inp.housed_count - inp.mortality_count
    tcp = _q(pig_cw * pig_count) - _q(pcw * inp.housed_count)
    assume(tcp > 0)

    original = calculate_bordero(inp)
    serialized = serialize_to_dict(original)
    deserialized = load_data_class_from_dict(serialized, BatchFinancialResult)

    assert deserialized.pk == original.pk
    assert deserialized.sk == original.sk
    assert deserialized.housed_count == original.housed_count
    assert deserialized.mortality_count == original.mortality_count
    assert deserialized.pig_count == original.pig_count
    assert deserialized.piglet_weight == original.piglet_weight
    assert deserialized.pig_weight == original.pig_weight
    assert deserialized.total_feed == original.total_feed
    assert deserialized.days_housed == original.days_housed
    assert deserialized.cap == original.cap
    assert deserialized.map_value == original.map_value
    assert deserialized.price_per_kg == original.price_per_kg
    assert deserialized.gross_integrator_pct == original.gross_integrator_pct
    assert deserialized.carcass_yield_factor == original.carcass_yield_factor
    assert deserialized.piglet_carcass_weight == original.piglet_carcass_weight
    assert deserialized.pig_carcass_weight == original.pig_carcass_weight
    assert deserialized.total_piglet_carcass == original.total_piglet_carcass
    assert deserialized.total_pig_carcass == original.total_pig_carcass
    assert deserialized.total_carcass_produced == original.total_carcass_produced
    assert deserialized.real_conversion == original.real_conversion
    assert deserialized.piglet_adjustment == original.piglet_adjustment
    assert deserialized.carcass_adjustment == original.carcass_adjustment
    assert deserialized.adjusted_conversion == original.adjusted_conversion
    assert deserialized.daily_weight_gain == original.daily_weight_gain
    assert deserialized.daily_carcass_gain == original.daily_carcass_gain
    assert deserialized.real_mortality_pct == original.real_mortality_pct
    assert deserialized.adjusted_mortality_pct == original.adjusted_mortality_pct
    assert deserialized.mortality_adjustment_pct == original.mortality_adjustment_pct
    assert deserialized.conversion_adjustment_pct == original.conversion_adjustment_pct
    assert deserialized.integrator_pct == original.integrator_pct
    assert deserialized.gross_income == original.gross_income
    assert deserialized.net_income == original.net_income
    assert deserialized.gross_income_per_pig == original.gross_income_per_pig
    assert deserialized.net_income_per_pig == original.net_income_per_pig
