import dataclasses

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class RawMaterialType:
    pk: str = "RAW_MATERIAL_TYPE"
    sk: str = ""
    code: str = ""
    description: str = ""
    category: str = ""
