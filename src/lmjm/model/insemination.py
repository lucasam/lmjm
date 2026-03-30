import dataclasses


@dataclasses.dataclass
class Insemination:
    pk: str
    sk: str
    insemination_date: str
    semen: str
