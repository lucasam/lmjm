from decimal import Decimal

Q = Decimal("0.0001")


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to 4 decimal places."""
    return value.quantize(Q)


def compute_cap_map(
    car: Decimal,
    mar: Decimal,
    avg_slaughter_weight: Decimal,
    avg_piglet_weight: Decimal,
    average_age: Decimal,
) -> dict[str, Decimal]:
    """Pure function: computes CAP(1-4) and MAP(1-2) from integrator weekly data.

    Returns dict with keys: cap_1, cap_2, cap_3, cap_4, map_1, map_2.
    """
    cap_1 = _q(
        car
        - (avg_slaughter_weight - Decimal("85")) * Decimal("0.0095")
        - (avg_piglet_weight - Decimal("22")) * Decimal("0.0125")
    )
    cap_2 = _q(cap_1 - Decimal("0.03"))
    cap_3 = _q(cap_2 - Decimal("0.015"))
    cap_4 = _q(cap_1 - Decimal("0.015"))
    map_1 = _q(Decimal(Decimal(130) - average_age) * Decimal("0.0183") + mar)
    map_2 = _q(map_1 - Decimal("0.4"))
    return {
        "cap_1": cap_1,
        "cap_2": cap_2,
        "cap_3": cap_3,
        "cap_4": cap_4,
        "map_1": map_1,
        "map_2": map_2,
    }
