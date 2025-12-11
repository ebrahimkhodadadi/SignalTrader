"""Discord Client Module for SignalTrader

This module provides a Discord bot implementation for monitoring trading signals
from configured channels.

Features:
    - Real-time message monitoring from configured channels
    - Support for new messages, edits, and deletions
    - Optional mention mode (only respond to bot mentions)
    - Graceful error handling and logging

Dependencies:
    - discord.py: Discord API client
    - loguru: Structured logging
    - MessageHandler: Signal processing logic
"""

from __future__ import annotations
import asyncio
from typing import Optional, List, Set, TYPE_CHECKING
from loguru import logger

try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

if TYPE_CHECKING:
    import discord


class DiscordClientManager:
    """
    Manages Discord bot connection and message handling for trading signals.

    This class handles:
    - Discord bot initialization and authentication
    - Event-driven message processing
    - Channel filtering and validation
    - Connection resilience and error recovery
    """

    def __init__(self, bot_token: str, channel_ids: List[int] = None, mention_mode: bool = False):
        """Initialize Discord client manager.

        Args:
            bot_token: Discord bot token for authentication
            channel_ids: List of Discord channel IDs to monitor
            mention_mode: If True, only respond to @bot mentions
        """
        if not DISCORD_AVAILABLE:
            raise ImportError("discord.py is required for Discord provider. Install with: pip install discord.py")

        self._token = bot_token
        self._channel_ids: Set[int] = set(channel_ids or [])
        self._mention_mode = mention_mode
        self._client: Optional[commands.Bot] = None
        self._running = False

        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Discord bot with necessary intents."""
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            intents.direct_messages = True

            self._client = commands.Bot(command_prefix='!', intents=intents)
            self._register_handlers()
            logger.debug("Discord client initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize Discord client: {e}")
            raise

    def _register_handlers(self) -> None:
        """Register Discord event handlers."""
        if not self._client:
            return

        @self._client.event
        async def on_ready():
            logger.success(f"Discord bot connected as {self._client.user}")
            logger.info(f"Monitoring {len(self._channel_ids)} channels")

        @self._client.event
        async def on_message(message: "discord.Message"):
            """Handle new Discord messages."""
            # Ignore own messages
            if message.author == self._client.user:
                return

            # Check if message is from monitored channel
            if self._channel_ids and message.channel.id not in self._channel_ids:
                return

            # Skip if mention_mode and no mention
            if self._mention_mode and self._client.user not in message.mentions:
                return

            # Skip empty messages
            if not message.content:
                return

            await self._handle_signal_message(message, "new")

        @self._client.event
        async def on_message_edit(before: "discord.Message", after: "discord.Message"):
            """Handle edited Discord messages."""
            if after.author == self._client.user:
                return

            if self._channel_ids and after.channel.id not in self._channel_ids:
                return

            if not after.content:
                return

            await self._handle_signal_message(after, "edited")

        @self._client.event
        async def on_message_delete(message: "discord.Message"):
            """Handle deleted Discord messages."""
            if message.author == self._client.user:
                return

            if self._channel_ids and message.channel.id not in self._channel_ids:
                return

            await self._handle_signal_message(message, "deleted")

        @self._client.event
        async def on_error(event, *args, **kwargs):
            """Handle Discord errors."""
            logger.error(f"Discord event error in {event}: {args}, {kwargs}")

    async def start_monitoring(self) -> None:
        """
        Start the Discord bot monitoring loop.

        This method runs indefinitely, handling connection failures and
        automatically reconnecting when issues occur.
        """
        if not self._client:
            logger.error("Discord client not initialized")
            return

        self._running = True
        try:
            logger.info("Starting Discord bot monitoring...")
            await self._client.start(self._token)
        except discord.errors.LoginFailure:
            logger.critical("Invalid Discord bot token")
        except Exception as e:
            logger.error(f"Discord bot error: {e}")
        finally:
            self._running = False
            logger.info("Discord bot monitoring stopped")

    async def stop(self) -> None:
        """Stop Discord bot gracefully.

        Closes the connection and cleans up resources.
        """
        if self._client and self._running:
            try:
                logger.info("Stopping Discord bot...")
                await self._client.close()
                self._running = False
            except Exception as e:
                logger.warning(f"Error stopping Discord bot: {e}")

    async def _handle_signal_message(self, message: "discord.Message", event_type: str) -> None:
        """Handle incoming signal message from Discord.

        Parses message content and coordinates with trading system.

        Args:
            message: Discord message object
            event_type: Type of event ("new", "edited", "deleted")
        """
        try:
            # Extract message info
            text = message.content.lower()
            chat_id = message.channel.id
            message_id = message.id
            username = message.author.name

            # Build comment with Discord metadata
            channel_name = getattr(message.channel, 'name', 'unknown')
            guild_name = getattr(message.guild, 'name', 'DM') if message.guild else 'DM'
            comment = f"Discord #{channel_name} (@{guild_name}) - {message.author.mention}"

            # Map Discord event to MessageType
            from MessageHandler import Handle, MessageType
            if event_type == "new":
                msg_type = MessageType.New
            elif event_type == "edited":
                msg_type = MessageType.Edited
            elif event_type == "deleted":
                msg_type = MessageType.Deleted
            else:
                msg_type = MessageType.New

            # Process signal through message handler
            logger.debug(f"Processing Discord signal from {username}: {text[:50]}...")
            Handle(
                message_type=msg_type,
                text=text,
                comment=comment,
                username=username,
                message_id=message_id,
                chat_id=chat_id
            )

        except ImportError:
            logger.error("MessageHandler not available - signal processing skipped")
        except Exception as e:
            logger.error(f"Error handling Discord message: {e}")


# Backward compatibility alias
Discord = DiscordClientManager
