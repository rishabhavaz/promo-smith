"""Smart promo generation logic.

Decides whether to bump an existing code's device count or create a new one.
This runs for ALL prefixes — the decision is based on what the user already
has in the database, NOT on which prefix is selected.
"""

from datetime import datetime, timedelta, timezone
from src.utils.duration import duration_to_days
from src.config import EXPIRY_THRESHOLD_DAYS, MAX_DEVICE_LIMIT, AGGREGATE_DEVICE_LIMIT


def _compute_aggregate_device_limit(all_records: list) -> int:
    """Sum promoCodeDeviceCountLimit across all of a user's promo records."""
    return sum(r.get("promoCodeDeviceCountLimit", 0) for r in all_records)


def _can_bump(record: dict, all_records: list) -> dict | None:
    """Check whether a specific record can have its device count bumped.

    Returns None if bump is allowed.
    Returns a dict with skip reason if bump is NOT allowed.
    """
    current_limit = record.get("promoCodeDeviceCountLimit") or 1

    if current_limit >= MAX_DEVICE_LIMIT:
        return {
            "reason": "per_code_limit_reached",
            "detail": (
                f"Code {record.get('promoCodeId', '?')} already at "
                f"max {MAX_DEVICE_LIMIT} devices"
            ),
        }

    aggregate_total = _compute_aggregate_device_limit(all_records)
    if aggregate_total + 1 > AGGREGATE_DEVICE_LIMIT:
        return {
            "reason": "aggregate_limit_reached",
            "detail": (
                f"User already has {aggregate_total} total devices "
                f"across all codes (max: {AGGREGATE_DEVICE_LIMIT})"
            ),
        }

    return None


def resolve_generation_action(
    user_id: str,
    existing_records: list,
    requested_duration: str,
    requested_end_date: str = "",
) -> dict:
    """Decide what to do when generating a promo for a user.

    This runs for ALL prefixes. The decision is:
    - If user is new (no records) -> create new code
    - If user has LIFETIME code AND request is LIFETIME -> bump existing
    - If user has code expiring near requested date -> bump existing
    - Otherwise -> create new code

    Args:
        user_id: The email or phone being processed.
        existing_records: All PromoCodeInfo records for this user (sorted by -createdAt).
        requested_duration: The duration string from the form (e.g. "90D", "LIFETIME").
        requested_end_date: Optional YYYY-MM-DD end date if support specified a custom till_date.

    Returns a dict describing the action to take:

        {"action": "create_new"}
        {"action": "create_new", "reason": "gap_too_large", "nearest_expiry_days_diff": int}
        {"action": "bump_device_count", "record": dict, "reason": "lifetime"|"near_expiry", ...}
        {"action": "skip", "reason": str, "detail": str, ...}
    """
    if not existing_records:
        return {"action": "create_new"}

    is_lifetime_request = (requested_duration or "").upper() == "LIFETIME"

    # --- Rule 1: LIFETIME request + user has LIFETIME code ---
    if is_lifetime_request:
        lifetime_records = [
            r for r in existing_records
            if (r.get("promoCodeDuration") or "").upper() == "LIFETIME"
        ]

        if lifetime_records:
            for record in lifetime_records:
                block = _can_bump(record, existing_records)
                if block is None:
                    return {
                        "action": "bump_device_count",
                        "record": record,
                        "reason": "lifetime",
                    }

            first_block = _can_bump(lifetime_records[0], existing_records)
            return {
                "action": "skip",
                "reason": first_block["reason"],
                "detail": first_block["detail"],
                "record": lifetime_records[0],
            }

        # User has promos but none are LIFETIME — create a new LIFETIME code
        return {"action": "create_new"}

    # --- Rule 2: Non-lifetime request — compare expiry to requested end date ---
    requested_end = None

    if requested_end_date:
        try:
            requested_end = datetime.strptime(
                requested_end_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    if requested_end is None:
        days = duration_to_days(requested_duration)
        if days is not None:
            requested_end = datetime.now(timezone.utc) + timedelta(days=days)

    if requested_end is None:
        return {"action": "create_new"}

    best_record = None
    best_diff = None

    for rec in existing_records:
        rec_duration = rec.get("promoCodeDuration", "")
        rec_days = duration_to_days(rec_duration)
        if rec_days is None:
            continue

        created_str = rec.get("createdAt", "")
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        rec_expiry = created + timedelta(days=rec_days)
        diff = abs((rec_expiry - requested_end).days)

        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_record = rec

    if best_record is None:
        return {"action": "create_new"}

    if best_diff < EXPIRY_THRESHOLD_DAYS:
        block = _can_bump(best_record, existing_records)
        if block is not None:
            return {
                "action": "skip",
                "reason": block["reason"],
                "detail": block["detail"],
                "record": best_record,
            }
        return {
            "action": "bump_device_count",
            "record": best_record,
            "reason": "near_expiry",
            "days_diff": best_diff,
        }

    return {
        "action": "create_new",
        "reason": "gap_too_large",
        "nearest_expiry_days_diff": best_diff,
    }
