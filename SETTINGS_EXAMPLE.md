# SignalTrader Settings Template with Unified Providers

This file shows configuration examples for both Telegram and Discord providers.

## Minimal Settings (Telegram Only)

```json
{
  "providers": {
    "telegram": {
      "api_id": 12345678,
      "api_hash": "your_api_hash_from_my.telegram.org",
      "channels": {
        "whiteList": ["@trading_signals"],
        "blackList": []
      }
    }
  },
  "Notification": {
    "token": "your_telegram_bot_token_from_botfather",
    "chatId": 123456789
  },
  "MetaTrader": {
    "server": "your-broker-server",
    "username": 12345678,
    "password": "your_mt5_password",
    "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    "lot": "2%",
    "HighRisk": false
  }
}
```

## Full Settings with Discord

```json
{
  "providers": {
    "telegram": {
      "api_id": 12345678,
      "api_hash": "your_api_hash_from_my.telegram.org",
      "channels": {
        "whiteList": ["@trading_signals"],
        "blackList": []
      }
    },
    "discord": {
      "bot_token": "your_discord_bot_token_from_discord.com/developers",
      "channel_ids": [1234567890, 0987654321],
      "mention_mode": false
    }
  },
  "Notification": {
    "token": "your_telegram_bot_token_from_botfather",
    "chatId": 123456789
  },
  "MetaTrader": {
    "server": "your-broker-server",
    "username": 12345678,
    "password": "your_mt5_password",
    "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    "lot": "2%",
    "HighRisk": false,
    "SaveProfits": [25, 25, 25, 25],
    "CloserPrice": 0.5,
    "expirePendinOrderInMinutes": 30
  },
  "Timer": {
    "start": "08:00",
    "end": "18:00"
  },
  "disableCache": false
}
```

## Getting Discord Bot Token

1. Go to https://discord.com/developers/applications
2. Click "New Application" and name it "SignalTrader"
3. Go to "Bot" tab and click "Add Bot"
4. Under "TOKEN", click "Copy"
5. Paste as `"bot_token"` in settings.providers.discord
6. Enable "Message Content Intent" under Privileged Gateway Intents

## Getting Discord Channel IDs

1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click channel name and select "Copy Channel ID"
3. Add the ID to `"channel_ids"` array under providers.discord

## Providers Configuration

### Telegram Provider
Located under `providers.telegram`:
- **api_id**: Your Telegram API ID from https://my.telegram.org
- **api_hash**: Your Telegram API hash
- **channels.whiteList**: Channels to monitor (empty = all)
- **channels.blackList**: Channels to ignore

### Discord Provider
Located under `providers.discord`:
- **bot_token**: Your bot's authentication token (leave empty to disable)
- **channel_ids**: Array of channel IDs to monitor (empty = monitor all)
- **mention_mode**: If true, only respond to messages that mention the bot

## Running with Multiple Providers

Once configured, SignalTrader will automatically:
1. Start Telegram monitoring if `providers.telegram` is configured and `api_id`/`api_hash` are set
2. Start Discord monitoring if `providers.discord.bot_token` is set
3. Process signals from both simultaneously
4. Execute trades based on signals from any provider

This means you can receive signals from Telegram AND Discord at the same time!

## Backward Compatibility

The application still supports the legacy flat structure:
```json
{
  "Telegram": { ... },
  "Discord": { ... }
}
```

But the new unified structure under `providers` is recommended:
```json
{
  "providers": {
    "telegram": { ... },
    "discord": { ... }
  }
}
```
