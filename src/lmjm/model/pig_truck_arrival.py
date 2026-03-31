import dataclasses
from typing import Optional


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
    fiscal_document_number: str = ""
    animal_weight: int = 0
    gta_number: str = ""
    mossa: str = ""
    suplier_code: Optional[int] = None
