"""
Trade action handlers for close, update SL/TP, delete order
"""

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class ActionManager:
    """Manages trade operations and action callbacks"""

    def __init__(self, meta_trader, user_states: dict, db_manager=None):
        self.meta_trader = meta_trader
        self.user_states = user_states
        self.db_manager = db_manager

    # State constants
    STATE_AWAITING_LOT = "awaiting_lot"
    STATE_AWAITING_SL = "awaiting_sl"
    STATE_AWAITING_TP = "awaiting_tp"

    async def handle_close_action(self, query, user_id: int, identifier: int, close_type: str) -> None:
        """Handle close actions - close positions, half positions, or set risk-free"""
        try:
            logger.info(f"Handle close action: identifier={identifier}, close_type={close_type}")
            if close_type == "full":
                # Close full position(s)
                await query.answer("Closing position(s)...", show_alert=False)
                if self.meta_trader:
                    # Check if identifier is a signal_id or ticket
                    # Try to get positions from signal first
                    from Database import Migrations
                    db_manager = Migrations.db_manager
                    position_repo = db_manager.get_position_repository()
                    
                    # Get all positions linked to this signal
                    signal_positions = position_repo.get_positions_by_signal_id(identifier)
                    
                    if signal_positions:
                        # It's a signal_id, close all linked positions
                        total = len(signal_positions)
                        closed_count = 0
                        failed_count = 0
                        
                        # Show initial loading message
                        await query.edit_message_text(f"⏳ Closing {total} position(s)...\n\n🔄 Please wait...")
                        
                        for idx, pos in enumerate(signal_positions, 1):
                            pos_ticket = pos.position_id if hasattr(pos, 'position_id') else pos.get("position_id")
                            
                            # Update progress message
                            await query.edit_message_text(
                                f"⏳ Processing {idx}/{total}\n"
                                f"🎟️ Ticket: {pos_ticket}\n\n"
                                f"✅ Closed: {closed_count}\n"
                                f"❌ Failed: {failed_count}"
                            )
                            
                            if self.meta_trader.close_position(pos_ticket):
                                closed_count += 1
                            else:
                                failed_count += 1
                                logger.error(f"Failed to close position {pos_ticket} for signal {identifier}")
                        
                        # Show final results
                        if failed_count == 0:
                            await query.edit_message_text(
                                f"✅ Success!\n\n📊 Results:\n"
                                f"✅ Closed: {closed_count}/{total}",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                            )
                        else:
                            await query.edit_message_text(
                                f"⚠️ Completed with errors\n\n📊 Results:\n"
                                f"✅ Closed: {closed_count}/{total}\n"
                                f"❌ Failed: {failed_count}/{total}\n\n"
                                f"💡 Check logs for details",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                            )
                    else:
                        # Try as a direct position ticket
                        await query.edit_message_text("⏳ Closing position...\n\n🔄 Please wait...")
                        result = self.meta_trader.close_position(identifier)
                        if result:
                            await query.edit_message_text(
                                "✅ Position closed successfully",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                            )
                        else:
                            logger.error(f"Failed to close position {identifier}")
                            await query.edit_message_text(
                                "❌ Failed to close position",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                            )
                else:
                    await query.edit_message_text(
                        "❌ MetaTrader not available",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                    )
            elif close_type == "half":
                # Close half position
                await query.answer("Closing half position...", show_alert=False)
                if self.meta_trader:
                    await query.edit_message_text(f"⏳ Closing half position...\n\n🔄 Please wait...")
                    result = self.meta_trader.close_half_position(identifier)
                    if result:
                        await query.edit_message_text(
                            "✅ Half position closed successfully",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                        )
                    else:
                        logger.error(f"Failed to close half position {identifier}")
                        await query.edit_message_text(
                            "❌ Failed to close half position",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                        )
                else:
                    await query.edit_message_text(
                        "❌ MetaTrader not available",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                    )
            elif close_type == "risk_free":
                # Save profit (set risk-free by closing some lots)
                await query.answer("Setting risk-free...", show_alert=False)
                if self.meta_trader:
                    await query.edit_message_text("⏳ Setting risk-free...\n\n🔄 Please wait...")
                    try:
                        result = self.meta_trader.save_profit_position(identifier, 0)
                        if result:
                            await query.edit_message_text(
                                "✅ Position set to risk-free (first TP level)",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                            )
                            logger.info(f"Successfully set risk-free for position {identifier}")
                        else:
                            error_msg = "Failed to set risk-free - check logs for details (may be: invalid profit percentage, position not found, or minimal lot size)"
                            logger.error(f"Failed to set risk-free for position {identifier}: {error_msg}")
                            await query.edit_message_text(
                                f"❌ {error_msg}",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                            )
                    except Exception as e:
                        logger.error(f"Exception setting risk-free for position {identifier}: {str(e)}")
                        await query.edit_message_text(
                            f"❌ Error setting risk-free:\n{str(e)}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                        )
                else:
                    await query.edit_message_text(
                        "❌ MetaTrader not available",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                    )
            elif close_type == "lot":
                # Get position or order lot size and create dynamic buttons
                if not self.meta_trader:
                    await query.answer("❌ MetaTrader not available", show_alert=True)
                    return

                # Get position or order by ticket
                position_or_order = self.meta_trader.get_position_or_order(identifier)
                if not position_or_order:
                    await query.answer("❌ Position/Order not found", show_alert=True)
                    return

                current_lot = position_or_order.volume
                
                # If lot is exactly 0.01, just show close button
                if current_lot <= 0.01:
                    await query.edit_message_text(
                        f"📊 Current lot: {current_lot}\n\n⚠️ Lot size is at minimum (0.01). Close the entire position?",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close Position", callback_data=f"close_full_{identifier}")]])
                    )
                    return

                # Generate lot buttons from current_lot - 0.01 down to 0.01
                lot_buttons = []
                current = round(current_lot - 0.01, 2)
                
                # Create rows of 4 buttons each
                row = []
                while current >= 0.01:
                    row.append(InlineKeyboardButton(str(current), callback_data=f"close_lot_{identifier}_{current}"))
                    if len(row) == 4:
                        lot_buttons.append(row)
                        row = []
                    current = round(current - 0.01, 2)
                
                # Add remaining buttons
                if row:
                    lot_buttons.append(row)
                
                # Add back button
                lot_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="positions")])

                self.user_states[user_id]["state"] = self.STATE_AWAITING_LOT
                self.user_states[user_id]["context"]["identifier"] = identifier
                
                await query.edit_message_text(
                    f"📊 Current lot size: {current_lot}\n\n📝 Select lot size to close (0.01 to {round(current_lot - 0.01, 2)}):",
                    reply_markup=InlineKeyboardMarkup(lot_buttons)
                )

        except Exception as e:
            logger.error(f"Error in close action: {e}", exc_info=True)
            await query.answer(f"Error: {str(e)}", show_alert=True)

    async def handle_update_action(self, query, user_id: int, identifier: int, update_type: str) -> None:
        """Handle update SL/TP - show current values and options"""
        try:
            if not self.meta_trader:
                await query.answer("❌ MetaTrader not available", show_alert=True)
                return
            
            # First, check if identifier is a signal ID or a ticket ID
            # Try to get as signal first
            ticket = identifier  # Default to direct ticket
            if self.db_manager:
                signal_repo = self.db_manager.get_signal_repository()
                signal = signal_repo.get_signal_by_id(identifier)
                
                if signal:
                    # This is a signal, get the linked position
                    position_repo = self.db_manager.get_position_repository()
                    db_positions = position_repo.get_positions_by_signal_id(identifier)
                    if not db_positions:
                        await query.answer("❌ No position linked to this signal", show_alert=True)
                        return
                    # Get the ticket from the first linked position
                    ticket = db_positions[0].position_id if hasattr(db_positions[0], 'position_id') else db_positions[0].get("position_id")
            
            try:
                position_or_order = self.meta_trader.get_position_or_order(ticket)
            except Exception as e:
                logger.error(f"Error getting position/order for ticket {ticket}: {e}", exc_info=True)
                await query.answer(f"❌ Error: {str(e)}", show_alert=True)
                return
            
            if not position_or_order:
                await query.answer("❌ Position/Order not found", show_alert=True)
                return
            
            if update_type == "sl":
                current_sl = position_or_order.sl if hasattr(position_or_order, 'sl') else position_or_order.get("sl", "N/A")
                if user_id not in self.user_states:
                    self.user_states[user_id] = {}
                if "context" not in self.user_states[user_id]:
                    self.user_states[user_id]["context"] = {}
                self.user_states[user_id]["state"] = self.STATE_AWAITING_SL
                self.user_states[user_id]["context"]["identifier"] = ticket  # Store actual ticket
                self.user_states[user_id]["context"]["signal_id"] = identifier  # Also store signal ID for back button
                await query.edit_message_text(
                    f"📊 Current Stop Loss: {current_sl}\n\n📝 Send new Stop Loss value:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{identifier}")]])
                )
            elif update_type == "tp":
                current_tp = position_or_order.tp if hasattr(position_or_order, 'tp') else position_or_order.get("tp", "N/A")
                if user_id not in self.user_states:
                    self.user_states[user_id] = {}
                if "context" not in self.user_states[user_id]:
                    self.user_states[user_id]["context"] = {}
                self.user_states[user_id]["state"] = self.STATE_AWAITING_TP
                self.user_states[user_id]["context"]["identifier"] = ticket  # Store actual ticket
                self.user_states[user_id]["context"]["signal_id"] = identifier  # Also store signal ID for back button
                await query.edit_message_text(
                    f"📊 Current Take Profit: {current_tp}\n\n📝 Send new Take Profit value:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"signal_{identifier}")]])
                )
        except Exception as e:
            logger.error(f"Error in update action for position {identifier}: {e}", exc_info=True)
            await query.answer(f"Error: {str(e)}", show_alert=True)

    async def handle_delete_order(self, query, user_id: int, ticket: int) -> None:
        """Handle delete pending order"""
        try:
            await query.answer("Deleting order...", show_alert=False)
            if self.meta_trader:
                await query.edit_message_text(f"⏳ Deleting order {ticket}...\n\n🔄 Please wait...")
                result = self.meta_trader.delete_order(ticket)
                if result:
                    logger.info(f"Successfully deleted order {ticket}")
                    await query.edit_message_text(
                        "✅ Order deleted successfully",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                    )
                else:
                    logger.error(f"Failed to delete order {ticket}")
                    await query.edit_message_text(
                        "❌ Delete failed (check logs)",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                    )
            else:
                await query.edit_message_text(
                    "❌ MetaTrader not available",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                )
        except Exception as e:
            logger.error(f"Error deleting order {ticket}: {e}")
            await query.answer(f"Error: {str(e)}", show_alert=True)

    async def handle_close_custom_lot(self, query, user_id: int, identifier: int, lot_size: float) -> None:
        """Handle closing custom lot size from inline button"""
        try:
            logger.info(f"Handling close custom lot: identifier={identifier}, lot_size={lot_size}")
            await query.answer(f"Closing {lot_size} lots...", show_alert=False)
            if self.meta_trader:
                await query.edit_message_text(f"⏳ Closing {lot_size} lots...\n\n🔄 Please wait...")
                try:
                    result = self.meta_trader.close_position(identifier, volume=lot_size)
                    if result:
                        logger.info(f"Successfully closed {lot_size} lots for position {identifier}")
                        await query.edit_message_text(
                            f"✅ Successfully closed {lot_size} lots",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                        )
                    else:
                        logger.error(f"Failed to close {lot_size} lots for position {identifier}")
                        await query.edit_message_text(
                            f"❌ Failed to close {lot_size} lots (check logs)",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                        )
                except Exception as e:
                    logger.error(f"Exception closing {lot_size} lots for position {identifier}: {str(e)}")
                    await query.edit_message_text(
                        f"❌ Error closing lot:\n{str(e)}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                    )
            else:
                await query.edit_message_text(
                    "❌ MetaTrader not available",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="positions")]])
                )
        except Exception as e:
            logger.error(f"Error closing {lot_size} lots for position {identifier}: {e}")
            await query.answer(f"Error: {str(e)}", show_alert=True)
