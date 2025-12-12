import asyncio
from loguru import logger

from .connection.connection import ConnectionManager, AccountConfig
from .trading.market_data import MarketData
from .trading.validation import PriceValidator
from .trading.orders import OrderManager
from .trading.positions import PositionManager
from .monitoring.monitoring import MonitoringManager
from .trading.trading import TradingOperations
from .trading.utils import get_mt5_time, get_symbols

# Re-export for backward compatibility
__all__ = ['MetaTrader', 'get_mt5_time', 'get_symbols']


class MetaTrader:
    """Main MetaTrader orchestrator class using modular components"""

    def __init__(self, path, server, user, password, saveProfits=None, closePositionsOnTrail=True):
        self.path = path
        self.server = server
        self.user = user
        self.password = password
        self.saveProfits = saveProfits
        self.closePositionsOnTrail = closePositionsOnTrail
        self.magic = 2025

        # Initialize components
        self.connection = ConnectionManager(path, server, user, password)
        self.market_data = MarketData(self.magic)
        self.validator = PriceValidator(self.connection)
        self.order_manager = OrderManager(self.connection, self.market_data, self.validator, self.magic)
        self.position_manager = PositionManager(self.market_data, self.connection, self.magic)
        self.monitoring = MonitoringManager(self.connection, self.market_data, self.position_manager, saveProfits, closePositionsOnTrail)
    
    # Connection methods
    def Login(self) -> bool:
        return self.connection.login()

    def validate_symbol(self, symbol):
        return self.connection.validate_symbol(symbol)

    def CheckSymbol(self, symbol):
        return self.connection.check_symbol(symbol)

    @staticmethod
    def get_mt5_time():
        return get_mt5_time()

    @staticmethod
    def GetSymbols():
        return get_symbols()

    # Market data methods
    def get_current_price(self, symbol, action=None):
        return self.market_data.get_current_price(symbol, action)

    def get_open_positions(self, ticket_id=None):
        return self.market_data.get_open_positions(ticket_id)

    def get_pending_orders(self, ticket_id=None):
        return self.market_data.get_pending_orders(ticket_id)

    def get_position(self, ticket_id):
        """Get open position by ticket ID (only positions, not orders)"""
        return self.market_data.get_position(ticket_id)

    def get_position_or_order(self, ticket_id):
        return self.market_data.get_position_or_order(ticket_id)

    # Position management methods
    def close_half_position(self, ticket):
        return self.position_manager.close_half_position(ticket)

    def save_profit_position(self, ticket, index):
        return self.position_manager.save_profit_position(ticket, index, self.saveProfits, self.closePositionsOnTrail)

    def update_stop_loss(self, ticket, new_stop_loss):
        return self.position_manager.update_stop_loss(ticket, new_stop_loss)

    def close_position(self, ticket, volume=None):
        """Close position with optional custom volume"""
        if volume is not None:
            return self.position_manager.close_position(ticket, volume)
        return self.position_manager.close_position(ticket)

    def close_custom_lot(self, ticket, lot_size):
        """Close a custom volume from a position"""
        return self.position_manager.close_custom_lot(ticket, lot_size)

    def update_position_sl(self, ticket, new_sl):
        """Update position stop loss and return tuple (success, error_message)"""
        result = self.update_stop_loss(ticket, new_sl)
        # If the position_manager method is updated to return error messages, use them
        # For now, just return the boolean
        return result

    def update_position_tp(self, ticket, new_tp):
        """Update position take profit and return tuple (success, error_message)"""
        return self.position_manager.update_take_profit(ticket, new_tp)

    def get_position_by_ticket(self, ticket):
        """Get position by ticket ID"""
        return self.market_data.get_position(ticket)

    def get_order_by_ticket(self, ticket):
        """Get pending order by ticket ID"""
        pos_or_order = self.market_data.get_position_or_order(ticket)
        if pos_or_order and hasattr(pos_or_order, 'type'):
            # Check if it's an order (not a position)
            import MetaTrader5 as mt5
            if pos_or_order.type not in [mt5.POSITION_TYPE_BUY, mt5.POSITION_TYPE_SELL]:
                return pos_or_order
        return None

    def delete_order(self, ticket):
        """Delete pending order"""
        return self.position_manager.delete_order(ticket)

    def get_account_info(self):
        """Get account information"""
        return self.connection.get_account_info() if hasattr(self.connection, 'get_account_info') else {}

    # Validation methods
    def validate(self, action, price, symbol, currentPrice=None, isSl=False, isSecondPrice=False):
        return self.validator.validate(action, price, symbol, currentPrice, isSl, isSecondPrice)

    def validate_tp_list(self, action, tp_list, symbol, firstPrice, secondPrice=None, closerPrice=None):
        return self.validator.validate_tp_list(action, tp_list, symbol, firstPrice, secondPrice, closerPrice)

    def calculate_lot_size_with_prices(self, symbol, risk_percentage, open_price, stop_loss_price, account_size):
        return self.validator.calculate_lot_size_with_prices(symbol, risk_percentage, open_price, stop_loss_price, account_size)

    def ConvertCloserPrice(self, symbol, actionType, price, closerPrice, isCurrentPrice=None, isTp=None):
        return self.validator.convert_closer_price(symbol, actionType, price, closerPrice, isCurrentPrice, isTp)

    def calculate_new_price(self, symbol, price, num_points, tp, actionType):
        return self.validator.calculate_new_price(symbol, price, num_points, tp, actionType)

    # Order methods
    def determine_order_type_and_price(self, symbol, open_order_price, order_type_signal, distance_threshold=None, force=False):
        return self.order_manager.determine_order_type_and_price(symbol, open_order_price, order_type_signal, distance_threshold, force)

    # Order execution
    def OpenPosition(self, type, lot, symbol, sl, tp, price, expirePendinOrderInMinutes, comment, signal_id, closerPrice, isFirst=False, isSecond=False, force=False):
        return self.order_manager.open_position(type, lot, symbol, sl, tp, price, expirePendinOrderInMinutes, comment, signal_id, closerPrice, isFirst, isSecond, force)

    def AnyPositionByData(self, symbol, openPrice, sl, tp):
        return self.order_manager.any_position_by_data(symbol, openPrice, sl, tp)

    # Account configuration
    MetaTraderAccount = AccountConfig

    # Static trading operations
    @staticmethod
    def Trade(message_username, message_id, message_chatid, actionType, symbol, openPrice, secondPrice, tp_list, sl, comment, provider="telegram"):
        TradingOperations.trade(message_username, message_id, message_chatid, actionType, symbol, openPrice, secondPrice, tp_list, sl, comment, provider)

    @staticmethod
    def RiskFreePositions(chat_id, message_id):
        TradingOperations.risk_free_positions(chat_id, message_id)

    @staticmethod
    def RiskFreeSignal(signal_id):
        TradingOperations.risk_free_signal(signal_id)

    @staticmethod
    def Update_last_signal(chat_id, stop_loss):
        TradingOperations.update_last_signal(chat_id, stop_loss)

    @staticmethod
    def Update_signal(signal_id, takeProfits, stopLoss):
        TradingOperations.update_signal(signal_id, takeProfits, stopLoss)

    @staticmethod
    def Delete_signal(signal_id):
        TradingOperations.delete_signal(signal_id)

    @staticmethod
    def Close_half_signal(signal_id):
        TradingOperations.close_half_signal(signal_id)
                
    # Monitoring methods
    @staticmethod
    async def monitor_all_accounts():
        await MonitoringManager.monitor_all_accounts()

    async def monitor_account(self):
        await self.monitoring.monitor_account()

    def trailing(self):
        self.monitoring.trailing()

    def manage_positions(self):
        self.monitoring.manage_positions()
                







            