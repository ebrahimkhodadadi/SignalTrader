"""
Telegram Client Module for SignalTrader

This module provides a Telegram client implementation for monitoring trading signals
from configured providers (Telegram) and handling various message events.

Features:
    - Real-time message monitoring from configured channels
    - Support for new messages, edits, and deletions
    - Channel filtering (whitelist/blacklist)
    - Automatic reconnection on connection failures
    - Comprehensive error handling and logging

Dependencies:
    - telethon: Telegram API client
    - loguru: Structured logging
    - Configure: Configuration management
    - MessageHandler: Signal processing logic
"""

import asyncio
import sys
from typing import Optional, Tuple, Any
from loguru import logger
from telethon import TelegramClient, events
from telethon.errors import RPCError, AuthKeyError
from telethon.errors.rpcerrorlist import FloodWaitError, NetworkMigrateError, ServerError
from MessageHandler import Handle, HandleParentEdit, HandleParentDelete, HandleParentRiskFree, HandleParentTP, HandleEdite, HandleDelete, MessageType
import Configure


class TelegramClientManager:
    """
    Manages Telegram client connection and message handling for trading signals.

    This class handles:
    - Telegram client initialization and authentication
    - Event-driven message processing
    - Channel filtering and validation
    - Connection resilience and error recovery
    """

    def __init__(self, api_id: int, api_hash: str):
        """
        Initialize the Telegram client manager.

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.client: Optional[TelegramClient] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Telegram client with session persistence."""
        try:
            self.client = TelegramClient(
                session='TelegramSession',
                api_id=self.api_id,
                api_hash=self.api_hash
            )
            logger.debug("Telegram client initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize Telegram client: {e}")
            raise

    async def start_monitoring(self) -> None:
        """
        Start the main message monitoring loop with automatic reconnection.

        This method runs indefinitely, handling connection failures and
        automatically reconnecting when issues occur.
        """
        # Configure stdout for proper encoding
        sys.stdout.reconfigure(encoding='utf-8')

        logger.debug("Starting Telegram message monitoring...")

        while True:
            try:
                # Start the client
                await self.client.start()
                logger.success("Telegram client connected and authenticated")

                # Register event handlers
                self._register_event_handlers()

                # Run until disconnected
                logger.debug("Monitoring active. Press Ctrl+C to stop.")
                await self.client.run_until_disconnected()

            except (AuthKeyError, OSError) as e:
                logger.critical(f"Authentication or network error: {e}")
                logger.debug(
                    "Please check your API credentials and network connection")
                await asyncio.sleep(30)  # Longer delay for auth errors

            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(
                    f"Rate limited by Telegram. Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)

            except (NetworkMigrateError, ServerError, RPCError) as e:
                logger.error(f"Telegram server error: {e}")
                logger.debug("Retrying connection in 10 seconds...")
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Unexpected error in message monitoring: {e}")
                logger.debug("Retrying connection in 5 seconds...")
                await asyncio.sleep(5)

            except KeyboardInterrupt:
                logger.debug("Received shutdown signal")
                break

            finally:
                # Ensure client is properly disconnected
                if self.client and self.client.is_connected():
                    await self.client.disconnect()
                    logger.debug("Telegram client disconnected")

    def _register_event_handlers(self) -> None:
        """Register all Telegram event handlers."""

        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            """Handle new incoming messages."""
            try:
                if event.message.is_reply:
                    await self._handle_reply_message(event)
                else:
                    await self._handle_new_message(event)
            except Exception as e:
                logger.error(f"Error handling new message: {e}")

        @self.client.on(events.MessageEdited)
        async def handle_edited_message(event):
            """Handle message edits."""
            try:
                chat_id = clear_chat_id(event.chat_id)
                message_id = event.message.id

                # Check if message has content
                if not event.message.message:
                    # logger.debug(f"Edited message {message_id} has no content, skipping")
                    return

                # Clean and normalize text
                text = event.message.message.lower()
                text = text.encode('utf-8', errors='ignore').decode('utf-8')

                logger.debug(
                    f"Processing edited message in chat {chat_id}, message {message_id}")
                HandleEdite(chat_id, message_id, text)

            except Exception as e:
                logger.error(f"Error handling edited message: {e}")

        @self.client.on(events.MessageDeleted)
        async def handle_deleted_message(event):
            """Handle message deletions."""
            try:
                chat_id = clear_chat_id(event.chat_id)

                for msg_id in event.deleted_ids:
                    logger.debug(
                        f"Processing deleted message {msg_id} in chat {chat_id}")
                    HandleDelete(chat_id, msg_id)

            except Exception as e:
                logger.error(f"Error handling deleted message: {e}")

    async def _handle_reply_message(self, event) -> None:
        """Handle messages that are replies to other messages."""
        try:
            replied = await event.message.get_reply_message()
            if not replied:
                return

            parent_chat_id = clear_chat_id(event.chat_id)
            parent_msg_id = replied.id
            message_text = event.message.message.lower()

            logger.debug(
                f"Processing reply to message {parent_msg_id} in chat {parent_chat_id}")

            # Handle different types of reply commands
            HandleParentEdit(parent_chat_id, parent_msg_id, message_text)
            HandleParentDelete(parent_chat_id, parent_msg_id, message_text)
            HandleParentRiskFree(parent_chat_id, parent_msg_id, message_text)
            HandleParentTP(parent_chat_id, parent_msg_id, message_text)

        except Exception as e:
            logger.error(f"Error handling reply message: {e}")

    async def _handle_new_message(self, event) -> None:
        """Handle new (non-reply) messages."""
        try:
            await self._handle_event(MessageType.New, event)
        except Exception as e:
            logger.error(f"Error handling new message: {e}")

    async def _handle_event(self, message_type: MessageType, event) -> None:
        """
        Handle a message event after channel validation.

        Args:
            message_type: Type of message event (New, Edited, etc.)
            event: Telegram event object
        """
        try:
            # Extract message details
            message_details = await self._get_message_details(event)
            if not message_details:
                logger.debug("Could not extract message details")
                return

            username, message_id, message_link, chat_id = message_details

            # Validate channel access
            if not self._is_channel_allowed(username, chat_id):
                # logger.debug(
                #     f"Message from unauthorized channel: {username or chat_id}")
                return

            # Clean message text
            text = event.raw_text.encode(
                'utf-8', errors='ignore').decode('utf-8')

            # Process the message
            # logger.debug(f"Processing {message_type.name} message from {username or chat_id}")
            Handle(message_type, text, message_link,
                   username, message_id, chat_id, provider="telegram")

        except Exception as e:
            logger.error(f"Error processing message event: {e}")

    def _is_channel_allowed(self, username: Optional[str], chat_id: int) -> bool:
        """
        Check if a channel is allowed based on whitelist/blacklist configuration.

        Args:
            username: Channel username (if available)
            chat_id: Numeric chat ID

        Returns:
            True if channel is allowed, False otherwise
        """
        try:
            from Configure.settings.Settings import Settings
            white_list = Settings.telegram_channels_whitelist()
            black_list = Settings.telegram_channels_blacklist()

            # Check whitelist (if specified)
            if white_list:
                allowed_usernames = {str(u).lower() for u in white_list}
                allowed_chat_ids = {str(cid) for cid in white_list}

                username_allowed = username and username.lower() in allowed_usernames
                chat_id_allowed = str(
                    chat_id) in allowed_chat_ids or chat_id in white_list

                if not (username_allowed or chat_id_allowed):
                    return False

            # Check blacklist (always applies)
            if black_list:
                blocked_usernames = {str(u).lower() for u in black_list}
                blocked_chat_ids = {str(cid) for cid in black_list}

                username_blocked = username and username.lower() in blocked_usernames
                chat_id_blocked = str(
                    chat_id) in blocked_chat_ids or chat_id in black_list

                if username_blocked or chat_id_blocked:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking channel permissions: {e}")
            return False

    async def _get_message_details(self, event) -> Optional[Tuple[Optional[str], Optional[int], str, int]]:
        """
        Extract detailed information from a Telegram message event.

        Args:
            event: Telegram event object

        Returns:
            Tuple of (username, message_id, message_link, chat_id) or None if extraction fails
        """
        try:
            chat = await event.get_chat()
            chat_id = chat.id
            message_id = event.message.id

            if hasattr(chat, 'username') and chat.username:
                # Public channel with username
                username = chat.username
                message_link = f"https://t.me/{username}/{message_id}"
            elif hasattr(chat, 'title') and chat.title:
                # Private group or channel
                username = chat.title
                message_link = f"{username}/{message_id}"
            else:
                username = None
                message_link = f"chat_{chat_id}/{message_id}"

            return username, message_id, message_link, chat_id

        except Exception as e:
            logger.error(f"Error extracting message details: {e}")
            return None


# Utility functions
def clear_chat_id(chat_id: Optional[int]) -> Optional[int]:
    """
    Normalize chat ID by removing Telegram's internal prefixes.

    Telegram uses -100 prefixes for supergroups/channels.
    This function extracts the actual identifier.

    Args:
        chat_id: Raw chat ID from Telegram

    Returns:
        Normalized chat ID
    """
    if chat_id is None:
        return chat_id

    # Strip -100 prefix if present (for supergroups/channels)
    if str(chat_id).startswith("-100"):
        raw_id = int(str(chat_id)[4:])
    else:
        raw_id = chat_id

    return abs(raw_id)


# Backward compatibility alias
Telegram = TelegramClientManager
