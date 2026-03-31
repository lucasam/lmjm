import dataclasses


@dataclasses.dataclass
class Mortality:
    pk: str
    sk: str
    mortality_date: str = ""
    sex: str = ""
    origin: str = ""
    death_reason: str = ""
    reported_by: str = ""
