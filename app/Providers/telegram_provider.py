"""Telegram provider wrapper implementing the Provider interface.

This wrapper composes the existing TelegramClientManager implementation in
`app/Providers/telegram/telegram.py` to provide a simple, consistent interface that
other providers can follow.
"""
from typing import Optional

from .telegram.telegram import TelegramClientManager
from .provider import Provider


class TelegramProvider(Provider):
    """Provider adapter for Telegram-based signal input."""

    def __init__(self, api_id: int, api_hash: str):
        self._client = TelegramClientManager(api_id, api_hash)

    @property
    def name(self) -> str:
        return "telegram"

    async def start_monitoring(self) -> None:
        await self._client.start_monitoring()

    async def stop(self) -> None:
        # Attempt graceful disconnect if possible
        try:
            if self._client and getattr(self._client, 'client', None):
                client = self._client.client
                if client and getattr(client, 'is_connected', lambda: False)():
                    await client.disconnect()
        except Exception:
            # Best-effort; don't raise during shutdown
            pass
