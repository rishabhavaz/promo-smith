"""Shared duration conversion utility."""


def duration_to_days(duration_str: str) -> int | None:
    """Convert a promo duration string to number of days. Returns None for LIFETIME."""
    if not duration_str or duration_str.upper() == "LIFETIME":
        return None
    d = duration_str.upper().strip()
    if d.endswith("D"):
        try:
            return int(d[:-1])
        except ValueError:
            return None
    if d == "6M":
        return 180
    if d == "1Y":
        return 365
    try:
        return int(d)
    except ValueError:
        return None
