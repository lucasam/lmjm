import dataclasses


@dataclasses.dataclass
class Medication:
    pk: str
    sk: str
    medication_name: str = ""
    expiration_date: str = ""
    part_number: str = ""
