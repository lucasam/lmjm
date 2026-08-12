import dataclasses
from enum import StrEnum
from typing import Optional

from lmjm.model.sex import Sex, coerce_sex, optional_sex_field
from lmjm.util.marshmallow_serializer import serialization_config


class AnimalStatus(StrEnum):
    # Values are declared equal to the member names so the enum serializes to
    # the same string regardless of whether marshmallow dumps by name or value.
    Ativa = "Ativa"
    Vendida = "Vendida"
    Morto = "Morto"
    Baixa = "Baixa"


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class Animal:
    pk: str
    sk: str = "Animal"
    species: Optional[str] = None
    ear_tag: Optional[str] = None
    breed: Optional[str] = None
    sex: Optional[Sex] = optional_sex_field()
    birth_date: Optional[str] = None
    mother: Optional[str] = None
    batch: Optional[str] = None
    status: Optional[AnimalStatus] = None
    pregnant: Optional[bool] = None
    implanted: Optional[bool] = None
    inseminated: Optional[bool] = None
    lactating: Optional[bool] = None
    transferred: Optional[bool] = None
    notes: Optional[list[str]] = None
    tags: Optional[list[str]] = None

    def __post_init__(self) -> None:
        if self.status is not None and not isinstance(self.status, AnimalStatus):
            self.status = AnimalStatus(self.status)
        self.sex = coerce_sex(self.sex)
