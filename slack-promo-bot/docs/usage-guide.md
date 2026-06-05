# Promo Smith — Usage Guide

> **Audience:** Support & Marketing teams  
> **Last updated:** June 2026  
> **Internal tool — do not share outside the organization**

---

## Table of Contents

1. [What is Promo Smith?](#what-is-promo-smith)
2. [How to Open the Bot](#how-to-open-the-bot)
3. [Filling Out the Form](#filling-out-the-form)
4. [Understanding the Review Screens](#understanding-the-review-screens)
5. [Device ID & Mixpanel URL Guide](#device-id--mixpanel-url-guide)
6. [Extension Codes (Renewals)](#extension-codes-renewals)
7. [End Date vs Duration](#end-date-vs-duration)
8. [Dos and Don'ts](#dos-and-donts)
9. [Prefix Reference](#prefix-reference)
10. [Duration Reference](#duration-reference)
11. [Troubleshooting](#troubleshooting)

---

## What is Promo Smith?

Promo Smith is our internal Slack bot that generates promo codes for Avaz users. It connects directly to our backend (Parse/Back4App) and creates codes that unlock subscriptions on user devices.

You can:
- Generate promo codes for up to **5 users at once**
- Target a **specific device** by pasting a Mixpanel URL
- Set a **custom end date** or use a standard duration (30 days, 1 year, lifetime, etc.)
- Extend existing subscriptions using extension prefixes

---

## How to Open the Bot

There are two ways to open Promo Smith:

### Option A: Slash Command (Recommended)
Type this in any Slack channel:
```
/generate-promo
```
Results will be posted **in that same channel**.

### Option B: Global Shortcut
1. Click the **lightning bolt** icon (or press `Cmd+K` / `Ctrl+K`) in Slack
2. Search for **"Promo Smith"** or **"promo_global_shortcut"**
3. Select it

When using the shortcut, results will be sent to your **DMs with the bot**.

---

## Filling Out the Form

When the modal opens, you'll see:

### 1. Notes (at the top)
- **Required.** Write the reason for generating these promo codes.
- Example: *"User lost access after switching phones — re-issuing lifetime code"*
- This gets logged in the notification channel for audit purposes.

### 2. Entry Rows (up to 5)
Each row has these fields:

| Field | Required? | What to enter |
|-------|-----------|---------------|
| **User ID** | Yes (at least 1 row) | Email address or phone number of the user |
| **Mixpanel URL or Device ID** | No | Paste the Mixpanel profile URL or the raw device ID (see [Device ID Guide](#device-id--mixpanel-url-guide)) |
| **Prefix** | Yes (has default) | Select the promo code prefix from the dropdown |
| **Duration** | Yes (has default) | Select the duration from the dropdown |
| **End Date** | No | Pick a specific end date using the date picker. **Overrides the Duration dropdown if set.** |

- Empty rows are automatically skipped — you don't need to fill all 5.
- The first row's User ID field is auto-focused for quick entry.

### 3. Click "Generate"
This takes you to a review screen, **not** directly to code generation.

---

## Understanding the Review Screens

After you click Generate, the bot shows one or more review screens depending on the situation. **No promo codes are created until you reach the final "Confirm & Generate" step.**

### Screen 1: User Status Preview
Shows each user's current status in the database:
- **Green dot** = New user, no existing promos
- **Yellow dot** = User already has promo codes (shows existing codes, expiry, device count)

If you provided a Mixpanel URL or device ID, the **full device ID** will be displayed here. **Check it carefully** — you'll see a warning notice at the top reminding you to verify.

### Screen 2: Confirmation
A final summary of everything that's about to happen. Shows:
- Each entry with prefix, duration, and full device ID
- Partner and target channel
- Notes/reason

Click **"Confirm & Generate"** only when everything looks correct.

---

## Device ID & Mixpanel URL Guide

This is the most critical part of the process. When you target a specific device, the promo code gets **permanently linked** to that device. A wrong device ID means the code won't work for the user.

### How to Get a Mixpanel URL

1. Open **Mixpanel** and find the user's profile
2. Copy the **full URL** from your browser's address bar
3. Paste it into the **"Mixpanel URL or Device ID"** field in the form

### What the Bot Extracts

The bot reads the `distinct_id` from the Mixpanel URL and strips the app package name to get the actual device ID.

**Examples of what the bot extracts:**

| Mixpanel distinct_id | Extracted Device ID |
|---|---|
| `com.avazapp.international.lite-a772969c704b6c9f` | `a772969c704b6c9f` |
| `com.avazapp.international.lite-d75d655430db31c3` | `d75d655430db31c3` |
| `com.avazapp.autism.en.AvazSubscription-D8465185-F82C-4A0D-83FD-B2CC4C3631E6` | `D8465185-F82C-4A0D-83FD-B2CC4C3631E6` |
| `com.avazapp.autism.en_in.avaz-85ff7281ace2fec6` | `85ff7281ace2fec6` |

The bot recognizes the package name (the part before the first `-` that contains dots like `com.avazapp.…`) and removes it automatically.

### When to Paste a Raw Device ID Instead

If the Mixpanel URL doesn't work or you already have the device ID from another source, you can paste the **raw device ID** directly:
```
a772969c704b6c9f
```
or
```
D8465185-F82C-4A0D-83FD-B2CC4C3631E6
```

The bot will use it as-is without any extraction.

### How to Verify the Device ID

**Always check the device ID on the review screen before confirming.** The full device ID is shown next to the phone emoji. Compare it against what you see in Mixpanel:

1. In Mixpanel, look at the user's `distinct_id` or `$device_id` property
2. The device ID is the part **after** the package name and hyphen
3. On the review screen, the full device ID should match exactly

### If the Extraction Looks Wrong

If the bot shows an error like *"Could not extract device ID from this URL"*, or the extracted ID doesn't look right:

1. **Don't proceed** — go back and fix it
2. Go to Mixpanel, find the user's `distinct_id` value
3. Manually copy just the device ID part (after the package name)
4. Paste the **raw device ID** into the field instead of the URL

---

## Extension Codes (Renewals)

Extension prefixes (`AVZ-ACAPEXT-` and `AVZ-SPEXT-`) trigger a special flow:

1. The bot shows an **Extension History Review** screen with the user's existing promo codes
2. You review their history and click **"Proceed to Generate"**
3. Then you go through the normal confirmation screen

### Smart Extension Logic

The bot is smart about extensions:

- **User has a LIFETIME code and you request LIFETIME again** — Instead of creating a duplicate, the bot bumps the device count on the existing code (up to 5 devices max).
- **Existing code expires near your requested end date (within 5 days)** — The bot bumps the device count on that existing code instead of creating a new one.
- **Device limit reached (5 devices on a single code)** — The bot skips that entry and tells you why.
- **No matching existing code** — A brand new code is created.

---

## End Date vs Duration

You have two ways to set how long a promo code lasts:

### Duration Dropdown
Pick a preset: `LIFETIME`, `30D`, `60D`, `90D`, `6M`, or `1Y`.

### End Date Picker
Pick a specific calendar date. **This overrides the Duration dropdown** — the bot calculates the number of days from today to your chosen date and uses that instead.

For example, if today is June 5 and you pick July 27, the bot creates a code valid for 52 days.

**The end date must be in the future.** The bot will show an error if you pick today or a past date.

---

## Dos and Don'ts

### DO

- **Always fill in the Notes field** with a clear reason. This is our audit trail.
- **Double-check the user's email or phone number** before submitting. A typo means the code goes to the wrong person (or nobody).
- **Verify the device ID on the review screen.** Compare it against Mixpanel. This is the single most important check.
- **Use the End Date picker** when you know the exact date the subscription should end. It's more precise than duration.
- **Use `/generate-promo` from the relevant channel** so results are posted where your team can see them.
- **Check the existing promo history** on the User Status screen. If the user already has an active code, you may not need to create another one.
- **Paste the raw device ID** if you're unsure the Mixpanel URL is extracting correctly. It's safer to copy the device ID manually.

### DON'T

- **Don't rush through the review screens.** They exist to prevent mistakes. Read every field before clicking Confirm.
- **Don't generate LIFETIME codes unless necessary.** Use a specific duration or end date when the situation calls for a temporary subscription.
- **Don't use extension prefixes (`AVZ-ACAPEXT-`, `AVZ-SPEXT-`) for new users.** These are for renewing existing subscriptions. Use the appropriate standard prefix for new users.
- **Don't paste partial or edited Mixpanel URLs.** Either paste the complete URL or paste the raw device ID — nothing in between.
- **Don't create duplicate codes for the same user** without checking their history first. The User Status screen shows what they already have.
- **Don't ignore the "SKIPPED" or "ERROR" results.** If the bot skips an entry, read the reason. It usually means the device limit is reached or there's already an active code.
- **Don't share promo codes in public channels.** Post results in private channels or DMs only.

---

## Prefix Reference

| Prefix | Use Case |
|--------|----------|
| `AVZ-2DA-` | Standard 2-device access (default) |
| `AVZ-ACE-` | ACE program |
| `AVZ-ACE1Y-` | ACE program — 1 year |
| `AVZ-ACAP-` | ACAP program |
| `AVZ-ARMB-` | ARM-B program |
| `AVZ-ACAPEXT-` | ACAP extension / renewal |
| `AVZ-SPEXT-` | SP extension / renewal |
| `AVZ-RZPLT-` | Razorpay — Lifetime |
| `AVZ-RZP1Y-` | Razorpay — 1 year |
| `AVZ-RZP1M-` | Razorpay — 1 month |
| `AVZ-STRLT-` | Stripe — Lifetime |
| `AVZ-STR1Y-` | Stripe — 1 year |
| `AVZ-STR1M-` | Stripe — 1 month |

> Prefixes ending in `EXT-` trigger the extension flow with history review.

---

## Duration Reference

| Value | Meaning |
|-------|---------|
| `LIFETIME` | Never expires |
| `30D` | 30 days |
| `60D` | 60 days |
| `90D` | 90 days |
| `6M` | 6 months (~180 days) |
| `1Y` | 1 year (~365 days) |
| End Date picker | Calculates days from today to your chosen date |

---

## Troubleshooting

### "Could not extract device ID from this URL"
The Mixpanel URL format wasn't recognized. **Solution:** Copy the device ID manually from Mixpanel and paste it as a raw string instead of the URL.

### "Invalid user ID — Must be email or phone"
The User ID field doesn't contain a valid email or phone number. Check for typos, extra spaces, or accidental characters.

### "End date must be in the future"
Your selected End Date is today or in the past. Pick a future date.

### Results show "SKIPPED: per_code_limit_reached"
The user's existing promo code already has 5 devices attached (maximum). You cannot add more devices to that code. If the user truly needs another device, contact the dev team.

### Results show "UPDATED (devices: N)"
This is normal — the bot found an existing code that matches your request and bumped the device count instead of creating a duplicate. This is the intended behavior.

### "Promo generation failed — no entries found in metadata"
This happens when two bot instances are running simultaneously (e.g., local + Railway deployment). Only one instance should be running at a time. Check with the dev team.

### Results were posted in my DMs instead of the channel
Either the bot isn't in the target channel, or you used the global shortcut instead of `/generate-promo`. Use the slash command from the channel where you want results posted.

### I don't see the bot / "Access denied"
Your Slack user ID is not in the authorized users list. Contact the dev team to be added.
