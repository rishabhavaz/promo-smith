"""Shared duration conversion utility."""


def duration_to_days(duration_str: str) -> int | None:
    """Convert a promo duration string to number of days. Returns None for LIFETIME.

    Accepts "{n}D", "{n}M", "{n}Y" for any positive integer n, plus "LIFETIME".
    Months are approximated as 30 days, years as 365 days.
    """
    if not duration_str or duration_str.upper() == "LIFETIME":
        return None
    d = duration_str.upper().strip()
    if d.endswith("D"):
        try:
            return int(d[:-1])
        except ValueError:
            return None
    if d.endswith("M"):
        try:
            return int(d[:-1]) * 30
        except ValueError:
            return None
    if d.endswith("Y"):
        try:
            return int(d[:-1]) * 365
        except ValueError:
            return None
    try:
        return int(d)
    except ValueError:
        return None
