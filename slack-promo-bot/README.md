# Promo Smith - Slack Promo Code Generator Bot

A modular Slack bot for generating and managing promotional codes for the Avaz platform.

## 🚀 Quick Start

```bash
cd slack-promo-bot
source .venv/bin/activate
python app.py
```

You should see:
```
⚡️ Promo Smith bot is starting...
✅ Promo Smith bot is running!
```

## 📁 Project Structure

```
slack-promo-bot/
├── app.py                  # Main entry point (start here!)
├── src/
│   ├── config.py          # Configuration
│   ├── core/              # Business logic (generation, database)
│   ├── slack_ui/          # User interface (modals, handlers, notifications)
│   └── utils/             # Utilities (validation)
├── requirements.txt       # Dependencies
└── .env                   # Environment variables (not in git)
```

## ⚙️ Configuration

Create/edit `.env` file:
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
PARSE_APP_ID=...
PARSE_MASTER_KEY=...
PROMO_NOTIFY_CHANNEL=C...    # Optional
```

## 💡 Usage

### In Slack
- **Global Shortcut**: `promo_global_shortcut` - Opens modal anywhere
- **Slash Command**: `/generate-promo` - Opens modal in current channel

### Promo Generation Flow
1. Open modal via shortcut or command
2. Fill in: users (emails/phones), prefix, duration, notes
3. Review confirmation with full user list
4. Confirm → bot generates codes and posts results
5. Optional: notification sent to configured channel

## 🎯 Common Tasks

| I Want To... | File to Edit | Line |
|--------------|--------------|------|
| Add new prefix | `src/slack_ui/modal_views.py` | ~36 |
| Add duration option | `src/slack_ui/modal_views.py` | ~71 |
| Change validation | `src/utils/validation.py` | - |
| Modify generation | `src/core/promo_generator.py` | - |
| Update database | `src/core/parse_api.py` | - |
| Change notifications | `src/slack_ui/notifications.py` | - |
| Configure settings | `src/config.py` or `.env` | - |

## 🔄 After Making Changes

```bash
# Stop bot
pkill -f "python.*app.py"

# Restart bot
python app.py
```

## 🐛 Troubleshooting

**Import errors?**
- Check virtual env: `source .venv/bin/activate`
- Verify `__init__.py` files exist in all `src/` subdirectories

**Modal not updating?**
- Restart the bot (loads code at startup)

**Database errors?**
- Verify `.env` has correct Parse credentials

## 📐 Architecture Overview

```
┌─────────────────────┐
│   Presentation      │  ← src/slack_ui/ (modals, handlers)
├─────────────────────┤
│   Business Logic    │  ← src/core/ (generation, validation)
├─────────────────────┤
│   Data Access       │  ← src/core/parse_api.py
└─────────────────────┘
```

**Design Principles:**
- Clean separation of concerns
- No circular dependencies
- Single responsibility per module
- Easy to test and extend

## 🔒 Security

- Master key preferred over REST key
- Environment variables (never commit `.env`)
- Input validation before processing
- Error handling with fallbacks

## 📝 Developer Notes

### Adding a New Promo Prefix
Edit `src/slack_ui/modal_views.py`:
```python
# Line ~36-48: Add to options list
{"text": {"type": "plain_text", "text": "AVZ-NEWPREFIX-"}, "value": "AVZ-NEWPREFIX-"}
```

### Adding Database Fields
Edit `src/core/promo_generator.py`:
```python
# Line ~46-52: Modify payload
payload = {
    "promoCodeId": code,
    # ... existing fields
    "newField": value,  # Add here
}
```

### Testing
1. Make changes
2. Stop bot: `Ctrl+C`
3. Restart: `python app.py`
4. Test in Slack with `/generate-promo`

## 📊 Code Statistics

- **8 modules** totaling ~730 lines (was 1 file with 509 lines)
- Clean hierarchy with clear responsibilities
- Well-documented with docstrings

## 📄 License

Internal use only - Avaz Inc.