"""Slack event handlers for the promo bot."""
import re
import json
from src.config import DEFAULT_PREFIX, DEFAULT_DURATION, DEFAULT_PARTNER, PROMO_NOTIFY_CHANNEL
from src.utils.validation import parse_user_ids, validate_user_id
from src.utils.authz import get_requester_user_id, is_authorized_slack_user, unauthorized_text
from src.slack_ui.modal_views import (
    build_promo_form_modal,
    build_confirmation_modal,
    build_access_denied_modal,
)
from src.core.promo_generator import create_promo_for_user
from src.slack_ui.notifications import notify_channel, format_results_message


def handle_open_modal(ack, body, client, private_metadata=""):
    """
    Handle opening the promo generation modal.
    
    Args:
        ack: Slack acknowledgement function
        body: Request body from Slack
        client: Slack client
        private_metadata: Optional metadata to attach to the modal
    """
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        # Slash commands can be answered without opening a modal
        if body.get("command"):
            ack(unauthorized_text(requester_user_id))
            return

        # Global shortcuts don't have a channel context → show a modal instead
        ack()
        try:
            client.views_open(trigger_id=body["trigger_id"], view=build_access_denied_modal())
        except Exception as e:
            print(f"[handle_open_modal] views_open(access_denied) failed: {e}")
        return

    ack()
    try:
        view = build_promo_form_modal()
        if private_metadata:
            view["private_metadata"] = private_metadata
        client.views_open(trigger_id=body["trigger_id"], view=view)
    except Exception as e:
        print(f"[handle_open_modal] views_open failed: {e}")


def handle_promo_submit(ack, body, client, view):
    """
    Handle promo generation form submission and show confirmation modal.
    
    Args:
        ack: Slack acknowledgement function
        body: Request body from Slack
        client: Slack client
        view: The submitted view
    """
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    vals = view["state"]["values"]
    
    # Extract and validate users input
    _users_block = vals.get("users_text") or {}
    _users_action = _users_block.get("value") or {}
    raw = _users_action.get("value") or ""
    
    # Check for line breaks without commas (common mistake)
    if ("\n" in raw or "\r" in raw) and "," not in raw:
        ack({
            "response_action": "errors",
            "errors": {"users_text": "Use commas to separate entries. Line breaks are not separators."}
        })
        return

    ids = parse_user_ids(raw)

    # Validate user IDs
    if not ids:
        ack({
            "response_action": "errors",
            "errors": {"users_text": "Enter at least one email or phone. Separate with commas only."}
        })
        return
        
    invalid = [x for x in ids if not validate_user_id(x)]
    if invalid:
        ack({
            "response_action": "errors",
            "errors": {"users_text": f"These look invalid: {', '.join(invalid[:5])}"}
        })
        return

    # Validate custom days if provided
    _custom_block = vals.get("custom_days") or {}
    _custom_action = _custom_block.get("value") or {}
    custom_days_raw = (_custom_action.get("value") or "").strip()
    if custom_days_raw:
        if not re.fullmatch(r"\d+", custom_days_raw) or int(custom_days_raw) <= 0:
            ack({
                "response_action": "errors",
                "errors": {"custom_days": "Enter a positive number of days (e.g., 45)."}
            })
            return

    # Validate notes (mandatory)
    _notes_block = vals.get("notes") or {}
    _notes_action = _notes_block.get("value") or {}
    notes_raw = (_notes_action.get("value") or "").strip()
    if not notes_raw:
        ack({
            "response_action": "errors",
            "errors": {"notes": "Please provide the reason for these promo codes."}
        })
        return

    # Extract selected values
    selected_prefix_opt = (vals.get("prefix", {}).get("value", {}).get("selected_option") or {})
    selected_duration_opt = (vals.get("duration", {}).get("value", {}).get("selected_option") or {})
    selected_partner_opt = (vals.get("partner", {}).get("value", {}).get("selected_option") or {})

    partner = selected_partner_opt.get("value", DEFAULT_PARTNER)

    # Compute duration: custom_days overrides dropdown if present
    duration_choice = selected_duration_opt.get("value", DEFAULT_DURATION)
    duration = f"{int(custom_days_raw)}D" if custom_days_raw else duration_choice

    # Compute prefix: custom_prefix overrides dropdown if present
    prefix_choice = selected_prefix_opt.get("value", DEFAULT_PREFIX)
    _cp_block = vals.get("custom_prefix") or {}
    _cp_action = _cp_block.get("value") or {}
    custom_prefix_raw = (_cp_action.get("value") or "").strip()
    prefix = custom_prefix_raw or prefix_choice

    # Determine target channel for results
    post_channel_block = vals.get("post_channel") or {}
    post_channel_action = post_channel_block.get("value") or {}
    post_channel_id = (post_channel_action.get("selected_conversation") or "").strip()
    target_for_results = post_channel_id or (view.get("private_metadata") or "").strip()
    target_display = f"<#{target_for_results}>" if target_for_results else "DM"

    # Build and push confirmation modal
    confirm_view = build_confirmation_modal(
        ids=ids,
        prefix=prefix,
        duration=duration,
        partner=partner,
        notes=notes_raw,
        target_display=target_display,
        target_for_results=target_for_results
    )

    ack({
        "response_action": "push",
        "view": confirm_view,
    })


def handle_promo_confirm(ack, body, client, view):
    """
    Handle confirmation and generate promo codes.
    
    Args:
        ack: Slack acknowledgement function
        body: Request body from Slack
        client: Slack client
        view: The confirmation view
    """
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    # Close the entire modal stack
    ack({"response_action": "clear"})

    # Extract metadata
    try:
        meta_json = view.get("private_metadata") or "{}"
        data = json.loads(meta_json)
    except Exception:
        data = {}

    ids = data.get("ids") or []
    if isinstance(ids, str):
        ids = [s for s in re.split(r"\s*,\s*", ids) if s]

    prefix = data.get("prefix", DEFAULT_PREFIX)
    duration = data.get("duration", DEFAULT_DURATION)
    partner = data.get("partner", DEFAULT_PARTNER)
    notes = data.get("notes", "")

    # Determine target for results
    target = data.get("target") or None
    if not target:
        dm = client.conversations_open(users=requester_user_id)
        target = dm["channel"]["id"]

    # Generate promo codes
    rows, errors = [], 0
    for uid in ids:
        try:
            promo_id = create_promo_for_user(uid, prefix, duration, partner)
            rows.append((uid, promo_id, duration, partner))
        except Exception as e:
            rows.append((uid, f"ERROR: {e}", duration, partner))
            errors += 1

    # Format and post results
    message = format_results_message(prefix, duration, partner, notes, ids, rows, errors)
    
    try:
        client.chat_postMessage(channel=target, text=message)
    except Exception as e:
        print(f"[results] chat_postMessage failed for {target}: {e}")
        # Fallback to DM
        try:
            dm = client.conversations_open(users=requester_user_id)
            dm_channel = dm["channel"]["id"]
            client.chat_postMessage(channel=dm_channel, text=message)
        except Exception as e2:
            print(f"[results] DM fallback failed: {e2}")

    # Send notification to configured channel if set
    notify_channel(
        client=client,
        notify_channel=PROMO_NOTIFY_CHANNEL,
        target=target,
        prefix=prefix,
        duration=duration,
        partner=partner,
        processed_count=len(ids),
        errors=errors,
        requester_user_id=requester_user_id,
        notes=notes,
        rows=rows,
    )
