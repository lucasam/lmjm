"""Feed type code → description mapping.

Used to translate supplier product codes (cProd from NF-e) to human-readable feed type names.
"""

FEED_TYPE_MAP: dict[str, str] = {
    "130867": "ST01",
    "130871": "ST02",
    "130887": "ST03",
    "130888": "ST04",
    "765668": "ST05",
    "130906": "ST06",
    "104278": "Super Plus",
}


def get_feed_type_description(code: str) -> str:
    """Return the human-readable description for a feed type code, or the code itself if unknown."""
    return FEED_TYPE_MAP.get(code, code)


def get_all_feed_types() -> dict[str, str]:
    """Return the full feed type mapping."""
    return dict(FEED_TYPE_MAP)
