import dataclasses


@dataclasses.dataclass
class PigTruckArrival:
    pk: str
    sk: str
    animal_count: int = 0
    sex: str = ""
    arrival_date: str = ""
    pig_age_days: int = 0
    origin_name: str = ""
    origin_type: str = ""
