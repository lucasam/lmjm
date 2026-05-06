import dataclasses
from enum import StrEnum, auto
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


class ProcedureActionType(StrEnum):
    weight = auto()
    insemination = auto()
    diagnostic = auto()
    observation = auto()
    inspected = auto()
    implant = auto()


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class ProcedureAction:
    pk: str
    sk: str
    action_type: ProcedureActionType = ProcedureActionType.inspected
    ear_tag: str = ""
    weighing_date: Optional[str] = None
    weight_kg: Optional[int] = None
    insemination_date: Optional[str] = None
    semen: Optional[str] = None
    diagnostic_date: Optional[str] = None
    pregnant: Optional[bool] = None
    tags: Optional[str] = None
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.action_type, str) and not isinstance(self.action_type, ProcedureActionType):
            self.action_type = ProcedureActionType(self.action_type)
