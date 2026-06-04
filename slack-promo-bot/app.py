"""
Promo Smith - Slack Bot for Promo Code Generation
Main application entry point.
"""
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from src.slack_ui.handlers import (
    handle_open_modal, handle_promo_submit, handle_promo_confirm,
    handle_extension_proceed, handle_user_status_proceed,
    handle_override_choice_change,
)


# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN)


@app.shortcut("promo_global_shortcut")
def open_promo_modal(ack, body, client):
    """Handle global shortcut to open promo generation modal."""
    handle_open_modal(ack, body, client)


@app.command("/generate-promo")
def open_from_cmd(ack, body, client):
    """Handle slash command to open promo generation modal."""
    # Pass channel_id as private_metadata for result routing
    channel_id = body.get("channel_id", "")
    handle_open_modal(ack, body, client, private_metadata=channel_id)


@app.action("override_choice")
def override_choice_change(ack, body, client):
    """Update modal when override choice changes."""
    handle_override_choice_change(ack, body, client)


@app.view("promo_gui_submit")
def promo_submit(ack, body, client, view):
    """Handle promo form submission and show confirmation modal."""
    handle_promo_submit(ack, body, client, view)


@app.view("promo_ext_history")
def ext_history_proceed(ack, body, client, view):
    """Handle 'Proceed to Generate' from extension history review."""
    handle_extension_proceed(ack, body, client, view)


@app.view("promo_user_status")
def user_status_proceed(ack, body, client, view):
    """Handle 'Proceed to Confirm' from user status preview."""
    handle_user_status_proceed(ack, body, client, view)


@app.view("promo_gui_confirm")
def promo_confirm(ack, body, client, view):
    """Handle confirmation and generate promo codes."""
    handle_promo_confirm(ack, body, client, view)


def main():
    """Start the Slack bot in Socket Mode."""
    print("⚡️ Promo Smith bot is starting... [v2 — 5-row table + device ID]")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
    print("✅ Promo Smith bot is running! [v2]")


if __name__ == "__main__":
    main()