# Promo Smith — Project Overview & UI/UX

Promo Smith is an internal Slack bot that helps Avaz team members generate promotional codes for one or more users (email addresses and/or phone numbers). It provides a guided Slack modal experience with validation, a confirmation step, and clear result reporting.

## What the bot does

- **Generates promo codes**: For each user identifier provided, the bot creates a promo code of the form `PREFIX + 4-char suffix` (e.g. `AVZ-2DA-7KQ2`).
- **Persists promos to Parse/Back4App**: Writes records into the `PromoCodeInfo` class via the Parse REST API.
- **Prevents collisions**: Checks whether a generated promo already exists before creating it (retries on rare collisions).
- **Posts results back to Slack**: Shows a per-user success/error list after generation.
- **Optionally notifies an audit channel**: If `PROMO_NOTIFY_CHANNEL` is configured, it posts a summary there too.
- **Supports extension workflows**: For extension prefixes, it shows a history review screen before allowing generation.

## How users access it in Slack

Promo Smith supports two entry points:

- **Slash command**: `/generate-promo`
  - Opens the modal and automatically routes results back to the **current channel** (where the command was invoked).
- **Global shortcut**: `promo_global_shortcut`
  - Opens the modal from anywhere and routes results to the requester’s **DM** (because there may be no channel context).

If access control is enabled (see **Authorization & guardrails**), unauthorized users get:

- **Slash command**: an immediate text response (no modal opened).
- **Global shortcut**: an **“Access denied”** modal.

## UI/UX flow (what the user experiences)

### 1) “Generate Promos” form modal

Users fill a single modal titled **“Generate Promos”** and click **Generate**.

#### Fields

- **Users (emails or phone numbers)** (`users_text`)
  - Input: multi-line text box (focuses on load).
  - Format: **comma-separated only**.
  - UX guardrail: if the user enters line breaks but no commas, the bot shows an inline error: *“Use commas to separate entries. Line breaks are not separators.”*
  - Normalization:
    - Emails are lowercased.
    - Phone numbers are normalized to an “E.164-ish” form by keeping only `+` and digits.
  - Validation:
    - Email: must match a basic email pattern.
    - Phone: `+` optional, 7–15 digits.

- **Prefix** (`prefix`)
  - Input: dropdown of known Avaz promo prefixes.
  - Some prefixes are treated as **extension prefixes** (see “Extension history review” below).

- **Custom Prefix (optional)** (`custom_prefix`)
  - Input: free text.
  - Behavior: if provided, it **overrides** the Prefix dropdown selection.

- **Duration** (`duration`)
  - Input: dropdown (e.g. `LIFETIME`, `30D`, `60D`, `90D`, `6M`, `1Y`).

- **Validity override** (`override_type`)
  - Input: radio buttons that dynamically change the form.
  - Options:
    - **Use Duration dropdown** (no override)
    - **Override with day count**
    - **Override with end date**
  - Dynamic UI:
    - If **day count** is selected, the modal updates to show **Number of days** (`custom_days`) as a number input.
    - If **end date** is selected, the modal updates to show **End date** (`till_date`) as a datepicker.
  - Validation:
    - Day count must be a **positive integer**.
    - End date must be a **future date**; the bot converts it to an `XD` duration where \(X\) is the number of days from “today”.

- **Notes (reason for promo)** (`notes`)
  - Input: multi-line text box.
  - Required: the bot blocks submission if empty (inline error).

### 2) Submit → validation → next screen

When the user clicks **Generate**, the bot validates inputs and then pushes one of two follow-up modals:

### A) Normal prefixes → “Confirm Generation” modal

For most prefixes, the bot pushes a confirmation modal titled **“Confirm Generation”**.

It shows a clear “review before confirming” summary:

- Prefix
- Duration (and “till date” annotation if applicable)
- Partner (currently defaults from config and is not exposed as a form field)
- Where results will be posted (channel for `/generate-promo`, otherwise DM)
- Notes / reason
- User list (up to 20 shown; remainder summarized)

CTA button: **“✓ Confirm & Generate”**.

### B) Extension prefixes → “Extension History” review modal

For extension prefixes (configured in `EXTENSION_PREFIXES`), the bot inserts an extra safety step before confirmation:

- It fetches existing promo history for each user.
- It shows an **“Extension History Review”** screen listing existing promo codes per user (up to 5 per user, newest first), including:
  - Promo code ID
  - Stored duration string
  - Created date
  - An expiry status (e.g. “X days left”, “Expires today”, or “Expired … days ago”) when the duration can be interpreted as days/months/years.

CTA button: **“Proceed to Generate”**, which then pushes the normal **“Confirm Generation”** modal.

### 3) Confirm → generation → results message

When the user confirms:

- The modal stack is closed.
- The bot generates one promo per user and writes them to Parse.
- The bot posts a results message to:
  - The original channel (when invoked via `/generate-promo`), or
  - A DM channel (when invoked via the global shortcut, or if posting fails).

The results message includes:

- The chosen prefix/duration/partner
- Notes
- Totals (processed, errors)
- A per-user list:
  - `user_id → promo_code`, or
  - `user_id → ERROR: ...` if generation failed for that entry

## Authorization & guardrails

- **Allow-list support**: Set `PROMO_AUTHORIZED_USER_IDS` to a comma-separated list of Slack member IDs (`U...`) to restrict who can generate promos.
  - If unset/empty, the bot allows everyone (backwards compatible).
- **Input validation**: Users must be comma-separated, valid email/phone identifiers; Notes are mandatory.
- **Slack posting fallbacks**:
  - If posting results to the target channel fails, the bot attempts a DM fallback.
  - If audit notification fails, the bot attempts to DM the requester with the error details.

## Where to look in the code (UI/UX)

- **Entry points**: `app.py` (slash command + shortcut + handlers)
- **Modal layouts**: `src/slack_ui/modal_views.py`
- **UX orchestration + validation**: `src/slack_ui/handlers.py`
- **Result/notification messages**: `src/slack_ui/notifications.py`
- **User parsing/validation rules**: `src/utils/validation.py`
- **Authorization behavior**: `src/utils/authz.py`
- **Parse persistence**: `src/core/parse_api.py` and `src/core/promo_generator.py`

