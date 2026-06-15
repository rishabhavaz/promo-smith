"""Slack modal view definitions."""
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from src.config import DEFAULT_PREFIX, DEFAULT_DURATION
from src.utils.duration import duration_to_days

NUM_ENTRY_ROWS = 5


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


# ---- Shared option lists ----

PREFIX_OPTIONS = [
    _mk_plain_option("AVZ-2DA-"),
    _mk_plain_option("AVZ-ACE-"),
    _mk_plain_option("AVZ-ACE1Y-"),
    _mk_plain_option("AVZ-ACAP-"),
    _mk_plain_option("AVZ-ARMB-"),
    _mk_plain_option("AVZ-ACAPEXT-"),
    _mk_plain_option("AVZ-SPEXT-"),
    _mk_plain_option("AVZ-RZPLT-"),
    _mk_plain_option("AVZ-RZP1Y-"),
    _mk_plain_option("AVZ-RZP1M-"),
    _mk_plain_option("AVZ-STRLT-"),
    _mk_plain_option("AVZ-STR1Y-"),
    _mk_plain_option("AVZ-STR1M-"),
]

DURATION_UNIT_OPTIONS = [
    {"text": {"type": "plain_text", "text": "Lifetime"}, "value": "LIFETIME"},
    {"text": {"type": "plain_text", "text": "Days"}, "value": "D"},
    {"text": {"type": "plain_text", "text": "Months"}, "value": "M"},
    {"text": {"type": "plain_text", "text": "Years"}, "value": "Y"},
]


def _parse_duration(duration: str) -> tuple[str, str]:
    """Split a canonical duration string into (amount_str, unit_value) for form pre-fill.

    "LIFETIME" or "" -> ("", "LIFETIME")
    "30D"            -> ("30", "D")
    "6M"             -> ("6", "M")
    "1Y"             -> ("1", "Y")
    """
    if not duration or duration.upper() == "LIFETIME":
        return ("", "LIFETIME")
    d = duration.upper().strip()
    for suffix in ("D", "M", "Y"):
        if d.endswith(suffix):
            try:
                int(d[:-1])
                return (d[:-1], suffix)
            except ValueError:
                return ("", "LIFETIME")
    return ("", "LIFETIME")


def _build_entry_blocks(n: int, *, user_id="", mixpanel="", prefix="", duration="",
                        till_date=""):
    """Build Slack blocks for a single entry row (1-indexed)."""
    user_el = {
        "type": "plain_text_input",
        "action_id": "value",
        "placeholder": {"type": "plain_text", "text": "email or phone number"},
    }
    if n == 1:
        user_el["focus_on_load"] = True
    if user_id:
        user_el["initial_value"] = user_id

    mixpanel_el = {
        "type": "plain_text_input",
        "action_id": "value",
        "placeholder": {"type": "plain_text", "text": "Optional — paste Mixpanel URL or device ID"},
    }
    if mixpanel:
        mixpanel_el["initial_value"] = mixpanel

    till_date_el = {
        "type": "datepicker",
        "action_id": "value",
        "placeholder": {"type": "plain_text", "text": "Optional end date"},
    }
    if (till_date or "").strip():
        till_date_el["initial_date"] = till_date.strip()

    # Split canonical duration into amount + unit for the two form fields
    amount_str, unit_val = _parse_duration(duration)

    dur_amount_el = {
        "type": "number_input",
        "action_id": "value",
        "is_decimal_allowed": False,
        "min_value": "1",
        "placeholder": {"type": "plain_text", "text": "e.g. 30 (ignored for Lifetime)"},
    }
    if amount_str:
        dur_amount_el["initial_value"] = amount_str

    blocks = [
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"━━━━━━━━━━━━━━  *ENTRY {n}*  ━━━━━━━━━━━━━━"}],
        },
        {
            "type": "input",
            "block_id": f"user_{n}",
            "optional": True,
            "label": {"type": "plain_text", "text": "User ID (email or phone)"},
            "element": user_el,
        },
        {
            "type": "input",
            "block_id": f"mixpanel_{n}",
            "optional": True,
            "label": {"type": "plain_text", "text": "Mixpanel URL or Device ID"},
            "element": mixpanel_el,
        },
        {
            "type": "input",
            "block_id": f"prefix_{n}",
            "label": {"type": "plain_text", "text": "Prefix"},
            "element": {
                "type": "static_select",
                "action_id": "value",
                "initial_option": _pick_initial_option(PREFIX_OPTIONS, prefix, DEFAULT_PREFIX),
                "options": PREFIX_OPTIONS,
            },
        },
        {
            "type": "input",
            "block_id": f"dur_amount_{n}",
            "optional": True,
            "label": {"type": "plain_text", "text": "Duration Amount"},
            "hint": {"type": "plain_text", "text": "Ignored when unit is Lifetime or End Date is set"},
            "element": dur_amount_el,
        },
        {
            "type": "input",
            "block_id": f"dur_unit_{n}",
            "label": {"type": "plain_text", "text": "Duration Unit"},
            "element": {
                "type": "static_select",
                "action_id": "value",
                "initial_option": _pick_initial_option(
                    DURATION_UNIT_OPTIONS, unit_val, "LIFETIME",
                ),
                "options": DURATION_UNIT_OPTIONS,
            },
        },
        {
            "type": "input",
            "block_id": f"till_date_{n}",
            "optional": True,
            "label": {"type": "plain_text", "text": "End Date (overrides Duration if set)"},
            "element": till_date_el,
        },
    ]
    return blocks


def build_promo_form_modal(*, entries=None, notes=""):
    """Build the 5-row promo generation form modal.

    Args:
        entries: Optional list of dicts with keys user_id, mixpanel, prefix, duration
                 for pre-populating the form.
        notes: Pre-filled notes text.
    """
    entries = entries or []

    # Notes at top for quick single-entry use
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
            "block_id": "notes",
            "label": {"type": "plain_text", "text": "Notes (reason for promo)"},
            "element": notes_el,
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Fill one row per user (up to 5). Empty rows are skipped. "
                        "Paste a Mixpanel URL or device ID to target a specific device."
                    ),
                }
            ],
        },
    ]

    for n in range(1, NUM_ENTRY_ROWS + 1):
        e = entries[n - 1] if n - 1 < len(entries) else {}
        blocks.extend(_build_entry_blocks(
            n,
            user_id=e.get("user_id", ""),
            mixpanel=e.get("mixpanel", ""),
            prefix=e.get("prefix", ""),
            duration=e.get("duration", ""),
            till_date=e.get("till_date", ""),
        ))
        if n < NUM_ENTRY_ROWS:
            blocks.append({"type": "divider"})

    return {
        "type": "modal",
        "callback_id": "promo_gui_submit",
        "title": {"type": "plain_text", "text": "Generate Promos"},
        "submit": {"type": "plain_text", "text": "Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
    }


def build_confirmation_modal(entries: list, partner: str, notes: str,
                             target_display: str, target_for_results: str):
    """Build the confirmation modal showing a per-entry summary table.

    Args:
        entries: List of entry dicts (user_id, device_id, prefix, duration).
        partner: Distribution partner.
        notes: Reason for generation.
        target_display: Display name for results destination.
        target_for_results: Actual channel/DM ID for results.
    """
    entry_lines = []
    has_any_device = any(e.get("device_id") for e in entries)
    for i, e in enumerate(entries, 1):
        dur_text = e["duration"]
        if e.get("till_date"):
            try:
                till_fmt = datetime.strptime(e["till_date"], "%Y-%m-%d").strftime("%b %d, %Y")
                dur_text = f"{e['duration']} (till {till_fmt})"
            except ValueError:
                pass
        line = f"{i}. `{e['user_id']}`  ·  `{e['prefix']}`  ·  {dur_text}"
        if e.get("device_id"):
            line += f"\n    📱 `{e['device_id']}`"
        entry_lines.append(line)

    meta = {
        "entries": entries,
        "partner": partner,
        "target": target_for_results,
        "notes": notes,
    }

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Review Before Confirming", "emoji": True},
        },
        {"type": "divider"},
    ]

    if has_any_device:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "⚠️ *Device ID Verification*\n"
                    "Verify each device ID is correct — promo codes will be "
                    "permanently linked to these devices."
                ),
            },
        })
        blocks.append({"type": "divider"})

    blocks.extend([
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{len(entries)} entry/entries to generate*"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(entry_lines)},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Partner*\n`{partner}`"},
                {"type": "mrkdwn", "text": f"*Post Results To*\n{target_display}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Reason for Generation*\n{notes}"},
        },
        {"type": "divider"},
    ])

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "✅ Press *Confirm & Generate* to create these promo codes\n"
                "❌ Press *Cancel* to go back and make changes"
            ),
        },
    })

    return {
        "type": "modal",
        "callback_id": "promo_gui_confirm",
        "title": {"type": "plain_text", "text": "Confirm Generation"},
        "submit": {"type": "plain_text", "text": "✓ Confirm & Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps(meta),
        "blocks": blocks,
    }


def build_user_status_modal(
    *,
    entries: list,
    partner: str,
    notes: str,
    target_display: str,
    target_for_results: str,
    promo_records: list,
) -> dict:
    """Build a modal showing each user's existing subscription status before confirmation."""
    by_user = defaultdict(list)
    for rec in promo_records:
        by_user[rec.get("promoCodeUser", "").lower()].append(rec)

    ids = [e["user_id"] for e in entries]
    new_count = sum(1 for uid in ids if uid.lower() not in by_user)
    existing_count = len(ids) - new_count
    has_any_device = any(e.get("device_id") for e in entries)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "User Status Preview", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"{len(ids)} user(s) entered  ·  "
                        f"🟢 {new_count} new  ·  🟡 {existing_count} existing"
                    ),
                }
            ],
        },
        {"type": "divider"},
    ]

    # Device ID verification notice at top
    if has_any_device:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "⚠️ *Device ID Verification*\n"
                    "Please double-check that each device ID below is correct. "
                    "Once generated, promo codes will be permanently linked to "
                    "these devices and cannot be reassigned."
                ),
            },
        })
        blocks.append({"type": "divider"})

    for entry in entries:
        uid = entry["user_id"]
        records = by_user.get(uid.lower(), [])

        # Duration display
        dur_text = entry["duration"]
        if entry.get("till_date"):
            try:
                till_fmt = datetime.strptime(entry["till_date"], "%Y-%m-%d").strftime("%b %d, %Y")
                dur_text = f"{entry['duration']} (till {till_fmt})"
            except ValueError:
                pass

        # User heading
        if not records:
            heading = f"🟢  *{uid}*\n_New user — no existing promos_"
        else:
            heading = f"🟡  *{uid}*\n_{len(records)} existing promo(s)_"

        # Request settings — device ID on its own line for full visibility
        lines = [
            heading,
            "",
            f"▸ *Prefix:*  `{entry['prefix']}`  ·  *Duration:*  `{dur_text}`",
        ]
        if entry.get("device_id"):
            lines.append(f"📱  *Device:*  `{entry['device_id']}`")

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        })

        # Existing promo history (context block — smaller text for less clutter)
        if records:
            promo_lines = []
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
                used_icon = "✅" if used else "⬜"

                promo_lines.append(
                    f"› `{code}` · {dur} · {rec_partner} · {created_fmt}\n"
                    f"   {expiry} · {used_icon} · Devices: {len(devices)}/{device_limit}"
                )

            if len(records) > 5:
                promo_lines.append(f"_…and {len(records) - 5} more_")

            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "\n".join(promo_lines)}],
            })

        blocks.append({"type": "divider"})

    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "Press *Proceed to Confirm* to continue or *Cancel* to go back.",
        }],
    })

    if len(blocks) > 48:
        blocks = blocks[:47]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_…truncated. {len(entries)} entries total._"},
        })

    meta = {
        "entries": entries,
        "partner": partner,
        "target": target_for_results,
        "notes": notes,
    }

    return {
        "type": "modal",
        "callback_id": "promo_user_status",
        "title": {"type": "plain_text", "text": "User Status"},
        "submit": {"type": "plain_text", "text": "Proceed to Confirm"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps(meta),
        "blocks": blocks,
    }


def build_extension_history_modal(entries: list, partner: str, notes: str,
                                   target_display: str, target_for_results: str,
                                   promo_records: list):
    """Build a modal showing existing promo history for each user before granting extensions."""
    by_user = defaultdict(list)
    for rec in promo_records:
        by_user[rec.get("promoCodeUser", "").lower()].append(rec)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Extension History Review", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"{len(entries)} entry/entries · Partner: `{partner}` "
                        f"· Post to: {target_display}"
                    ),
                }
            ],
        },
        {"type": "divider"},
    ]

    has_any_device = any(e.get("device_id") for e in entries)

    if has_any_device:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "⚠️ *Device ID Verification*\n"
                    "Verify each device ID is correct — promo codes will be "
                    "permanently linked to these devices."
                ),
            },
        })
        blocks.append({"type": "divider"})

    for entry in entries:
        uid = entry["user_id"]
        records = by_user.get(uid.lower(), [])

        dur_text = entry["duration"]
        if entry.get("till_date"):
            try:
                till_fmt = datetime.strptime(entry["till_date"], "%Y-%m-%d").strftime("%b %d, %Y")
                dur_text = f"{entry['duration']} (till {till_fmt})"
            except ValueError:
                pass

        # Request settings — device ID on its own line
        settings_lines = [f"▸ *Prefix:*  `{entry['prefix']}`  ·  *Duration:*  `{dur_text}`"]
        if entry.get("device_id"):
            settings_lines.append(f"📱  *Device:*  `{entry['device_id']}`")
        settings_block = "\n".join(settings_lines)

        if not records:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"🟢  *{uid}*\n_No existing promos — new user_\n\n"
                        f"{settings_block}"
                    ),
                },
            })
        else:
            lines = [f"🟡  *{uid}*\n_{len(records)} existing promo(s)_"]
            lines.append("")
            lines.append(settings_block)

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)},
            })

            # Existing promo history in context block
            promo_lines = []
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
                promo_lines.append(f"› `{code}` · {dur} · {created_fmt}\n   {expiry}")
            if len(records) > 5:
                promo_lines.append(f"_…and {len(records) - 5} more_")
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "\n".join(promo_lines)}],
            })

        blocks.append({"type": "divider"})

    if len(blocks) > 48:
        blocks = blocks[:47]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_…truncated. {len(entries)} entries total._"},
        })

    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "Press *Proceed to Generate* to create extension codes, or *Cancel* to go back.",
        }],
    })

    meta = {
        "entries": entries,
        "partner": partner,
        "target": target_for_results,
        "notes": notes,
    }

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
