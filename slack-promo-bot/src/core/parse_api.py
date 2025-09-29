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


def create_promo_object(payload: dict) -> None:
    """Create a new promo code object in the database."""
    api_root = os.environ["PARSE_API_ROOT"].rstrip("/")
    url = f"{api_root}/classes/PromoCodeInfo"
    resp = requests.post(url, headers=_parse_headers(), json=payload, timeout=10)
    resp.raise_for_status()
