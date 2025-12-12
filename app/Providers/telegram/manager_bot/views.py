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


class ViewManager:
    """Manages all UI display methods"""

    def __init__(self, meta_trader, user_states: dict):
        self.meta_trader = meta_trader
        self.user_states = user_states
        self.active_updates = {}  # Track active auto-updates: {user_id: {"state": "signal_list", "message_id": 123, "chat_id": 456}}
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
            self.user_states[user_id] = {"state": STATE_SIGNAL_LIST, "context": {}}

            if not self.meta_trader:
                await query.edit_message_text(
                    "❌ MetaTrader connection not available",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            positions = self.meta_trader.get_open_positions() or []
            orders = self.meta_trader.get_pending_orders() or []

            if not positions and not orders:
                await query.edit_message_text(
                    "📭 No active positions or orders",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            # Group positions/orders by signal
            signals_dict = {}
            
            for pos in positions:
                ticket = pos.ticket if hasattr(pos, 'ticket') else pos.get("ticket")
                signal = find_signal_by_ticket(ticket)
                if signal:
                    signal_id = signal.id if hasattr(signal, 'id') else signal.get("id")
                    if signal_id not in signals_dict:
                        signals_dict[signal_id] = {"signal": signal, "positions": [], "orders": []}
                    signals_dict[signal_id]["positions"].append({"ticket": ticket, "data": pos})

            for order in orders:
                ticket = order.ticket if hasattr(order, 'ticket') else order.get("ticket")
                signal = find_signal_by_ticket(ticket)
                if signal:
                    signal_id = signal.id if hasattr(signal, 'id') else signal.get("id")
                    if signal_id not in signals_dict:
                        signals_dict[signal_id] = {"signal": signal, "positions": [], "orders": []}
                    signals_dict[signal_id]["orders"].append({"ticket": ticket, "data": order})

            if not signals_dict:
                await query.edit_message_text(
                    "📭 No active positions or orders linked to signals",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            # Build text and buttons grouped by signal
            text_parts = ["📊 **Active Signals - Grouped by Signal**\n"]
            buttons = []

            for signal_id, signal_data in signals_dict.items():
                signal = signal_data["signal"]
                open_price = signal.open_price if hasattr(signal, 'open_price') else signal.get("open_price", "N/A")
                signal_type = signal.signal_type if hasattr(signal, 'signal_type') else signal.get("signal_type", "N/A")
                num_positions = len(signal_data["positions"])
                num_orders = len(signal_data["orders"])
                
                # Get channel and message info
                channel_title = signal.telegram_channel_title if hasattr(signal, 'telegram_channel_title') else signal.get("telegram_channel_title", "Unknown")
                chat_id = signal.telegram_message_chatid if hasattr(signal, 'telegram_message_chatid') else signal.get("telegram_message_chatid")
                message_id = signal.telegram_message_id if hasattr(signal, 'telegram_message_id') else signal.get("telegram_message_id")
                
                # Build message link
                message_link = "N/A"
                if chat_id and message_id:
                    message_link = f"https://t.me/c/{abs(chat_id)}/{message_id}"
                
                # Get ticket IDs from positions and orders
                position_tickets = [pos["ticket"] for pos in signal_data["positions"]]
                order_tickets = [order["ticket"] for order in signal_data["orders"]]
                all_tickets = position_tickets + order_tickets
                tickets_text = " / ".join(str(t) for t in all_tickets) if all_tickets else "None"
                
                # Add signal type emoji
                type_emoji = "🟢" if signal_type == "BUY" else "🔴"
                
                text_parts.append(f"\n**#{signal_id}:**")
                text_parts.append(f"**Channel:** {channel_title}")
                text_parts.append(f"**Message:** [{message_link}]({message_link})")
                text_parts.append(f"{type_emoji} **{signal_type} | Tickets: {tickets_text}**")
                text_parts.append(f"  📈 Positions: {num_positions} | ⏳ Orders: {num_orders}")
                
                button_text = f"{type_emoji} #{signal_id} - {channel_title}"
                buttons.append([InlineKeyboardButton(button_text, callback_data=f"signal_{signal_id}")])

            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])

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
            asyncio.create_task(self._auto_update_signal_list(user_id, query.get_bot()))

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
                    buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]
                else:
                    # Group positions/orders by signal
                    signals_dict = {}
                    
                    for pos in positions:
                        ticket = pos.ticket if hasattr(pos, 'ticket') else pos.get("ticket")
                        signal = find_signal_by_ticket(ticket)
                        if signal:
                            signal_id = signal.id if hasattr(signal, 'id') else signal.get("id")
                            if signal_id not in signals_dict:
                                signals_dict[signal_id] = {"signal": signal, "positions": [], "orders": []}
                            signals_dict[signal_id]["positions"].append({"ticket": ticket, "data": pos})

                    for order in orders:
                        ticket = order.ticket if hasattr(order, 'ticket') else order.get("ticket")
                        signal = find_signal_by_ticket(ticket)
                        if signal:
                            signal_id = signal.id if hasattr(signal, 'id') else signal.get("id")
                            if signal_id not in signals_dict:
                                signals_dict[signal_id] = {"signal": signal, "positions": [], "orders": []}
                            signals_dict[signal_id]["orders"].append({"ticket": ticket, "data": order})

                    if not signals_dict:
                        text = "📭 No active positions or orders linked to signals"
                        buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]
                    else:
                        # Build updated text and buttons
                        text_parts = ["📊 **Active Signals - Grouped by Signal** 🔄 (Auto-updating)\n"]
                        buttons = []

                        for signal_id, signal_data in signals_dict.items():
                            signal = signal_data["signal"]
                            signal_type = signal.signal_type if hasattr(signal, 'signal_type') else signal.get("signal_type", "N/A")
                            num_positions = len(signal_data["positions"])
                            num_orders = len(signal_data["orders"])
                            
                            # Get channel and message info
                            channel_title = signal.telegram_channel_title if hasattr(signal, 'telegram_channel_title') else signal.get("telegram_channel_title", "Unknown")
                            chat_id = signal.telegram_message_chatid if hasattr(signal, 'telegram_message_chatid') else signal.get("telegram_message_chatid")
                            message_id = signal.telegram_message_id if hasattr(signal, 'telegram_message_id') else signal.get("telegram_message_id")
                            
                            # Build message link
                            message_link = "N/A"
                            if chat_id and message_id:
                                message_link = f"https://t.me/c/{abs(chat_id)}/{message_id}"
                            
                            # Get ticket IDs
                            position_tickets = [pos["ticket"] for pos in signal_data["positions"]]
                            order_tickets = [order["ticket"] for order in signal_data["orders"]]
                            all_tickets = position_tickets + order_tickets
                            tickets_text = " / ".join(str(t) for t in all_tickets) if all_tickets else "None"
                            
                            # Add signal type emoji
                            type_emoji = "🟢" if signal_type == "BUY" else "🔴"
                            
                            text_parts.append(f"\n**#{signal_id}:**")
                            text_parts.append(f"**Channel:** {channel_title}")
                            text_parts.append(f"**Message:** [{message_link}]({message_link})")
                            text_parts.append(f"{type_emoji} **{signal_type} | Tickets: {tickets_text}**")
                            text_parts.append(f"  📈 Positions: {num_positions} | ⏳ Orders: {num_orders}")
                            
                            button_text = f"{type_emoji} #{signal_id} - {channel_title}"
                            buttons.append([InlineKeyboardButton(button_text, callback_data=f"signal_{signal_id}")])

                        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
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
                        logger.debug(f"Could not update signal list for user {user_id}: {e}")
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
            self.user_states[user_id] = {"state": STATE_VIEWING_SIGNAL, "context": {"signal_id": signal_id}}
            
            # Stop auto-update for this user
            self._stop_auto_update(user_id)

            signal_repo = db_manager.get_signal_repository()
            signal = signal_repo.get_signal_by_id(signal_id)
            if not signal:
                await query.edit_message_text("❌ Signal not found", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="signals")]]))
                return

            position = get_position_for_signal(self.meta_trader, signal_id)

            entry_price = signal.open_price if hasattr(signal, 'open_price') else signal.get("open_price", "N/A")
            second_price = signal.second_price if hasattr(signal, 'second_price') else signal.get("second_price")
            stop_loss = signal.stop_loss if hasattr(signal, 'stop_loss') else signal.get("stop_loss", "N/A")
            tp_list = signal.tp_list if hasattr(signal, 'tp_list') else signal.get("tp_list", "N/A")
            signal_type = signal.signal_type if hasattr(signal, 'signal_type') else signal.get("signal_type", "N/A")
            channel = signal.telegram_channel_title if hasattr(signal, 'telegram_channel_title') else signal.get("telegram_channel_title", "Unknown")
            message_id = signal.telegram_message_id if hasattr(signal, 'telegram_message_id') else signal.get("telegram_message_id")
            chat_id = signal.telegram_message_chatid if hasattr(signal, 'telegram_message_chatid') else signal.get("telegram_message_chatid")
            
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
            db_positions_sorted = sorted(db_positions, key=lambda x: (x.position_id if hasattr(x, 'position_id') else x.get("position_id")), reverse=True)
            
            open_price_tickets = []
            second_price_tickets = []
            has_positions = False
            has_orders = False
            
            # First position (most recent) = open price, second position = second price
            for idx, db_pos in enumerate(db_positions_sorted[:2]):
                ticket = db_pos.position_id if hasattr(db_pos, 'position_id') else db_pos.get("position_id")
                
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
            
            all_tickets_text = " / ".join(str(t) for t in (open_price_tickets + second_price_tickets)) if (open_price_tickets + second_price_tickets) else "None"
            
            # Determine emoji based on type and if position still exists in MT5
            if open_price_tickets:
                # Check if open price position still exists
                open_ticket = int(open_price_tickets[0])
                mt5_open = self.meta_trader.get_position_by_ticket(open_ticket)
                if not mt5_open:
                    mt5_open = self.meta_trader.get_order_by_ticket(open_ticket)
                open_price_emoji = ("📈" if self.meta_trader.get_position_by_ticket(open_ticket) else "⏳") if mt5_open else "❌"
            else:
                open_price_emoji = "❌"
            
            if second_price_tickets:
                # Check if second price position still exists
                second_ticket = int(second_price_tickets[0])
                mt5_second = self.meta_trader.get_position_by_ticket(second_ticket)
                if not mt5_second:
                    mt5_second = self.meta_trader.get_order_by_ticket(second_ticket)
                second_price_emoji = ("📈" if self.meta_trader.get_position_by_ticket(second_ticket) else "⏳") if mt5_second else "❌"
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
                    InlineKeyboardButton("🔴 Close All", callback_data=f"close_{signal_id}_full"),
                    InlineKeyboardButton("🟢 Risk Free", callback_data=f"close_{signal_id}_risk_free"),
                ],
                [
                    InlineKeyboardButton("⬆️ Update SL", callback_data=f"update_{signal_id}_sl"),
                    InlineKeyboardButton("⬆️ Update TP", callback_data=f"update_{signal_id}_tp"),
                ],
                [
                    InlineKeyboardButton(f"{open_price_emoji} Open Price ({entry_price})", callback_data=f"manage_{signal_id}_open"),
                ],
            ]
            # Add second price button if available
            if second_price:
                buttons.append([
                    InlineKeyboardButton(f"{second_price_emoji} Second Price ({second_price})", callback_data=f"manage_{signal_id}_second"),
                ])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="signals")])
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
                logger.error(f"Error showing signal detail for signal_id={signal_id}: {e}", exc_info=True)
                try:
                    await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="signals")]]))
                except:
                    await query.answer(f"❌ Error: {str(e)}", show_alert=True)

    async def show_manage_signal_entries(self, query, user_id: int, signal_id: int, entry_type: str) -> None:
        """Show positions/orders for a specific entry price (open or second)"""
        try:
            self.user_states[user_id] = {"state": "manage_entries", "context": {"signal_id": signal_id, "entry_type": entry_type}}
            
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
            db_positions_sorted = sorted(db_positions, key=lambda x: (x.position_id if hasattr(x, 'position_id') else x.get("position_id")), reverse=True)
            
            # Get ticket based on entry_type: first (open) or second
            ticket = None
            if entry_type == "open" and len(db_positions_sorted) > 0:
                ticket = db_positions_sorted[0].position_id if hasattr(db_positions_sorted[0], 'position_id') else db_positions_sorted[0].get("position_id")
            elif entry_type == "second" and len(db_positions_sorted) > 1:
                ticket = db_positions_sorted[1].position_id if hasattr(db_positions_sorted[1], 'position_id') else db_positions_sorted[1].get("position_id")
            else:
                await query.edit_message_text(
                    f"❌ No {entry_type} price position found",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}")]])
                )
                return
            
            # Try to get it from MT5 (could be position or order)
            position = self.meta_trader.get_position_by_ticket(ticket)
            if not position:
                position = self.meta_trader.get_order_by_ticket(ticket)
            
            if not position:
                await query.edit_message_text(
                    f"❌ Position/Order #{ticket} not found in MT5 (may have been closed)",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}")]])
                )
                return
            
            # Display position details
            symbol = position.symbol if hasattr(position, 'symbol') else "N/A"
            
            # Get prices (different fields for positions vs orders)
            if hasattr(position, 'open_price'):
                open_price = position.open_price
                current_price = position.price if hasattr(position, 'price') else "N/A"
            else:
                # It's an order
                open_price = position.price_open if hasattr(position, 'price_open') else "N/A"
                current_price = position.price_open if hasattr(position, 'price_open') else "N/A"
            
            stop_loss = position.stop_loss if hasattr(position, 'stop_loss') else "N/A"
            take_profit = position.take_profit if hasattr(position, 'take_profit') else "N/A"
            lots = position.volume if hasattr(position, 'volume') else (position.volume_current if hasattr(position, 'volume_current') else 1)
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
                    InlineKeyboardButton("🔴 Close Full", callback_data=f"close_{ticket}_full"),
                    InlineKeyboardButton("🟡 Close Half", callback_data=f"close_{ticket}_half"),
                ],
                [
                    InlineKeyboardButton("📉 Close Custom", callback_data=f"close_{ticket}_lot"),
                    InlineKeyboardButton("🟢 Risk Free", callback_data=f"close_{ticket}_risk_free"),
                ],
                [
                    InlineKeyboardButton("⬆️ Update SL", callback_data=f"update_{ticket}_sl"),
                    InlineKeyboardButton("⬆️ Update TP", callback_data=f"update_{ticket}_tp"),
                ],
            ]
            
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}")])
            
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            
        except Exception as e:
            logger.error(f"Error showing manage signal entries: {e}", exc_info=True)
            try:
                await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="signals")]]))
            except:
                await query.answer(f"❌ Error: {str(e)}", show_alert=True)

    async def show_position_list(self, query, user_id: int) -> None:
        """Show all MT5 positions and pending orders as inline buttons"""
        try:
            STATE_POSITION_LIST = "position_list"
            self.user_states[user_id] = {"state": STATE_POSITION_LIST, "context": {}}

            if not self.meta_trader:
                await query.edit_message_text("❌ MetaTrader connection not available")
                return

            positions = self.meta_trader.get_open_positions() or []
            orders = self.meta_trader.get_pending_orders() or []

            if not positions and not orders:
                await query.edit_message_text(
                    "📭 No open positions or pending orders",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
                )
                return

            buttons = []

            for pos in positions:
                symbol = pos.symbol if hasattr(pos, 'symbol') else pos.get("symbol", "UNKNOWN")
                ticket = pos.ticket if hasattr(pos, 'ticket') else pos.get("ticket")
                button_text = f"📈 {ticket}"
                buttons.append([InlineKeyboardButton(button_text, callback_data=f"position_{ticket}")])

            for order in orders:
                symbol = order.symbol if hasattr(order, 'symbol') else order.get("symbol", "UNKNOWN")
                ticket = order.ticket if hasattr(order, 'ticket') else order.get("ticket")
                button_text = f"⏳ {ticket}"
                buttons.append([InlineKeyboardButton(button_text, callback_data=f"position_{ticket}")])

            text = f"📈 **Positions & Orders** 🔄 (Auto-updating)\n\n**Open:** {len(positions)} | **Pending:** {len(orders)}\n\nSelect for actions:"
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
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
            asyncio.create_task(self._auto_update_position_list(user_id, query.get_bot()))

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
                    buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]
                else:
                    buttons = []

                    for pos in positions:
                        symbol = pos.symbol if hasattr(pos, 'symbol') else pos.get("symbol", "UNKNOWN")
                        ticket = pos.ticket if hasattr(pos, 'ticket') else pos.get("ticket")
                        button_text = f"📈 {ticket}"
                        buttons.append([InlineKeyboardButton(button_text, callback_data=f"position_{ticket}")])

                    for order in orders:
                        symbol = order.symbol if hasattr(order, 'symbol') else order.get("symbol", "UNKNOWN")
                        ticket = order.ticket if hasattr(order, 'ticket') else order.get("ticket")
                        button_text = f"⏳ {ticket}"
                        buttons.append([InlineKeyboardButton(button_text, callback_data=f"position_{ticket}")])

                    text = f"📈 **Positions & Orders** 🔄 (Auto-updating)\n\n**Open:** {len(positions)} | **Pending:** {len(orders)}\n\nSelect for actions:"
                    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])

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
                        logger.debug(f"Could not update position list for user {user_id}: {e}")
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
            self.user_states[user_id] = {"state": STATE_VIEWING_POSITION, "context": {"ticket": ticket}}
            
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
                symbol = position.symbol if hasattr(position, 'symbol') else "N/A"
                open_price = position.open_price if hasattr(position, 'open_price') else "N/A"
                current_price = position.price if hasattr(position, 'price') else "N/A"
                stop_loss = position.stop_loss if hasattr(position, 'stop_loss') else "N/A"
                take_profit = position.take_profit if hasattr(position, 'take_profit') else "N/A"
                lots = position.volume if hasattr(position, 'volume') else 1
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
                        InlineKeyboardButton("🔴 Close Full", callback_data=f"close_{ticket}_full"),
                        InlineKeyboardButton("🟡 Close Half", callback_data=f"close_{ticket}_half"),
                    ],
                    [
                        InlineKeyboardButton("📉 Close Custom", callback_data=f"close_{ticket}_lot"),
                        InlineKeyboardButton("🟢 Risk Free", callback_data=f"close_{ticket}_risk_free"),
                    ],
                    [
                        InlineKeyboardButton("⬆️ Update SL", callback_data=f"update_{ticket}_sl"),
                        InlineKeyboardButton("⬆️ Update TP", callback_data=f"update_{ticket}_tp"),
                    ],
                ]
            else:
                symbol = order.symbol if hasattr(order, 'symbol') else "N/A"
                order_type = order.type if hasattr(order, 'type') else "N/A"
                open_price = order.price_open if hasattr(order, 'price_open') else "N/A"
                stop_loss = order.stop_loss if hasattr(order, 'stop_loss') else "N/A"
                take_profit = order.take_profit if hasattr(order, 'take_profit') else "N/A"
                lots = order.volume_current if hasattr(order, 'volume_current') else 1

                text = f"""⏳ **Pending Order**

**Ticket:** #{ticket}
**Symbol:** {symbol}
**Type:** {order_type}
**Open Price:** {open_price}
**SL:** {stop_loss} | **TP:** {take_profit}
**Lots:** {lots}"""

                buttons = [
                    [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{ticket}")],
                ]

            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="positions")])
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
            self.user_states[user_id] = {"state": STATE_MAIN_MENU, "context": {}}

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
            
            margin_usage = ((account_info.margin / (account_info.margin + account_info.margin_free)) * 100) if (account_info.margin + account_info.margin_free) > 0 else 0
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
                    InlineKeyboardButton("📊 Active Signals", callback_data="signals"),
                    InlineKeyboardButton("📈 Active Positions", callback_data="positions"),
                ],
                [
                    InlineKeyboardButton("🔄 New Trade", callback_data="open_trade"),
                    InlineKeyboardButton("🧪 Signal Tester", callback_data="tester"),
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
                
                margin_usage = ((account_info.margin / (account_info.margin + account_info.margin_free)) * 100) if (account_info.margin + account_info.margin_free) > 0 else 0
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
                        InlineKeyboardButton("📊 Active Signals", callback_data="signals"),
                        InlineKeyboardButton("📈 Active Positions", callback_data="positions"),
                    ],
                    [
                        InlineKeyboardButton("🔄 New Trade", callback_data="open_trade"),
                        InlineKeyboardButton("🧪 Signal Tester", callback_data="tester"),
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
                        logger.debug(f"Could not update account details for user {user_id}: {e}")
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
            self.user_states[user_id] = {"state": STATE_MAIN_MENU, "context": {}}
            
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
            
            margin_usage = ((account_info.margin / (account_info.margin + account_info.margin_free)) * 100) if (account_info.margin + account_info.margin_free) > 0 else 0
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
                    InlineKeyboardButton("📊 Active Signals", callback_data="signals"),
                    InlineKeyboardButton("📈 Active Positions", callback_data="positions"),
                ],
                [
                    InlineKeyboardButton("🔄 New Trade", callback_data="open_trade"),
                    InlineKeyboardButton("🧪 Signal Tester", callback_data="tester"),
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
            self.user_states[user_id] = {"state": STATE_MAIN_MENU, "context": {}}

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
