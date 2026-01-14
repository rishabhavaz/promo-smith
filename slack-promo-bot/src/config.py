"""Configuration settings for the Promo Bot."""
import os
from dotenv import load_dotenv

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

# --- Promo defaults ---
DEFAULT_PREFIX   = os.getenv("PROMO_PREFIX", "AVZ-2DA-")
DEFAULT_DURATION = os.getenv("PROMO_DURATION", "LIFETIME")
DEFAULT_PARTNER  = os.getenv("PROMO_PARTNER",  "AVAZ")

# --- Notification settings ---
PROMO_NOTIFY_CHANNEL = os.getenv("PROMO_NOTIFY_CHANNEL", "").strip()  # Slack channel ID (e.g., C0123456789)
ENABLE_CONVERSATIONS_JOIN = os.getenv("ENABLE_CONVERSATIONS_JOIN", "0") == "1"

# --- Authorization / guard rails ---
# Comma-separated Slack user IDs allowed to generate promos (e.g., "U0123ABC,U0456DEF").
# If empty/unset, everyone is allowed (backwards compatible). Set this to enable access control.
PROMO_AUTHORIZED_USER_IDS = {
    u.strip() for u in os.getenv("PROMO_AUTHORIZED_USER_IDS", "").split(",") if u.strip()
}
