"""
Command and callback handlers for user interactions
"""

from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class HandlerManager:
    """Manages command and callback handlers"""

    def __init__(self, views, actions, input_handler, user_states: dict):
        self.views = views
        self.actions = actions
        self.input_handler = input_handler
        self.user_states = user_states

    # State constants
    STATE_MAIN_MENU = "main_menu"
    STATE_AWAITING_LOT = "awaiting_lot"
    STATE_AWAITING_SL = "awaiting_sl"
    STATE_AWAITING_TP = "awaiting_tp"
    STATE_TESTER = "tester"

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - Show account details and main menu"""
        try:
            user_id = update.effective_user.id
            self.user_states[user_id] = {
                "state": self.STATE_MAIN_MENU, "context": {}}

            # Show account details and main menu
            await self.views.show_account_details(update, user_id)
        except Exception as e:
            logger.error(f"Error handling start: {e}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button callbacks - routes to appropriate view or action"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            callback_data = query.data
            await query.answer()

            logger.info(f"Callback received: {callback_data}")

            # Handle single-word callbacks first (before splitting)
            if callback_data == "menu":
                # Show account details as main menu
                await self.views.show_account_details_from_callback(query, user_id)
                return
            elif callback_data == "signals":
                await self.views.show_signal_list(query, user_id)
                return
            elif callback_data == "open_trade":
                await self.views.show_open_trade_form(query, user_id)
                return
            elif callback_data == "positions":
                await self.views.show_position_list(query, user_id)
                return
            elif callback_data == "tester":
                await self.views.show_tester(query, user_id)
                return
            elif callback_data == "trade":
                await self.views.show_trade_summary(query, user_id)
                return
            elif callback_data == "history":
                await self.views.show_history_menu(query, user_id)
                return
            elif callback_data == "history_today":
                await self.views.show_history_results(query, user_id, "today")
                return
            elif callback_data == "history_yesterday":
                await self.views.show_history_results(query, user_id, "yesterday")
                return
            elif callback_data == "history_calendar":
                await self.views.show_history_calendar(query, user_id)
                return
            elif callback_data == "history_calendar_reset":
                # Reset calendar selection
                if user_id in self.user_states and "context" in self.user_states[user_id]:
                    self.user_states[user_id]["context"].pop("from_date", None)
                    self.user_states[user_id]["context"].pop("to_date", None)
                await self.views.show_history_calendar(query, user_id)
                return
            elif callback_data == "history_custom_view":
                # View custom date range
                if user_id in self.user_states and "context" in self.user_states[user_id]:
                    from_date = self.user_states[user_id]["context"].get("from_date")
                    to_date = self.user_states[user_id]["context"].get("to_date")
                    if from_date and to_date:
                        await self.views.show_history_results(query, user_id, "custom", from_date, to_date)
                    else:
                        await query.answer("Please select both start and end dates", show_alert=True)
                return
            elif callback_data == "history_back":
                # Go back to history results using stored context
                if user_id in self.user_states and "context" in self.user_states[user_id]:
                    context = self.user_states[user_id]["context"]
                    range_type = context.get("history_range_type", "today")
                    from_date = context.get("from_date")
                    to_date = context.get("to_date")

                    if range_type == "custom" and from_date and to_date:
                        await self.views.show_history_results(query, user_id, "custom", from_date, to_date)
                    else:
                        await self.views.show_history_results(query, user_id, range_type)
                else:
                    await self.views.show_history_menu(query, user_id)
                return
            elif callback_data == "cal_noop":
                # No operation for calendar headers
                await query.answer()
                return
            elif callback_data == "history_page_next":
                # Go to next page
                if user_id in self.user_states and "context" in self.user_states[user_id]:
                    context = self.user_states[user_id]["context"]
                    current_page = context.get("history_page", 0)
                    context["history_page"] = current_page + 1

                    range_type = context.get("history_range_type", "today")
                    from_date = context.get("from_date")
                    to_date = context.get("to_date")

                    if range_type == "custom" and from_date and to_date:
                        await self.views.show_history_results(query, user_id, "custom", from_date, to_date)
                    else:
                        await self.views.show_history_results(query, user_id, range_type)
                return
            elif callback_data == "history_page_prev":
                # Go to previous page
                if user_id in self.user_states and "context" in self.user_states[user_id]:
                    context = self.user_states[user_id]["context"]
                    current_page = context.get("history_page", 0)
                    context["history_page"] = max(0, current_page - 1)

                    range_type = context.get("history_range_type", "today")
                    from_date = context.get("from_date")
                    to_date = context.get("to_date")

                    if range_type == "custom" and from_date and to_date:
                        await self.views.show_history_results(query, user_id, "custom", from_date, to_date)
                    else:
                        await self.views.show_history_results(query, user_id, range_type)
                return

            # Now handle compound callbacks that need splitting
            parts = callback_data.split("_")
            action = parts[0]
            
            logger.info(f"Parsed callback - action: {action}, parts: {parts}")

            # Check for close_lot BEFORE close to avoid parsing conflict
            # close_lot has format: close_lot_{identifier}-{lot_size}
            if len(parts) >= 3 and parts[0] == "close" and parts[1] == "lot":
                identifier_lot = parts[2]
                if '-' in identifier_lot:
                    identifier_str, lot_str = identifier_lot.split('-', 1)
                    try:
                        identifier = int(identifier_str)
                        lot_size = float(lot_str)
                        logger.info(f"Close lot callback: identifier={identifier}, lot_size={lot_size}")
                        await self.actions.handle_close_custom_lot(query, user_id, identifier, lot_size)
                    except (ValueError, IndexError) as e:
                        logger.error(f"Invalid close_lot format: {callback_data}, error: {e}")
                        await query.answer("Invalid lot format", show_alert=True)
                else:
                    logger.error(f"Invalid close_lot format (no dash): {callback_data}")
                    await query.answer("Invalid lot format", show_alert=True)
            elif action == "signal":
                signal_id = int(parts[1])
                await self.views.show_signal_detail(query, user_id, signal_id)
            elif action == "position":
                ticket = int(parts[1])
                await self.views.show_position_detail(query, user_id, ticket)
            elif action == "close":
                identifier = int(parts[1])
                close_type = "_".join(parts[2:])
                await self.actions.handle_close_action(query, user_id, identifier, close_type)
            elif action == "update":
                identifier = int(parts[1])
                update_type = "_".join(parts[2:])
                await self.actions.handle_update_action(query, user_id, identifier, update_type)
            elif action == "delete":
                ticket = int(parts[1])
                await self.actions.handle_delete_order(query, user_id, ticket)
            elif action == "manage":
                signal_id = int(parts[1])
                entry_type = "_".join(parts[2:])  # "open" or "second"
                await self.views.show_manage_signal_entries(query, user_id, signal_id, entry_type)
            elif action == "history" and len(parts) >= 2 and parts[1] == "detail":
                # history_detail_{index}
                result_index = int(parts[2])
                logger.info(f"[HISTORY_HANDLER] User {user_id} viewing history detail for result_index: {result_index}")
                await self.views.show_history_detail(query, user_id, result_index)
            elif action == "cal":
                # Calendar navigation and day selection
                # Formats: cal_prev_{year}_{month}_{mode}, cal_next_{year}_{month}_{mode}, cal_day_{year}_{month}_{day}_{mode}
                if len(parts) < 2:
                    await query.answer("Invalid calendar action", show_alert=True)
                    return

                cal_action = parts[1]

                if cal_action == "prev":
                    # Navigate to previous month
                    year = int(parts[2])
                    month = int(parts[3])
                    mode = parts[4] if len(parts) > 4 else "from"

                    # Calculate previous month
                    if month == 1:
                        year -= 1
                        month = 12
                    else:
                        month -= 1

                    await self.views.show_history_calendar(query, user_id, year, month, mode)

                elif cal_action == "next":
                    # Navigate to next month
                    year = int(parts[2])
                    month = int(parts[3])
                    mode = parts[4] if len(parts) > 4 else "from"

                    # Calculate next month
                    if month == 12:
                        year += 1
                        month = 1
                    else:
                        month += 1

                    await self.views.show_history_calendar(query, user_id, year, month, mode)

                elif cal_action == "day":
                    # Select a day
                    from datetime import datetime

                    year = int(parts[2])
                    month = int(parts[3])
                    day = int(parts[4])
                    mode = parts[5] if len(parts) > 5 else "from"

                    selected_date = datetime(year, month, day)

                    # Store in user context
                    if user_id not in self.user_states:
                        self.user_states[user_id] = {}
                    if "context" not in self.user_states[user_id]:
                        self.user_states[user_id]["context"] = {}

                    if mode == "from":
                        self.user_states[user_id]["context"]["from_date"] = selected_date
                        # Switch to selecting 'to' date
                        await self.views.show_history_calendar(query, user_id, year, month, "to")
                    else:  # mode == "to"
                        from_date = self.user_states[user_id]["context"].get("from_date")

                        # Validate: to_date must be >= from_date
                        if from_date and selected_date < from_date:
                            await query.answer("End date must be after start date", show_alert=True)
                            await self.views.show_history_calendar(query, user_id, year, month, "to")
                        else:
                            self.user_states[user_id]["context"]["to_date"] = selected_date
                            # Show calendar with both dates selected
                            await self.views.show_history_calendar(query, user_id, year, month, "to")

                else:
                    await query.answer("Invalid calendar action", show_alert=True)
            else:
                logger.warning(f"Unknown action: {action} from callback: {callback_data}")
                await query.answer("Unknown action", show_alert=True)

        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            try:
                await query.answer(f"Error: {str(e)}", show_alert=True)
            except:
                pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages for state-based input only"""
        try:
            user_id = update.effective_user.id
            user_state = self.user_states.get(user_id, {})
            state = user_state.get("state")
            message_text = update.message.text

            if state == self.STATE_AWAITING_LOT:
                await self.input_handler.handle_lot_input(update, user_id, message_text)
            elif state == self.STATE_AWAITING_SL:
                await self.input_handler.handle_sl_input(update, user_id, message_text)
            elif state == self.STATE_AWAITING_TP:
                await self.input_handler.handle_tp_input(update, user_id, message_text)
            elif state == "awaiting_trade_input":
                await self.input_handler.handle_trade_input(update, user_id, message_text)
            elif state == self.STATE_TESTER:
                await self.input_handler.handle_tester_input(update, user_id, message_text)
            else:
                # Default: show main menu
                text = "👋 **Signal Trader Bot Menu**\n\nSelect an option:"
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
                        InlineKeyboardButton("📜 History", callback_data="history"),
                    ],
                ]
                await update.message.reply_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
        except Exception as e:
            logger.error(f"Error handling message: {e}")
