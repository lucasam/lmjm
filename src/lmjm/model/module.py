import dataclasses


@dataclasses.dataclass
class Module:
    pk: str
    sk: str = "Module"
    module_number: int = 0
    name: str = ""
