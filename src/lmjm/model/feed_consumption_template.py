import dataclasses
from decimal import Decimal


@dataclasses.dataclass
class FeedConsumptionTemplate:
    pk: str = "FEED_CONSUMPTION_TEMPLATE"
    sk: str = ""
    sequence: int = 0
    expected_piglet_weight: Decimal = Decimal(0)
    expected_kg_per_animal: Decimal = Decimal(0)
