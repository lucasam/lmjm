import dataclasses


@dataclasses.dataclass
class Weight:
    pk: str
    sk: str
    weight_kg: int = 0
    weighing_date: str = ""
