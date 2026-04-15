import dataclasses
from decimal import Decimal


@dataclasses.dataclass
class FeedConsumptionPlan:
    pk: str
    sk: str
    day_number: int = 0
    expected_kg_per_animal: Decimal = Decimal(0)
    expected_piglet_weight: int = 0
    date: str = ""
