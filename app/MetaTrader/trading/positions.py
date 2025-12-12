import math
import MetaTrader5 as mt5
from loguru import logger


class PositionManager:
    """Handles position operations like closing, modifying, and profit taking"""

    def __init__(self, market_data, connection_manager=None, magic_number=2025):
        self.market_data = market_data
        self.connection = connection_manager
        self.magic = magic_number

    def close_position(self, ticket):
        """Close a position or cancel a pending order"""
        user_prefix = f"[User {self.connection.user}] " if self.connection else ""
        logger.info(f"{user_prefix}Attempting to close ticket {ticket}")

        position = self.market_data.get_open_positions(ticket)
        action = mt5.TRADE_ACTION_DEAL

        # If no open position found, check for pending orders
        if position is None:
            position = self.market_data.get_pending_orders(ticket)
            action = mt5.TRADE_ACTION_REMOVE

        if position is None:
            user_prefix = f"[User {self.connection.user}] " if self.connection else ""
            logger.warning(f"{user_prefix}Position/order {ticket} not found")
            return False

        symbol = position.symbol
        volume = position.volume if hasattr(position, "volume") else position.volume_current

        # Initialize request
        request = {
            "action": action,
            "magic": self.magic,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if action == mt5.TRADE_ACTION_DEAL:
            # Handle closing an open position
            if position.type not in [mt5.POSITION_TYPE_BUY, mt5.POSITION_TYPE_SELL]:
                logger.error(f"Invalid position type for ticket {ticket}")
                return False

            # Determine closing direction and price
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL  # Sell to close buy
                price = mt5.symbol_info_tick(symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY   # Buy to close sell
                price = mt5.symbol_info_tick(symbol).ask

            # Validate tick data
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Failed to get tick data for {symbol}")
                return False
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

            # Build request for closing position
            request.update({
                "symbol": symbol,
                "volume": volume,
                "price": price,
                "deviation": 10,
                "type": order_type,
                "position": ticket
            })

            user_prefix = f"[User {self.connection.user}] " if self.connection else ""
            logger.info(f"{user_prefix}Closing position {ticket}: {symbol} {volume} lots at {price}")
        else:
            # Handle removing a pending order
            request.update({"order": ticket})
            logger.info(f"{user_prefix}Cancelling pending order {ticket}: {symbol}")

        # Send the request
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            user_prefix = f"[User {self.connection.user}] " if self.connection else ""
            logger.error(f"{user_prefix}Failed to close/cancel {ticket}: {result.comment}")
            return False

        user_prefix = f"[User {self.connection.user}] " if self.connection else ""
        logger.success(f"{user_prefix}Successfully closed/cancelled ticket {ticket}")
        return True

    def close_half_position(self, ticket):
        """Close half of the position volume"""
        position = self.market_data.get_open_positions(ticket)
        if (position is None):
            return

        new_lot_size = math.floor((position.volume / 2) * 100) / 100
        logger.warning(f"new lot size to close half of {
                        ticket} is {new_lot_size}")

        if new_lot_size >= 0.01:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": float(new_lot_size),
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": position.ticket,
                "price": mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
                "deviation": 10,
                "magic": self.magic,
                # "comment": "Closing half position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            logger.info(f"{result}")
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Failed to close half position for {
                              position.symbol}: {result.comment}")
                return False
            else:
                logger.success(f"Successfully closed half position for {
                                position.symbol}, ticket {ticket}")
        # else:
        #     self.close_position(ticket)

    def close_custom_lot(self, ticket, lot_size):
        """Close a custom volume from a position"""
        position = self.market_data.get_open_positions(ticket)
        if position is None:
            logger.error(f"Position {ticket} not found")
            return False

        # Validate lot size
        if lot_size <= 0 or lot_size > position.volume:
            logger.error(f"Invalid lot size {lot_size} for position {ticket} (max: {position.volume})")
            return False

        try:
            # Determine close direction based on position type
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                close_price = mt5.symbol_info_tick(position.symbol).bid
            else:  # SELL position
                order_type = mt5.ORDER_TYPE_BUY
                close_price = mt5.symbol_info_tick(position.symbol).ask

            if close_price is None:
                logger.error(f"Failed to get close price for symbol {position.symbol}")
                return False

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": float(lot_size),
                "type": order_type,
                "position": position.ticket,
                "price": close_price,
                "deviation": 10,
                "magic": self.magic,
                "comment": f"Close custom lot {lot_size}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Failed to close {lot_size} lots for position {ticket}: {result.comment}")
                return False
            else:
                logger.success(f"Successfully closed {lot_size} lots from position {ticket} ({position.symbol})")
                return True

        except Exception as e:
            logger.error(f"Exception during custom lot close for position {ticket}: {str(e)}")
            return False

    def save_profit_position(self, ticket, index, save_profits=None, close_positions=True):
        """Save profit of the position volume based on profit-taking strategy"""

        position = self.market_data.get_open_positions(ticket)
        if position is None:
            logger.warning(f"Position {ticket} not found for profit saving")
            return False

        # Validate save_profits configuration
        if save_profits is None or len(save_profits) == 0:
            logger.warning(f"No profit saving strategy configured for position {ticket}")
            return False

        if index >= len(save_profits):
            logger.error(f"Profit saving index {index} out of range for position {ticket}")
            return False

        profit_percentage = save_profits[index]

        # Skip if profit percentage is zero (user doesn't want to save profit at this level)
        if profit_percentage == 0:
            logger.info(f"Skipping profit saving for position {ticket} at level {index} (percentage set to 0)")
            return False

        # Calculate lot size to close
        new_lot_size = round(position.volume * (profit_percentage / 100), 2)

        if new_lot_size <= 0:
            logger.warning(f"Calculated lot size {new_lot_size} is invalid for position {ticket}")
            return False

        logger.info(f"Saving {profit_percentage}% profit from position {ticket}: closing {new_lot_size} lots")

        # Close entire position if percentage is 100%
        if profit_percentage == 100:
            logger.info(f"Closing entire position {ticket} for 100% profit taking")
            return self.close_position(ticket)

        if (position.volume <= 0.01 and new_lot_size <= 0.01) and close_positions:
            logger.warning(f"Lot size {new_lot_size} below minimum 0.01 for position {ticket}, closing entire position instead")
            return self.close_position(ticket)
        elif (position.volume <= 0.01 and new_lot_size <= 0.01) and close_positions == False: # Skip if position closing is disabled
            logger.info(f"Position closing disabled for trailing - skipping profit saving for {ticket}")
            return True

        # Execute partial closure
        try:
            # Determine close direction based on position type
            if position.type == mt5.ORDER_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                close_price = mt5.symbol_info_tick(position.symbol).bid
            else:  # SELL position
                order_type = mt5.ORDER_TYPE_BUY
                close_price = mt5.symbol_info_tick(position.symbol).ask

            if close_price is None:
                logger.error(f"Failed to get close price for symbol {position.symbol}")
                return False

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": float(new_lot_size),
                "type": order_type,
                "position": position.ticket,
                "price": close_price,
                "deviation": 10,
                "magic": self.magic,
                "comment": f"Profit taking {profit_percentage}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Failed to save {profit_percentage}% profit for position {ticket}: {result.comment}")
                return False
            else:
                logger.success(f"Successfully saved {profit_percentage}% profit from position {ticket} ({position.symbol})")
                return True

        except Exception as e:
            logger.error(f"Exception during profit saving for position {ticket}: {str(e)}")
            return False

    def update_stop_loss(self, ticket, new_stop_loss):
        """
        Updates stop loss for either an open position or a pending order.
        Automatically detects the type and applies the correct request.
        Returns: (success, error_message)
        """
        # Try to find active position first
        position = mt5.positions_get(ticket=ticket)
        if position and len(position) > 0:
            position = position[0]
            symbol_info = mt5.symbol_info(position.symbol)
            if not symbol_info:
                logger.error(f"Symbol info not found for {position.symbol}")
                return False, "Symbol info not found"

            digits = symbol_info.digits
            new_stop_loss = round(new_stop_loss, digits)

            if position.sl == new_stop_loss:
                return False, "Already at target SL"

            logger.info(f"Updating stop loss for position {ticket} to {new_stop_loss}")

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": position.symbol,
                "sl": float(new_stop_loss),
                "tp": position.tp,
                "magic": position.magic,
                "deviation": 10
            }

        else:
            # If not a position, check for pending order
            order = mt5.orders_get(ticket=ticket)
            if not order or len(order) == 0:
                logger.warning(f"Ticket {ticket} not found as position or order")
                return False, "Position/order not found"

            order = order[0]
            symbol_info = mt5.symbol_info(order.symbol)
            if not symbol_info:
                logger.error(f"Symbol info not found for {order.symbol}")
                return False, "Symbol info not found"

            digits = symbol_info.digits
            new_stop_loss = round(new_stop_loss, digits)

            if order.sl == new_stop_loss:
                return False, "Already at target SL"

            logger.info(f"Updating stop loss for pending order {ticket} to {new_stop_loss}")

            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "symbol": order.symbol,
                "price": order.price_open,
                "sl": float(new_stop_loss),
                "tp": order.tp,
                "type_time": order.type_time,
                "type_filling": order.type_filling
            }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = result.comment if result.comment else "Unknown error"
            logger.error(f"Failed to update stop loss for ticket {ticket}: {error_msg}")
            return False, error_msg
        else:
            logger.success(f"Stop loss updated successfully for ticket {ticket} to {new_stop_loss}")
            return True, None

    def update_take_profit(self, ticket, new_take_profit):
        """
        Updates take profit for either an open position or a pending order.
        Automatically detects the type and applies the correct request.
        Returns: (success, error_message)
        """
        # Try to find active position first
        position = mt5.positions_get(ticket=ticket)
        if position and len(position) > 0:
            position = position[0]
            symbol_info = mt5.symbol_info(position.symbol)
            if not symbol_info:
                logger.error(f"Symbol info not found for {position.symbol}")
                return False, "Symbol info not found"

            digits = symbol_info.digits
            new_take_profit = round(new_take_profit, digits)

            if position.tp == new_take_profit:
                return False, "Already at target TP"

            logger.info(f"Updating take profit for position {ticket} to {new_take_profit}")

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": position.symbol,
                "sl": position.sl,
                "tp": float(new_take_profit),
                "magic": position.magic,
                "deviation": 10
            }

        else:
            # If not a position, check for pending order
            order = mt5.orders_get(ticket=ticket)
            if not order or len(order) == 0:
                logger.warning(f"Ticket {ticket} not found as position or order")
                return False, "Position/order not found"

            order = order[0]
            symbol_info = mt5.symbol_info(order.symbol)
            if not symbol_info:
                logger.error(f"Symbol info not found for {order.symbol}")
                return False, "Symbol info not found"

            digits = symbol_info.digits
            new_take_profit = round(new_take_profit, digits)

            if order.tp == new_take_profit:
                return False, "Already at target TP"

            logger.info(f"Updating take profit for pending order {ticket} to {new_take_profit}")

            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "symbol": order.symbol,
                "price": order.price_open,
                "sl": order.sl,
                "tp": float(new_take_profit),
                "type_time": order.type_time,
                "type_filling": order.type_filling
            }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = result.comment if result.comment else "Unknown error"
            logger.error(f"Failed to update take profit for ticket {ticket}: {error_msg}")
            return False, error_msg
        else:
            logger.success(f"Take profit updated successfully for ticket {ticket} to {new_take_profit}")
            return True, None

    def delete_order(self, ticket):
        """Cancel/delete a pending order"""
        order = mt5.orders_get(ticket=ticket)
        if not order or len(order) == 0:
            logger.warning(f"Order {ticket} not found")
            return False

        order = order[0]
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to delete order {ticket}: {result.comment}")
            return False

        logger.success(f"Order {ticket} deleted successfully")
        return True