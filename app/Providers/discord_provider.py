"""Discord provider wrapper implementing the Provider interface.

This wrapper composes the existing DiscordClientManager implementation in
`app/Providers/discord/discord.py` to provide a simple, consistent interface that
other providers can follow.
"""
from typing import Optional, List

from .discord.discord import DiscordClientManager
from .provider import Provider


class DiscordProvider(Provider):
    """Provider adapter for Discord-based signal input."""

    def __init__(self, bot_token: str, channel_ids: List[int] = None, mention_mode: bool = False):
        self._client = DiscordClientManager(bot_token, channel_ids, mention_mode)

    @property
    def name(self) -> str:
        return "discord"

    async def start_monitoring(self) -> None:
        await self._client.start_monitoring()

    async def stop(self) -> None:
        # Attempt graceful disconnect if possible
        try:
            if self._client:
                await self._client.stop()
        except Exception:
            # Best-effort; don't raise during shutdown
            pass
