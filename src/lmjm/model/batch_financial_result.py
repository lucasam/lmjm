import dataclasses
from decimal import Decimal

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class BatchFinancialResult:
    pk: str
    sk: str
    type: str = ""
    created_at: str = ""

    # Farm data
    housed_count: int = 0
    mortality_count: int = 0
    pig_count: int = 0
    piglet_weight: Decimal = Decimal(0)
    pig_weight: Decimal = Decimal(0)
    total_feed: Decimal = Decimal(0)
    days_housed: int = 0

    # Integrator parameters
    cap: Decimal = Decimal(0)
    map_value: Decimal = Decimal(0)
    price_per_kg: Decimal = Decimal(0)
    gross_integrator_pct: Decimal = Decimal("5.1")

    # Carcass calculations
    carcass_yield_factor: Decimal = Decimal(0)
    piglet_carcass_weight: Decimal = Decimal(0)
    pig_carcass_weight: Decimal = Decimal(0)
    total_piglet_carcass: Decimal = Decimal(0)
    total_pig_carcass: Decimal = Decimal(0)
    total_carcass_produced: Decimal = Decimal(0)

    # Feed conversion
    real_conversion: Decimal = Decimal(0)
    piglet_adjustment: Decimal = Decimal(0)
    carcass_adjustment: Decimal = Decimal(0)
    adjusted_conversion: Decimal = Decimal(0)

    # Performance
    daily_weight_gain: Decimal = Decimal(0)
    daily_carcass_gain: Decimal = Decimal(0)

    # Mortality
    real_mortality_pct: Decimal = Decimal(0)
    adjusted_mortality_pct: Decimal = Decimal(0)

    # Integrator percentage
    mortality_adjustment_pct: Decimal = Decimal(0)
    conversion_adjustment_pct: Decimal = Decimal(0)
    integrator_pct: Decimal = Decimal(0)

    # Financial result
    gross_income: Decimal = Decimal(0)
    net_income: Decimal = Decimal(0)
    gross_income_per_pig: Decimal = Decimal(0)
    net_income_per_pig: Decimal = Decimal(0)
