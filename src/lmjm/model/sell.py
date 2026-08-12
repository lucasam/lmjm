import dataclasses
from decimal import Decimal
from typing import Optional

from lmjm.model.sex import Sex, coerce_sex, optional_sex_field
from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class Sell:
    pk: str  # "Sell|{uuid}"
    sk: str = "Sell"
    sell_date: str = ""  # YYYY-MM-DD
    number_of_animals: int = 0
    animal_age: Optional[int] = None
    sex: Optional[Sex] = optional_sex_field()
    batch: Optional[str] = None
    description: Optional[str] = None
    buyer: Optional[str] = None
    average_weight: Decimal = Decimal(0)
    unit_value: Decimal = Decimal(0)
    total_value: Decimal = Decimal(0)
    total_commission: Decimal = Decimal(0)
    total_transportation: Decimal = Decimal(0)
    net_value: Decimal = Decimal(0)  # total_value - total_commission - total_transportation
    price_per_arroba: Decimal = Decimal(0)
    # Optional ear_tags of animals sold in this transaction. The count need not
    # match number_of_animals; associated animals get status "Vendida".
    associated_ear_tags: Optional[list[str]] = None

    def __post_init__(self) -> None:
        self.sex = coerce_sex(self.sex)
