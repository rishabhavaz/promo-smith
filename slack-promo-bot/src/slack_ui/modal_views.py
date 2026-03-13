"""Slack modal view definitions."""
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from src.config import DEFAULT_PREFIX, DEFAULT_DURATION
from src.utils.duration import duration_to_days


def _expiry_text(created_at_str: str, duration_str: str) -> str:
    """Return a human-readable expiry status string."""
    days = duration_to_days(duration_str)
    if days is None:
        return "Never expires (LIFETIME)"
    try:
        created = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return "Unknown"
    expiry = created + timedelta(days=days)
    remaining = (expiry - datetime.now(timezone.utc)).days
    expiry_fmt = expiry.strftime("%b %d, %Y")
    if remaining > 0:
        return f"*{remaining} days left* (expires {expiry_fmt})"
    elif remaining == 0:
        return "*Expires today*"
    else:
        return f"~Expired {abs(remaining)} days ago~ ({expiry_fmt})"


def _mk_plain_option(value: str) -> dict:
    return {"text": {"type": "plain_text", "text": value}, "value": value}


def _pick_initial_option(options: list, selected_value: str, default_value: str) -> dict:
    for opt in options or []:
        if opt.get("value") == selected_value:
            return opt
    for opt in options or []:
        if opt.get("value") == default_value:
            return opt
    return (options or [_mk_plain_option(default_value)])[0]


def build_promo_form_modal(
    *,
    users_raw: str = "",
    prefix: str = DEFAULT_PREFIX,
    custom_prefix: str = "",
    duration: str = DEFAULT_DURATION,
    custom_days: str = "",
    till_date: str = "",
    notes: str = "",
):
    """Build the initial promo generation form modal."""
    prefix_options = [
        _mk_plain_option("AVZ-2DA-"),
        _mk_plain_option("AVZ-ACE-"),
        _mk_plain_option("AVZ-ACE1Y-"),
        _mk_plain_option("AVZ-ACAP-"),
        _mk_plain_option("AVZ-ARMB-"),
        _mk_plain_option("AVZ-ACAPEXT-"),
        _mk_plain_option("AVZ-SPEXT-"),
        _mk_plain_option("AVZ-RZPLT-"),
        _mk_plain_option("AVZ-STRLT-"),
        _mk_plain_option("AVZ-LOANER-"),
        _mk_plain_option("AVZ-MGRT-"),
        _mk_plain_option("AVZ-LEGACY-"),
    ]

    duration_options = [
        _mk_plain_option("LIFETIME"),
        _mk_plain_option("30D"),
        _mk_plain_option("60D"),
        _mk_plain_option("90D"),
        _mk_plain_option("6M"),
        _mk_plain_option("1Y"),
    ]

    user_el = {
        "type": "plain_text_input",
        "action_id": "value",
        "multiline": True,
        "focus_on_load": True,
        "placeholder": {"type": "plain_text", "text": "abc@gmail.com, +14155552671, xyz@company.com"},
    }
    if (users_raw or "").strip():
        user_el["initial_value"] = users_raw

    custom_prefix_el = {
        "type": "plain_text_input",
        "action_id": "value",
        "placeholder": {"type": "plain_text", "text": "e.g., AVZ-TRIAL-"},
    }
    if (custom_prefix or "").strip():
        custom_prefix_el["initial_value"] = custom_prefix

    notes_el = {
        "type": "plain_text_input",
        "action_id": "value",
        "multiline": True,
        "placeholder": {"type": "plain_text", "text": "Why are you creating these promo codes?"},
    }
    if (notes or "").strip():
        notes_el["initial_value"] = notes

    blocks = [
        {
            "type": "input",
            "block_id": "users_text",
            "label": {"type": "plain_text", "text": "Users (emails or phone numbers)"},
            "element": user_el,
            "hint": {"type": "plain_text", "text": "Comma-separated. Field wraps up to 3 lines for readability."},
        },
        {
            "type": "input",
            "block_id": "prefix",
            "label": {"type": "plain_text", "text": "Prefix"},
            "element": {
                "type": "static_select",
                "action_id": "value",
                "initial_option": _pick_initial_option(prefix_options, prefix, DEFAULT_PREFIX),
                "options": prefix_options,
            },
        },
        {
            "type": "input",
            "block_id": "custom_prefix",
            "optional": True,
            "label": {"type": "plain_text", "text": "Custom Prefix (optional)"},
            "element": custom_prefix_el,
        },
        {
            "type": "input",
            "block_id": "duration_block",
            "optional": False,
            "label": {"type": "plain_text", "text": "Duration"},
            "hint": {
                "type": "plain_text",
                "text": "Default duration. Ignored if an override field below is filled.",
            },
            "element": {
                "type": "static_select",
                "action_id": "duration",
                "initial_option": _pick_initial_option(duration_options, duration, DEFAULT_DURATION),
                "options": duration_options,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "ℹ️ *Override fields below are optional.* Only fill them if you need a custom duration. "
                        "If both are filled, End date takes priority."
                    ),
                }
            ],
        },
        {
            "type": "input",
            "block_id": "custom_days_block",
            "optional": True,
            "label": {"type": "plain_text", "text": "Override — Number of days"},
            "hint": {
                "type": "plain_text",
                "text": "If filled, this overrides the Duration dropdown above. Must be a positive whole number.",
            },
            "element": {
                "type": "plain_text_input",
                "action_id": "custom_days",
                "placeholder": {"type": "plain_text", "text": "e.g., 45"},
                **(
                    {"initial_value": str(custom_days).strip()}
                    if (custom_days or "").strip()
                    else {}
                ),
            },
        },
        {
            "type": "input",
            "block_id": "till_date_block",
            "optional": True,
            "label": {"type": "plain_text", "text": "Override — End date"},
            "hint": {
                "type": "plain_text",
                "text": "Highest priority. If filled, this overrides everything above. Must be a future date.",
            },
            "element": {
                "type": "datepicker",
                "action_id": "till_date",
                "placeholder": {"type": "plain_text", "text": "Select date"},
                **(
                    {"initial_date": str(till_date).strip()}
                    if (till_date or "").strip()
                    else {}
                ),
            },
        },
    ]

    blocks.append(
        {
            "type": "input",
            "block_id": "notes",
            "label": {"type": "plain_text", "text": "Notes (reason for promo)"},
            "element": notes_el,
        }
    )

    return {
        "type": "modal",
        "callback_id": "promo_gui_submit",
        "title": {"type": "plain_text", "text": "Generate Promos"},
        "submit": {"type": "plain_text", "text": "Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
    }


def build_confirmation_modal(ids: list, prefix: str, duration: str, partner: str,
                             notes: str, target_display: str, target_for_results: str,
                             duration_display: str = "", till_date: str = ""):
    """
    Build the confirmation modal with all generation details.
    
    Args:
        ids: List of user IDs
        prefix: Promo code prefix
        duration: Promo duration (e.g. "97D")
        partner: Distribution partner
        notes: Reason for generation
        target_display: Display name for results destination
        target_for_results: Actual channel/DM ID for results
        till_date: Optional YYYY-MM-DD end date selected by the user
        
    Returns:
        Modal view dictionary
    """
    user_list_text = "\n".join([f"• `{uid}`" for uid in ids[:20]])
    if len(ids) > 20:
        user_list_text += f"\n_...and {len(ids) - 20} more_"

    duration_text = (duration_display or "").strip()
    if not duration_text:
        duration_text = f"`{duration}`"
        if till_date:
            try:
                till_fmt = datetime.strptime(till_date, "%Y-%m-%d").strftime("%b %d, %Y")
                duration_text = f"`{duration}` (till {till_fmt})"
            except ValueError:
                pass

    meta = {
        "ids": ids,
        "prefix": prefix,
        "duration": duration,
        "partner": partner,
        "target": target_for_results,
        "notes": notes,
    }
    if till_date:
        meta["till_date"] = till_date

    return {
        "type": "modal",
        "callback_id": "promo_gui_confirm",
        "title": {"type": "plain_text", "text": "Confirm Generation"},
        "submit": {"type": "plain_text", "text": "✓ Confirm & Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps(meta),
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚠️ Review Before Confirming", "emoji": True}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Promo Code Settings*"}
            },
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Prefix*\n`{prefix}`"},
                {"type": "mrkdwn", "text": f"*Duration*\n{duration_text}"},
                {"type": "mrkdwn", "text": f"*Partner*\n`{partner}`"},
                {"type": "mrkdwn", "text": f"*Post Results To*\n{target_display}"},
            ]},
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Reason for Generation*\n{notes}"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Users ({len(ids)} total)*\n{user_list_text}"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "✅ Press *Confirm & Generate* to create these promo codes\n❌ Press *Cancel* to go back and make changes"}
            },
        ],
    }


def build_user_status_modal(
    *,
    ids: list,
    prefix: str,
    duration: str,
    partner: str,
    notes: str,
    target_display: str,
    target_for_results: str,
    promo_records: list,
    duration_display: str = "",
    till_date: str = "",
) -> dict:
    """Build a modal showing each user's existing subscription status before confirmation.

    Fetched records are grouped by promoCodeUser and displayed per-user with
    promo details, expiry status, used/unused flag, and device usage.
    """
    by_user = defaultdict(list)
    for rec in promo_records:
        by_user[rec.get("promoCodeUser", "").lower()].append(rec)

    new_count = sum(1 for uid in ids if uid.lower() not in by_user)
    existing_count = len(ids) - new_count

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔍 User Status Preview", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"{len(ids)} user(s) entered — "
                        f"🟢 {new_count} new · 🟡 {existing_count} already in database"
                    ),
                }
            ],
        },
        {"type": "divider"},
    ]

    for uid in ids:
        records = by_user.get(uid.lower(), [])

        if not records:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🟢 *`{uid}`* — _New user, no existing promos_",
                },
            })
        else:
            lines = [f"🟡 *`{uid}`* — {len(records)} existing promo(s)"]
            for rec in records[:5]:
                code = rec.get("promoCodeId", "?")
                dur = rec.get("promoCodeDuration", "?")
                rec_partner = rec.get("promoCodeDistributionPartner", "?")
                created = rec.get("createdAt", "")
                used = rec.get("promoCodeUsed", False)
                devices = rec.get("promoCodeUsedDevices") or []
                device_limit = rec.get("promoCodeDeviceCountLimit", 0)

                try:
                    created_fmt = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    ).strftime("%b %d, %Y")
                except (ValueError, TypeError):
                    created_fmt = "?"

                expiry = _expiry_text(created, dur)
                used_text = "✅ Used" if used else "⬜ Unused"
                device_text = f"Devices: {len(devices)}/{device_limit}"

                lines.append(
                    f"  • `{code}` · {dur} · {rec_partner} · Created {created_fmt}"
                    f"\n    {expiry} · {used_text} · {device_text}"
                )
            if len(records) > 5:
                lines.append(f"  _...and {len(records) - 5} more_")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)},
            })
        blocks.append({"type": "divider"})

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": (
                    "Review the users above, then press "
                    "*Proceed to Confirm* to continue or *Cancel* to go back."
                ),
            }
        ],
    })

    if len(blocks) > 48:
        blocks = blocks[:47]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_...truncated. {len(ids)} users total._"},
        })

    meta = {
        "ids": ids,
        "prefix": prefix,
        "duration": duration,
        "partner": partner,
        "target": target_for_results,
        "notes": notes,
        "duration_display": duration_display,
    }
    if till_date:
        meta["till_date"] = till_date

    return {
        "type": "modal",
        "callback_id": "promo_user_status",
        "title": {"type": "plain_text", "text": "User Status"},
        "submit": {"type": "plain_text", "text": "Proceed to Confirm"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps(meta),
        "blocks": blocks,
    }


def build_extension_history_modal(ids: list, prefix: str, duration: str, partner: str,
                                   notes: str, target_display: str, target_for_results: str,
                                   promo_records: list, till_date: str = ""):
    """
    Build a modal showing existing promo history for each user before granting extensions.

    Args:
        ids: List of user IDs (emails/phones) being processed
        prefix: Selected extension prefix
        duration: Selected duration (computed days string like "97D")
        partner: Distribution partner
        notes: Reason for extension
        target_display: Human-readable results destination
        target_for_results: Channel/DM ID for results
        promo_records: Raw Parse records returned by fetch_promos_for_users
        till_date: Optional YYYY-MM-DD end date selected by the user
    """
    by_user = defaultdict(list)
    for rec in promo_records:
        by_user[rec.get("promoCodeUser", "").lower()].append(rec)

    duration_text = f"`{duration}`"
    if till_date:
        try:
            till_fmt = datetime.strptime(till_date, "%Y-%m-%d").strftime("%b %d, %Y")
            duration_text = f"`{duration}` (till {till_fmt})"
        except ValueError:
            pass

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Extension History Review", "emoji": True}
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn",
                 "text": f"Prefix: `{prefix}` · Duration: {duration_text} · Partner: `{partner}` · Post to: {target_display}"}
            ]
        },
        {"type": "divider"},
    ]

    for uid in ids:
        records = by_user.get(uid.lower(), [])

        if not records:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*`{uid}`*\n_No existing promos found — new user_"}
            })
        else:
            lines = [f"*`{uid}`* — {len(records)} existing promo(s)"]
            for rec in records[:5]:
                code = rec.get("promoCodeId", "?")
                dur = rec.get("promoCodeDuration", "?")
                created = rec.get("createdAt", "")
                try:
                    created_fmt = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    ).strftime("%b %d, %Y")
                except (ValueError, TypeError):
                    created_fmt = "?"
                expiry = _expiry_text(created, dur)
                lines.append(f"  • `{code}` · {dur} · Created {created_fmt} · {expiry}")
            if len(records) > 5:
                lines.append(f"  _...and {len(records) - 5} more_")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)}
            })
        blocks.append({"type": "divider"})

    if len(blocks) > 48:
        blocks = blocks[:47]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_...truncated. {len(ids)} users total._"}
        })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn",
             "text": "Press *Proceed to Generate* to create extension codes, or *Cancel* to go back."}
        ]
    })

    meta = {
        "ids": ids,
        "prefix": prefix,
        "duration": duration,
        "partner": partner,
        "target": target_for_results,
        "notes": notes,
    }
    if till_date:
        meta["till_date"] = till_date

    return {
        "type": "modal",
        "callback_id": "promo_ext_history",
        "title": {"type": "plain_text", "text": "Extension History"},
        "submit": {"type": "plain_text", "text": "Proceed to Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps(meta),
        "blocks": blocks,
    }


def build_access_denied_modal():
    """A simple modal shown when a user is not authorized to generate promos."""
    return {
        "type": "modal",
        "callback_id": "promo_access_denied",
        "title": {"type": "plain_text", "text": "Access denied"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*You are not authorized to generate promo codes.*\n\n"
                        "If you believe this is a mistake, contact the Promo Smith admins."
                    ),
                },
            }
        ],
    }
