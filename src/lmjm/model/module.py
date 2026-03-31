import dataclasses


@dataclasses.dataclass
class Module:
    pk: str
    sk: str = "Module"
    module_number: int = 0
    name: str = ""
    area: int = 0
    supported_animal_count: int = 0
    silo_capacity: int = 0
