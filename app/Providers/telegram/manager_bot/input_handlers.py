"""
Keyboard input handlers for lot, SL, TP, and signal tester inputs
"""

from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


class InputHandler:
    """Manages keyboard input processing"""

    def __init__(self, user_states: dict, meta_trader=None):
        self.user_states = user_states
        self.meta_trader = meta_trader

    # State constants
    STATE_POSITION_LIST = "position_list"

    async def handle_lot_input(self, update: Update, user_id: int, lot_text: str) -> None:
        """Handle lot input from keyboard - close custom lot size"""
        try:
            identifier = self.user_states[user_id].get("context", {}).get("identifier")

            if lot_text == "Custom":
                await update.message.reply_text("📝 Enter custom lot size (e.g., 0.5):")
                return

            try:
                lots = float(lot_text)
                if self.meta_trader and identifier:
                    result = self.meta_trader.close_position(identifier, volume=lots)
                    if result:
                        await update.message.reply_text(
                            f"✅ Successfully closed {lots} lots",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Failed to close {lots} lots",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                        )
                else:
                    await update.message.reply_text(
                        "❌ MetaTrader not available",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                    )
                self.user_states[user_id]["state"] = self.STATE_POSITION_LIST
            except ValueError:
                await update.message.reply_text("❌ Invalid lot value. Enter a number like 0.5 or 1.0")
        except Exception as e:
            logger.error(f"Error in lot input: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_sl_input(self, update: Update, user_id: int, sl_text: str) -> None:
        """Handle SL input from keyboard - update stop loss"""
        try:
            identifier = self.user_states[user_id].get("context", {}).get("identifier")
            signal_id = self.user_states[user_id].get("context", {}).get("signal_id")

            try:
                sl_value = float(sl_text)
                if self.meta_trader and identifier:
                    result = self.meta_trader.update_position_sl(identifier, sl_value)
                    # Handle both tuple and boolean returns for compatibility
                    if isinstance(result, tuple):
                        success, error_msg = result
                    else:
                        success = result
                        error_msg = None
                    
                    if success:
                        await update.message.reply_text(
                            f"✅ Stop Loss updated to {sl_value}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}" if signal_id else "positions")]])
                        )
                    else:
                        error_display = error_msg if error_msg else "Failed to update stop loss"
                        logger.error(f"Failed to update stop loss for ticket {identifier}: {error_display}")
                        await update.message.reply_text(
                            f"❌ Failed to update SL to {sl_value}\n\n💡 {error_display}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}" if signal_id else "positions")]])
                        )
                else:
                    await update.message.reply_text(
                        "❌ MetaTrader not available",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}" if signal_id else "positions")]])
                    )
                self.user_states[user_id]["state"] = "viewing_signal" if signal_id else self.STATE_POSITION_LIST
            except ValueError:
                await update.message.reply_text("❌ Invalid SL value. Enter a number like 1.2450")
        except Exception as e:
            logger.error(f"Error in SL input: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_tp_input(self, update: Update, user_id: int, tp_text: str) -> None:
        """Handle TP input from keyboard - update take profit"""
        try:
            identifier = self.user_states[user_id].get("context", {}).get("identifier")
            signal_id = self.user_states[user_id].get("context", {}).get("signal_id")

            try:
                tp_value = float(tp_text)
                if self.meta_trader and identifier:
                    result = self.meta_trader.update_position_tp(identifier, tp_value)
                    # Handle both tuple and boolean returns for compatibility
                    if isinstance(result, tuple):
                        success, error_msg = result
                    else:
                        success = result
                        error_msg = None
                    
                    if success:
                        await update.message.reply_text(
                            f"✅ Take Profit updated to {tp_value}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}" if signal_id else "positions")]])
                        )
                    else:
                        error_display = error_msg if error_msg else "Failed to update take profit"
                        logger.error(f"Failed to update take profit for ticket {identifier}: {error_display}")
                        await update.message.reply_text(
                            f"❌ Failed to update TP to {tp_value}\n\n💡 {error_display}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}" if signal_id else "positions")]])
                        )
                else:
                    await update.message.reply_text(
                        "❌ MetaTrader not available",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{signal_id}" if signal_id else "positions")]])
                    )
                self.user_states[user_id]["state"] = "viewing_signal" if signal_id else self.STATE_POSITION_LIST
            except ValueError:
                await update.message.reply_text("❌ Invalid TP value. Enter a number like 1.2550")
        except Exception as e:
            logger.error(f"Error in TP input: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_tester_input(self, update: Update, user_id: int, signal_text: str) -> None:
        """Parse signal and export: open_price, second_price, SL, TP"""
        try:
            from Analayzer.parsers.signal_parser import SignalParser
            result = SignalParser.parse_message(signal_text)

            if result and result[0] is not None:
                action_type, symbol, first_price, second_price, take_profits, stop_loss = result
                tp_text = ", ".join(str(tp) for tp in take_profits) if take_profits else "None"

                text = f"""✅ **Signal Parsed**

**Symbol:** {symbol or 'N/A'}
**Action:** {action_type or 'N/A'}
**Open Price:** {first_price or 'N/A'}
**Second Price:** {second_price or 'None'}
**Stop Loss:** {stop_loss or 'N/A'}
**Take Profit List:** {tp_text}"""
            else:
                text = "❌ Could not parse. Example:\n`EUR/USD BUY 1.2500 SL: 1.2450 TP: 1.2550, 1.2600`"

            keyboard = [["⬅️ Back to Menu"]]
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        except Exception as e:
            logger.error(f"Error in tester input: {e}")
            keyboard = [["⬅️ Back to Menu"]]
            await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    async def handle_trade_input(self, update: Update, user_id: int, trade_text: str) -> None:
        """Handle manual trade input - parse and execute trade"""
        try:
            from Analayzer.Analayzer import parse_message
            from MetaTrader import Trade
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            logger.info(f"Trade input received from user {user_id}: {trade_text}")
            
            # Parse the trade text
            result = parse_message(trade_text)
            
            if not result or result[0] is None:
                logger.warning(f"Failed to parse trade input from user {user_id}")
                await update.message.reply_text(
                    "❌ Invalid format. Please use:\n"
                    "`SYMBOL ACTION PRICE1 PRICE2 TP1,TP2,... SL COMMENT`\n\n"
                    "Example: `EURUSD BUY 1.0850 1.0855 1.0870,1.0885 1.0830 Manual trade`",
                    parse_mode="Markdown"
                )
                return
            
            action_type, symbol, first_price, second_price, take_profits, stop_loss = result
            logger.info(f"Trade parsed: {symbol} {action_type} @{first_price}")
            
            # Show loading message
            loading_msg = await update.message.reply_text("⏳ Opening trade...\n\n🔄 Please wait...")
            
            try:
                # Get chat and message info
                chat_id = update.effective_chat.id
                username = update.effective_user.username or "unknown"
                message_id = loading_msg.message_id
                comment = trade_text.split()[-1] if len(trade_text.split()) > 6 else "Manual trade"
                
                logger.info(f"Executing trade for user {username}: {symbol} {action_type}")
                
                # Execute trade using the Trade function
                Trade(
                    message_username=username,
                    message_id=message_id,
                    message_chatid=chat_id,
                    actionType=action_type,
                    symbol=symbol,
                    openPrice=first_price,
                    secondPrice=second_price,
                    tp_list=take_profits,
                    sl=stop_loss,
                    comment=comment,
                    provider="telegram"
                )
                
                # Get the signal that was just created to show its details
                from Database.database_manager import db_manager
                signal_repo = db_manager.get_signal_repository()
                
                # Try to find the most recent signal for this symbol
                import time
                time.sleep(0.5)  # Wait a moment for signal to be saved
                
                # Query signals for this symbol
                signals = signal_repo.get_all_signals_paginated(limit=100, offset=0)
                matching_signal = None
                for sig in signals:
                    sig_symbol = sig.symbol if hasattr(sig, 'symbol') else sig.get('symbol')
                    if sig_symbol and sig_symbol.upper() == symbol.upper():
                        matching_signal = sig
                        break
                
                if matching_signal:
                    signal_id = matching_signal.id if hasattr(matching_signal, 'id') else matching_signal.get('id')
                    logger.info(f"Found matching signal {signal_id}")
                    # Update loading message with success and show signal details
                    await loading_msg.edit_text(
                        f"✅ Trade opened successfully!\n\n"
                        f"📊 Signal ID: {signal_id}\n"
                        f"🔄 Loading position details..."
                    )
                    
                    # Show signal details
                    from .views import ViewManager
                    view_manager = ViewManager(self.meta_trader, self.user_states)
                    
                    # Create a fake query object to use edit_message_text
                    class FakeQuery:
                        def __init__(self, message):
                            self.message = message
                        
                        async def edit_message_text(self, *args, **kwargs):
                            await self.message.edit_text(*args, **kwargs)
                        
                        async def answer(self, *args, **kwargs):
                            pass
                    
                    fake_query = FakeQuery(loading_msg)
                    await view_manager.show_signal_detail(fake_query, user_id, signal_id)
                else:
                    await loading_msg.edit_text(
                        "✅ Trade executed successfully!\n\n"
                        "📊 Position details will appear shortly.",
                        parse_mode="Markdown"
                    )
                
                self.user_states[user_id]["state"] = None
                
            except Exception as e:
                logger.error(f"Error executing trade: {e}", exc_info=True)
                await loading_msg.edit_text(
                    f"❌ Failed to execute trade:\n\n{str(e)}",
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Error in trade input: {e}", exc_info=True)
            keyboard = [["⬅️ Back to Menu"]]
            await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
