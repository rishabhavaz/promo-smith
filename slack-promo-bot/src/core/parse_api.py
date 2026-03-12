"""Parse/Back4App API interactions."""
import os
import json
import requests
from src.config import PARSE_APP_ID, PARSE_REST_KEY, PARSE_MASTER


def _parse_headers():
    """Build Parse REST headers with authentication."""
    headers = {
        "X-Parse-Application-Id": PARSE_APP_ID,
        "Content-Type": "application/json",
    }
    # Prefer master key if available; else use REST key
    if PARSE_MASTER:
        headers["X-Parse-Master-Key"] = PARSE_MASTER
    elif PARSE_REST_KEY:
        headers["X-Parse-REST-API-Key"] = PARSE_REST_KEY
    return headers


def promo_exists(promo_code_id: str) -> bool:
    """Check if a promo code already exists in the database."""
    api_root = os.environ["PARSE_API_ROOT"].rstrip("/")
    url = f"{api_root}/classes/PromoCodeInfo"
    params = {"where": json.dumps({"promoCodeId": promo_code_id}), "limit": 1}
    resp = requests.get(url, headers=_parse_headers(), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json() or {}
    results = data.get("results", [])
    return len(results) > 0


def fetch_promos_for_users(user_ids: list) -> list:
    """Fetch all existing promo records for a list of user IDs (emails/phones)."""
    if not user_ids:
        return []
    api_root = os.environ["PARSE_API_ROOT"].rstrip("/")
    url = f"{api_root}/classes/PromoCodeInfo"
    normalized = [uid.strip().lower() for uid in user_ids]
    where = json.dumps({"promoCodeUser": {"$in": normalized}})
    params = {"where": where, "limit": 1000, "order": "-createdAt"}
    resp = requests.get(url, headers=_parse_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return (resp.json() or {}).get("results", [])


def create_promo_object(payload: dict) -> None:
    """Create a new promo code object in the database."""
    api_root = os.environ["PARSE_API_ROOT"].rstrip("/")
    url = f"{api_root}/classes/PromoCodeInfo"
    resp = requests.post(url, headers=_parse_headers(), json=payload, timeout=10)
    resp.raise_for_status()


def update_promo_object(object_id: str, updates: dict) -> None:
    """Update an existing promo code object in the database.

    Args:
        object_id: The Parse objectId of the record to update.
        updates: Dict of field names to new values.
    """
    api_root = os.environ["PARSE_API_ROOT"].rstrip("/")
    url = f"{api_root}/classes/PromoCodeInfo/{object_id}"
    resp = requests.put(url, headers=_parse_headers(), json=updates, timeout=10)
    resp.raise_for_status()
