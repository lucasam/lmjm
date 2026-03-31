import dataclasses


@dataclasses.dataclass
class MedicationShot:
    pk: str
    sk: str
    medication_name: str = ""
    shot_count: int = 0
    date: str = ""
