from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from lmjm.model import AnimalStatus, Sell, Sex
from lmjm.repo import AnimalRepo
from lmjm.util.response import respond

logger = logging.getLogger()

_MONEY_FIELDS = (
    "average_weight",
    "unit_value",
    "total_value",
    "total_commission",
    "total_transportation",
    "price_per_arroba",
)


def parse_sell_request(body: dict[str, Any], pk: str) -> tuple[Optional[Sell], Optional[dict[str, Any]]]:
    """Build a Sell from a request body.

    Returns (sell, None) on success or (None, error_response) when validation
    fails. net_value is computed here (total_value - commission - transportation).
    """
    try:
        sell_date = datetime.strptime(str(body.get("sell_date", "")), "%Y%m%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None, respond(status_code=400, error="sell_date must be in YYYYMMDD format")

    try:
        money = {field: Decimal(str(body.get(field, 0) or 0)) for field in _MONEY_FIELDS}
    except (InvalidOperation, ValueError):
        return None, respond(status_code=400, error="Monetary fields must be valid numbers")

    net_value = money["total_value"] - money["total_commission"] - money["total_transportation"]

    sex_raw = body.get("sex")
    sex: Optional[Sex] = None
    if sex_raw is not None and str(sex_raw) != "":
        try:
            sex = Sex(sex_raw)
        except ValueError:
            valid = ", ".join(s.value for s in Sex)
            return None, respond(status_code=400, error=f"Invalid sex '{sex_raw}'. Valid values: {valid}")

    animal_age = body.get("animal_age")
    associated = [str(tag).strip() for tag in (body.get("associated_ear_tags") or []) if str(tag).strip()]

    sell = Sell(
        pk=pk,
        sk="Sell",
        sell_date=sell_date,
        number_of_animals=int(body.get("number_of_animals", 0) or 0),
        animal_age=int(animal_age) if animal_age is not None and str(animal_age) != "" else None,
        sex=sex,
        batch=body.get("batch") or None,
        description=body.get("description") or None,
        buyer=body.get("buyer") or None,
        average_weight=money["average_weight"],
        unit_value=money["unit_value"],
        total_value=money["total_value"],
        total_commission=money["total_commission"],
        total_transportation=money["total_transportation"],
        net_value=net_value,
        price_per_arroba=money["price_per_arroba"],
        associated_ear_tags=associated or None,
    )
    return sell, None


def flip_animals_to_vendida(animal_repo: AnimalRepo, ear_tags: Optional[list[str]]) -> list[str]:
    """Best-effort: set each associated animal's status to "Vendida".

    Failures (missing animal, update error) are logged and skipped so that
    saving the Sell never fails because of an animal deactivation problem.
    """
    flipped: list[str] = []
    for ear_tag in ear_tags or []:
        try:
            animal = animal_repo.get_by_ear_tag(ear_tag)
            if animal is None:
                logger.warning("Sell association ear_tag not found, skipping: %s", ear_tag)
                continue
            animal.status = AnimalStatus.Vendida
            animal_repo.update(animal)
            flipped.append(ear_tag)
        except Exception:  # noqa: BLE001 - best-effort, never fail the save
            logger.exception("Failed to deactivate animal %s; continuing", ear_tag)
    return flipped
