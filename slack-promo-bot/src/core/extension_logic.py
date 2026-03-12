"""Smart extension logic for deciding how to handle promo extensions."""
from datetime import datetime, timedelta, timezone
from src.config import EXPIRY_THRESHOLD_DAYS
from src.utils.duration import duration_to_days


def resolve_extension_action(user_id: str, existing_records: list, requested_duration: str) -> dict:
    """Decide the extension action for a user based on their existing promos.

    Args:
        user_id: The user email/phone being processed.
        existing_records: That user's existing promo records (newest first).
        requested_duration: The duration string requested for the extension.

    Returns a dict describing the action:
        {"action": "create_new"}
            No existing promos — create a fresh code.
        {"action": "create_new", "reason": "expiring_soon"}
            Existing code expiring within threshold — allow new code.
        {"action": "create_new", "reason": "not_expiring_yet", "warning": "..."}
            Existing code still active — allow but flag it.
        {"action": "bump_device_count", "record": <record>, "reason": "lifetime"}
            LIFETIME code — bump device count instead of creating new.
    """
    if not existing_records:
        return {"action": "create_new"}

    record = existing_records[0]
    dur = record.get("promoCodeDuration", "")

    if dur.upper() == "LIFETIME":
        return {"action": "bump_device_count", "record": record, "reason": "lifetime"}

    total_days = duration_to_days(dur)
    if total_days is None:
        return {"action": "create_new"}

    created = record.get("createdAt", "")
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return {"action": "create_new"}

    expiry = created_dt + timedelta(days=total_days)
    remaining = (expiry - datetime.now(timezone.utc)).days

    if remaining <= EXPIRY_THRESHOLD_DAYS:
        return {"action": "create_new", "reason": "expiring_soon"}

    return {
        "action": "create_new",
        "reason": "not_expiring_yet",
        "warning": f"Existing code still has {remaining} days left",
    }
