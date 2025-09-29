"""User input validation and parsing utilities."""
import re


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
