"""Slack event handlers for the promo bot."""
import json
from src.config import (
    DEFAULT_PREFIX, DEFAULT_DURATION, DEFAULT_PARTNER,
    PROMO_NOTIFY_CHANNEL, EXTENSION_PREFIXES,
)
from src.utils.validation import parse_user_ids, validate_user_id, extract_device_id
from src.utils.authz import get_requester_user_id, is_authorized_slack_user, unauthorized_text
from src.slack_ui.modal_views import (
    build_promo_form_modal,
    build_confirmation_modal,
    build_access_denied_modal,
    build_extension_history_modal,
    build_user_status_modal,
    NUM_ENTRY_ROWS,
)
from src.core.promo_generator import create_promo_for_user
from src.core.parse_api import fetch_promos_for_users, update_promo_object
from src.core.extension_logic import resolve_generation_action
from src.slack_ui.notifications import notify_channel, format_results_message


def _read_entries_from_form(vals: dict) -> list[dict]:
    """Parse the 5 entry rows from a submitted form's state values.

    Returns a list of entry dicts for non-empty rows:
        {user_id, mixpanel_raw, device_id, prefix, duration}
    """
    entries = []
    for n in range(1, NUM_ENTRY_ROWS + 1):
        user_raw = (
            ((vals.get(f"user_{n}") or {}).get("value") or {}).get("value") or ""
        ).strip()
        if not user_raw:
            continue

        mixpanel_raw = (
            ((vals.get(f"mixpanel_{n}") or {}).get("value") or {}).get("value") or ""
        ).strip()

        prefix_val = (
            ((vals.get(f"prefix_{n}") or {}).get("value") or {}).get("selected_option") or {}
        ).get("value", DEFAULT_PREFIX)

        duration_val = (
            ((vals.get(f"duration_{n}") or {}).get("value") or {}).get("selected_option") or {}
        ).get("value", DEFAULT_DURATION)

        # Normalize user ID
        ids = parse_user_ids(user_raw)
        user_id = ids[0] if ids else user_raw.strip().lower()

        # Extract device ID from Mixpanel URL or raw input
        device_id = extract_device_id(mixpanel_raw) if mixpanel_raw else None

        entries.append({
            "user_id": user_id,
            "mixpanel_raw": mixpanel_raw,
            "device_id": device_id,
            "prefix": prefix_val,
            "duration": duration_val,
        })
    return entries


def _read_entries_from_metadata(view: dict, caller: str = "") -> dict:
    """Read entries and shared fields from a modal's private_metadata."""
    raw = view.get("private_metadata") or "{}"
    print(f"[metadata:{caller}] raw private_metadata ({len(raw)} chars): {raw[:200]}")
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"[metadata:{caller}] JSON parse FAILED: {e}")
        data = {}
    entries = data.get("entries") or []
    print(f"[metadata:{caller}] parsed {len(entries)} entries")
    return data


def handle_open_modal(ack, body, client, private_metadata=""):
    """Handle opening the promo generation modal."""
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        if body.get("command"):
            ack(unauthorized_text(requester_user_id))
            return
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
    """Legacy handler — no-op with the new 5-row form."""
    ack()


def handle_promo_submit(ack, body, client, view):
    """Handle promo generation form submission and show status/confirmation modal."""
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    vals = view["state"]["values"]

    # Parse entries from the 5 rows
    entries = _read_entries_from_form(vals)

    if not entries:
        ack({
            "response_action": "errors",
            "errors": {"user_1": "Enter at least one user to generate promo codes."},
        })
        return

    # Validate each entry's user ID
    for i, entry in enumerate(entries):
        if not validate_user_id(entry["user_id"]):
            n = _find_row_number(vals, entry["user_id"])
            ack({
                "response_action": "errors",
                "errors": {
                    f"user_{n}": f"Invalid user ID: {entry['user_id']}. Must be email or phone.",
                },
            })
            return

    # Validate Mixpanel fields — warn if URL couldn't yield a device ID
    for entry in entries:
        if entry["mixpanel_raw"] and not entry["device_id"]:
            n = _find_row_number(vals, entry["user_id"])
            ack({
                "response_action": "errors",
                "errors": {
                    f"mixpanel_{n}": "Could not extract device ID from this URL. Check the format.",
                },
            })
            return

    # Validate notes (mandatory)
    _notes_block = vals.get("notes") or {}
    _notes_action = _notes_block.get("value") or {}
    notes_raw = (_notes_action.get("value") or "").strip()
    if not notes_raw:
        ack({
            "response_action": "errors",
            "errors": {"notes": "Please provide the reason for these promo codes."},
        })
        return

    partner = DEFAULT_PARTNER

    # Determine target channel for results
    target_for_results = (view.get("private_metadata") or "").strip()
    target_display = f"<#{target_for_results}>" if target_for_results else "DM"

    # Strip mixpanel_raw from entries for metadata (not needed downstream)
    clean_entries = [
        {
            "user_id": e["user_id"],
            "device_id": e["device_id"],
            "prefix": e["prefix"],
            "duration": e["duration"],
        }
        for e in entries
    ]
    print(f"[handle_promo_submit] {len(clean_entries)} clean entries: {clean_entries}")

    # Fetch existing promo records for all users
    user_ids = [e["user_id"] for e in entries]
    try:
        promo_records = fetch_promos_for_users(user_ids)
    except Exception as e:
        promo_records = []
        print(f"[handle_promo_submit] fetch_promos_for_users failed: {e}")

    # Extension prefixes: show extension history if any entry uses one
    has_extension = any(e["prefix"] in EXTENSION_PREFIXES for e in entries)

    if has_extension:
        history_view = build_extension_history_modal(
            entries=clean_entries,
            partner=partner,
            notes=notes_raw,
            target_display=target_display,
            target_for_results=target_for_results,
            promo_records=promo_records,
        )
        ack({"response_action": "push", "view": history_view})
        return

    # Normal flow: user status preview
    status_view = build_user_status_modal(
        entries=clean_entries,
        partner=partner,
        notes=notes_raw,
        target_display=target_display,
        target_for_results=target_for_results,
        promo_records=promo_records,
    )
    ack({"response_action": "push", "view": status_view})


def _find_row_number(vals: dict, user_id: str) -> int:
    """Find which entry row contains the given user_id."""
    for n in range(1, NUM_ENTRY_ROWS + 1):
        raw = (
            ((vals.get(f"user_{n}") or {}).get("value") or {}).get("value") or ""
        ).strip()
        if raw and user_id in raw.lower():
            return n
    return 1


def handle_promo_confirm(ack, body, client, view):
    """Handle confirmation and generate promo codes."""
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    ack({"response_action": "clear"})

    data = _read_entries_from_metadata(view, caller="handle_promo_confirm")
    entries = data.get("entries") or []
    partner = data.get("partner", DEFAULT_PARTNER)
    notes = data.get("notes", "")
    target = data.get("target") or None

    if not entries:
        print(f"[handle_promo_confirm] WARNING: entries is empty! Full metadata: {data}")
        # DM the requester so they see the issue immediately
        try:
            dm = client.conversations_open(users=requester_user_id)
            client.chat_postMessage(
                channel=dm["channel"]["id"],
                text=(
                    "⚠️ *Promo generation failed — no entries found in metadata.*\n"
                    "This usually means another bot instance (e.g. Railway) handled the submission "
                    "instead of this one. Stop the Railway deployment and retry.\n"
                    f"Debug: metadata keys = {list(data.keys())}"
                ),
            )
        except Exception:
            pass
        return

    if not target:
        dm = client.conversations_open(users=requester_user_id)
        target = dm["channel"]["id"]

    # Fetch existing records for smart generation logic
    user_ids = [e["user_id"] for e in entries]
    try:
        all_promo_records = fetch_promos_for_users(user_ids)
    except Exception as e:
        print(f"[handle_promo_confirm] fetch_promos_for_users failed: {e}")
        all_promo_records = []

    # Generate promo codes per entry
    rows = []
    errors = 0
    for entry in entries:
        uid = entry["user_id"]
        prefix = entry.get("prefix", DEFAULT_PREFIX)
        duration = entry.get("duration", DEFAULT_DURATION)
        device_id = entry.get("device_id")

        try:
            user_records = [
                r for r in all_promo_records
                if r.get("promoCodeUser", "").lower() == uid.lower()
            ]
            action = resolve_generation_action(uid, user_records, duration)

            if action["action"] == "bump_device_count":
                record = action["record"]
                new_limit = (record.get("promoCodeDeviceCountLimit") or 1) + 1
                updates = {
                    "promoCodeDeviceCountLimit": new_limit,
                    "promoCodeUsed": False,
                }
                if device_id:
                    updates["promoCodeUsedDevices"] = {
                        "__op": "AddUnique",
                        "objects": [device_id],
                    }
                update_promo_object(record["objectId"], updates)
                reason = action.get("reason", "")
                code = record.get("promoCodeId", "?")
                rows.append({
                    "user_id": uid,
                    "result": f"UPDATED {code} (devices: {new_limit}, reason: {reason})",
                    "prefix": prefix,
                    "duration": duration,
                    "partner": partner,
                    "device_id": device_id,
                })

            elif action["action"] == "skip":
                detail = action.get("detail", "limit reached")
                rows.append({
                    "user_id": uid,
                    "result": f"SKIPPED: {detail}",
                    "prefix": prefix,
                    "duration": duration,
                    "partner": partner,
                    "device_id": device_id,
                })

            else:
                # Create new promo code
                promo_id = create_promo_for_user(
                    uid, prefix, duration, partner, device_id=device_id,
                )

                # If device_id provided and there's a pre-existing promo,
                # also add device to it and bump its limit
                if device_id and user_records:
                    _attach_device_to_existing(user_records, device_id)

                rows.append({
                    "user_id": uid,
                    "result": f"CREATED {promo_id} (reason: {duration})",
                    "prefix": prefix,
                    "duration": duration,
                    "partner": partner,
                    "device_id": device_id,
                })

        except Exception as e:
            rows.append({
                "user_id": uid,
                "result": f"ERROR: {e}",
                "prefix": prefix,
                "duration": duration,
                "partner": partner,
                "device_id": device_id,
            })
            errors += 1

    # Format and post results
    message = format_results_message(notes, entries, rows, errors)

    try:
        client.chat_postMessage(channel=target, text=message)
    except Exception as e:
        print(f"[results] chat_postMessage failed for {target}: {e}")
        try:
            dm = client.conversations_open(users=requester_user_id)
            dm_channel = dm["channel"]["id"]
            client.chat_postMessage(channel=dm_channel, text=message)
        except Exception as e2:
            print(f"[results] DM fallback failed: {e2}")

    notify_channel(
        client=client,
        notify_channel_id=PROMO_NOTIFY_CHANNEL,
        target=target,
        processed_count=len(entries),
        errors=errors,
        requester_user_id=requester_user_id,
        notes=notes,
        rows=rows,
    )


def _attach_device_to_existing(user_records: list, device_id: str):
    """Attach a device ID to the most recent existing promo and bump its limit."""
    if not user_records or not device_id:
        return
    # Pick the most recent record (already sorted by -createdAt from API)
    record = user_records[0]
    new_limit = (record.get("promoCodeDeviceCountLimit") or 1) + 1
    try:
        update_promo_object(record["objectId"], {
            "promoCodeDeviceCountLimit": new_limit,
            "promoCodeUsedDevices": {
                "__op": "AddUnique",
                "objects": [device_id],
            },
        })
    except Exception as e:
        print(f"[_attach_device_to_existing] failed for {record.get('promoCodeId')}: {e}")


def handle_extension_proceed(ack, body, client, view):
    """Handle 'Proceed to Generate' from the extension history review modal."""
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    data = _read_entries_from_metadata(view, caller="handle_extension_proceed")
    entries = data.get("entries", [])
    partner = data.get("partner", DEFAULT_PARTNER)
    notes = data.get("notes", "")
    target = data.get("target", "")
    target_display = f"<#{target}>" if target else "DM"

    confirm_view = build_confirmation_modal(
        entries=entries,
        partner=partner,
        notes=notes,
        target_display=target_display,
        target_for_results=target,
    )
    ack({"response_action": "push", "view": confirm_view})


def handle_user_status_proceed(ack, body, client, view):
    """Handle 'Proceed to Confirm' from the user status preview modal."""
    requester_user_id = get_requester_user_id(body)
    if not is_authorized_slack_user(requester_user_id):
        ack({"response_action": "update", "view": build_access_denied_modal()})
        return

    data = _read_entries_from_metadata(view, caller="handle_user_status_proceed")
    entries = data.get("entries", [])
    partner = data.get("partner", DEFAULT_PARTNER)
    notes = data.get("notes", "")
    target = data.get("target", "")
    target_display = f"<#{target}>" if target else "DM"

    confirm_view = build_confirmation_modal(
        entries=entries,
        partner=partner,
        notes=notes,
        target_display=target_display,
        target_for_results=target,
    )
    ack({"response_action": "push", "view": confirm_view})
