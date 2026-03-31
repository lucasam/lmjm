import dataclasses


@dataclasses.dataclass
class FeedConsumptionPlan:
    pk: str
    sk: str
    day_number: int = 0
    expected_grams_per_animal: float = 0.0
    date: str = ""
