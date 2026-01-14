"""Slack authorization helpers (who is allowed to generate promos)."""

from __future__ import annotations

from typing import Any, Mapping

from src.config import PROMO_AUTHORIZED_USER_IDS


def get_requester_user_id(body: Mapping[str, Any]) -> str:
    """
    Extract the Slack user ID for the requester from various payload shapes.

    Supported payloads:
    - Slash command: body["user_id"]
    - Shortcut / view submission: body["user"]["id"]
    """
    if not body:
        return ""

    user = body.get("user")
    if isinstance(user, Mapping):
        uid = (user.get("id") or "").strip()
        if uid:
            return uid

    # Slash commands usually use "user_id"
    uid = (body.get("user_id") or "").strip()
    if uid:
        return uid

    # Some payloads may use "user" as a string
    if isinstance(user, str):
        return user.strip()

    return ""


def is_authorized_slack_user(user_id: str) -> bool:
    """
    Check whether the given Slack user ID is allowed to generate promos.

    Behavior:
    - If PROMO_AUTHORIZED_USER_IDS is empty/unset: allow everyone (backwards compatible)
    - Otherwise: allow only users in the allow-list
    """
    allowed = PROMO_AUTHORIZED_USER_IDS
    if not allowed:
        return True
    return user_id in allowed


def unauthorized_text(user_id: str) -> str:
    """User-friendly message for slash command responses."""
    if user_id:
        return f"Sorry <@{user_id}>, you are not authorized to generate promo codes."
    return "Sorry, you are not authorized to generate promo codes."

