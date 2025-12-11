"""
Telegram Manager Bot for Trade Management

Main orchestrator class that coordinates:
- handlers: Command and callback processing
- views: UI message display
- actions: Trade operations
- input_handlers: Keyboard input processing
- helpers: Database and utility functions

Features:
- Active Signals: Get from MetaTrader, grouped by signal with position/order counts
- Active Positions: All MT5 positions/orders with action buttons
- Signal Details: Entry price, SL, TP, message link, action buttons
- Position Details: All details with close, update SL/TP, delete buttons
- Signal Tester: Parse signals and export open_price, second_price, SL, TP list
- Trade Summary: Account balance, equity, margin, P&L stats

Button Architecture:
- Inline Buttons: Main navigation, signal/position selection, detail actions
- Keyboard Buttons: Back navigation, custom input (lot, SL, TP)

Uses python-telegram-bot library with async/await for concurrent operation.
"""

from typing import Optional, Dict
from loguru import logger
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import asyncio

from Configure.settings.Settings import Settings
from Database import Migrations
from Database.database_manager import db_manager
from Providers.provider import Provider
from MetaTrader import MetaTrader

from .handlers import HandlerManager
from .views import ViewManager
from .actions import ActionManager
from .input_handlers import InputHandler


class TelegramManagerBot(Provider):
    """Interactive Telegram bot for trade and signal management with inline buttons"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.app: Optional[Application] = None
        self.meta_trader: Optional[MetaTrader] = None
        self.user_states: Dict[int, Dict] = {}  # {user_id: {state, context}}

        # Initialize managers
        self.views = ViewManager(self.meta_trader, self.user_states)
        self.actions = ActionManager(self.meta_trader, self.user_states, db_manager)
        self.input_handler = InputHandler(self.user_states, self.meta_trader)
        self.handlers = HandlerManager(self.views, self.actions, self.input_handler, self.user_states)

    @property
    def name(self) -> str:
        """Return provider name"""
        return "telegram_manager_bot"

    @staticmethod
    def from_settings() -> Optional["TelegramManagerBot"]:
        """Factory method to create bot from settings"""
        try:
            settings = Settings.get_instance()
            if not settings:
                logger.error("Settings not initialized")
                return None
            bot = TelegramManagerBot(settings)
            return bot
        except Exception as e:
            logger.error(f"Error creating TelegramManagerBot from settings: {e}")
            return None

    async def start_monitoring(self) -> None:
        """Start provider monitoring (implements Provider interface) without closing the global event loop"""
        try:
            logger.info("Initializing Telegram Manager Bot...")

            # Initialize MetaTrader connection
            mt_config = self.settings.MetaTrader
            self.meta_trader = MetaTrader(
                path=mt_config.path,
                server=mt_config.server,
                user=mt_config.username,
                password=mt_config.password,
                saveProfits=mt_config.SaveProfits,
                closePositionsOnTrail=mt_config.ClosePositionsOnTrail
            )

            # Update managers with initialized meta_trader
            self.views.meta_trader = self.meta_trader
            self.actions.meta_trader = self.meta_trader
            self.input_handler.meta_trader = self.meta_trader

            # Get bot token from settings
            bot_token = self.settings.TelegramBot.bot_token
            if not bot_token:
                logger.error("Bot token not configured in settings")
                return

            # Create Application with bot token
            self.app = Application.builder().token(bot_token).build()

            # Register handlers
            self.app.add_handler(CommandHandler("start", self.handlers.handle_start))
            self.app.add_handler(CommandHandler("menu", self.handlers.handle_start))
            self.app.add_handler(CallbackQueryHandler(self.handlers.handle_callback))
            self.app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, self.handlers.handle_message))

            # Initialize and start application without closing the event loop
            logger.info("Starting Telegram Manager Bot (non-blocking polling)...")
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            logger.info("Telegram Manager Bot polling started")

        except Exception as e:
            logger.error(f"Error in start_monitoring: {e}")

    async def stop(self) -> None:
        """Stop the bot without closing the global event loop"""
        try:
            if self.app:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
                logger.info("Telegram Manager Bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
