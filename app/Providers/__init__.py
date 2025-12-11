"""Providers package for SignalTrader.

Multi-provider architecture supporting signal monitoring from various sources:
- Telegram: Built-in provider using Telethon
- Discord: Example template for extending to Discord
- Future: Email, Slack, RSS feeds, custom APIs, etc.

Each provider implements the Provider interface for consistent integration.

Usage:
    from Providers.loader import get_providers
    providers = get_providers()
    for prov in providers:
        await prov.start_monitoring()
"""

from .provider import Provider
from . import loader

# Lazy imports to avoid import errors when optional dependencies are missing
def __getattr__(name):
    if name == "TelegramProvider":
        from .telegram_provider import TelegramProvider
        return TelegramProvider
    elif name == "DiscordProvider":
        from .discord_provider import DiscordProvider
        return DiscordProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Provider",
    "TelegramProvider",
    "DiscordProvider",
    "loader",
]
