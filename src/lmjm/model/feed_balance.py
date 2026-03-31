import dataclasses


@dataclasses.dataclass
class FeedBalance:
    pk: str
    sk: str
    measurement_date: str = ""
    balance_kg: float = 0.0
