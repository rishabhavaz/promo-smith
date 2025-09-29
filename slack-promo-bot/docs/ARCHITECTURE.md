# Promo Smith - Architecture Overview

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Slack App                            │
│                  (Commands & Shortcuts)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                        app.py                                │
│                   (Main Entry Point)                         │
│  • Registers Slack handlers                                  │
│  • Routes events to handlers                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐           ┌──────────────────┐
│   src/config.py  │           │  src/slack_ui/   │
│                  │           │    handlers.py   │
│ • Environment    │◄──────────┤                  │
│ • Defaults       │           │ • Form submit    │
│ • Tokens         │           │ • Confirmation   │
└──────────────────┘           │ • Orchestration  │
                               └────────┬─────────┘
                                        │
                     ┌──────────────────┼──────────────────┐
                     │                  │                  │
                     ▼                  ▼                  ▼
        ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
        │  src/slack_ui/  │  │   src/utils/    │  │   src/core/     │
        │  modal_views.py │  │  validation.py  │  │ promo_generator │
        │                 │  │                 │  │      .py        │
        │ • Form modal    │  │ • Parse IDs     │  │                 │
        │ • Confirmation  │  │ • Validate      │  │ • Generate code │
        │   modal         │  │   emails/phones │  │ • Check exists  │
        └─────────────────┘  └─────────────────┘  └────────┬────────┘
                                                            │
                                                            ▼
        ┌─────────────────┐                      ┌─────────────────┐
        │  src/slack_ui/  │                      │   src/core/     │
        │ notifications.py│                      │  parse_api.py   │
        │                 │                      │                 │
        │ • Format msgs   │                      │ • DB queries    │
        │ • Post to Slack │                      │ • Create promo  │
        │ • Fallback DM   │                      │ • Auth headers  │
        └─────────────────┘                      └────────┬────────┘
                                                          │
                                                          ▼
                                               ┌─────────────────────┐
                                               │  Parse/Back4App DB  │
                                               │  (PromoCodeInfo)    │
                                               └─────────────────────┘
```

## 📦 Module Responsibilities

### **app.py** (Entry Point)
- Initializes Slack Bolt app
- Registers shortcuts (`promo_global_shortcut`)
- Registers slash commands (`/generate-promo`)
- Registers view handlers (submit, confirm)
- Starts Socket Mode handler

### **src/config.py** (Configuration)
- Loads `.env` variables
- Defines constants (tokens, defaults, channels)
- Single source of truth for settings

### **src/slack_ui/** (User Interface Layer)

#### handlers.py
- `handle_open_modal()` - Opens promo form
- `handle_promo_submit()` - Validates & shows confirmation
- `handle_promo_confirm()` - Generates codes & posts results

#### modal_views.py
- `build_promo_form_modal()` - Initial input form
- `build_confirmation_modal()` - Review screen with details

#### notifications.py
- `notify_channel()` - Sends to configured channel
- `format_results_message()` - Formats promo results
- `_fallback_dm_requester()` - DM on channel failure

### **src/core/** (Business Logic Layer)

#### promo_generator.py
- `create_promo_for_user()` - Main generation function
- `_gen_suffix()` - Random 4-char suffix
- Handles collision retry logic

#### parse_api.py
- `promo_exists()` - Check for duplicates
- `create_promo_object()` - Insert into DB
- `_parse_headers()` - Auth header builder

### **src/utils/** (Utilities)

#### validation.py
- `parse_user_ids()` - Parse comma-separated input
- `validate_user_id()` - Email/phone validation
- `_norm_id()` - Normalize IDs

## 🔄 Data Flow

### 1. User Interaction
```
User → Slash Command/Shortcut → app.py → handle_open_modal()
```

### 2. Form Submission
```
User fills form → Submit → handle_promo_submit()
  ↓
parse_user_ids() → validate_user_id()
  ↓
build_confirmation_modal() → Push to Slack
```

### 3. Confirmation & Generation
```
User confirms → handle_promo_confirm()
  ↓
FOR EACH user_id:
  create_promo_for_user()
    ↓
  _gen_suffix() → Check promo_exists() → create_promo_object()
  ↓
Collect results → format_results_message()
  ↓
Post to channel + notify_channel()
```

## 🎯 Design Principles

1. **Separation of Concerns**
   - UI logic separated from business logic
   - API interactions isolated
   - Configuration centralized

2. **Clear Dependencies**
   - One-way dependency flow (no circular imports)
   - Core modules don't depend on UI modules
   - Utils are standalone

3. **Single Responsibility**
   - Each module has one clear purpose
   - Functions do one thing well
   - Easy to test and maintain

4. **Extensibility**
   - Add new prefixes in `modal_views.py`
   - Add new validation rules in `validation.py`
   - Swap DB backend by changing `parse_api.py`

## 🔒 Security Layers

- Environment variables for sensitive data
- Master key preferred over REST key
- Input validation before processing
- Error handling with graceful fallbacks
