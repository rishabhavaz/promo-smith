"""
Promo Smith - Slack Bot for Promo Code Generation
Main application entry point.
"""
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from src.slack_ui.handlers import handle_open_modal, handle_promo_submit, handle_promo_confirm


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


@app.view("promo_gui_submit")
def promo_submit(ack, body, client, view):
    """Handle promo form submission and show confirmation modal."""
    handle_promo_submit(ack, body, client, view)


@app.view("promo_gui_confirm")
def promo_confirm(ack, body, client, view):
    """Handle confirmation and generate promo codes."""
    handle_promo_confirm(ack, body, client, view)


def main():
    """Start the Slack bot in Socket Mode."""
    print("⚡️ Promo Smith bot is starting...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
    print("✅ Promo Smith bot is running!")


if __name__ == "__main__":
    main()