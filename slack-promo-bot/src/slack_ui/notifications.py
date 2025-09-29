"""Slack notification helpers."""
import re
from src.config import ENABLE_CONVERSATIONS_JOIN


def notify_channel(client, notify_channel: str, target: str, prefix: str, duration: str, 
                  partner: str, processed_count: int, errors: int, requester_user_id: str, 
                  notes: str = "", rows: list = None) -> None:
    """
    Send a notification to a configured channel about promo generation.
    
    Args:
        client: Slack client instance
        notify_channel: Channel ID to send notification to
        target: Where results were posted
        prefix: Promo code prefix used
        duration: Duration used
        partner: Partner used
        processed_count: Number of promos processed
        errors: Number of errors encountered
        requester_user_id: ID of user who requested generation
        notes: Optional notes/reason for generation
        rows: Optional list of (user_id, promo_code, duration, partner) tuples
    """
    channel = (notify_channel or "").strip()
    if not channel:
        return

    # Optional join for public channels (C…) — disabled by default to avoid missing_scope logs
    if ENABLE_CONVERSATIONS_JOIN and re.fullmatch(r"C[A-Z0-9]+", channel):
        try:
            client.conversations_join(channel=channel)
        except Exception as e:
            # Ignore join failures; we'll attempt to post anyway
            print(f"[notify] conversations_join failed for {channel}: {e}")

    try:
        requester = f"<@{requester_user_id}>"
    except Exception:
        requester = "unknown"

    lines = [
        f"*Promo generation completed* by {requester}",
        f"Channel: <#{target}>",
        f"Prefix: `{prefix}` · Duration: `{duration}` · Partner: `{partner}`",
    ]
    
    if notes:
        lines.append(f"Notes: {notes}")
    
    lines.append(f"Processed: {processed_count} · Errors: {errors}")
    
    # Add generated promo codes
    if rows:
        lines.append("\n*Generated Codes:*")
        for uid, code_or_err, _, _ in rows:
            if str(code_or_err).startswith("ERROR:"):
                lines.append(f"• `{uid}` → _{code_or_err}_")
            else:
                lines.append(f"• `{uid}` → `{code_or_err}`")
    
    text = "\n".join(lines)

    try:
        client.chat_postMessage(channel=channel, text=text)
    except Exception as e:
        # Fall back: DM requester with the error for visibility
        print(f"[notify] chat_postMessage failed for {channel}: {e}")
        _fallback_dm_requester(client, requester_user_id, channel, e)


def _fallback_dm_requester(client, requester_user_id: str, channel: str, error: Exception):
    """Send a DM to the requester if channel notification fails."""
    try:
        dm = client.conversations_open(users=requester_user_id)
        dm_channel = dm["channel"]["id"]
        client.chat_postMessage(
            channel=dm_channel,
            text=(
                f"Could not post summary to {channel}. "
                f"Please invite the bot to that channel (or set a valid channel ID).\n"
                f"Error: {error}"
            ),
        )
    except Exception as e2:
        print(f"[notify] DM fallback failed: {e2}")


def format_results_message(prefix: str, duration: str, partner: str, 
                          notes: str, ids: list, rows: list, errors: int) -> str:
    """
    Format the promo generation results message.
    
    Args:
        prefix: Promo code prefix
        duration: Duration
        partner: Partner
        notes: Generation notes/reason
        ids: List of user IDs
        rows: List of (user_id, promo_code, duration, partner) tuples
        errors: Number of errors
        
    Returns:
        Formatted message string
    """
    lines = [f"*Promo results* (prefix={prefix}, duration={duration}, partner={partner})"]
    
    if notes:
        lines.append(f"Notes: {notes}")
        
    lines.append(f"Processed: {len(ids)} · Errors: {errors}")
    
    for uid, code_or_err, _, _ in rows:
        if str(code_or_err).startswith("ERROR:"):
            lines.append(f"• `{uid}` → _{code_or_err}_")
        else:
            lines.append(f"• `{uid}` → `{code_or_err}`")
            
    return "\n".join(lines)
