import dataclasses
from enum import StrEnum
from typing import Any, Optional

import desert
from marshmallow import fields


class Sex(StrEnum):
    # Member names give readable Male/Female semantics; values follow the
    # pattern stored on Animal records ("M"/"F"). Fields must serialize by value
    # (use optional_sex_field) so the persisted string stays "M"/"F".
    Male = "M"
    Female = "F"


def optional_sex_field() -> Any:
    """Dataclass field for an optional Sex that serializes by value ("M"/"F")."""
    return dataclasses.field(
        default=None,
        metadata=desert.metadata(fields.Enum(Sex, by_value=True, allow_none=True)),
    )


def coerce_sex(value: Any) -> Optional[Sex]:
    """Coerce a raw value ("M"/"F") into a Sex, leaving None and Sex untouched."""
    if value is None or isinstance(value, Sex):
        return value
    return Sex(value)
