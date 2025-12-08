import MetaTrader5 as mt5
from loguru import logger


class MarketData:
    """Handles market data queries and position/order information"""

    def __init__(self, magic_number=2025):
        self.magic = magic_number

    def get_current_price(self, symbol, action=None):
        """Get the current price of the symbol"""
        tick = mt5.symbol_info_tick(symbol)
        # logger.info(f"{symbol} current price is: {tick.bid}")
        if action == mt5.ORDER_TYPE_BUY:
            return tick.ask if tick else None
        elif action == mt5.ORDER_TYPE_SELL:
            return tick.bid if tick else None
        return tick.bid if tick else None

    def get_open_positions(self, ticket_id=None):
        """Get open positions from MetaTrader"""
        if ticket_id != None:
            positions = mt5.positions_get(ticket=ticket_id)
            if (len(positions) == 0):
                # logger.error(f"Can't find position {ticket_id}")
                return None
            return positions[0]
        else:
            positions = mt5.positions_get()
            return list(positions) if positions else []

    def get_pending_orders(self, ticket_id=None):
        """Get pending orders from MetaTrader"""
        if ticket_id != None:
            orders = mt5.orders_get(ticket=ticket_id)
            if (len(orders) == 0):
                # logger.error(f"Can't find order {ticket_id}")
                return None
            return orders[0]
        else:
            orders = mt5.orders_get()
            return list(orders) if orders else []

    def get_position(self, ticket_id):
        """Get open position by ticket ID (only positions, not orders)"""
        return self.get_open_positions(ticket_id=ticket_id)

    def get_position_or_order(self, ticket_id):
        """Get position or order by ticket ID"""
        position = self.get_open_positions(ticket_id=ticket_id)
        if position != None:
            return position
        return self.get_pending_orders(ticket_id=ticket_id)