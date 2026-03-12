"""Configuration settings for the Promo Bot."""
import os
from dotenv import load_dotenv

# Load .env for local dev — override=True ensures .env values always win
# over any previously exported shell variables (prevents stale production
# keys from leaking in when you switch between prod/dev configs).
load_dotenv(override=True)

# --- Slack tokens ---
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]    # xoxb-***
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]    # xapp-***

# --- Parse/Back4App setup ---
os.environ.setdefault("PARSE_API_ROOT", os.getenv("PARSE_API_ROOT", "https://parseapi.back4app.com/"))

PARSE_APP_ID   = os.environ["PARSE_APP_ID"]
PARSE_REST_KEY = os.environ.get("PARSE_REST_KEY", "")
PARSE_MASTER   = os.environ.get("PARSE_MASTER_KEY", "")

# --- Promo defaults ---
DEFAULT_PREFIX   = os.getenv("PROMO_PREFIX", "AVZ-2DA-")
DEFAULT_DURATION = os.getenv("PROMO_DURATION", "LIFETIME")
DEFAULT_PARTNER  = os.getenv("PROMO_PARTNER",  "AVAZ")

# --- Notification settings ---
PROMO_NOTIFY_CHANNEL = os.getenv("PROMO_NOTIFY_CHANNEL", "").strip()  # Slack channel ID (e.g., C0123456789)
ENABLE_CONVERSATIONS_JOIN = os.getenv("ENABLE_CONVERSATIONS_JOIN", "0") == "1"

# --- Extension prefixes (show history before granting) ---
EXTENSION_PREFIXES = {"AVZ-ACAPEXT-", "AVZ-SPEXT-"}

# Days before expiry when an extension is freely granted
EXPIRY_THRESHOLD_DAYS = int(os.getenv("EXPIRY_THRESHOLD_DAYS", "4"))

# --- Authorization / guard rails ---
# Comma-separated Slack user IDs allowed to generate promos (e.g., "U0123ABC,U0456DEF").
# If empty/unset, everyone is allowed (backwards compatible). Set this to enable access control.
PROMO_AUTHORIZED_USER_IDS = {
    u.strip() for u in os.getenv("PROMO_AUTHORIZED_USER_IDS", "").split(",") if u.strip()
}
