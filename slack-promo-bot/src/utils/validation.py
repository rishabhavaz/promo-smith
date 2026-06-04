"""User input validation and parsing utilities."""
import re
from urllib.parse import urlparse, parse_qs


# Regular expressions for validation
EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RX = re.compile(r"^\+?\d{7,15}$")  # simple E.164-ish


def _norm_id(s: str) -> str:
    """Normalize a user ID (email or phone)."""
    s = s.strip()
    if "@" in s:
        return s.lower()
    return re.sub(r"[^\d+]", "", s)  # keep only + and digits


def parse_user_ids(raw: str):
    """
    Parse comma-separated user IDs from raw input.
    
    Args:
        raw: Raw comma-separated string of emails/phone numbers
        
    Returns:
        List of normalized, deduplicated user IDs
    """
    parts = [p for p in re.split(r"\s*,\s*", raw or "") if p]
    ids = [_norm_id(p) for p in parts]
    
    # Dedupe while retaining order
    seen = {}
    for identifier in ids:
        if identifier not in seen:
            seen[identifier] = True
            
    return list(seen.keys())


def validate_user_id(user_id: str) -> bool:
    """Check if a user ID is a valid email or phone number."""
    return EMAIL_RX.match(user_id) is not None or PHONE_RX.match(user_id) is not None


def extract_device_id(raw: str) -> str | None:
    """Extract a device ID from a Mixpanel URL or return a raw device ID string.

    Supports:
    - Mixpanel profile URLs with distinct_id / $device_id in fragment or query
    - Raw hex device IDs passed directly
    """
    if not raw or not raw.strip():
        return None
    raw = raw.strip()

    if not raw.startswith("http"):
        # Treat as raw device ID
        return raw

    # Parse Mixpanel URL
    parsed = urlparse(raw)

    # Check fragment (#distinct_id=ABC or #id=ABC)
    if parsed.fragment:
        frag = parsed.fragment
        # Try key=value pairs in the fragment
        for part in frag.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                if k in ("distinct_id", "$device_id", "id"):
                    return v
        # Fragment might be like "user-ABC"
        if frag.startswith("user-"):
            return frag[5:]

    # Check query parameters
    query_params = parse_qs(parsed.query)
    for key in ("distinct_id", "$device_id", "id"):
        if key in query_params:
            return query_params[key][0]

    # Last resort: return the last non-empty path segment
    segments = [s for s in parsed.path.rstrip("/").split("/") if s]
    if segments:
        last = segments[-1]
        if re.fullmatch(r"[0-9a-fA-F]{8,}", last):
            return last

    return None
