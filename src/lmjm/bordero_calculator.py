import dataclasses
from decimal import Decimal

from lmjm.model.batch_financial_result import BatchFinancialResult

Q = Decimal("0.0001")

GROSS_INTEGRATOR_PCT = Decimal("5.1")


@dataclasses.dataclass
class BorderoInput:
    housed_count: int
    mortality_count: int
    piglet_weight: Decimal
    pig_weight: Decimal
    total_feed: Decimal
    days_housed: int
    cap: Decimal
    map_value: Decimal
    price_per_kg: Decimal
    piglet_adjustment: Decimal
    carcass_adjustment: Decimal


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to 4 decimal places."""
    return value.quantize(Q)


def calculate_bordero(inp: BorderoInput) -> BatchFinancialResult:
    """Pure function: computes all derived Borderô fields. Raises ValueError on invalid input."""
    if inp.housed_count == 0:
        raise ValueError("Housed count must be greater than zero")
    if inp.days_housed <= 0:
        raise ValueError("Days housed must be positive")

    # Farm data
    pig_count = inp.housed_count - inp.mortality_count

    # Carcass calculations
    carcass_yield_factor = _q((inp.pig_weight - Decimal("6.629")) / Decimal("1.289"))
    piglet_carcass_weight = _q(inp.piglet_weight * carcass_yield_factor)
    pig_carcass_weight = _q(inp.pig_weight * carcass_yield_factor)
    total_piglet_carcass = _q(piglet_carcass_weight * inp.housed_count)
    total_pig_carcass = _q(pig_carcass_weight * pig_count)
    total_carcass_produced = _q(total_pig_carcass - total_piglet_carcass)

    if total_carcass_produced <= 0:
        raise ValueError("Total carcass produced must be positive")

    # Feed conversion
    real_conversion = _q(inp.total_feed / total_carcass_produced)
    adjusted_conversion = _q(real_conversion + inp.piglet_adjustment + inp.carcass_adjustment)

    # Mortality
    real_mortality_pct = _q(Decimal(inp.mortality_count) / Decimal(inp.housed_count) * 100)
    adjusted_mortality_pct = real_mortality_pct

    # Integrator percentage adjustments (standard Borderô approach)
    mortality_adjustment_pct = _q(inp.map_value - adjusted_mortality_pct)
    conversion_adjustment_pct = _q(inp.cap - adjusted_conversion)
    integrator_pct = _q(GROSS_INTEGRATOR_PCT + mortality_adjustment_pct + conversion_adjustment_pct)

    # Financial result
    gross_income = _q(total_carcass_produced * inp.price_per_kg * integrator_pct / 100)
    net_income = gross_income

    # Performance
    daily_weight_gain = _q((inp.pig_weight - inp.piglet_weight) / Decimal(inp.days_housed))
    daily_carcass_gain = _q((pig_carcass_weight - piglet_carcass_weight) / Decimal(inp.days_housed))

    # Per-pig metrics
    gross_income_per_pig = _q(gross_income / Decimal(pig_count))
    net_income_per_pig = _q(net_income / Decimal(pig_count))

    return BatchFinancialResult(
        pk="",
        sk="",
        housed_count=inp.housed_count,
        mortality_count=inp.mortality_count,
        pig_count=pig_count,
        piglet_weight=inp.piglet_weight,
        pig_weight=inp.pig_weight,
        total_feed=inp.total_feed,
        days_housed=inp.days_housed,
        cap=inp.cap,
        map_value=inp.map_value,
        price_per_kg=inp.price_per_kg,
        gross_integrator_pct=GROSS_INTEGRATOR_PCT,
        carcass_yield_factor=carcass_yield_factor,
        piglet_carcass_weight=piglet_carcass_weight,
        pig_carcass_weight=pig_carcass_weight,
        total_piglet_carcass=total_piglet_carcass,
        total_pig_carcass=total_pig_carcass,
        total_carcass_produced=total_carcass_produced,
        real_conversion=real_conversion,
        piglet_adjustment=inp.piglet_adjustment,
        carcass_adjustment=inp.carcass_adjustment,
        adjusted_conversion=adjusted_conversion,
        daily_weight_gain=daily_weight_gain,
        daily_carcass_gain=daily_carcass_gain,
        real_mortality_pct=real_mortality_pct,
        adjusted_mortality_pct=adjusted_mortality_pct,
        mortality_adjustment_pct=mortality_adjustment_pct,
        conversion_adjustment_pct=conversion_adjustment_pct,
        integrator_pct=integrator_pct,
        gross_income=gross_income,
        net_income=net_income,
        gross_income_per_pig=gross_income_per_pig,
        net_income_per_pig=net_income_per_pig,
    )
