# Telegram Manager Bot

## Overview

The Telegram Manager Bot is an interactive Telegram interface for managing active trading signals and positions in real-time. It fetches **live position data directly from MetaTrader MT5** instead of the database, ensuring you always see current market conditions and P&L.

**Features:**
- 📊 Live open positions and pending orders directly from MetaTrader
- 📈 Real-time profit/loss calculations
- 🎯 Close positions (full or half) at market price
- 🛡️ Set risk-free (move stop-loss to entry price)
- 🔄 Refresh position data on demand
- 📚 View historical signals from database
- 🔐 Optional user whitelist for security
- 📱 Support for **multiple manager chats** (personal, groups, channels)
- 🤖 Runs concurrently with signal provider (no interference)

---

## Setup Instructions

### Step 1: Get Your Telegram API Credentials

You'll need your Telegram API credentials (same as signal provider):

1. Go to https://my.telegram.org/apps
2. Log in with your Telegram account
3. Create a new application:
   - App title: "TelegramTrader Manager"
   - Short name: "telegramtrader_manager"
   - Submit
4. Copy your **API ID** and **API Hash**

### Step 2: Find Your Chat/User ID (Manager Chats)

The manager bot needs to know which chats to use for the management interface. You can configure **multiple chats** (personal, groups, channels):

**Option A: Use Your Personal Chat (Recommended for Testing)**
1. Open Telegram and search for `@userinfobot`
2. Message it `/start`
3. Copy your **User ID** (format: `12345678`)

**Option B: Use Private Groups/Channels**
1. Create private groups or channels
2. Add `@userinfobot` to each group
3. Send `/start` in each group
4. Copy the **Chat IDs** (format: `-100123456789`)

**Option C: Mix Multiple Chats**
You can add multiple User IDs and Chat IDs to manage trades from different interfaces.

### Step 3: Create a Telegram Bot Token (Optional)

If you want to use a separate bot for the manager instead of your user account:

1. Message `@BotFather` on Telegram
2. Send `/newbot`
3. Follow prompts to create a new bot
4. Copy the **Bot Token** (format: `123456789:ABCdefGHIjklmnoPQRstuvWXYZ`)
5. Add the bot to your manager chat

**Note:** If you don't have a `bot_token`, the bot will use the same Telegram session as the signal provider.

### Step 4: Configure settings.json

Add the `telegram_bot` section under `providers` in your `settings.json`:

```json
{
  "Telegram": {
    "api_id": 12345678,
    "api_hash": "YOUR_TELEGRAM_API_HASH_HERE",
    "channels": {
      "whiteList": ["@your_channel_username"],
      "blackList": []
    }
  },
  "providers": {
    "telegram_bot": {
      "enabled": true,
      "bot_token": null,
      "allowed_users": [],
      "button_labels": {
        "close_full": "Close Full",
        "close_half": "Close Half",
        "risk_free": "Risk Free",
        "refresh": "Refresh"
      }
    }
  }
}
```

**Note:** If you don't have a `providers` section in your settings, create it. You can also add other providers (Discord, etc.) in the same section.

**Configuration Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | bool | No | `true` | Enable/disable manager bot |
| `bot_token` | string | No | `null` | Bot token from BotFather (if null, uses Telegram session) |
| `allowed_users` | array | No | `[]` | List of user IDs allowed to use manager (empty = all users allowed) |
| `button_labels` | object | No | (defaults) | Customizable button text for different languages |

### Step 5: Restart the Application

```bash
python runner.py
```

Check logs for:
```
Telegram Manager Bot loaded
Telegram Manager Bot started for chat 12345678
```

---

## Usage Guide

### Commands

Send these commands in the manager chat:

#### `/active`
Lists all active signals with their entry prices, stop-loss, and take-profit levels.

**Example Output:**
```
📊 ACTIVE SIGNALS

EURUSD | BUY
Entry: 1.0550 | SL: 1.0520
TP: 1.0650 1.0750 1.0850
Created: 2025-12-11 10:30:00

GBPUSD | SELL
Entry: 1.2380 | SL: 1.2450
TP: 1.2300 1.2200 1.2100
Created: 2025-12-11 10:25:00
```

#### `/positions`
Shows all open positions with current profit/loss and action buttons.

**Example Output:**
```
📈 OPEN POSITIONS

EURUSD BUY | 1.5L
Entry: 1.0550 | Current: 1.0580
SL: 1.0520 | TP: 1.0650
📈 P&L: $45.00 (0.43%)

[Close Full] [Close Half] [Risk Free] [Refresh]
```

#### `/signals`
Lists recent signals (last 50) with their status (Active/Closed).

**Example Output:**
```
📋 ALL SIGNALS (Last 50)

EURUSD | BUY | ✅ Active
GBPUSD | SELL | ❌ Closed
GOLD | BUY | ✅ Active
...
```

#### `/help`
Shows all available commands and actions.

---

## Position Action Buttons

### Close Full ❌
Closes the entire position immediately.

**Action:** Closes all lots at current market price  
**Example:** If you have 1.5L open, closes all 1.5L  
**Confirmation:** "✅ Position Closed Successfully"

### Close Half 📉
Closes 50% of the position for scaling out.

**Action:** Closes half the position at current market price  
**Example:** If you have 1.5L open, closes 0.75L (remaining: 0.75L)  
**Confirmation:** "✅ Half Position Closed Successfully"

### Risk Free 🛡️
Moves the stop-loss to the entry price, making the position risk-free.

**Action:** Updates SL to entry price  
**Example:** Entry 1.0550 with SL 1.0520 → SL becomes 1.0550  
**Best Use:** When position is profitable and you want to lock in profit  
**Confirmation:** "✅ Stop Loss Moved to Entry"

### Refresh 🔄
Updates position data and P&L display.

**Action:** Fetches current position data from MetaTrader  
**Use Case:** Verify latest P&L without reopening the bot  
**Confirmation:** "✅ Updated"

---

## Configuration Examples

### Example 1: Basic Setup (All Users Allowed)

```json
"providers": {
  "telegram_bot": {
    "enabled": true,
    "bot_token": null,
    "allowed_users": []
  }
}
```

Manager runs in your Telegram account. Live position data fetched directly from MetaTrader. Accessible from your account and any user who messages the bot (if allowed_users is empty).

### Example 2: Restricted to Specific Users Only

```json
"providers": {
  "telegram_bot": {
    "enabled": true,
    "bot_token": null,
    "allowed_users": [123456789, 987654321]
  }
}
```

Manager accessible only to specified user IDs. Other users will receive "You are not authorized" message.

### Example 3: With Dedicated Bot Token & Custom Labels

```json
"providers": {
  "telegram_bot": {
    "enabled": true,
    "bot_token": "123456789:ABCdefGHIjklmnoPQRstuvWXYZ",
    "allowed_users": [123456789],
    "button_labels": {
      "close_full": "🔴 Close",
      "close_half": "🟡 Half",
      "risk_free": "🟢 Risk Free",
      "refresh": "🔄 Update"
    }
  }
}
```

Manager runs with dedicated bot token and custom button labels in different language.

---

## Security & Best Practices

### 🔐 User Whitelist (Recommended for Teams)

If you're managing trades on a team account, use `allowed_users` to restrict access:

```json
"allowed_users": [123456789, 987654321]
```

Only these user IDs can:
- View positions and signals
- Execute position closures
- Set risk-free

### 🔑 API Credentials Security

- **Never** share your API hash or bot token
- Use environment variables for production:
  ```json
  "api_id": "${TELEGRAM_API_ID}",
  "api_hash": "${TELEGRAM_API_HASH}",
  "providers": {
    "telegram_bot": {
      "bot_token": "${TELEGRAM_BOT_TOKEN}",
      "allowed_users": [123456789]
    }
  }
  ```

### 🔐 Separate Bot for Manager

For better security separation, create a dedicated bot for the manager:

1. Message `@BotFather` → `/newbot`
2. Create bot: "TelegramTrader Manager"
3. Add bot token to `settings.json`
4. Add bot to your manager chat

This way, signal provider and manager bot have separate credentials.

### ⚠️ Action Logging

All manager bot actions are logged:
- Position closures
- SL updates
- Risk-free activations
- User authorizations

Check logs for audit trail: `app/log/`

---

## Troubleshooting

### Manager Bot Not Starting

**Problem:** Logs show "Telegram Manager Bot not configured"

**Solution:** Ensure the manager bot section exists in `settings.json`:
```json
"providers": {
  "telegram_bot": {
    "enabled": true,
    "bot_token": null,
    "allowed_users": []
  }
}
```

### "You are not authorized" Message

**Problem:** Bot replies with authorization error

**Solution:** Check if `allowed_users` is configured:
```json
"allowed_users": [YOUR_USER_ID]  // Get from @userinfobot
```

If `allowed_users` is empty, all users should be allowed.

### Commands Not Responding

**Problem:** Bot doesn't respond to `/active`, `/positions`, etc.

**Solution:**
1. Verify the bot is running (check logs for "Telegram Manager Bot loaded")
2. Ensure MetaTrader 5 is running and connected
3. Check internet connection
4. Try `/help` command to verify bot is responding
5. Restart the application

---

## Advanced Features (Future)

The following features are planned for future releases:

- ✅ Custom close amounts (0.01 - 0.5 lots)
- ✅ Update stop-loss with inline input
- ✅ Trailing stop-loss activation
- ✅ Save profit at configured levels
- ✅ Live P&L updates with message editing
- ✅ Position history and statistics
- ✅ Multi-account management

---

## FAQ

**Q: Can I use the same Telegram account for signals and manager?**  
A: Yes, if you set `bot_token: null`, it will reuse the signal provider's session.

**Q: How do I disable the manager bot?**  
A: Set `"enabled": false` in `telegram_bot` section.

**Q: Is there a limit to how many signals I can view?**  
A: `/active` shows all active signals. `/signals` shows last 50 signals.

**Q: What happens if I close a position from the manager bot and MT5 simultaneously?**  
A: The manager bot will show an error. Try `/positions` refresh to sync.

**Q: Can I customize button labels?**  
A: Yes, use `button_labels` section:
```json
"button_labels": {
  "close_full": "🔴 CLOSE",
  "close_half": "📉 HALF",
  "risk_free": "💰 SAFE"
}
```

---

## Related Documentation

- [Configuration Guide](./Config.md) - Full settings reference
- [MetaTrader Integration](./MetaTrader.md) - Position and order management
- [Telegram Provider](./Telegram.md) - Signal monitoring setup
- [Release Notes](./Release.md) - Version history

---

## Support

For issues or feature requests:
1. Check logs in `app/log/` for error details
2. Review this documentation
3. Open an issue on GitHub with logs and configuration (credentials redacted)
