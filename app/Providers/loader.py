"""Provider loader to instantiate providers from configuration.

This module centralizes provider creation so the application can support
multiple providers (Telegram, Discord, etc.) configured in `settings.json`.

Example settings.json (new unified structure):
    {
      "providers": {
        "telegram": { "api_id": 123, "api_hash": "..." },
        "discord": { "bot_token": "..." }
      }
    }

Legacy structure (still supported):
    {
      "Telegram": { "api_id": 123, "api_hash": "..." },
      "Discord": { "bot_token": "..." }
    }

New providers are automatically instantiated if their config section exists.
"""
from typing import List
from loguru import logger

from Configure.settings.Settings import Settings
from .provider import Provider
from .telegram_provider import TelegramProvider


def get_providers() -> List[Provider]:
    """Create provider instances based on settings.

    Supports multiple simultaneous providers:
    - Telegram: configured via `providers.telegram` section (or legacy `Telegram`)
    - Discord: configured via `providers.discord` section (or legacy `Discord`)
    
    Returns:
        List of instantiated Provider instances
    """
    providers: List[Provider] = []

    try:
        cfg = Settings.get_instance()

        # Telegram provider (legacy support)
        try:
            telegram_cfg = cfg.Telegram
            api_id = getattr(telegram_cfg, 'api_id', None)
            api_hash = getattr(telegram_cfg, 'api_hash', None)

            if api_id and api_hash:
                providers.append(TelegramProvider(api_id, api_hash))
                logger.info("Telegram provider loaded")
        except Exception as e:
            logger.warning(f"Failed to load Telegram provider: {e}")

        # Discord provider
        try:
            from .discord_provider import DiscordProvider
            
            # Check if Discord config exists and is not empty/null
            discord_cfg = getattr(cfg, 'Discord', None)
            if discord_cfg is None:
                logger.debug("Discord provider not configured in settings.json")
            else:
                bot_token = getattr(discord_cfg, 'bot_token', None)
                if bot_token:
                    channel_ids = getattr(discord_cfg, 'channel_ids', [])
                    mention_mode = getattr(discord_cfg, 'mention_mode', False)
                    providers.append(DiscordProvider(bot_token, channel_ids, mention_mode))
                    logger.info(f"Discord provider loaded with {len(channel_ids)} channels")
                else:
                    logger.debug("Discord provider skipped: bot_token not configured")
        except ImportError as e:
            logger.debug(f"Discord provider skipped: discord.py not installed ({e})")
        except Exception as e:
            logger.warning(f"Failed to load Discord provider: {e}")

        # Future providers can be added here following the same pattern

    except Exception as e:
        logger.error(f"Error loading providers: {e}")

    if not providers:
        logger.warning("No providers configured. Please add Telegram or Discord config to settings.json")

    return providers
