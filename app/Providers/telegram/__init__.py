"""Telegram provider package for SignalTrader.

This package contains the Telegram client implementation and provider adapter.
"""

from .telegram import TelegramClientManager, Telegram

__all__ = ["TelegramClientManager", "Telegram"]
