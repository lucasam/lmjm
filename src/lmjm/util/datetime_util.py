from datetime import datetime


def parse_datetime_input(raw: str) -> tuple[str, str]:
    """Parse a date or datetime input string.

    Args:
        raw: Input in YYYYMMDDHHmm (12 chars) or YYYYMMDD (8 chars) format.

    Returns:
        Tuple of (stored_value, sk_date_part):
        - stored_value: 'YYYY-MM-DDTHH:MM' for DynamoDB attribute
        - sk_date_part: 'YYYYMMDDHHmm' for sort key construction

    Raises:
        ValueError: If input doesn't match either format.
    """
    if len(raw) == 12:
        dt = datetime.strptime(raw, "%Y%m%d%H%M")
    elif len(raw) == 8:
        dt = datetime.strptime(raw, "%Y%m%d")
    else:
        raise ValueError("Input must be in YYYYMMDDHHmm or YYYYMMDD format")
    stored = dt.strftime("%Y-%m-%dT%H:%M")
    sk_part = dt.strftime("%Y%m%d%H%M")
    return stored, sk_part
