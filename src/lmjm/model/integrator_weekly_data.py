import dataclasses
from decimal import Decimal

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class IntegratorWeeklyData:
    pk: str = "INTEGRATOR_WEEKLY_DATA"
    sk: str = ""
    date_generated: str = ""
    validity_start: str = ""
    validity_end: str = ""
    source_data_start: str = ""
    source_data_end: str = ""
    car: Decimal = Decimal(0)
    mar: Decimal = Decimal(0)
    avg_piglet_weight: Decimal = Decimal(0)
    avg_slaughter_weight: Decimal = Decimal(0)
    average_age: int = 0
    number_of_samples: int = 0
    gdp: Decimal = Decimal(0)

    # Computed CAP/MAP variants
    cap_1: Decimal = Decimal(0)
    cap_2: Decimal = Decimal(0)
    cap_3: Decimal = Decimal(0)
    cap_4: Decimal = Decimal(0)
    map_1: Decimal = Decimal(0)
    map_2: Decimal = Decimal(0)
