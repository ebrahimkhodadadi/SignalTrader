"""Telegram notification configuration for SignalTrader"""

from typing import Optional
from notifiers import get_notifier
from notifiers.logging import NotificationHandler
from loguru import logger


class NotificationManager:
    """Manages Telegram notifications for the trading bot"""

    def __init__(self):
        self._handler: Optional[NotificationHandler] = None
        self._notifier = None

    def configure_notifications(self, token: str, chat_id: str) -> bool:
        """Configure Telegram notifications

        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID for notifications

        Returns:
            True if configuration successful, False if skipped or error
        """
        # Skip if token or chat_id are empty
        if not token or not chat_id:
            logger.warning("Telegram notification settings are empty - notifications will be skipped")
            return False
        
        try:
            params = {
                "token": token,
                "chat_id": chat_id
            }

            # Initialize notifier
            self._notifier = get_notifier('telegram')

            # Send startup notification
            startup_message = self._get_startup_message()
            self._notifier.notify(message=startup_message, **params)

            # Configure logging handler
            self._handler = NotificationHandler("telegram", defaults=params)
            logger.add(
                self._handler,
                format="🔔 **SignalTrader Alert**\n"
                       "🕐 `{time:YYYY-MM-DD HH:mm:ss}` | ⏰ `{extra[mt5_time]}`\n"
                       "📝 {message}",
                level="INFO"  # Send info, warnings and above to Telegram
            )

            logger.success(f"Telegram notifications configured for chat {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to configure Telegram notifications: {e}")
            return False

    def _get_startup_message(self) -> str:
        """Generate startup notification message"""
        try:
            import Helper
            jalali_time = Helper.get_jalali_datetime()
            return f"🤖 **SignalTrader Started!**\n\n🕐 {jalali_time}\n\nBot is now monitoring for trading signals."
        except Exception:
            return "🤖 **SignalTrader Started!**\n\nBot is now active and monitoring for trading signals."

    def send_notification(self, message: str) -> bool:
        """Send a custom notification message

        Args:
            message: Message to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._notifier:
            logger.warning("Notifications not configured")
            return False

        try:
            # This would use the configured params from the handler
            # For now, just log that we would send
            logger.info(f"Would send notification: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False


# Global instance for backward compatibility
_notification_manager = NotificationManager()


# Backward compatibility function
def ConfigNotification(token, chatId):
    """Legacy function for backward compatibility"""
    return _notification_manager.configure_notifications(token, chatId)


