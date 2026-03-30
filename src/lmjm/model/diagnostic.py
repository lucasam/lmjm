import dataclasses
from typing import Optional


@dataclasses.dataclass
class Diagnostic:
    pk: str
    sk: str
    diagnostic_date: str
    pregnant: bool
    breeding_date: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    semen: Optional[str] = None
