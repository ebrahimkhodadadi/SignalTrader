# SignalTrader Provider Architecture - Reorganized Structure

## New Folder Organization

```
app/
├── Providers/                          # Provider framework
│   ├── provider.py                     # Abstract Provider base class
│   ├── telegram_provider.py            # Telegram provider adapter
│   ├── discord_provider.py             # Discord provider adapter
│   ├── loader.py                       # Provider factory/loader
│   ├── __init__.py                     # Package exports
│   ├── telegram/                       # Telegram client implementation
│   │   ├── telegram.py                 # TelegramClientManager (moved from app/Telegram/)
│   │   └── __init__.py                 # Package exports
│   └── discord/                        # Discord client implementation
│       ├── discord.py                  # DiscordClientManager
│       └── __init__.py                 # Package exports
│
├── Configure/                          # (existing)
├── Database/                           # (existing)
├── MetaTrader/                         # (existing)
├── Helper/                             # (existing)
├── MessageHandler.py                   # (existing)
└── runner.py                           # (updated to use Providers.loader)

docs/
├── PROVIDERS.md                        # Provider documentation (moved from app/Providers/)
├── STRUCTURE.md                        # This file
├── Telegram.md                         # (existing)
├── MetaTrader.md                       # (existing)
└── ...                                 # (other docs)
```

## What Changed

### Moved Files
- `app/Telegram/Telegram.py` → `app/Providers/telegram/telegram.py`
- Discord implementation created in `app/Providers/discord/discord.py`
- `app/Providers/PROVIDERS.md` → `docs/PROVIDERS.md`

### New Structure Pattern
Both Telegram and Discord now follow the same pattern:
- `provider/provider.py` - Client implementation (e.g., `TelegramClientManager`)
- `provider_provider.py` - Adapter/wrapper implementing Provider interface
- `provider/__init__.py` - Package exports

### Updated Imports
- `telegram_provider.py`: Now imports from `.telegram.telegram`
- `discord_provider.py`: Now imports from `.discord.discord`
- `runner.py`: Removed unused `TelegramProvider` import (uses loader instead)

### Folder Deletions
- Deleted `app/Telegram/` (entire folder - moved to Providers)
- Deleted old `app/Providers/PROVIDERS.md` (moved to docs/)

## Benefits of This Organization

1. **Consistent Pattern**: All providers follow same folder structure
2. **Scalable Structure**: New providers can follow the same pattern
3. **Better Documentation**: Provider docs now with other architecture docs in `/docs`
4. **Reduced Root Clutter**: No scattered provider folders at app root level
5. **Clear Ownership**: Each client implementation is owned by its provider package
6. **Easy to Reference**: Documentation in `/docs` makes it easy to find
7. **Provider Independence**: Easy to add/remove providers without affecting core app

## Adding a New Provider (e.g., Slack)

1. Create `app/Providers/slack/` folder with `slack.py` (client implementation)
2. Create `app/Providers/slack_provider.py` (adapter implementing Provider interface)
3. Add to `loader.py` to auto-discover from settings.json
4. Update `docs/PROVIDERS.md` with configuration instructions
5. Done! No changes needed to runner or other components.

## File Import Paths (No Change to Usage)

Users don't need to change their imports - the provider framework is internal to the app:
- Settings configuration remains the same: `settings.json`
- Runner still works the same: calls `get_providers()` automatically
- All providers load via configuration, not code changes

