import os, time, random, re, json
from typing import Set
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests

# Load .env for local dev
load_dotenv()

# --- Slack tokens ---
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]    # xoxb-***
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]    # xapp-***

# --- Parse/Back4App setup ---
os.environ.setdefault("PARSE_API_ROOT", os.getenv("PARSE_API_ROOT", "https://parseapi.back4app.com/"))

PARSE_APP_ID   = os.environ["PARSE_APP_ID"]
PARSE_REST_KEY = os.environ.get("PARSE_REST_KEY", "")
PARSE_MASTER   = os.environ.get("PARSE_MASTER_KEY", "")

DEFAULT_PREFIX   = os.getenv("PROMO_PREFIX", "AVZ-2DA-")
DEFAULT_DURATION = os.getenv("PROMO_DURATION", "LIFETIME")
DEFAULT_PARTNER  = os.getenv("PROMO_PARTNER",  "AVAZ")
PROMO_NOTIFY_CHANNEL = os.getenv("PROMO_NOTIFY_CHANNEL", "").strip()  # Slack channel ID (e.g., C0123456789)

# Helper: Build Parse REST headers
def _parse_headers():
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

def _promo_exists(promo_code_id: str) -> bool:
    api_root = os.environ["PARSE_API_ROOT"].rstrip("/")
    url = f"{api_root}/classes/PromoCodeInfo"
    params = {"where": json.dumps({"promoCodeId": promo_code_id}), "limit": 1}
    resp = requests.get(url, headers=_parse_headers(), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json() or {}
    results = data.get("results", [])
    return len(results) > 0

def _create_promo_object(payload: dict) -> None:
    api_root = os.environ["PARSE_API_ROOT"].rstrip("/")
    url = f"{api_root}/classes/PromoCodeInfo"
    resp = requests.post(url, headers=_parse_headers(), json=payload, timeout=10)
    resp.raise_for_status()

# === Promo generation logic (ported from your script) ===
_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

def _gen_suffix(seen: Set[str]) -> str:
    while True:
        s = "".join(random.choice(_CHARS) for _ in range(4))
        if s not in seen:
            seen.add(s)
            return s

def create_promo_for_user(user_id: str, prefix: str, duration: str, partner: str) -> str:
    uid = user_id.strip().lower()
    seen: Set[str] = set()
    for _ in range(100):  # retry on rare collisions
        code = f"{prefix}{_gen_suffix(seen)}"
        # If exists, try next code
        if _promo_exists(code):
            continue
        payload = {
            "promoCodeId": code,
            "promoCodeDeviceCountLimit": 1,
            "promoCodeUser": uid,
            "promoCodeDuration": duration,
            "promoCodeDistributionPartner": partner,
            # Optional fields you can add:
            # "promoCodeStartDate": "2024-09-06T11:52:13.070701",
            # "promoCodeEndDate":   "2025-09-06T11:52:13.070701",
            # "validApplicationIds": ["com.avazapp.autism.en.AvazEverydayBeta"],
        }
        _create_promo_object(payload)
        return code
    raise RuntimeError("Could not generate a unique promo after many attempts")

# === Modal UI (Block Kit) — static with permanent custom fields ===
PROMO_VIEW = {
    "type": "modal",
    "callback_id": "promo_gui_submit",
    "title": {"type": "plain_text", "text": "Generate Promos"},
    "submit": {"type": "plain_text", "text": "Generate"},
    "close": {"type": "plain_text", "text": "Cancel"},
    "blocks": [
        {
            "type": "input",
            "block_id": "users_text",
            "label": {"type": "plain_text", "text": "Users (emails or phone numbers)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "value",
                "multiline": True,
                "focus_on_load": True,
                "placeholder": {"type": "plain_text", "text": "abc@gmail.com, +14155552671, xyz@company.com\na@example.com, +919999999999\n(Comma-separated; wraps to 3 lines)"}
            },
            "hint": {"type": "plain_text", "text": "Comma-separated. Field wraps up to 3 lines for readability."}
        },
        {
            "type": "input",
            "block_id": "prefix",
            "label": {"type": "plain_text", "text": "Prefix"},
            "element": {
                "type": "static_select",
                "action_id": "value",
                "initial_option": {"text": {"type": "plain_text", "text": DEFAULT_PREFIX}, "value": DEFAULT_PREFIX},
                "options": [
                    {"text": {"type": "plain_text", "text": "AVZ-2DA-"},   "value": "AVZ-2DA-"},
                    {"text": {"type": "plain_text", "text": "AVZ-ACE-"},   "value": "AVZ-ACE-"},
                    {"text": {"type": "plain_text", "text": "AVZ-ACE1Y-"}, "value": "AVZ-ACE1Y-"},
                    {"text": {"type": "plain_text", "text": "AVZ-ACAP-"},  "value": "AVZ-ACAP-"},
                    {"text": {"type": "plain_text", "text": "AVZ-ARMB-"},  "value": "AVZ-ARMB-"},
                    {"text": {"type": "plain_text", "text": "AVZ-ACAPEXT-"},  "value": "AVZ-ACAPEXT-"},
                    {"text": {"type": "plain_text", "text": "AVZ-SPEXT-"},  "value": "AVZ-SPEXT-"},
                    {"text": {"type": "plain_text", "text": "AVZ-RZPLT-"},  "value": "AVZ-RZPLT-"},
                    {"text": {"type": "plain_text", "text": "AVZ-STRLT-"},  "value": "AVZ-STRLT-"},
                    {"text": {"type": "plain_text", "text": "AVZ-LOANER-"},  "value": "AVZ-LOANER-"},
                    {"text": {"type": "plain_text", "text": "AVZ-MGRT-"},  "value": "AVZ-MGRT-"},
                    {"text": {"type": "plain_text", "text": "AVZ-LEGACY-"},  "value": "AVZ-LEGACY-"}
                ] 
            }
        },
        {
            "type": "input",
            "block_id": "custom_prefix",
            "optional": True,
            "label": {"type": "plain_text", "text": "Custom Prefix (optional)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "value",
                "placeholder": {"type": "plain_text", "text": "e.g., AVZ-TRIAL-"}
            }
        },
        {
            "type": "input",
            "block_id": "duration",
            "label": {"type": "plain_text", "text": "Duration"},
            "element": {
                "type": "static_select",
                "action_id": "value",
                "initial_option": {"text": {"type": "plain_text", "text": DEFAULT_DURATION}, "value": DEFAULT_DURATION},
                "options": [
                    {"text": {"type": "plain_text", "text": "LIFETIME"}, "value": "LIFETIME"},
                    {"text": {"type": "plain_text", "text": "30D"},      "value": "30D"},
                    {"text": {"type": "plain_text", "text": "60D"},      "value": "60D"},
                    {"text": {"type": "plain_text", "text": "90D"},      "value": "90D"},
                    {"text": {"type": "plain_text", "text": "6M"},       "value": "6M"},
                    {"text": {"type": "plain_text", "text": "1Y"},       "value": "1Y"}
                ]
            }
        },
        {
            "type": "input",
            "block_id": "custom_days",
            "optional": True,
            "label": {"type": "plain_text", "text": "Custom days (number, optional)"},
            "element": {
                "type": "number_input",
                "is_decimal_allowed": False,
                "min_value": "1",
                "action_id": "value",
                "placeholder": {"type": "plain_text", "text": "e.g., 45 (overrides Duration if set)"}
            }
        },
    ]
}

# === Utilities to parse multi-input users ===
EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RX = re.compile(r"^\+?\d{7,15}$")  # simple E.164-ish

def _norm_id(s: str) -> str:
    s = s.strip()
    if "@" in s:
        return s.lower()
    return re.sub(r"[^\d+]", "", s)  # keep only + and digits

def parse_ids(raw: str):
    parts = [p for p in re.split(r"\s*,\s*", raw or "") if p]
    ids = [_norm_id(p) for p in parts]
    # dedupe retain order
    seen = {}
    for identifier in ids:
        if identifier not in seen:
            seen[identifier] = True
    return list(seen.keys())

# === Notify helper ===
def _notify_channel_if_configured(client, notify_channel: str, target: str, prefix: str, duration: str, partner: str, processed_count: int, errors: int, requester_user_id: str) -> None:
    channel = (notify_channel or "").strip()
    if not channel:
        return

    # Best-effort join for public channels (C…)
    if re.fullmatch(r"C[A-Z0-9]+", channel):
        try:
            client.conversations_join(channel=channel)
        except Exception as e:
            # Ignore join failures; we'll attempt to post anyway
            print(f"[notify] conversations_join failed for {channel}: {e}")

    try:
        requester = f"<@{requester_user_id}>"
    except Exception:
        requester = "unknown"

    text = "\n".join([
        f"*Promo generation completed* by {requester}",
        f"Channel: <#{target}>",
        f"Prefix: `{prefix}` · Duration: `{duration}` · Partner: `{partner}`",
        f"Processed: {processed_count} · Errors: {errors}",
    ])

    try:
        client.chat_postMessage(channel=channel, text=text)
    except Exception as e:
        # Fall back: DM requester with the error for visibility
        print(f"[notify] chat_postMessage failed for {channel}: {e}")
        try:
            dm = client.conversations_open(users=requester_user_id)
            dm_channel = dm["channel"]["id"]
            client.chat_postMessage(
                channel=dm_channel,
                text=(
                    f"Could not post summary to {channel}. "
                    f"Please invite the bot to that channel (or set a valid channel ID).\n"
                    f"Error: {e}"
                ),
            )
        except Exception as e2:
            print(f"[notify] DM fallback failed: {e2}")

# === Bolt App ===
app = App(token=SLACK_BOT_TOKEN)

## Removed dynamic re-render actions; modal is static now

# Global shortcut → open modal
@app.shortcut("promo_global_shortcut")
def open_promo_modal(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=PROMO_VIEW)

# Slash command → open modal with private_metadata for channel reply routing
@app.command("/generate-promo")
def open_from_cmd(ack, body, client):
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={**PROMO_VIEW, "private_metadata": body.get("channel_id", "")},
    )

# Modal submission → validate → generate → DM CSV
@app.view("promo_gui_submit")
def handle_promo_submit(ack, body, client, view):
    vals = view["state"]["values"]
    # Safely read users input; Slack may send None for empty plain_text_input
    _users_block = vals.get("users_text") or {}
    _users_action = _users_block.get("value") or {}
    raw = _users_action.get("value") or ""
    # If users pasted line-separated entries without commas, show a clear error
    if ("\n" in raw or "\r" in raw) and "," not in raw:
        ack({
            "response_action": "errors",
            "errors": {"users_text": "Use commas to separate entries. Line breaks are not separators."}
        })
        return

    ids = parse_ids(raw)

    # Inline validation (before ack):
    if not ids:
        ack({
            "response_action": "errors",
            "errors": {"users_text": "Enter at least one email or phone. Separate with commas only."}
        })
        return
    invalid = [x for x in ids if not (EMAIL_RX.match(x) or PHONE_RX.match(x))]
    if invalid:
        ack({
            "response_action": "errors",
            "errors": {"users_text": f"These look invalid: {', '.join(invalid[:5])}"}
        })
        return

    # Validate custom days if provided
    _custom_block = vals.get("custom_days") or {}
    _custom_action = _custom_block.get("value") or {}
    custom_days_raw = ( _custom_action.get("value") or "" ).strip()
    if custom_days_raw:
        if not re.fullmatch(r"\d+", custom_days_raw) or int(custom_days_raw) <= 0:
            ack({
                "response_action": "errors",
                "errors": {"custom_days": "Enter a positive number of days (e.g., 45)."}
            })
            return

    # Passed validation → proceed
    # Determine selected values
    selected_prefix_opt = (vals.get("prefix", {}).get("value", {}).get("selected_option") or {})
    selected_duration_opt = (vals.get("duration", {}).get("value", {}).get("selected_option") or {})
    selected_partner_opt = (vals.get("partner", {}).get("value", {}).get("selected_option") or {})

    partner = selected_partner_opt.get("value", DEFAULT_PARTNER)

    # Compute duration: custom_days overrides dropdown if present
    duration_choice = selected_duration_opt.get("value", DEFAULT_DURATION)
    if custom_days_raw:
        duration = f"{int(custom_days_raw)}D"
    else:
        duration = duration_choice

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

    # Push confirmation modal
    confirm_view = {
        "type": "modal",
        "callback_id": "promo_gui_confirm",
        "title": {"type": "plain_text", "text": "Confirm Generation"},
        "submit": {"type": "plain_text", "text": "Confirm"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps({
            "ids": ids,
            "prefix": prefix,
            "duration": duration,
            "partner": partner,
            "target": target_for_results,
        }),
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": "You're about to generate promo codes with the following settings:"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Prefix*\n`{prefix}`"},
                {"type": "mrkdwn", "text": f"*Duration*\n`{duration}`"},
                {"type": "mrkdwn", "text": f"*Partner*\n`{partner}`"},
                {"type": "mrkdwn", "text": f"*Users*\n{len(ids)}"},
                {"type": "mrkdwn", "text": f"*Post to*\n{target_display}"},
            ]},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "Press Confirm to proceed or Cancel to go back."}},
        ],
    }

    ack({
        "response_action": "push",
        "view": confirm_view,
    })

# Confirmation submit → generate → post results
@app.view("promo_gui_confirm")
def handle_promo_confirm(ack, body, client, view):
    # Close the confirm modal immediately
    ack()

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

    target = data.get("target") or None
    if not target:
        dm = client.conversations_open(users=body["user"]["id"])  # returns D… id
        target = dm["channel"]["id"]

    rows, errors = [], 0
    for uid in ids:
        try:
            promo_id = create_promo_for_user(uid, prefix, duration, partner)
            rows.append((uid, promo_id, duration, partner))
        except Exception as e:
            rows.append((uid, f"ERROR: {e}", duration, partner))
            errors += 1

    lines = [f"*Promo results* (prefix={prefix}, duration={duration}, partner={partner})",
             f"Processed: {len(ids)} · Errors: {errors}"]
    for uid, code_or_err, _, _ in rows:
        if str(code_or_err).startswith("ERROR:"):
            lines.append(f"• `{uid}` → _{code_or_err}_")
        else:
            lines.append(f"• `{uid}` → `{code_or_err}`")

    client.chat_postMessage(channel=target, text="\n".join(lines))

    # Optional: also notify a specific channel if configured
    _notify_channel_if_configured(
        client=client,
        notify_channel=PROMO_NOTIFY_CHANNEL,
        target=target,
        prefix=prefix,
        duration=duration,
        partner=partner,
        processed_count=len(ids),
        errors=errors,
        requester_user_id=body["user"]["id"],
    )

# --- Optional: Uncomment if you want text commands as well ---
# @app.command("/promo")
# def promo_single_cmd(ack, respond, command):
#     ack()
#     text = (command.get("text") or "").strip()
#     if not text:
#         respond("Usage: /promo user@example.com [prefix=...] [duration=...] [partner=...]")
#         return
#     parts = text.split()
#     uid = parts[0]
#     prefix = DEFAULT_PREFIX; duration = DEFAULT_DURATION; partner = DEFAULT_PARTNER
#     for p in parts[1:]:
#         if p.startswith("prefix="):   prefix = p.split("=",1)[1]
#         elif p.startswith("duration="): duration = p.split("=",1)[1]
#         elif p.startswith("partner="):  partner = p.split("=",1)[1]
#     try:
#         code = create_promo_for_user(uid, prefix, duration, partner)
#         respond(f"✅ {code} for {uid} (duration={duration}, partner={partner})")
#     except Exception as e:
#         respond(f"❌ Failed: {e}")

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()