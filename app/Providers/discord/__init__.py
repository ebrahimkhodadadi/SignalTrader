"""Discord provider package for SignalTrader.

This package contains the Discord bot implementation and provider adapter.
"""

from .discord import DiscordClientManager, Discord

__all__ = ["DiscordClientManager", "Discord"]
