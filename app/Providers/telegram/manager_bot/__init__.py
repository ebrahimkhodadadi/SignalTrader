"""
Manager Bot Package

Modular structure for Telegram bot functionality:
- manager_bot.py: Main bot class orchestrating handlers
- handlers.py: Command and callback handlers
- views.py: Message display and UI methods
- actions.py: Trade operation handlers
- input_handlers.py: Keyboard input processing
- helpers.py: Utility methods and database queries
"""

from .manager_bot import TelegramManagerBot

__all__ = ['TelegramManagerBot']
