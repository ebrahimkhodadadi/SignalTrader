"""
View methods for displaying UI messages and inline buttons
"""

from typing import Optional
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import MetaTrader5 as mt5

from Database.database_manager import db_manager
from .helpers import find_signal_by_ticket, get_position_for_signal


class ViewManager:
    """Manages all UI display methods"""

    def __init__(self, meta_trader, user_states: dict):
        self.meta_trader = meta_trader
        self.user_states = user_states

    async def show_main_menu(self, query) -> None:
        """Show main menu with inline buttons"""
        try:
            text = """👋 **Signal Trader Bot Menu**

Select an option:"""
            buttons = [
                [
                    InlineKeyboardButton("📊 Active Signals", callback_data="signals"),
                    InlineKeyboardButton("📈 Active Positions", callback_data="positions"),
                ],
                [
                    InlineKeyboardButton("🔄 New Trade", callback_data="open_trade"),
                    InlineKeyboardButton("🧪 Signal Tester", callback_data="tester"),
                ],
                [
                    InlineKeyboardButton("💼 Trade Summary", callback_data="trade"),
                ],
            ]
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.error(f"Error showing main menu: {e}")

    async def show_open_trade_form(self, query, user_id: int) -> None:
        """Show form to open a new manual trade"""
        try:
            from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
            
            logger.info(f"User {user_id} requested open trade form")
            
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
                logger.info(f"Trade form sent to user {user_id}")

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

        except Exception as e:
            logger.error(f"Error showing signal list: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]))

    async def show_signal_detail(self, query, user_id: int, signal_id: int) -> None:
        """Show signal details with message link and action buttons"""
        try:
            logger.info(f"Showing signal detail for signal_id={signal_id}")
            STATE_VIEWING_SIGNAL = "viewing_signal"
            self.user_states[user_id] = {"state": STATE_VIEWING_SIGNAL, "context": {"signal_id": signal_id}}

            signal_repo = db_manager.get_signal_repository()
            signal = signal_repo.get_signal_by_id(signal_id)
            logger.info(f"Signal lookup result: {signal is not None}")
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
            
            # Get tickets from positions linked to this signal
            logger.info(f"About to fetch positions for signal_id={signal_id}")
            position_repo = db_manager.get_position_repository()
            db_positions = position_repo.get_positions_by_signal_id(signal_id)
            logger.info(f"Fetched {len(db_positions)} positions for signal_id={signal_id}")
            
            # Separate tickets by entry type (open vs second price) and check if position or order
            open_price_tickets = []
            second_price_tickets = []
            has_positions = False
            has_orders = False
            
            for pos in db_positions:
                ticket = pos.position_id if hasattr(pos, 'position_id') else pos.get("position_id")
                # Get MT5 position details to check entry price
                mt5_pos = self.meta_trader.get_position_by_ticket(ticket)
                mt5_order = None
                if not mt5_pos:
                    mt5_order = self.meta_trader.get_order_by_ticket(ticket)
                
                # Determine if it's a position or order
                if mt5_pos:
                    has_positions = True
                    open_price_mt5 = mt5_pos.open_price if hasattr(mt5_pos, 'open_price') else None
                else:
                    has_orders = True
                    open_price_mt5 = mt5_order.price_open if hasattr(mt5_order, 'price_open') else None
                
                # Compare with signal prices to determine which entry type
                if open_price_mt5 and open_price_mt5 == entry_price:
                    open_price_tickets.append(ticket)
                elif second_price and open_price_mt5 and open_price_mt5 == second_price:
                    second_price_tickets.append(ticket)
                else:
                    # If can't match, add to open price by default
                    open_price_tickets.append(ticket)
            
            open_tickets_text = " / ".join(str(t) for t in open_price_tickets) if open_price_tickets else "None"
            second_tickets_text = " / ".join(str(t) for t in second_price_tickets) if second_price_tickets else "None"
            all_tickets_text = " / ".join(str(t) for t in (open_price_tickets + second_price_tickets)) if (open_price_tickets + second_price_tickets) else "None"
            logger.info(f"Open price tickets: {open_tickets_text}, Second price tickets: {second_tickets_text}")
            
            # Determine emoji based on type
            open_price_emoji = "📈" if has_positions else "⏳"
            second_price_emoji = "📈" if has_positions else "⏳"

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

            logger.info(f"Building buttons for signal_id={signal_id}")
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
            logger.info(f"About to edit message for signal_id={signal_id}")
            logger.info(f"Text length: {len(text)}, buttons count: {len(buttons)}")
            logger.info(f"Message text preview: {text[:100]}...")
            logger.info(f"Buttons: {[[[btn.text for btn in row] for row in buttons]]}")
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            logger.info(f"Successfully showed signal detail for signal_id={signal_id}")

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
        """Show positions/orders for a specific entry price (open or second) - similar to position detail"""
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
            
            # Get the first position for this entry type
            first_ticket = db_positions[0].position_id if hasattr(db_positions[0], 'position_id') else db_positions[0].get("position_id")
            position = self.meta_trader.get_position_by_ticket(first_ticket)
            
            if not position:
                await query.edit_message_text(f"❌ Position not found", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}")]]))
                return
            
            # Display position details
            symbol = position.symbol if hasattr(position, 'symbol') else "N/A"
            open_price = position.open_price if hasattr(position, 'open_price') else "N/A"
            current_price = position.price if hasattr(position, 'price') else "N/A"
            stop_loss = position.stop_loss if hasattr(position, 'stop_loss') else "N/A"
            take_profit = position.take_profit if hasattr(position, 'take_profit') else "N/A"
            lots = position.volume if hasattr(position, 'volume') else 1
            pnl = position.profit if hasattr(position, 'profit') else 0
            pnl_emoji = "📈" if pnl >= 0 else "📉"

            text = f"""📍 **Position**

**Ticket:** #{first_ticket}
**Symbol:** {symbol}
**Open:** {open_price} | **Current:** {current_price}
**SL:** {stop_loss} | **TP:** {take_profit}
**Lots:** {lots}

{pnl_emoji} **P&L:** ${pnl:.2f}"""

            buttons = [
                [
                    InlineKeyboardButton("🔴 Close Full", callback_data=f"close_{first_ticket}_full"),
                    InlineKeyboardButton("🟡 Close Half", callback_data=f"close_{first_ticket}_half"),
                ],
                [
                    InlineKeyboardButton("📉 Close Custom", callback_data=f"close_{first_ticket}_lot"),
                    InlineKeyboardButton("🟢 Risk Free", callback_data=f"close_{first_ticket}_risk_free"),
                ],
                [
                    InlineKeyboardButton("⬆️ Update SL", callback_data=f"update_{first_ticket}_sl"),
                    InlineKeyboardButton("⬆️ Update TP", callback_data=f"update_{first_ticket}_tp"),
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

            text = f"📈 **Positions & Orders**\n\n**Open:** {len(positions)} | **Pending:** {len(orders)}\n\nSelect for actions:"
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            logger.error(f"Error showing position list: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]]))

    async def show_position_detail(self, query, user_id: int, ticket: int) -> None:
        """Show position/order details with action buttons"""
        try:
            STATE_VIEWING_POSITION = "viewing_position"
            self.user_states[user_id] = {"state": STATE_VIEWING_POSITION, "context": {"ticket": ticket}}

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
