"""Slack modal view definitions."""
import json
from src.config import DEFAULT_PREFIX, DEFAULT_DURATION


def build_promo_form_modal():
    """Build the initial promo generation form modal."""
    return {
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
                    "placeholder": {"type": "plain_text", "text": "abc@gmail.com, +14155552671, xyz@company.com"}
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
            {
                "type": "input",
                "block_id": "notes",
                "label": {"type": "plain_text", "text": "Notes (reason for promo)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Why are you creating these promo codes?"}
                }
            },
        ]
    }


def build_confirmation_modal(ids: list, prefix: str, duration: str, partner: str, 
                             notes: str, target_display: str, target_for_results: str):
    """
    Build the confirmation modal with all generation details.
    
    Args:
        ids: List of user IDs
        prefix: Promo code prefix
        duration: Promo duration
        partner: Distribution partner
        notes: Reason for generation
        target_display: Display name for results destination
        target_for_results: Actual channel/DM ID for results
        
    Returns:
        Modal view dictionary
    """
    # Format user list for display (show first 20, then indicate if more)
    user_list_text = "\n".join([f"• `{uid}`" for uid in ids[:20]])
    if len(ids) > 20:
        user_list_text += f"\n_...and {len(ids) - 20} more_"
    
    return {
        "type": "modal",
        "callback_id": "promo_gui_confirm",
        "title": {"type": "plain_text", "text": "Confirm Generation"},
        "submit": {"type": "plain_text", "text": "✓ Confirm & Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps({
            "ids": ids,
            "prefix": prefix,
            "duration": duration,
            "partner": partner,
            "target": target_for_results,
            "notes": notes,
        }),
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
                {"type": "mrkdwn", "text": f"*Duration*\n`{duration}`"},
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
