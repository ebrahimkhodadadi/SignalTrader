````markdown
# Provider Configuration Guide

This file shows how to extend SignalTrader with additional providers beyond Telegram.

## Unified Provider Structure

SignalTrader uses a unified `providers` section in `settings.json` for all provider configurations:

```json
{
  "providers": {
    "telegram": { ... },
    "discord": { ... }
  }
}
```

## Current Providers

### Telegram
Configure under `providers.telegram`:
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
  }
}
```

### Telegram Manager Bot
Interactive trade management interface. Configure under `providers.telegram_bot`:
```json
{
  "providers": {
    "telegram_bot": {
      "enabled": true,
      "bot_token": null,
      "manager_chat_ids": [123456789],
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

See [Telegram Manager Bot Documentation](./TelegramManagerBot.md) for detailed setup and usage.

### Discord
Configure under `providers.discord`:
```json
{
  "providers": {
    "discord": {
      "bot_token": "your_bot_token_here",
      "channel_ids": [123456789, 987654321],
      "mention_mode": false
    }
  }
}
```

## Setting Up Discord

1. **Install dependency:**
   ```bash
   pip install discord.py
   ```

2. **Create bot at Discord Developer Portal:**
   - Go to https://discord.com/developers/applications
   - Click "New Application"
   - Go to "Bot" tab and click "Add Bot"
   - Under "TOKEN", click "Copy" and paste as `bot_token`
   - Enable "Message Content Intent" under Privileged Gateway Intents

3. **Get Channel IDs:**
   - Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
   - Right-click channel name and select "Copy Channel ID"
   - Add IDs to `channel_ids` array

4. **Add to settings.json** under `providers.discord`

## Other Potential Providers

- **Slack**: Monitor Slack channels for signals
- **Email**: Parse trading signals from email
- **RSS Feeds**: Subscribe to trading signal feeds
- **WebSocket**: Connect to custom APIs for live signals
- **IqOption API**: Monitor IqOption platform signals directly

## Architecture

All providers implement the `Provider` interface:

```python
class Provider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'telegram', 'discord')"""
    
    @abstractmethod
    async def start_monitoring(self) -> None:
        """Start provider monitoring loop"""
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop provider and clean up resources"""
```

This design allows:
- **Multiple simultaneous providers**: Run Telegram + Discord + Slack at once
- **Easy addition**: Implement the interface and add to loader
- **Configuration-driven**: Enable/disable providers via settings.json
- **Graceful shutdown**: Each provider has clean stop method

## Adding Your Own Provider

1. Create `app/Providers/your_provider/` folder with implementation
2. Create `app/Providers/your_provider_provider.py` adapter implementing `Provider` interface
3. Add configuration parsing to `loader.py`
4. Update `settings.json` under `providers.your_provider`
5. The runner will automatically discover and start it!

## Backward Compatibility

The system supports legacy flat structure for backward compatibility:
```json
{
  "Telegram": { ... },
  "Discord": { ... }
}
```

But the new unified structure under `providers` is recommended for all new configurations.

````