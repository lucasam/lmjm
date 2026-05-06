import dataclasses
from enum import StrEnum, auto
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


class ProcedureStatus(StrEnum):
    open = auto()
    confirmed = auto()
    cancelled = auto()


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class Procedure:
    pk: str
    sk: str = "Procedure"
    procedure_date: str = ""
    status: ProcedureStatus = ProcedureStatus.open
    applied_count: Optional[int] = None
    failed_count: Optional[int] = None
    failures: Optional[list[dict[str, str]]] = None

    def __post_init__(self) -> None:
        if isinstance(self.status, str) and not isinstance(self.status, ProcedureStatus):
            self.status = ProcedureStatus(self.status)
