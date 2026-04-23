import dataclasses
import os

MAX_FEED_STOCK_THRESHOLD = 80_000
BEDROCK_TIMEOUT_SECONDS = 60
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")


@dataclasses.dataclass
class DailyBalance:
    date: str
    projected_balance_kg: int
    consumption_kg: int
    scheduled_delivery_kg: int
    arrival_kg: int


@dataclasses.dataclass
class FeedTypeGroup:
    feed_type: str
    entries: list
    production_weekdays: list[int]
    first_date: str
    last_date: str


@dataclasses.dataclass
class SuggestionContext:
    batch_id: str
    min_threshold: int
    max_threshold: int
    daily_balances: list[DailyBalance]
    scheduled_entries: list
    feed_type_groups: list[FeedTypeGroup]


@dataclasses.dataclass
class Suggestion:
    planned_date: str
    feed_type: str
    new_planned_date: str
    description: str
