from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """Abstract base class for signal providers (Telegram, Discord, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider name identifier (e.g., "telegram")."""

    @abstractmethod
    async def start_monitoring(self) -> None:
        """Start provider monitoring loop or background tasks."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop provider and release resources (connections, sessions)."""
