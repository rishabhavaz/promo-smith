"""Slack event handlers for the promo bot."""
import re
import json
from datetime import date
from src.config import (
    DEFAULT_PREFIX, DEFAULT_DURATION, DEFAULT_PARTNER,
    PROMO_NOTIFY_CHANNEL, EXTENSION_PREFIXES,
)
from src.utils.validation import parse_user_ids, validate_user_id
from src.utils.authz import get_requester_user_id, is_authorized_slack_user, unauthorized_text
from src.slack_ui.modal_views import (
    build_promo_form_modal,
    build_confirmation_modal,
    build_access_denied_modal,
    build_extension_history_modal,
    build_user_status_modal,
)
from src.core.promo_generator import create_promo_for_user
from src.core.parse_api import fetch_promos_for_users, update_promo_object
from src.core.extension_logic import resolve_extension_action
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


def handle_override_choice_change(ack, body, client):
    """Update the promo form modal when override choice changes."""
    ack()

    view = body.get("view") or {}
    vals = (view.get("state") or {}).get("values") or {}

    users_raw = (((vals.get("users_text") or {}).get("value") or {}).get("value") or "").strip()
    prefix_val = (
        (((vals.get("prefix") or {}).get("value") or {}).get("selected_option") or {}).get("value")
        or DEFAULT_PREFIX
    )
    duration_val = (
        (((vals.get("duration_block") or {}).get("duration") or {}).get("selected_option") or {}).get("value")
        or (((vals.get("duration") or {}).get("value") or {}).get("selected_option") or {}).get("value")
        or DEFAULT_DURATION
    )
    custom_prefix_raw = (((vals.get("custom_prefix") or {}).get("value") or {}).get("value") or "").strip()
    notes_raw = (((vals.get("notes") or {}).get("value") or {}).get("value") or "").strip()

    custom_days_raw = (
        (((vals.get("custom_days_block") or {}).get("custom_days") or {}).get("value") or "")
        or (((vals.get("custom_days") or {}).get("value") or {}).get("value") or "")
    ).strip()
    till_date_raw = (
        (((vals.get("till_date_block") or {}).get("till_date") or {}).get("selected_date") or "")
        or (((vals.get("till_date") or {}).get("value") or {}).get("selected_date") or "")
    ).strip()

    updated_view = build_promo_form_modal(
        users_raw=users_raw,
        prefix=prefix_val,
        custom_prefix=custom_prefix_raw,
        duration=duration_val,
        custom_days=custom_days_raw,
        till_date=till_date_raw,
        notes=notes_raw,
    )

    # Preserve private_metadata (e.g. channel routing from /generate-promo)
    pm = (view.get("private_metadata") or "").strip()
    if pm:
        updated_view["private_metadata"] = pm

    try:
        client.views_update(view_id=view["id"], hash=view.get("hash"), view=updated_view)
    except Exception as e:
        print(f"[handle_override_choice_change] views_update failed: {e}")


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

    # Read all three duration inputs — priority: End date → Day count → Dropdown
    # .get() for block IDs guards against stale modals opened by a prior process
    till_date_raw = (vals.get("till_date_block", {}).get("till_date", {}).get("selected_date") or "").strip()
    custom_days_raw = (vals.get("custom_days_block", {}).get("custom_days", {}).get("value") or "").strip()
    duration_choice = vals.get("duration_block", {}).get("duration", {}).get("selected_option", {}).get("value") or DEFAULT_DURATION

    duration_source = "preset"
    duration_display = duration_choice
    duration = duration_choice
    till_date_for_display = ""

    if till_date_raw:
        try:
            target_date = date.fromisoformat(till_date_raw)
        except ValueError:
            ack({
                "response_action": "errors",
                "errors": {"till_date_block": "Invalid date."}
            })
            return

        delta_days = (target_date - date.today()).days
        if delta_days <= 0:
            ack({
                "response_action": "errors",
                "errors": {"till_date_block": "End date must be in the future."}
            })
            return

        duration_source = "end_date"
        duration = f"{delta_days}D"
        till_date_for_display = till_date_raw
        duration_display = f"Until {till_date_raw} ({delta_days} days from today)"
    elif custom_days_raw:
        if not re.fullmatch(r"\d+", custom_days_raw) or int(custom_days_raw) <= 0:
            ack({
                "response_action": "errors",
                "errors": {"custom_days_block": "Must be a positive whole number (e.g., 45)."}
            })
            return

        days = int(custom_days_raw)
        duration_source = "custom_days"
        duration = f"{days}D"
        duration_display = f"{days} days (custom override)"

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
    selected_partner_opt = (vals.get("partner", {}).get("value", {}).get("selected_option") or {})

    partner = selected_partner_opt.get("value", DEFAULT_PARTNER)

    # Only carry till_date forward when it actually won
    till_date_raw = till_date_for_display

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

    # Extension prefixes: show existing promo history before confirmation
    if prefix in EXTENSION_PREFIXES:
        try:
            promo_records = fetch_promos_for_users(ids)
        except Exception as e:
            promo_records = []
            print(f"[handle_promo_submit] fetch_promos_for_users failed: {e}")

        history_view = build_extension_history_modal(
            ids=ids,
            prefix=prefix,
            duration=duration,
            partner=partner,
            notes=notes_raw,
            target_display=target_display,
            target_for_results=target_for_results,
            promo_records=promo_records,
            till_date=till_date_raw,
        )
        # Preserve the resolved duration display/source for the final confirmation step
        try:
            meta = json.loads(history_view.get("private_metadata") or "{}")
        except Exception:
            meta = {}
        meta["duration_display"] = duration_display
        meta["duration_source"] = duration_source
        history_view["private_metadata"] = json.dumps(meta)

        ack({"response_action": "push", "view": history_view})
        return

    # Normal flow: fetch user status from DB and show preview
    try:
        promo_records = fetch_promos_for_users(ids)
    except Exception as e:
        promo_records = []
        print(f"[handle_promo_submit] fetch_promos_for_users failed: {e}")

    status_view = build_user_status_modal(
        ids=ids,
        prefix=prefix,
        duration=duration,
        partner=partner,
        notes=notes_raw,
        target_display=target_display,
        target_for_results=target_for_results,
        promo_records=promo_records,
        duration_display=duration_display,
        till_date=till_date_raw,
    )

    ack({"response_action": "push", "view": status_view})


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

    # For extension prefixes, re-fetch fresh records for smart logic
    all_promo_records = []
    if prefix in EXTENSION_PREFIXES:
        try:
            all_promo_records = fetch_promos_for_users(ids)
        except Exception as e:
            print(f"[handle_promo_confirm] fetch_promos_for_users failed: {e}")

    # Generate promo codes
    rows, errors = [], 0
    for uid in ids:
        try:
            if prefix in EXTENSION_PREFIXES:
                user_records = [
                    r for r in all_promo_records
                    if r.get("promoCodeUser", "").lower() == uid.lower()
                ]
                till_date = data.get("till_date", "")
                action = resolve_extension_action(
                    uid, user_records, duration, requested_end_date=till_date
                )

                if action["action"] == "bump_device_count":
                    record = action["record"]
                    new_limit = (record.get("promoCodeDeviceCountLimit") or 1) + 1
                    update_promo_object(record["objectId"], {
                        "promoCodeDeviceCountLimit": new_limit,
                        "promoCodeUsed": False,
                    })
                    reason = action.get("reason", "")
                    code = record.get("promoCodeId", "?")
                    rows.append((
                        uid,
                        f"UPDATED {code} (devices: {new_limit}, reason: {reason})",
                        duration,
                        partner,
                    ))

                elif action["action"] == "skip":
                    detail = action.get("detail", "limit reached")
                    rows.append((uid, f"SKIPPED: {detail}", duration, partner))

                else:
                    promo_id = create_promo_for_user(uid, prefix, duration, partner)
                    rows.append((uid, promo_id, duration, partner))
            else:
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


def handle_extension_proceed(ack, body, client, view):
    """
    Handle 'Proceed to Generate' from the extension history review modal.
    Pushes the standard confirmation modal onto the stack.
    """
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    try:
        data = json.loads(view.get("private_metadata") or "{}")
    except Exception:
        data = {}

    ids = data.get("ids", [])
    if isinstance(ids, str):
        ids = [s for s in re.split(r"\s*,\s*", ids) if s]

    prefix = data.get("prefix", DEFAULT_PREFIX)
    duration = data.get("duration", DEFAULT_DURATION)
    partner = data.get("partner", DEFAULT_PARTNER)
    notes = data.get("notes", "")
    target = data.get("target", "")
    till_date = data.get("till_date", "")
    duration_display = data.get("duration_display", "")
    target_display = f"<#{target}>" if target else "DM"

    confirm_view = build_confirmation_modal(
        ids=ids,
        prefix=prefix,
        duration=duration,
        partner=partner,
        notes=notes,
        target_display=target_display,
        target_for_results=target,
        duration_display=duration_display,
        till_date=till_date,
    )

    ack({"response_action": "push", "view": confirm_view})


def handle_user_status_proceed(ack, body, client, view):
    """
    Handle 'Proceed to Confirm' from the user status preview modal.
    Pushes the standard confirmation modal onto the stack.
    """
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    try:
        data = json.loads(view.get("private_metadata") or "{}")
    except Exception:
        data = {}

    ids = data.get("ids", [])
    if isinstance(ids, str):
        ids = [s for s in re.split(r"\s*,\s*", ids) if s]

    prefix = data.get("prefix", DEFAULT_PREFIX)
    duration = data.get("duration", DEFAULT_DURATION)
    partner = data.get("partner", DEFAULT_PARTNER)
    notes = data.get("notes", "")
    target = data.get("target", "")
    till_date = data.get("till_date", "")
    duration_display = data.get("duration_display", "")
    target_display = f"<#{target}>" if target else "DM"

    confirm_view = build_confirmation_modal(
        ids=ids,
        prefix=prefix,
        duration=duration,
        partner=partner,
        notes=notes,
        target_display=target_display,
        target_for_results=target,
        duration_display=duration_display,
        till_date=till_date,
    )

    ack({"response_action": "push", "view": confirm_view})
