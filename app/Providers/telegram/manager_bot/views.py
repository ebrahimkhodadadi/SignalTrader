"""
View methods for displaying UI messages and inline buttons
"""

from typing import Optional
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import MetaTrader5 as mt5
import asyncio

from Database.database_manager import db_manager
from .helpers import find_signal_by_ticket, get_position_for_signal
from report import ChannelAnalyzer


class ViewManager:
    """Manages all UI display methods"""

    def __init__(self, meta_trader, user_states: dict):
        self.meta_trader = meta_trader
        self.user_states = user_states
        # Track active auto-updates: {user_id: {"state": "signal_list", "message_id": 123, "chat_id": 456}}
        self.active_updates = {}
        self.update_interval = 5  # Update every 5 seconds

    def _stop_auto_update(self, user_id: int) -> None:
        """Stop auto-update for a user"""
        if user_id in self.active_updates:
            del self.active_updates[user_id]

    async def show_open_trade_form(self, query, user_id: int) -> None:
        """Show form to open a new manual trade"""
        try:
            from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

            # Set user state to awaiting trade input
            self.user_states[user_id] = {
                "state": "awaiting_trade_input",
                "context": {}
            }

            text = """📝 **Open New Trade**

Please provide trade details in the following format:

```
SYMBOL ACTION PRICE1 PRICE2 TP1,TP2,... SL COMMENT
```

**Example:**
```
EURUSD BUY 1.0850 1.0855 1.0870,1.0885,1.0900 1.0830 Manual trade entry
```

**Parameters:**
- **SYMBOL**: Trading pair (e.g., EURUSD, GBPUSD)
- **ACTION**: BUY or SELL
- **PRICE1**: Entry price
- **PRICE2**: Confirmation price
- **TP1,TP2,...**: Take profits (comma-separated)
- **SL**: Stop loss level
- **COMMENT**: Optional comment (e.g., Manual entry)
"""

            # Send a new message without keyboard buttons
            try:
                await query.message.reply_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardRemove()
                )

            except AttributeError as e:
                logger.error(f"Error accessing query.message: {e}")
                # Fallback: edit the message with text only and edit the button state
                await query.edit_message_text(text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error sending trade form: {e}")
                await query.edit_message_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error showing open trade form: {e}")
            await query.answer(f"Error: {str(e)}", show_alert=True)

    async def show_signal_list(self, query, user_id: int) -> None:
        """Show list of active signals grouped by signal with their positions/orders"""
        try:
            STATE_SIGNAL_LIST = "signal_list"
            self.user_states[user_id] = {
                "state": STATE_SIGNAL_LIST, "context": {}}

            if not self.meta_trader:
                await query.edit_message_text(
                    "❌ MetaTrader connection not available",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            positions = self.meta_trader.get_open_positions() or []
            orders = self.meta_trader.get_pending_orders() or []

            if not positions and not orders:
                await query.edit_message_text(
                    "📭 No active positions or orders",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            # Group positions/orders by signal
            signals_dict = {}

            for pos in positions:
                ticket = pos.ticket if hasattr(
                    pos, 'ticket') else pos.get("ticket")
                signal = find_signal_by_ticket(ticket)
                if signal:
                    signal_id = signal.id if hasattr(
                        signal, 'id') else signal.get("id")
                    if signal_id not in signals_dict:
                        signals_dict[signal_id] = {
                            "signal": signal, "positions": [], "orders": []}
                    signals_dict[signal_id]["positions"].append(
                        {"ticket": ticket, "data": pos})

            for order in orders:
                ticket = order.ticket if hasattr(
                    order, 'ticket') else order.get("ticket")
                signal = find_signal_by_ticket(ticket)
                if signal:
                    signal_id = signal.id if hasattr(
                        signal, 'id') else signal.get("id")
                    if signal_id not in signals_dict:
                        signals_dict[signal_id] = {
                            "signal": signal, "positions": [], "orders": []}
                    signals_dict[signal_id]["orders"].append(
                        {"ticket": ticket, "data": order})

            if not signals_dict:
                await query.edit_message_text(
                    "📭 No active positions or orders linked to signals",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            # Build text and buttons grouped by signal
            text_parts = ["📊 **Active Signals - Grouped by Signal**\n"]
            buttons = []

            for signal_id, signal_data in signals_dict.items():
                signal = signal_data["signal"]
                open_price = signal.open_price if hasattr(
                    signal, 'open_price') else signal.get("open_price", "N/A")
                signal_type = signal.signal_type if hasattr(
                    signal, 'signal_type') else signal.get("signal_type", "N/A")
                num_positions = len(signal_data["positions"])
                num_orders = len(signal_data["orders"])

                # Get channel and message info
                channel_title = signal.telegram_channel_title if hasattr(
                    signal, 'telegram_channel_title') else signal.get("telegram_channel_title", "Unknown")
                chat_id = signal.telegram_message_chatid if hasattr(
                    signal, 'telegram_message_chatid') else signal.get("telegram_message_chatid")
                message_id = signal.telegram_message_id if hasattr(
                    signal, 'telegram_message_id') else signal.get("telegram_message_id")

                # Build message link
                message_link = "N/A"
                if chat_id and message_id:
                    message_link = f"https://t.me/c/{abs(chat_id)}/{message_id}"

                # Get ticket IDs from positions and orders
                position_tickets = [pos["ticket"]
                                    for pos in signal_data["positions"]]
                order_tickets = [order["ticket"]
                                 for order in signal_data["orders"]]
                all_tickets = position_tickets + order_tickets
                tickets_text = " / ".join(str(t)
                                          for t in all_tickets) if all_tickets else "None"

                # Add signal type emoji
                type_emoji = "🟢" if signal_type == "BUY" else "🔴"

                text_parts.append(f"\n**#{signal_id}:**")
                text_parts.append(f"**Channel:** {channel_title}")
                text_parts.append(
                    f"**Message:** [{message_link}]({message_link})")
                text_parts.append(
                    f"{type_emoji} **{signal_type} | Tickets: {tickets_text}**")
                text_parts.append(
                    f"  📈 Positions: {num_positions} | ⏳ Orders: {num_orders}")

                button_text = f"{type_emoji} #{signal_id} - {channel_title}"
                buttons.append([InlineKeyboardButton(
                    button_text, callback_data=f"signal_{signal_id}")])

            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data="menu")])

            text = "\n".join(text_parts)
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

            # Store message info for auto-update
            self.active_updates[user_id] = {
                "state": "signal_list",
                "message_id": query.message.message_id,
                "chat_id": query.message.chat_id,
                "last_text": text,  # Store for comparison
                "last_buttons": buttons
            }

            # Start auto-update task for this user
            asyncio.create_task(
                self._auto_update_signal_list(user_id, query.get_bot()))

        except Exception as e:
            logger.error(f"Error showing signal list: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]))

    async def _auto_update_signal_list(self, user_id: int, bot) -> None:
        """Automatically update signal list for user every 5 seconds"""
        try:
            while user_id in self.active_updates and self.active_updates[user_id]["state"] == "signal_list":
                await asyncio.sleep(self.update_interval)

                # Check if user is still on signal_list page
                if user_id not in self.active_updates or self.active_updates[user_id]["state"] != "signal_list":
                    break

                update_info = self.active_updates[user_id]

                if not self.meta_trader:
                    continue

                positions = self.meta_trader.get_open_positions() or []
                orders = self.meta_trader.get_pending_orders() or []

                if not positions and not orders:
                    text = "📭 No active positions or orders"
                    buttons = [[InlineKeyboardButton(
                        "⬅️ Back", callback_data="menu")]]
                else:
                    # Group positions/orders by signal
                    signals_dict = {}

                    for pos in positions:
                        ticket = pos.ticket if hasattr(
                            pos, 'ticket') else pos.get("ticket")
                        signal = find_signal_by_ticket(ticket)
                        if signal:
                            signal_id = signal.id if hasattr(
                                signal, 'id') else signal.get("id")
                            if signal_id not in signals_dict:
                                signals_dict[signal_id] = {
                                    "signal": signal, "positions": [], "orders": []}
                            signals_dict[signal_id]["positions"].append(
                                {"ticket": ticket, "data": pos})

                    for order in orders:
                        ticket = order.ticket if hasattr(
                            order, 'ticket') else order.get("ticket")
                        signal = find_signal_by_ticket(ticket)
                        if signal:
                            signal_id = signal.id if hasattr(
                                signal, 'id') else signal.get("id")
                            if signal_id not in signals_dict:
                                signals_dict[signal_id] = {
                                    "signal": signal, "positions": [], "orders": []}
                            signals_dict[signal_id]["orders"].append(
                                {"ticket": ticket, "data": order})

                    if not signals_dict:
                        text = "📭 No active positions or orders linked to signals"
                        buttons = [[InlineKeyboardButton(
                            "⬅️ Back", callback_data="menu")]]
                    else:
                        # Build updated text and buttons
                        text_parts = [
                            "📊 **Active Signals - Grouped by Signal** 🔄 (Auto-updating)\n"]
                        buttons = []

                        for signal_id, signal_data in signals_dict.items():
                            signal = signal_data["signal"]
                            signal_type = signal.signal_type if hasattr(
                                signal, 'signal_type') else signal.get("signal_type", "N/A")
                            num_positions = len(signal_data["positions"])
                            num_orders = len(signal_data["orders"])

                            # Get channel and message info
                            channel_title = signal.telegram_channel_title if hasattr(
                                signal, 'telegram_channel_title') else signal.get("telegram_channel_title", "Unknown")
                            chat_id = signal.telegram_message_chatid if hasattr(
                                signal, 'telegram_message_chatid') else signal.get("telegram_message_chatid")
                            message_id = signal.telegram_message_id if hasattr(
                                signal, 'telegram_message_id') else signal.get("telegram_message_id")

                            # Build message link
                            message_link = "N/A"
                            if chat_id and message_id:
                                message_link = f"https://t.me/c/{abs(chat_id)}/{message_id}"

                            # Get ticket IDs
                            position_tickets = [pos["ticket"]
                                                for pos in signal_data["positions"]]
                            order_tickets = [order["ticket"]
                                             for order in signal_data["orders"]]
                            all_tickets = position_tickets + order_tickets
                            tickets_text = " / ".join(str(t)
                                                      for t in all_tickets) if all_tickets else "None"

                            # Add signal type emoji
                            type_emoji = "🟢" if signal_type == "BUY" else "🔴"

                            text_parts.append(f"\n**#{signal_id}:**")
                            text_parts.append(f"**Channel:** {channel_title}")
                            text_parts.append(
                                f"**Message:** [{message_link}]({message_link})")
                            text_parts.append(
                                f"{type_emoji} **{signal_type} | Tickets: {tickets_text}**")
                            text_parts.append(
                                f"  📈 Positions: {num_positions} | ⏳ Orders: {num_orders}")

                            button_text = f"{type_emoji} #{signal_id} - {channel_title}"
                            buttons.append([InlineKeyboardButton(
                                button_text, callback_data=f"signal_{signal_id}")])

                        buttons.append([InlineKeyboardButton(
                            "⬅️ Back", callback_data="menu")])
                        text = "\n".join(text_parts)

                # Only update if content has changed
                content_changed = (update_info.get("last_text") != text or
                                   update_info.get("last_buttons") != buttons)

                if content_changed:
                    # Update the message
                    try:
                        await bot.edit_message_text(
                            chat_id=update_info["chat_id"],
                            message_id=update_info["message_id"],
                            text=text,
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                        # Update stored content for next comparison
                        update_info["last_text"] = text
                        update_info["last_buttons"] = buttons
                    except Exception as e:
                        logger.debug(
                            f"Could not update signal list for user {user_id}: {e}")
                        # Stop updating if message no longer exists
                        if user_id in self.active_updates:
                            del self.active_updates[user_id]
                        break

        except Exception as e:
            logger.error(f"Error in auto-update signal list: {e}")
            if user_id in self.active_updates:
                del self.active_updates[user_id]

    async def show_signal_detail(self, query, user_id: int, signal_id: int) -> None:
        """Show signal details with message link and action buttons"""
        try:
            STATE_VIEWING_SIGNAL = "viewing_signal"
            self.user_states[user_id] = {
                "state": STATE_VIEWING_SIGNAL, "context": {"signal_id": signal_id}}

            # Stop auto-update for this user
            self._stop_auto_update(user_id)

            signal_repo = db_manager.get_signal_repository()
            signal = signal_repo.get_signal_by_id(signal_id)
            if not signal:
                await query.edit_message_text("❌ Signal not found", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="signals")]]))
                return

            position = get_position_for_signal(self.meta_trader, signal_id)

            entry_price = signal.open_price if hasattr(
                signal, 'open_price') else signal.get("open_price", "N/A")
            second_price = signal.second_price if hasattr(
                signal, 'second_price') else signal.get("second_price")
            stop_loss = signal.stop_loss if hasattr(
                signal, 'stop_loss') else signal.get("stop_loss", "N/A")
            tp_list = signal.tp_list if hasattr(
                signal, 'tp_list') else signal.get("tp_list", "N/A")
            signal_type = signal.signal_type if hasattr(
                signal, 'signal_type') else signal.get("signal_type", "N/A")
            channel = signal.telegram_channel_title if hasattr(
                signal, 'telegram_channel_title') else signal.get("telegram_channel_title", "Unknown")
            message_id = signal.telegram_message_id if hasattr(
                signal, 'telegram_message_id') else signal.get("telegram_message_id")
            chat_id = signal.telegram_message_chatid if hasattr(
                signal, 'telegram_message_chatid') else signal.get("telegram_message_chatid")

            # Build message link
            if message_id and chat_id:
                # For private channels, use the chat_id; for public channels, use the username
                message_link = f"https://t.me/c/{abs(int(chat_id))}/{message_id}"
            else:
                message_link = "No link available"

            # Get the last 2 positions for this signal, sorted by ID descending
            position_repo = db_manager.get_position_repository()
            db_positions = position_repo.get_positions_by_signal_id(signal_id)

            # Sort by position_id descending and take last 2
            db_positions_sorted = sorted(db_positions, key=lambda x: (
                x.position_id if hasattr(x, 'position_id') else x.get("position_id")), reverse=True)

            open_price_tickets = []
            second_price_tickets = []
            has_positions = False
            has_orders = False

            # First position (most recent) = open price, second position = second price
            for idx, db_pos in enumerate(db_positions_sorted[:2]):
                ticket = db_pos.position_id if hasattr(
                    db_pos, 'position_id') else db_pos.get("position_id")

                # Check if exists in MT5
                mt5_obj = self.meta_trader.get_position_by_ticket(ticket)
                if not mt5_obj:
                    mt5_obj = self.meta_trader.get_order_by_ticket(ticket)

                if not mt5_obj:
                    logger.warning(f"Ticket {ticket}: Not found in MT5")
                    continue

                # Determine if position or order
                if self.meta_trader.get_position_by_ticket(ticket):
                    has_positions = True
                else:
                    has_orders = True

                # First = open price, Second = second price
                if idx == 0:
                    open_price_tickets.append(ticket)
                else:
                    second_price_tickets.append(ticket)

            all_tickets_text = " / ".join(str(t) for t in (open_price_tickets + second_price_tickets)) if (
                open_price_tickets + second_price_tickets) else "None"

            # Determine emoji based on type and if position still exists in MT5
            if open_price_tickets:
                # Check if open price position still exists
                open_ticket = int(open_price_tickets[0])
                mt5_open = self.meta_trader.get_position_by_ticket(open_ticket)
                if not mt5_open:
                    mt5_open = self.meta_trader.get_order_by_ticket(
                        open_ticket)
                open_price_emoji = ("📈" if self.meta_trader.get_position_by_ticket(
                    open_ticket) else "⏳") if mt5_open else "❌"
            else:
                open_price_emoji = "❌"

            if second_price_tickets:
                # Check if second price position still exists
                second_ticket = int(second_price_tickets[0])
                mt5_second = self.meta_trader.get_position_by_ticket(
                    second_ticket)
                if not mt5_second:
                    mt5_second = self.meta_trader.get_order_by_ticket(
                        second_ticket)
                second_price_emoji = ("📈" if self.meta_trader.get_position_by_ticket(
                    second_ticket) else "⏳") if mt5_second else "❌"
            else:
                second_price_emoji = "❌"

            # Add signal type emoji
            type_emoji = "🟢" if signal_type == "BUY" else "🔴"

            text = f"""📊 **Signal Details**

**Message:** [{message_link}]({message_link})
**Signal Type:** {type_emoji} {signal_type}
**Tickets:** {all_tickets_text}
**Entry Price:** {entry_price}
{'**Second Price:** ' + str(second_price) if second_price else ''}
**Stop Loss:** {stop_loss}
**Take Profit:** {tp_list}

**Linked Positions:** {1 if position else 0}"""

            buttons = [
                [
                    InlineKeyboardButton(
                        "🔴 Close All", callback_data=f"close_{signal_id}_full"),
                    InlineKeyboardButton(
                        "🟢 Risk Free", callback_data=f"close_{signal_id}_risk_free"),
                ],
                [
                    InlineKeyboardButton(
                        "⬆️ Update SL", callback_data=f"update_{signal_id}_sl"),
                    InlineKeyboardButton(
                        "⬆️ Update TP", callback_data=f"update_{signal_id}_tp"),
                ],
                [
                    InlineKeyboardButton(
                        f"{open_price_emoji} Open Price ({entry_price})", callback_data=f"manage_{signal_id}_open"),
                ],
            ]
            # Add second price button if available
            if second_price:
                buttons.append([
                    InlineKeyboardButton(
                        f"{second_price_emoji} Second Price ({second_price})", callback_data=f"manage_{signal_id}_second"),
                ])
            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data="signals")])
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as e:
            # If message is not modified (same content), just answer silently
            if "Message is not modified" in str(e):
                await query.answer("📍 Already viewing this signal", show_alert=False)
            else:
                logger.error(
                    f"Error showing signal detail for signal_id={signal_id}: {e}", exc_info=True)
                try:
                    await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="signals")]]))
                except:
                    await query.answer(f"❌ Error: {str(e)}", show_alert=True)

    async def show_manage_signal_entries(self, query, user_id: int, signal_id: int, entry_type: str) -> None:
        """Show positions/orders for a specific entry price (open or second)"""
        try:
            self.user_states[user_id] = {"state": "manage_entries", "context": {
                "signal_id": signal_id, "entry_type": entry_type}}

            # Get signal and its linked positions
            signal_repo = db_manager.get_signal_repository()
            signal = signal_repo.get_signal_by_id(signal_id)
            if not signal:
                await query.edit_message_text("❌ Signal not found", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="signals")]]))
                return

            position_repo = db_manager.get_position_repository()
            db_positions = position_repo.get_positions_by_signal_id(signal_id)

            if not db_positions:
                await query.edit_message_text(f"❌ No positions found for this signal", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}")]]))
                return

            # Sort by position_id descending and take last 2
            db_positions_sorted = sorted(db_positions, key=lambda x: (
                x.position_id if hasattr(x, 'position_id') else x.get("position_id")), reverse=True)

            # Get ticket based on entry_type: first (open) or second
            ticket = None
            if entry_type == "open" and len(db_positions_sorted) > 0:
                ticket = db_positions_sorted[0].position_id if hasattr(
                    db_positions_sorted[0], 'position_id') else db_positions_sorted[0].get("position_id")
            elif entry_type == "second" and len(db_positions_sorted) > 1:
                ticket = db_positions_sorted[1].position_id if hasattr(
                    db_positions_sorted[1], 'position_id') else db_positions_sorted[1].get("position_id")
            else:
                await query.edit_message_text(
                    f"❌ No {entry_type} price position found",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}")]])
                )
                return

            # Try to get it from MT5 (could be position or order)
            position = self.meta_trader.get_position_by_ticket(ticket)
            if not position:
                position = self.meta_trader.get_order_by_ticket(ticket)

            if not position:
                await query.edit_message_text(
                    f"❌ Position/Order #{ticket} not found in MT5 (may have been closed)",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}")]])
                )
                return

            # Display position details
            symbol = position.symbol if hasattr(position, 'symbol') else "N/A"

            # Get prices (different fields for positions vs orders)
            if hasattr(position, 'open_price'):
                open_price = position.open_price
                current_price = position.price if hasattr(
                    position, 'price') else "N/A"
            else:
                # It's an order
                open_price = position.price_open if hasattr(
                    position, 'price_open') else "N/A"
                current_price = position.price_open if hasattr(
                    position, 'price_open') else "N/A"

            stop_loss = position.stop_loss if hasattr(
                position, 'stop_loss') else "N/A"
            take_profit = position.take_profit if hasattr(
                position, 'take_profit') else "N/A"
            lots = position.volume if hasattr(position, 'volume') else (
                position.volume_current if hasattr(position, 'volume_current') else 1)
            pnl = position.profit if hasattr(position, 'profit') else 0
            pnl_emoji = "📈" if pnl >= 0 else "📉"

            text = f"""📍 **Position**

**Ticket:** #{ticket}
**Symbol:** {symbol}
**Open:** {open_price} | **Current:** {current_price}
**SL:** {stop_loss} | **TP:** {take_profit}
**Lots:** {lots}

{pnl_emoji} **P&L:** ${pnl:.2f}"""

            buttons = [
                [
                    InlineKeyboardButton(
                        "🔴 Close Full", callback_data=f"close_{ticket}_full"),
                    InlineKeyboardButton(
                        "🟡 Close Half", callback_data=f"close_{ticket}_half"),
                ],
                [
                    InlineKeyboardButton(
                        "📉 Close Custom", callback_data=f"close_{ticket}_lot"),
                    InlineKeyboardButton(
                        "🟢 Risk Free", callback_data=f"close_{ticket}_risk_free"),
                ],
                [
                    InlineKeyboardButton(
                        "⬆️ Update SL", callback_data=f"update_{ticket}_sl"),
                    InlineKeyboardButton(
                        "⬆️ Update TP", callback_data=f"update_{ticket}_tp"),
                ],
            ]

            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data=f"signal_{signal_id}")])

            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as e:
            logger.error(
                f"Error showing manage signal entries: {e}", exc_info=True)
            try:
                await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="signals")]]))
            except:
                await query.answer(f"❌ Error: {str(e)}", show_alert=True)

    async def show_position_list(self, query, user_id: int) -> None:
        """Show all MT5 positions and pending orders as inline buttons"""
        try:
            STATE_POSITION_LIST = "position_list"
            self.user_states[user_id] = {
                "state": STATE_POSITION_LIST, "context": {}}

            if not self.meta_trader:
                await query.edit_message_text("❌ MetaTrader connection not available")
                return

            positions = self.meta_trader.get_open_positions() or []
            orders = self.meta_trader.get_pending_orders() or []

            if not positions and not orders:
                await query.edit_message_text(
                    "📭 No open positions or pending orders",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            buttons = []

            for pos in positions:
                symbol = pos.symbol if hasattr(
                    pos, 'symbol') else pos.get("symbol", "UNKNOWN")
                ticket = pos.ticket if hasattr(
                    pos, 'ticket') else pos.get("ticket")
                button_text = f"📈 {ticket}"
                buttons.append([InlineKeyboardButton(
                    button_text, callback_data=f"position_{ticket}")])

            for order in orders:
                symbol = order.symbol if hasattr(
                    order, 'symbol') else order.get("symbol", "UNKNOWN")
                ticket = order.ticket if hasattr(
                    order, 'ticket') else order.get("ticket")
                button_text = f"⏳ {ticket}"
                buttons.append([InlineKeyboardButton(
                    button_text, callback_data=f"position_{ticket}")])

            text = f"📈 **Positions & Orders** 🔄 (Auto-updating)\n\n**Open:** {len(positions)} | **Pending:** {len(orders)}\n\nSelect for actions:"
            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data="menu")])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

            # Store message info for auto-update
            self.active_updates[user_id] = {
                "state": "position_list",
                "message_id": query.message.message_id,
                "chat_id": query.message.chat_id,
                "last_text": text,  # Store for comparison
                "last_buttons": buttons
            }

            # Start auto-update task for this user
            asyncio.create_task(
                self._auto_update_position_list(user_id, query.get_bot()))

        except Exception as e:
            logger.error(f"Error showing position list: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]))

    async def _auto_update_position_list(self, user_id: int, bot) -> None:
        """Automatically update position list for user every 5 seconds"""
        try:
            while user_id in self.active_updates and self.active_updates[user_id]["state"] == "position_list":
                await asyncio.sleep(self.update_interval)

                # Check if user is still on position_list page
                if user_id not in self.active_updates or self.active_updates[user_id]["state"] != "position_list":
                    break

                update_info = self.active_updates[user_id]

                if not self.meta_trader:
                    continue

                positions = self.meta_trader.get_open_positions() or []
                orders = self.meta_trader.get_pending_orders() or []

                if not positions and not orders:
                    text = "📭 No open positions or pending orders"
                    buttons = [[InlineKeyboardButton(
                        "⬅️ Back", callback_data="menu")]]
                else:
                    buttons = []

                    for pos in positions:
                        symbol = pos.symbol if hasattr(
                            pos, 'symbol') else pos.get("symbol", "UNKNOWN")
                        ticket = pos.ticket if hasattr(
                            pos, 'ticket') else pos.get("ticket")
                        button_text = f"📈 {ticket}"
                        buttons.append([InlineKeyboardButton(
                            button_text, callback_data=f"position_{ticket}")])

                    for order in orders:
                        symbol = order.symbol if hasattr(
                            order, 'symbol') else order.get("symbol", "UNKNOWN")
                        ticket = order.ticket if hasattr(
                            order, 'ticket') else order.get("ticket")
                        button_text = f"⏳ {ticket}"
                        buttons.append([InlineKeyboardButton(
                            button_text, callback_data=f"position_{ticket}")])

                    text = f"📈 **Positions & Orders** 🔄 (Auto-updating)\n\n**Open:** {len(positions)} | **Pending:** {len(orders)}\n\nSelect for actions:"
                    buttons.append([InlineKeyboardButton(
                        "⬅️ Back", callback_data="menu")])

                # Only update if content has changed
                content_changed = (update_info.get("last_text") != text or
                                   update_info.get("last_buttons") != buttons)

                if content_changed:
                    # Update the message
                    try:
                        await bot.edit_message_text(
                            chat_id=update_info["chat_id"],
                            message_id=update_info["message_id"],
                            text=text,
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                        # Update stored content for next comparison
                        update_info["last_text"] = text
                        update_info["last_buttons"] = buttons
                    except Exception as e:
                        logger.debug(
                            f"Could not update position list for user {user_id}: {e}")
                        # Stop updating if message no longer exists
                        if user_id in self.active_updates:
                            del self.active_updates[user_id]
                        break

        except Exception as e:
            logger.error(f"Error in auto-update position list: {e}")
            if user_id in self.active_updates:
                del self.active_updates[user_id]

    async def show_position_detail(self, query, user_id: int, ticket: int) -> None:
        """Show position/order details with action buttons"""
        try:
            STATE_VIEWING_POSITION = "viewing_position"
            self.user_states[user_id] = {
                "state": STATE_VIEWING_POSITION, "context": {"ticket": ticket}}

            # Stop auto-update for this user
            self._stop_auto_update(user_id)

            if not self.meta_trader:
                await query.edit_message_text("❌ MetaTrader not available")
                return

            position = self.meta_trader.get_position_by_ticket(ticket)
            order = None
            if not position:
                order = self.meta_trader.get_order_by_ticket(ticket)

            if not position and not order:
                await query.edit_message_text("❌ Position not found", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]]))
                return

            if position:
                symbol = position.symbol if hasattr(
                    position, 'symbol') else "N/A"
                open_price = position.open_price if hasattr(
                    position, 'open_price') else "N/A"
                current_price = position.price if hasattr(
                    position, 'price') else "N/A"
                stop_loss = position.stop_loss if hasattr(
                    position, 'stop_loss') else "N/A"
                take_profit = position.take_profit if hasattr(
                    position, 'take_profit') else "N/A"
                lots = position.volume if hasattr(position, 'volume') else 1
                pnl = position.profit if hasattr(position, 'profit') else 0
                pnl_emoji = "📈" if pnl >= 0 else "📉"

                # Get signal information from database
                position_repo = db_manager.get_position_repository()
                signal_repo = db_manager.get_signal_repository()

                db_position = position_repo.get_position_by_ticket(ticket)
                signal_info = ""

                if db_position:
                    signal_id = db_position.signal_id if hasattr(
                        db_position, 'signal_id') else db_position.get('signal_id')
                    signal = signal_repo.get_signal_by_id(signal_id)

                    if signal:
                        provider = signal.provider if hasattr(
                            signal, 'provider') else signal.get('provider', 'Unknown')
                        channel = signal.telegram_channel_title if hasattr(
                            signal, 'telegram_channel_title') else signal.get('telegram_channel_title', 'Unknown')
                        message_id = signal.telegram_message_id if hasattr(
                            signal, 'telegram_message_id') else signal.get('telegram_message_id')
                        chat_id = signal.telegram_message_chatid if hasattr(
                            signal, 'telegram_message_chatid') else signal.get('telegram_message_chatid')

                        # Escape markdown special characters
                        provider_escaped = str(provider).replace('_', '\\_').replace('*', '\\*').replace(
                            '[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('`', '\\`')
                        channel_escaped = str(channel).replace('_', '\\_').replace('*', '\\*').replace(
                            '[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('`', '\\`')

                        signal_info = f"\n\n📊 Signal Info:\n"
                        signal_info += f"Signal ID: #{signal_id}\n"
                        signal_info += f"Provider: {provider_escaped}\n"
                        signal_info += f"Channel: {channel_escaped}\n"

                        if message_id and chat_id:
                            # Convert chat_id for Telegram link format
                            chat_id_int = int(chat_id)
                            if chat_id_int < 0:
                                chat_id_str = str(chat_id_int)
                                if chat_id_str.startswith('-100'):
                                    # Remove -100 prefix
                                    chat_id_for_link = chat_id_str[4:]
                                else:
                                    chat_id_for_link = str(abs(chat_id_int))
                            else:
                                chat_id_for_link = str(chat_id_int)
                            message_link = f"https://t.me/c/{chat_id_for_link}/{message_id}"
                            signal_info += f"[View Signal]({message_link})"

                text = f"""📍 **Position**

**Ticket:** #{ticket}
**Symbol:** {symbol}
**Open:** {open_price} | **Current:** {current_price}
**SL:** {stop_loss} | **TP:** {take_profit}
**Lots:** {lots}

{pnl_emoji} **P&L:** ${pnl:.2f}{signal_info}"""

                buttons = [
                    [
                        InlineKeyboardButton(
                            "🔴 Close Full", callback_data=f"close_{ticket}_full"),
                        InlineKeyboardButton(
                            "🟡 Close Half", callback_data=f"close_{ticket}_half"),
                    ],
                    [
                        InlineKeyboardButton(
                            "📉 Close Custom", callback_data=f"close_{ticket}_lot"),
                        InlineKeyboardButton(
                            "🟢 Risk Free", callback_data=f"close_{ticket}_risk_free"),
                    ],
                    [
                        InlineKeyboardButton(
                            "⬆️ Update SL", callback_data=f"update_{ticket}_sl"),
                        InlineKeyboardButton(
                            "⬆️ Update TP", callback_data=f"update_{ticket}_tp"),
                    ],
                ]
            else:
                symbol = order.symbol if hasattr(order, 'symbol') else "N/A"
                order_type = order.type if hasattr(order, 'type') else "N/A"
                open_price = order.price_open if hasattr(
                    order, 'price_open') else "N/A"
                stop_loss = order.stop_loss if hasattr(
                    order, 'stop_loss') else "N/A"
                take_profit = order.take_profit if hasattr(
                    order, 'take_profit') else "N/A"
                lots = order.volume_current if hasattr(
                    order, 'volume_current') else 1

                # Get signal information from database
                position_repo = db_manager.get_position_repository()
                signal_repo = db_manager.get_signal_repository()

                db_position = position_repo.get_position_by_ticket(ticket)
                signal_info = ""

                if db_position:
                    signal_id = db_position.signal_id if hasattr(
                        db_position, 'signal_id') else db_position.get('signal_id')
                    signal = signal_repo.get_signal_by_id(signal_id)

                    if signal:
                        provider = signal.provider if hasattr(
                            signal, 'provider') else signal.get('provider', 'Unknown')
                        channel = signal.telegram_channel_title if hasattr(
                            signal, 'telegram_channel_title') else signal.get('telegram_channel_title', 'Unknown')
                        message_id = signal.telegram_message_id if hasattr(
                            signal, 'telegram_message_id') else signal.get('telegram_message_id')
                        chat_id = signal.telegram_message_chatid if hasattr(
                            signal, 'telegram_message_chatid') else signal.get('telegram_message_chatid')

                        # Escape markdown special characters
                        provider_escaped = str(provider).replace('_', '\\_').replace('*', '\\*').replace(
                            '[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('`', '\\`')
                        channel_escaped = str(channel).replace('_', '\\_').replace('*', '\\*').replace(
                            '[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('`', '\\`')

                        signal_info = f"\n\n📊 Signal Info:\n"
                        signal_info += f"Signal ID: #{signal_id}\n"
                        signal_info += f"Provider: {provider_escaped}\n"
                        signal_info += f"Channel: {channel_escaped}\n"

                        if message_id and chat_id:
                            # Convert chat_id for Telegram link format
                            chat_id_int = int(chat_id)
                            if chat_id_int < 0:
                                chat_id_str = str(chat_id_int)
                                if chat_id_str.startswith('-100'):
                                    # Remove -100 prefix
                                    chat_id_for_link = chat_id_str[4:]
                                else:
                                    chat_id_for_link = str(abs(chat_id_int))
                            else:
                                chat_id_for_link = str(chat_id_int)
                            message_link = f"https://t.me/c/{chat_id_for_link}/{message_id}"
                            signal_info += f"[View Signal]({message_link})"

                text = f"""⏳ **Pending Order**

**Ticket:** #{ticket}
**Symbol:** {symbol}
**Type:** {order_type}
**Open Price:** {open_price}
**SL:** {stop_loss} | **TP:** {take_profit}
**Lots:** {lots}{signal_info}"""

                buttons = [
                    [InlineKeyboardButton(
                        "🗑️ Delete", callback_data=f"delete_{ticket}")],
                ]

            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data="positions")])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.error(f"Error showing position detail: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]]))

    async def show_tester(self, query, user_id: int) -> None:
        """Show signal tester interface"""
        try:
            STATE_TESTER = "tester"
            self.user_states[user_id] = {"state": STATE_TESTER, "context": {}}

            text = """🧪 **Signal Tester**

Send a signal text to parse:

**Example:**
`EUR/USD BUY 1.2500 SL: 1.2450 TP: 1.2550, 1.2600`

Will export:
• Open Price
• Second Price
• Stop Loss
• Take Profit List"""

            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.error(f"Error showing tester: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]))

    async def show_account_details(self, update: Update, user_id: int) -> None:
        """Show full account details with main menu buttons on startup"""
        try:
            STATE_MAIN_MENU = "main_menu"
            self.user_states[user_id] = {
                "state": STATE_MAIN_MENU, "context": {}}

            if not self.meta_trader:
                await update.message.reply_text("❌ MetaTrader not available")
                return

            account_info = mt5.account_info()
            if not account_info:
                await update.message.reply_text("❌ Unable to fetch account info")
                return

            positions = self.meta_trader.get_open_positions() or []
            orders = self.meta_trader.get_pending_orders() or []

            # Calculate account metrics
            balance = account_info.balance
            equity = account_info.equity
            profit = equity - balance
            profit_percent = (profit / balance * 100) if balance else 0
            profit_emoji = "📈" if profit >= 0 else "📉"

            margin_usage = ((account_info.margin / (account_info.margin + account_info.margin_free))
                            * 100) if (account_info.margin + account_info.margin_free) > 0 else 0
            margin_emoji = "🟢" if margin_usage < 70 else "🟡" if margin_usage < 90 else "🔴"

            text = f"""👋 **Welcome to Signal Trader Bot**

📊 **Account Details** - {account_info.login}

**Balance:** ${balance:,.2f}
**Equity:** ${equity:,.2f}
{profit_emoji} **P&L:** ${profit:,.2f} ({profit_percent:+.2f}%)

💰 **Margin Info**
**Margin Used:** ${account_info.margin:,.2f}
**Free Margin:** ${account_info.margin_free:,.2f}
{margin_emoji} **Usage:** {margin_usage:.1f}%

📈 **Positions:** {len(positions)} open
⏳ **Pending Orders:** {len(orders)}

_Updated: {datetime.now().strftime('%H:%M:%S')}_

**Select an option:**"""

            buttons = [
                [
                    InlineKeyboardButton(
                        "📊 Active Signals", callback_data="signals"),
                    InlineKeyboardButton(
                        "📈 Active Positions", callback_data="positions"),
                ],
                [
                    InlineKeyboardButton(
                        "🔄 New Trade", callback_data="open_trade"),
                    InlineKeyboardButton(
                        "🧪 Signal Tester", callback_data="tester"),
                ],
                [
                    InlineKeyboardButton("📜 History", callback_data="history"),
                    InlineKeyboardButton("📊 Analyze", callback_data="analyze"),
                ],
            ]

            message = await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            # Store message info for auto-update with bot context
            self.active_updates[user_id] = {
                "state": "main_menu",
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "last_text": text,  # Store for comparison
                "last_buttons": buttons,
                "context": update.get_bot()  # Store bot for later use
            }

            # Start auto-update task for this user
            asyncio.create_task(self._auto_update_account_details(user_id))

        except Exception as e:
            logger.error(f"Error showing account details: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def _auto_update_account_details(self, user_id: int) -> None:
        """Automatically update account details for user every 5 seconds"""
        try:
            while user_id in self.active_updates and self.active_updates[user_id]["state"] == "main_menu":
                await asyncio.sleep(self.update_interval)

                # Check if user is still on main_menu page
                if user_id not in self.active_updates or self.active_updates[user_id]["state"] != "main_menu":
                    break

                update_info = self.active_updates[user_id]
                bot = update_info.get("context")

                if not bot or not self.meta_trader:
                    continue

                account_info = mt5.account_info()
                if not account_info:
                    continue

                positions = self.meta_trader.get_open_positions() or []
                orders = self.meta_trader.get_pending_orders() or []

                # Calculate account metrics
                balance = account_info.balance
                equity = account_info.equity
                profit = equity - balance
                profit_percent = (profit / balance * 100) if balance else 0
                profit_emoji = "📈" if profit >= 0 else "📉"

                margin_usage = ((account_info.margin / (account_info.margin + account_info.margin_free))
                                * 100) if (account_info.margin + account_info.margin_free) > 0 else 0
                margin_emoji = "🟢" if margin_usage < 70 else "🟡" if margin_usage < 90 else "🔴"

                text = f"""👋 **Welcome to Signal Trader Bot**

📊 **Account Details** - {account_info.login}

**Balance:** ${balance:,.2f}
**Equity:** ${equity:,.2f}
{profit_emoji} **P&L:** ${profit:,.2f} ({profit_percent:+.2f}%)

💰 **Margin Info**
**Margin Used:** ${account_info.margin:,.2f}
**Free Margin:** ${account_info.margin_free:,.2f}
{margin_emoji} **Usage:** {margin_usage:.1f}%

📈 **Positions:** {len(positions)} open
⏳ **Pending Orders:** {len(orders)}

_Updated: {datetime.now().strftime('%H:%M:%S')}_

**Select an option:**"""

                buttons = [
                    [
                        InlineKeyboardButton(
                            "📊 Active Signals", callback_data="signals"),
                        InlineKeyboardButton(
                            "📈 Active Positions", callback_data="positions"),
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 New Trade", callback_data="open_trade"),
                        InlineKeyboardButton(
                            "🧪 Signal Tester", callback_data="tester"),
                    ],
                    [
                        InlineKeyboardButton(
                            "📜 History", callback_data="history"),
                    ],
                ]

                # Only update if content has changed
                content_changed = (update_info.get("last_text") != text or
                                   update_info.get("last_buttons") != buttons)

                if content_changed:
                    # Update the message
                    try:
                        await bot.edit_message_text(
                            chat_id=update_info["chat_id"],
                            message_id=update_info["message_id"],
                            text=text,
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                        # Update stored content for next comparison
                        update_info["last_text"] = text
                        update_info["last_buttons"] = buttons
                    except Exception as e:
                        logger.debug(
                            f"Could not update account details for user {user_id}: {e}")
                        # Stop updating if message no longer exists
                        if user_id in self.active_updates:
                            del self.active_updates[user_id]
                        break

        except Exception as e:
            logger.error(f"Error in auto-update account details: {e}")
            if user_id in self.active_updates:
                del self.active_updates[user_id]

    async def show_account_details_from_callback(self, query, user_id: int) -> None:
        """Show account details from callback (used for menu navigation)"""
        try:
            STATE_MAIN_MENU = "main_menu"
            self.user_states[user_id] = {
                "state": STATE_MAIN_MENU, "context": {}}

            # Stop auto-update for this user
            self._stop_auto_update(user_id)

            if not self.meta_trader:
                await query.edit_message_text("❌ MetaTrader not available")
                return

            account_info = mt5.account_info()
            if not account_info:
                await query.edit_message_text("❌ Unable to fetch account info")
                return

            positions = self.meta_trader.get_open_positions() or []
            orders = self.meta_trader.get_pending_orders() or []

            # Calculate account metrics
            balance = account_info.balance
            equity = account_info.equity
            profit = equity - balance
            profit_percent = (profit / balance * 100) if balance else 0
            profit_emoji = "📈" if profit >= 0 else "📉"

            margin_usage = ((account_info.margin / (account_info.margin + account_info.margin_free))
                            * 100) if (account_info.margin + account_info.margin_free) > 0 else 0
            margin_emoji = "🟢" if margin_usage < 70 else "🟡" if margin_usage < 90 else "🔴"

            text = f"""👋 **Welcome to Signal Trader Bot**

📊 **Account Details** - {account_info.login}

**Balance:** ${balance:,.2f}
**Equity:** ${equity:,.2f}
{profit_emoji} **P&L:** ${profit:,.2f} ({profit_percent:+.2f}%)

💰 **Margin Info**
**Margin Used:** ${account_info.margin:,.2f}
**Free Margin:** ${account_info.margin_free:,.2f}
{margin_emoji} **Usage:** {margin_usage:.1f}%

📈 **Positions:** {len(positions)} open
⏳ **Pending Orders:** {len(orders)}

_Updated: {datetime.now().strftime('%H:%M:%S')}_

**Select an option:**"""

            buttons = [
                [
                    InlineKeyboardButton(
                        "📊 Active Signals", callback_data="signals"),
                    InlineKeyboardButton(
                        "📈 Active Positions", callback_data="positions"),
                ],
                [
                    InlineKeyboardButton(
                        "🔄 New Trade", callback_data="open_trade"),
                    InlineKeyboardButton(
                        "🧪 Signal Tester", callback_data="tester"),
                ],
                [
                    InlineKeyboardButton("📜 History", callback_data="history"),
                    InlineKeyboardButton("📊 Analyze", callback_data="analyze"),
                ],
            ]

            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as e:
            logger.error(f"Error showing account details from callback: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def show_trade_summary(self, query, user_id: int) -> None:
        """Show trade summary with account stats"""
        try:
            STATE_MAIN_MENU = "main_menu"
            self.user_states[user_id] = {
                "state": STATE_MAIN_MENU, "context": {}}

            if not self.meta_trader:
                await query.edit_message_text("❌ MetaTrader not available")
                return

            account_info = mt5.account_info()
            if not account_info:
                await query.edit_message_text("❌ Unable to fetch account info")
                return

            positions = self.meta_trader.get_open_positions() or []
            orders = self.meta_trader.get_pending_orders() or []

            balance = account_info.balance
            equity = account_info.equity
            profit = equity - balance
            profit_percent = (profit / balance * 100) if balance else 0
            profit_emoji = "📈" if profit >= 0 else "📉"

            text = f"""💼 **Trade Summary**

**Balance:** ${balance:,.2f}
**Equity:** ${equity:,.2f}
{profit_emoji} **P&L:** ${profit:,.2f} ({profit_percent:+.2f}%)

**Margin:** ${account_info.margin:,.2f}
**Free Margin:** ${account_info.margin_free:,.2f}

**Positions:** {len(positions)} open
**Orders:** {len(orders)} pending

_Updated: {datetime.now().strftime('%H:%M:%S')}_"""

            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.error(f"Error showing trade summary: {e}")
            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup(buttons))

    async def show_history_menu(self, query, user_id: int) -> None:
        """Show history time range selection menu"""
        try:
            # Stop any auto-updates
            self._stop_auto_update(user_id)

            STATE_HISTORY = "history_menu"
            self.user_states[user_id] = {"state": STATE_HISTORY, "context": {}}

            text = """📜 **Trading History**

Select a time range to view your trading history:

**Quick Options:**
• 📅 Today - View today's trades
• 📆 Yesterday - View yesterday's trades
• 🗓️ Calendar - Choose custom date range

History includes both closed and active positions with comprehensive metrics."""

            buttons = [
                [
                    InlineKeyboardButton(
                        "📅 Today", callback_data="history_today"),
                    InlineKeyboardButton(
                        "📆 Yesterday", callback_data="history_yesterday"),
                ],
                [
                    InlineKeyboardButton(
                        "🗓️ Calendar", callback_data="history_calendar"),
                ],
                [InlineKeyboardButton("⬅️ Back", callback_data="menu")]
            ]

            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.error(f"Error showing history menu: {e}")
            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup(buttons))

    async def show_history_calendar(self, query, user_id: int, year: int = None, month: int = None, mode: str = "from") -> None:
        """Show calendar for date selection"""
        try:
            # Stop any auto-updates
            self._stop_auto_update(user_id)

            import calendar
            from datetime import datetime

            now = datetime.now()
            year = year or now.year
            month = month or now.month

            # Store mode in user context (selecting 'from' or 'to' date)
            if user_id not in self.user_states:
                self.user_states[user_id] = {}
            if "context" not in self.user_states[user_id]:
                self.user_states[user_id]["context"] = {}

            self.user_states[user_id]["state"] = "history_calendar"
            self.user_states[user_id]["context"]["calendar_mode"] = mode
            self.user_states[user_id]["context"]["calendar_year"] = year
            self.user_states[user_id]["context"]["calendar_month"] = month

            # Get month calendar
            cal = calendar.monthcalendar(year, month)
            month_name = calendar.month_name[month]

            # Build calendar text
            from_date = self.user_states[user_id]["context"].get("from_date")
            to_date = self.user_states[user_id]["context"].get("to_date")

            text = f"""🗓️ **Calendar - Select {'Start' if mode == 'from' else 'End'} Date**

**{month_name} {year}**
"""

            if from_date:
                text += f"\n📍 From: {from_date.strftime('%Y-%m-%d')}"
            if to_date:
                text += f"\n📍 To: {to_date.strftime('%Y-%m-%d')}"

            # Build calendar buttons
            buttons = []

            # Month/Year navigation row
            buttons.append([
                InlineKeyboardButton(
                    "◀️", callback_data=f"cal_prev_{year}_{month}_{mode}"),
                InlineKeyboardButton(
                    f"{month_name} {year}", callback_data="cal_noop"),
                InlineKeyboardButton(
                    "▶️", callback_data=f"cal_next_{year}_{month}_{mode}"),
            ])

            # Weekday headers
            buttons.append([
                InlineKeyboardButton("Mo", callback_data="cal_noop"),
                InlineKeyboardButton("Tu", callback_data="cal_noop"),
                InlineKeyboardButton("We", callback_data="cal_noop"),
                InlineKeyboardButton("Th", callback_data="cal_noop"),
                InlineKeyboardButton("Fr", callback_data="cal_noop"),
                InlineKeyboardButton("Sa", callback_data="cal_noop"),
                InlineKeyboardButton("Su", callback_data="cal_noop"),
            ])

            # Calendar days
            for week in cal:
                week_buttons = []
                for day in week:
                    if day == 0:
                        week_buttons.append(InlineKeyboardButton(
                            " ", callback_data="cal_noop"))
                    else:
                        week_buttons.append(InlineKeyboardButton(
                            str(day),
                            callback_data=f"cal_day_{year}_{month}_{day}_{mode}"
                        ))
                buttons.append(week_buttons)

            # Action buttons
            if from_date and to_date:
                buttons.append([
                    InlineKeyboardButton(
                        "✅ View Results", callback_data="history_custom_view"),
                    InlineKeyboardButton(
                        "🔄 Reset", callback_data="history_calendar_reset")
                ])
            elif from_date and mode == "to":
                buttons.append([
                    InlineKeyboardButton(
                        "🔄 Reset", callback_data="history_calendar_reset")
                ])

            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data="history")])

            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.error(f"Error showing calendar: {e}")
            buttons = [[InlineKeyboardButton(
                "⬅️ Back", callback_data="history")]]
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup(buttons))

    async def show_history_results(self, query, user_id: int, range_type: str, from_date: datetime = None, to_date: datetime = None) -> None:
        """Show history results for selected date range"""
        try:
            # Stop any auto-updates
            self._stop_auto_update(user_id)

            # Initialize user state if needed
            if user_id not in self.user_states:
                self.user_states[user_id] = {}
            if "context" not in self.user_states[user_id]:
                self.user_states[user_id]["context"] = {}

            # Only reset page to 0 if this is a new search (different range type or dates)
            current_range = self.user_states[user_id]["context"].get(
                "history_range_type")
            current_from = self.user_states[user_id]["context"].get(
                "from_date")
            current_to = self.user_states[user_id]["context"].get("to_date")

            # Check if this is a new search vs pagination
            is_new_search = (
                current_range != range_type or
                (range_type == "custom" and (
                    current_from != from_date or current_to != to_date))
            )

            # Reset page only for new searches
            if is_new_search or "history_page" not in self.user_states[user_id]["context"]:
                self.user_states[user_id]["context"]["history_page"] = 0

            from .history_helpers import (
                get_date_range_timestamps, get_historical_deals,
                match_positions_with_signals, get_open_positions_with_metrics
            )

            # Get date range
            start, end = get_date_range_timestamps(
                range_type, from_date, to_date)

            # Show loading message
            await query.edit_message_text("🔄 Loading trading history...")

            # Fetch historical deals
            deals = get_historical_deals(start, end)

            # Match with signals
            historical_positions = match_positions_with_signals(deals)

            # Get open positions if they're within the date range
            open_positions = get_open_positions_with_metrics(self.meta_trader)

            # Filter open positions by date range
            filtered_open = [
                pos for pos in open_positions
                if start <= pos['metrics']['entry_time'] <= end
            ]

            # Combine results
            all_results = historical_positions + filtered_open
            logger.info(f"[HISTORY] User {user_id}: {len(all_results)} total positions")

            if not all_results:
                text = f"""📜 **Trading History**

**Period:** {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}

No trades found for this period."""

                buttons = [[InlineKeyboardButton(
                    "⬅️ Back", callback_data="history")]]
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
                return

            # Calculate summary statistics
            total_trades = len(all_results)
            closed_trades = len(
                [r for r in all_results if not r.get('metrics', {}).get('is_open', False)])
            open_trades = len(
                [r for r in all_results if r.get('metrics', {}).get('is_open', False)])

            total_profit = sum(r.get('metrics', {}).get('net_profit', 0) for r in all_results)
            winning_trades = len(
                [r for r in all_results if r.get('metrics', {}).get('net_profit', 0) > 0])
            losing_trades = len(
                [r for r in all_results if r.get('metrics', {}).get('net_profit', 0) < 0])
            win_rate = (winning_trades / total_trades *
                        100) if total_trades > 0 else 0

            # Count TP vs SL outcomes
            tp_count = len(
                [r for r in all_results if 'TP' in r.get('metrics', {}).get('exit_reason', '')])
            sl_count = len(
                [r for r in all_results if r.get('metrics', {}).get('exit_reason') == 'STOP_LOSS'])

            profit_emoji = "📈" if total_profit >= 0 else "📉"

            # Build summary text
            text = f"""📜 **Trading History**

**Period:** {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}

📊 **Summary:**
**Total Trades:** {total_trades} ({closed_trades} closed, {open_trades} open)
**Win Rate:** {win_rate:.1f}% ({winning_trades}W / {losing_trades}L)
{profit_emoji} **Total P&L:** ${total_profit:.2f}

🎯 **Outcomes:**
**TP Hit:** {tp_count} | **SL Hit:** {sl_count}

**Select a trade for details:**"""

            # Build buttons for each position
            buttons = []

            # Store results in user context for later
            self.user_states[user_id]["context"]["history_results"] = all_results
            self.user_states[user_id]["context"]["history_range_type"] = range_type

            # Get current page (default to 0)
            current_page = self.user_states[user_id]["context"].get(
                "history_page", 0)
            self.user_states[user_id]["context"]["history_page"] = current_page

            # Calculate pagination
            page_size = 20
            total_pages = (len(all_results) + page_size -
                           1) // page_size  # Ceiling division
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(all_results))

            # Update text with page info
            if total_pages > 1:
                text += f"\n\n_Page {current_page + 1}/{total_pages} - Showing {start_idx + 1}-{end_idx} of {len(all_results)} trades_"

            for idx in range(start_idx, end_idx):
                result = all_results[idx]
                metrics = result.get('metrics', {})
                signal = result.get('signal')

                # Build button text with ticket ID and symbol
                ticket_id = metrics.get('position_id', 'N/A')
                symbol = metrics.get('symbol', 'N/A')
                position_type = metrics.get('position_type', 'N/A')
                profit = metrics.get('net_profit', 0)
                status = "🟢" if metrics.get('is_open') else (
                    "📈" if profit >= 0 else "📉")
                exit_reason = metrics.get('exit_reason', 'OPEN')

                if signal and isinstance(signal, dict):
                    channel = signal.get('channel', 'Unknown')[:12]  # Truncate if too long
                    button_text = f"{status} #{ticket_id} {symbol} {position_type} - {channel} ${profit:.1f}"
                else:
                    button_text = f"{status} #{ticket_id} {symbol} {position_type} ${profit:.1f}"

                buttons.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"history_detail_{idx}"
                )])

            # Add pagination buttons if needed
            if total_pages > 1:
                pagination_buttons = []
                if current_page > 0:
                    pagination_buttons.append(InlineKeyboardButton(
                        "◀️ Previous", callback_data="history_page_prev"))
                if current_page < total_pages - 1:
                    pagination_buttons.append(InlineKeyboardButton(
                        "Next ▶️", callback_data="history_page_next"))

                if pagination_buttons:
                    buttons.append(pagination_buttons)

            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data="history")])

            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.error(f"Error showing history results: {e}")
            buttons = [[InlineKeyboardButton(
                "⬅️ Back", callback_data="history")]]
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup(buttons))

    async def show_history_detail(self, query, user_id: int, result_index: int) -> None:
        """Show detailed metrics for a specific historical position"""
        try:
            # Stop any auto-updates
            self._stop_auto_update(user_id)

            # Get results from user context
            results = self.user_states[user_id]["context"].get(
                "history_results", [])

            if result_index >= len(results):
                await query.answer("❌ Position not found", show_alert=True)
                return

            result = results[result_index]
            metrics = result.get('metrics')
            signal = result.get('signal')

            if not metrics:
                await query.answer("❌ Invalid position data", show_alert=True)
                return

            # If signal is not in cached data, try to fetch it directly from database
            if not signal:
                ticket_id = metrics.get('position_id')
                if ticket_id:
                    try:
                        signal_repo = db_manager.get_signal_repository()
                        signal_model = signal_repo.get_signal_by_position_id(ticket_id)

                        if signal_model:
                            # SignalModel object - access attributes directly
                            signal = {
                                'signal_id': signal_model.id,
                                'provider': signal_model.provider if signal_model.provider else 'telegram',
                                'channel': signal_model.telegram_channel_title,
                                'message_id': signal_model.telegram_message_id,
                                'chat_id': signal_model.telegram_message_chatid,
                                'signal_type': signal_model.signal_type,
                                'open_price': signal_model.open_price,
                                'stop_loss': signal_model.stop_loss,
                                'tp_list': signal_model.tp_list,
                                'symbol': signal_model.symbol
                            }
                    except Exception as e:
                        logger.error(f"Error fetching signal for ticket {ticket_id}: {e}")

            # Build detailed message using HTML (more robust than Markdown)
            position_type_emoji = "🟢" if metrics.get('position_type') == "BUY" else "🔴"
            status_emoji = "🟢" if metrics.get('is_open') else "✅"

            text = f"""📊 <b>Trade Details - {status_emoji} {'OPEN' if metrics.get('is_open') else 'CLOSED'}</b>

{position_type_emoji} <b>{metrics.get('position_type', 'N/A')} {metrics.get('symbol', 'N/A')}</b>
<b>Ticket:</b> #{metrics.get('position_id', 'N/A')}
"""

            # Add signal info if available
            if signal and isinstance(signal, dict):
                signal_id = signal.get('signal_id', 'N/A')
                provider = signal.get('provider', 'Unknown')
                channel = signal.get('channel', 'Unknown')
                message_id = signal.get('message_id')
                chat_id = signal.get('chat_id')

                text += f"\n📊 <b>Signal Info:</b>\n"
                text += f"Signal ID: #{signal_id}\n"
                text += f"Provider: {provider}\n"
                text += f"Channel: {channel}\n"

                if message_id and chat_id:
                    try:
                        # Convert chat_id for Telegram link format
                        chat_id_int = int(chat_id)
                        if chat_id_int < 0:
                            chat_id_str = str(chat_id_int)
                            if chat_id_str.startswith('-100'):
                                chat_id_for_link = chat_id_str[4:]
                            else:
                                chat_id_for_link = str(abs(chat_id_int))
                        else:
                            chat_id_for_link = str(chat_id_int)

                        message_link = f"https://t.me/c/{chat_id_for_link}/{message_id}"
                        text += f'<a href="{message_link}">View Signal</a>\n'
                    except Exception as link_error:
                        logger.warning(f"Error creating message link: {link_error}")
                        text += f"Message: Not available\n"
                else:
                    text += f"Message: Not available\n"

            # Price information
            entry_price = metrics.get('entry_price', 0)
            text += f"""
💰 <b>Price Info:</b>
<b>Entry:</b> {entry_price:.5f}
"""

            if metrics.get('is_open'):
                current_price = metrics.get('current_price', 0)
                text += f"<b>Current:</b> {current_price:.5f}\n"
            else:
                exit_price = metrics.get('exit_price', 0)
                text += f"<b>Exit:</b> {exit_price:.5f}\n"

            price_change = metrics.get('price_change', 0)
            text += f"<b>Change:</b> {price_change:.5f} pips\n"

            # P&L Information
            profit = metrics.get('net_profit', 0)
            profit_emoji = "📈" if profit >= 0 else "📉"
            roi_percent = metrics.get('roi_percent', 0)
            volume = metrics.get('volume', 0)

            text += f"""
{profit_emoji} <b>Performance:</b>
<b>P&L:</b> ${profit:.2f}
<b>ROI:</b> {roi_percent:.2f}%
<b>Volume:</b> {volume:.2f} lots
"""

            # Exit reason (if closed)
            if not metrics.get('is_open'):
                exit_reason = metrics.get('exit_reason', 'UNKNOWN')
                exit_emoji = "🎯" if "TP" in exit_reason else (
                    "🛑" if exit_reason == "STOP_LOSS" else "👋")
                text += f"<b>Exit Reason:</b> {exit_emoji} {exit_reason}\n"

            # Time information
            entry_time = metrics.get('entry_time')
            text += f"""
⏱️ <b>Time:</b>
<b>Opened:</b> {entry_time.strftime('%Y-%m-%d %H:%M:%S') if entry_time else 'N/A'}
"""

            if not metrics.get('is_open'):
                exit_time = metrics.get('exit_time')
                if exit_time:
                    text += f"<b>Closed:</b> {exit_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                else:
                    text += f"<b>Closed:</b> N/A\n"

            time_str = metrics.get('time_in_trade_str', 'N/A')
            text += f"<b>Duration:</b> {time_str}\n"

            # Add signal details if available
            if signal and isinstance(signal, dict):
                open_price = signal.get('open_price')
                stop_loss = signal.get('stop_loss')
                tp_list = signal.get('tp_list')

                if open_price or stop_loss or tp_list:
                    text += f"\n🎯 <b>Signal Details:</b>\n"
                    if open_price is not None:
                        text += f"Open Price: {open_price}\n"
                    if stop_loss is not None:
                        text += f"Stop Loss: {stop_loss}\n"
                    if tp_list is not None:
                        text += f"Take Profits: {tp_list}\n"

            # Buttons
            buttons = []

            # If position is open, add action buttons
            if metrics.get('is_open'):
                position_id = metrics.get('position_id')
                if position_id:
                    buttons.append([
                        InlineKeyboardButton(
                            "🔴 Close", callback_data=f"close_{position_id}_full"),
                        InlineKeyboardButton(
                            "⬆️ Update SL/TP", callback_data=f"position_{position_id}")
                    ])

            buttons.append([InlineKeyboardButton(
                "⬅️ Back", callback_data="history_back")])

            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as send_error:
                # Log the problematic text for debugging
                logger.error(f"Failed to send message. Error: {send_error}")
                logger.error(f"Message length: {len(text)} chars")
                logger.error(f"First 500 chars: {text[:500]}")
                logger.error(f"Chars around offset 394: {text[350:450]}")
                raise

        except Exception as e:
            logger.error(f"Error showing history detail: {e}", exc_info=True)
            buttons = [[InlineKeyboardButton(
                "⬅️ Back", callback_data="history_back")]]
            try:
                await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup(buttons))
            except:
                await query.answer(f"❌ Error: {str(e)}", show_alert=True)

    async def show_analyze_menu(self, query, user_id: int) -> None:
        """Show channel analysis main menu"""
        try:
            self._stop_auto_update(user_id)

            text = """📊 <b>Channel Analysis</b>

Analyze trading performance by signal provider channel.

Select analysis period:"""

            buttons = [
                [
                    InlineKeyboardButton("📅 All Time", callback_data="analyze_all"),
                    InlineKeyboardButton("📆 This Week", callback_data="analyze_week"),
                ],
                [
                    InlineKeyboardButton("📅 This Month", callback_data="analyze_month"),
                    InlineKeyboardButton("📅 Last 30 Days", callback_data="analyze_30days"),
                ],
                [
                    InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu"),
                ],
            ]

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as e:
            logger.error(f"Error showing analyze menu: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def show_channel_list(self, query, user_id: int, period: str = "all") -> None:
        """Show list of channels with summary statistics"""
        try:
            self._stop_auto_update(user_id)

            # Initialize analyzer
            analyzer = ChannelAnalyzer(db_manager)

            # Calculate date range based on period
            start_date = None
            end_date = None
            period_label = "All Time"

            if period == "week":
                from datetime import timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                period_label = "This Week"
            elif period == "month":
                from datetime import timedelta
                end_date = datetime.now()
                start_date = end_date.replace(day=1)
                period_label = "This Month"
            elif period == "30days":
                from datetime import timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                period_label = "Last 30 Days"

            # Get channel summaries
            channels = analyzer.get_all_channels_summary(start_date, end_date, min_positions=1)

            if not channels:
                text = f"📊 <b>Channel Analysis - {period_label}</b>\n\n❌ No channels found with trading activity."
                buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="analyze")]]
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
                return

            # Store period in user context for detail view
            if user_id not in self.user_states:
                self.user_states[user_id] = {"state": "analyze", "context": {}}
            self.user_states[user_id]["context"]["analyze_period"] = period
            self.user_states[user_id]["context"]["channels"] = channels

            # Build message with channel list
            text = f"📊 <b>Channel Analysis - {period_label}</b>\n\n"
            text += f"Found <b>{len(channels)}</b> channels:\n\n"

            # Show top channels (up to 10)
            for idx, stats in enumerate(channels[:10], 1):
                profit_emoji = "📈" if stats.net_profit >= 0 else "📉"
                win_rate_emoji = "🟢" if stats.win_rate >= 60 else "🟡" if stats.win_rate >= 40 else "🔴"

                text += f"{idx}. <b>{stats.channel_name}</b>\n"
                text += f"   {profit_emoji} P&L: <b>${stats.net_profit:.2f}</b>\n"
                text += f"   {win_rate_emoji} Win Rate: {stats.win_rate:.1f}%\n"
                text += f"   📊 Positions: {stats.closed_positions}\n\n"

            if len(channels) > 10:
                text += f"<i>...and {len(channels) - 10} more channels</i>\n\n"

            text += "\nSelect a channel for detailed analysis:"

            # Create buttons for channels (2 per row, up to 10 channels)
            buttons = []
            for idx in range(0, min(len(channels), 10), 2):
                row = []
                for i in range(2):
                    if idx + i < min(len(channels), 10):
                        channel_idx = idx + i
                        # Use short name for button (first 15 chars)
                        short_name = channels[channel_idx].channel_name[:15]
                        if len(channels[channel_idx].channel_name) > 15:
                            short_name += "..."
                        row.append(InlineKeyboardButton(
                            f"{channel_idx + 1}. {short_name}",
                            callback_data=f"analyze_detail_{channel_idx}"
                        ))
                buttons.append(row)

            # Navigation buttons
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="analyze")])

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as e:
            logger.error(f"Error showing channel list: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def show_channel_detail(self, query, user_id: int, channel_idx: int) -> None:
        """Show detailed analysis for a specific channel"""
        try:
            self._stop_auto_update(user_id)

            # Get channel from user context
            if user_id not in self.user_states or "context" not in self.user_states[user_id]:
                await query.answer("Session expired. Please start again.", show_alert=True)
                return

            context = self.user_states[user_id]["context"]
            channels = context.get("channels", [])
            period = context.get("analyze_period", "all")

            if channel_idx >= len(channels):
                await query.answer("Channel not found.", show_alert=True)
                return

            stats = channels[channel_idx]

            # Build detailed message
            profit_emoji = "📈" if stats.net_profit >= 0 else "📉"
            win_rate_emoji = "🟢" if stats.win_rate >= 60 else "🟡" if stats.win_rate >= 40 else "🔴"

            period_labels = {
                "all": "All Time",
                "week": "This Week",
                "month": "This Month",
                "30days": "Last 30 Days"
            }
            period_label = period_labels.get(period, "All Time")

            text = f"📊 <b>Channel Analysis - {period_label}</b>\n\n"
            text += f"<b>{stats.channel_name}</b>\n"
            text += f"Provider: {stats.provider}\n\n"

            text += f"📈 <b>Performance Overview</b>\n"
            text += f"{profit_emoji} Net P&L: <b>${stats.net_profit:.2f}</b>\n"
            text += f"💰 Total Profit: ${stats.total_profit:.2f}\n"
            text += f"💸 Total Loss: ${stats.total_loss:.2f}\n"
            if stats.profit_factor > 0:
                text += f"📊 Profit Factor: {stats.profit_factor:.2f}\n"
            if stats.average_roi != 0:
                text += f"📊 Avg ROI: {stats.average_roi:.2f}%\n\n"
            else:
                text += "\n"

            text += f"📊 <b>Position Statistics</b>\n"
            text += f"Total Positions: {stats.total_positions}\n"
            text += f"Open Positions: {stats.open_positions}\n"
            text += f"Closed Positions: {stats.closed_positions}\n\n"

            if stats.closed_positions > 0:
                text += f"{win_rate_emoji} Win Rate: <b>{stats.win_rate:.1f}%</b>\n"
                text += f"✅ Winning Trades: {stats.winning_positions}\n"
                text += f"❌ Losing Trades: {stats.losing_positions}\n\n"

            if stats.largest_win > 0 or stats.largest_loss < 0:
                text += f"💎 <b>Best/Worst Trades</b>\n"
                if stats.largest_win > 0:
                    text += f"📈 Largest Win: ${stats.largest_win:.2f}\n"
                if stats.largest_loss < 0:
                    text += f"📉 Largest Loss: ${stats.largest_loss:.2f}\n"
                if stats.average_win > 0:
                    text += f"📊 Avg Win: ${stats.average_win:.2f}\n"
                if stats.average_loss > 0:
                    text += f"📊 Avg Loss: ${stats.average_loss:.2f}\n"
                text += "\n"

            if stats.max_drawdown > 0:
                text += f"⚠️ <b>Risk Metrics</b>\n"
                text += f"Max Drawdown: ${stats.max_drawdown:.2f}\n"
                if stats.current_drawdown > 0:
                    text += f"Current Drawdown: ${stats.current_drawdown:.2f}\n"
                text += "\n"

            if stats.total_volume > 0:
                text += f"📊 Total Volume: {stats.total_volume:.2f} lots\n\n"

            if stats.first_trade_date and stats.last_trade_date:
                text += f"📅 <b>Activity Period</b>\n"
                text += f"First Trade: {stats.first_trade_date.strftime('%Y-%m-%d')}\n"
                text += f"Last Trade: {stats.last_trade_date.strftime('%Y-%m-%d')}\n"

            # Buttons
            buttons = [
                [InlineKeyboardButton("⬅️ Back to List", callback_data=f"analyze_{period}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
            ]

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as e:
            logger.error(f"Error showing channel detail: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)}")
