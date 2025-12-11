import math
import MetaTrader5 as mt5
from loguru import logger
from datetime import datetime, timedelta


class OrderManager:
    """Handles order execution, modification, and management"""

    def __init__(self, connection_manager, market_data, validator, magic_number=2025):
        self.connection = connection_manager
        self.market_data = market_data
        self.validator = validator
        self.magic = magic_number

    def determine_order_type_and_price(self, symbol, open_order_price, order_type_signal, distance_threshold=None, force=False):
        """Determine order type based on price and strategy"""
        if force:
            return order_type_signal

        current_price = self.market_data.get_current_price(symbol, order_type_signal)

        if (symbol == self.connection.validate_symbol('xauusd') and distance_threshold != None and distance_threshold != 0):
            min_distance = distance_threshold   # Minimum distance in pips for market order
            max_distance = distance_threshold  # Maximum distance in pips for market order
            distance = abs(open_order_price - current_price)

            if order_type_signal == mt5.ORDER_TYPE_BUY:
                if min_distance <= distance <= max_distance:
                    return mt5.ORDER_TYPE_BUY
                elif open_order_price > current_price:
                    return mt5.ORDER_TYPE_BUY_STOP
                else:
                    return mt5.ORDER_TYPE_BUY_LIMIT

            elif order_type_signal == mt5.ORDER_TYPE_SELL:
                if min_distance <= distance <= max_distance:
                    return mt5.ORDER_TYPE_SELL
                elif open_order_price < current_price:
                    return mt5.ORDER_TYPE_SELL_STOP
                else:
                    return mt5.ORDER_TYPE_SELL_LIMIT

        # Default behavior for other symbols (original logic)
        if order_type_signal == mt5.ORDER_TYPE_BUY:
            if open_order_price > current_price:
                return mt5.ORDER_TYPE_BUY_STOP
            elif open_order_price < current_price:
                return mt5.ORDER_TYPE_BUY_LIMIT

        elif order_type_signal == mt5.ORDER_TYPE_SELL:
            if open_order_price > current_price:
                return mt5.ORDER_TYPE_SELL_LIMIT
            elif open_order_price < current_price:
                return mt5.ORDER_TYPE_SELL_STOP

        return order_type_signal

    def open_position(self, type, lot, symbol, sl, tp, price, expirePendinOrderInMinutes, comment, signal_id, closerPrice, isFirst=False, isSecond=False, force=False):
        """Open a new position or pending order"""
        try:
            # Get filling mode
            # filling_mode = mt5.symbol_info(symbol).filling_mode - 1

            # Take ask price
            ask_price = mt5.symbol_info_tick(symbol).ask
            # Take bid price
            bid_price = mt5.symbol_info_tick(symbol).bid
            # Take the point of the asset
            point = mt5.symbol_info(symbol).point
            deviation = 20  # mt5.getSlippage(symbol)

            type = self.determine_order_type_and_price(
                symbol, price, type, force=force)

            action = mt5.TRADE_ACTION_PENDING
            if type == mt5.ORDER_TYPE_BUY or type == mt5.ORDER_TYPE_SELL:
                action = mt5.TRADE_ACTION_DEAL

            lot = float(lot)
            stopLoss = float(sl)
            openPrice = self.validator.convert_closer_price(
                symbol, type, price, closerPrice, isCurrentPrice=True)
            takeProfit = float(tp)

            if type != self.determine_order_type_and_price(symbol, openPrice, type, force=force):
                openPrice = float(price)

            if self.any_position_by_data(symbol, openPrice, stopLoss, takeProfit) == True:
                logger.info(f"[User {self.connection.user}] Position already exists: symbol={symbol}, openPrice={openPrice}, sl={stopLoss}, tp={takeProfit}")
                return

            # Open the trade
            request = {
                "action": action,
                "symbol": symbol,
                "volume": lot,
                "type": type,
                "price": openPrice,
                "sl": stopLoss,
                "tp": takeProfit,
                "type_filling": mt5.ORDER_FILLING_IOC,
                # comment.replace("https://t.me/", ""),
                # "comment": "SignalTrader",
                "deviation": deviation,
                "magic": self.magic,
                "type_time": mt5.ORDER_TIME_GTC,
            }

            # expiration
            if type != mt5.ORDER_TYPE_BUY and type != mt5.ORDER_TYPE_SELL:
                if expirePendinOrderInMinutes != None and expirePendinOrderInMinutes != 0:
                    symbol_info = mt5.symbol_info(symbol)
                    timestamp = symbol_info.time
                    # Calculate expiration time
                    expiration_time = datetime.fromtimestamp(
                        timestamp) + timedelta(minutes=expirePendinOrderInMinutes)
                    expiration_timestamp = int(expiration_time.timestamp())
                    request["expiration"] = expiration_timestamp
                    request["type_time"] = mt5.ORDER_TIME_SPECIFIED

            logger.info(f"[User {self.connection.user}] Opening {type} order: {symbol} {lot} lots @ {price}, SL: {sl}, TP: {tp}")

            # Send trading request
            result = mt5.order_send(request)

            if result is not None:
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[User {self.connection.user}] Order failed (code {result.retcode}): {result.comment}")
                    logger.debug(f"[User {self.connection.user}] Current market price: {self.market_data.get_current_price(symbol)}")

                    if result.retcode == 10015 and not force:  # Invalid price
                        logger.warning(f"[User {self.connection.user}] Retrying with market order due to invalid price")
                        if type in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_BUY_LIMIT]:
                            type = mt5.ORDER_TYPE_BUY
                        elif type in [mt5.ORDER_TYPE_SELL, mt5.ORDER_TYPE_SELL_LIMIT, mt5.ORDER_TYPE_SELL_STOP]:
                            type = mt5.ORDER_TYPE_SELL
                        return self.open_position(type, lot, symbol, sl, tp, price, expirePendinOrderInMinutes, comment, signal_id, closerPrice, isFirst, isSecond, force=True)
                    elif result.retcode == 10027:
                        logger.critical(f"[User {self.connection.user}] Algorithmic trading not enabled in MetaTrader terminal")
                    else:
                        logger.error(f"[User {self.connection.user}] Order error details: {mt5.last_error()}")
                else:
                    logger.success(f"[User {self.connection.user}] Order executed successfully - Ticket: {result.order}, Symbol: {symbol}")
            else:
                logger.error(f"[User {self.connection.user}] Order send failed - no response from MetaTrader")

            # save in database
            if signal_id != None:
                position_data = {
                    "signal_id": signal_id,
                    "user_id": self.connection.user,
                    "position_id": result.order,
                    "is_first": isFirst,
                    "is_second": isSecond
                }
                from Database import Migrations
                Migrations.position_repo.insert(position_data)

            return result
        except Exception as ex:
            logger.error(f"Unexpected error in open trade position: {ex}")

    def any_position_by_data(self, symbol, openPrice, sl, tp):
        """Check if any position or order already exists by this data"""
        positions = mt5.positions_get(symbol=symbol)
        if positions != None and len(positions) > 0:
            for position in positions:
                if (float(openPrice) == position.price_open and float(sl) == position.sl and float(tp) == position.tp):
                    return True

        orders = mt5.orders_get(symbol=symbol)
        if orders != None and len(orders) > 0:
            for order in orders:
                if (float(openPrice) == order.price_open and float(sl) == order.sl and float(tp) == order.tp):
                    return True

        return False