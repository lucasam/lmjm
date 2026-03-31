import dataclasses


@dataclasses.dataclass
class Warehouse:
    pk: str
    sk: str
    name: str = ""
    area: float = 0.0
    supported_animal_count: int = 0
    silo_capacity: float = 0.0
