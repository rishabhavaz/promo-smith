"""Slack notification helpers."""
import re
from src.config import ENABLE_CONVERSATIONS_JOIN


def notify_channel(client, notify_channel_id: str, target: str,
                   processed_count: int, errors: int, requester_user_id: str,
                   notes: str = "", rows: list = None) -> None:
    """Send a notification to a configured channel about promo generation.

    Args:
        client: Slack client instance
        notify_channel_id: Channel ID to send notification to
        target: Where results were posted
        processed_count: Number of promos processed
        errors: Number of errors encountered
        requester_user_id: ID of user who requested generation
        notes: Optional notes/reason for generation
        rows: List of result dicts with keys: user_id, result, prefix, duration, partner, device_id
    """
    channel = (notify_channel_id or "").strip()
    if not channel:
        return

    if ENABLE_CONVERSATIONS_JOIN and re.fullmatch(r"C[A-Z0-9]+", channel):
        try:
            client.conversations_join(channel=channel)
        except Exception as e:
            print(f"[notify] conversations_join failed for {channel}: {e}")

    try:
        requester = f"<@{requester_user_id}>"
    except Exception:
        requester = "unknown"

    # Collect unique prefixes and durations from rows for the summary line
    prefixes = []
    durations = []
    partner = ""
    for row in (rows or []):
        p = row.get("prefix", "")
        d = row.get("duration", "")
        if p and p not in prefixes:
            prefixes.append(p)
        if d and d not in durations:
            durations.append(d)
        if not partner:
            partner = row.get("partner", "")

    prefix_str = ", ".join(f"`{p}`" for p in prefixes) if prefixes else "—"
    duration_str = ", ".join(f"`{d}`" for d in durations) if durations else "—"
    partner_str = f"`{partner}`" if partner else "—"

    lines = [
        f"*Promo generation completed* by {requester}",
        f"Channel: <#{target}>",
        f"Prefix: {prefix_str} · Duration: {duration_str} · Partner: {partner_str}",
    ]

    if notes:
        lines.append(f'Notes: "{notes}"')

    lines.append(f"Processed: {processed_count} · Errors: {errors}")

    if rows:
        lines.append("\n*Generated Codes:*")
        for row in rows:
            uid = row["user_id"]
            result = row["result"]
            device_id = row.get("device_id")

            line = f"• `{uid}` → `{result}`"
            if device_id:
                line += f" · 📱 `{device_id}`"
            lines.append(line)

    text = "\n".join(lines)

    try:
        client.chat_postMessage(channel=channel, text=text)
    except Exception as e:
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


def format_results_message(notes: str, entries: list, rows: list, errors: int) -> str:
    """Format the promo generation results message posted to the target channel.

    Args:
        notes: Generation notes/reason
        entries: List of entry dicts submitted by the user
        rows: List of result dicts (user_id, result, prefix, duration, partner, device_id)
        errors: Number of errors
    """
    # Collect unique prefixes and durations for the header
    prefixes = []
    durations = []
    partner = ""
    for row in (rows or []):
        p = row.get("prefix", "")
        d = row.get("duration", "")
        if p and p not in prefixes:
            prefixes.append(p)
        if d and d not in durations:
            durations.append(d)
        if not partner:
            partner = row.get("partner", "")

    prefix_str = ", ".join(f"`{p}`" for p in prefixes) if prefixes else "—"
    duration_str = ", ".join(f"`{d}`" for d in durations) if durations else "—"
    partner_str = f"`{partner}`" if partner else "—"

    lines = [
        f"*Promo results*",
        f"Prefix: {prefix_str} · Duration: {duration_str} · Partner: {partner_str}",
    ]

    if notes:
        lines.append(f'Notes: "{notes}"')

    lines.append(f"Processed: {len(rows)} · Errors: {errors}")

    if rows:
        lines.append("\n*Generated Codes:*")
        for row in rows:
            uid = row["user_id"]
            result = row["result"]
            device_id = row.get("device_id")

            if str(result).startswith("ERROR:"):
                line = f"• `{uid}` → _{result}_"
            else:
                line = f"• `{uid}` → `{result}`"
            if device_id:
                line += f" · 📱 `{device_id}`"
            lines.append(line)

    return "\n".join(lines)
