import dataclasses
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class Batch:
    pk: str
    sk: str = "Batch"
    status: str = "created"
    supply_id: int = 0
    module_id: str = ""
    warehouse_ids: list[str] = dataclasses.field(default_factory=list)
    receive_date: str = ""
    expected_slaughter_date: Optional[str] = None
    pig_count: int = 0
    min_feed_stock_threshold: float = 0.0
    total_animal_count: Optional[int] = None
    average_start_date: Optional[str] = None
    distinct_origin_count: Optional[int] = None
    origin_types: Optional[list[str]] = None
