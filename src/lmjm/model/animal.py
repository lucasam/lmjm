import dataclasses
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class Animal:
    pk: str
    sk: str = "Animal"
    ear_tag: Optional[str] = None
    breed: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[str] = None
    mother: Optional[str] = None
    batch: Optional[str] = None
    status: Optional[str] = None
    pregnant: Optional[bool] = None
    implanted: Optional[bool] = None
    inseminated: Optional[bool] = None
    lactating: Optional[bool] = None
    transferred: Optional[bool] = None
    notes: Optional[list[str]] = None
    tags: Optional[list[str]] = None
