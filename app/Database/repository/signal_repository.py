"""Signal repository for database operations on trading signals"""

from typing import List, Dict, Optional, Any
from .Repository import SQLiteRepository
from ..models import SignalModel


class SignalRepository:
    """Repository for signal-related database operations"""

    def __init__(self, db_path: str = "signaltrader.db", enable_cache: bool = True):
        self.repository = SQLiteRepository(db_path, "Signals", enable_cache=enable_cache)

    def create_table(self) -> None:
        """Create the signals table"""
        from ..models import DatabaseSchema
        self.repository.create_table(DatabaseSchema.SIGNAL_COLUMNS)

    def insert_signal(self, signal_data: Dict[str, Any]) -> int:
        """Insert a new signal into the database"""
        return self.repository.insert(signal_data)

    def get_signal_by_id(self, signal_id: int) -> Optional[SignalModel]:
        """Get signal by ID"""
        result = self.repository.get_by_id(signal_id)
        return SignalModel.from_tuple(result) if result else None

    def get_signal_by_position_id(self, position_id: int) -> Optional[SignalModel]:
        """Get signal associated with a position ID"""
        query = """
            SELECT s.*
            FROM signals s
            INNER JOIN positions p ON p.signal_id = s.id
            WHERE p.position_id = ?
            LIMIT 1
        """
        results = self.repository.execute_query(query, (position_id,))
        if not results:
            return None
        return SignalModel.from_tuple(results[0])

    def get_signal_by_chat(self, chat_id: int, message_id: int) -> Optional[Dict]:
        """Get signal by chat and message ID"""
        query = """
            SELECT *
            FROM signals
            WHERE telegram_message_chatid = ? AND telegram_message_id = ?
            ORDER BY id DESC
            LIMIT 1
        """
        results = self.repository.execute_query(query, (chat_id, message_id))
        if not results:
            return None

        result = results[0]
        return {
            "id": result[0],
            "telegram_channel_title": result[1],
            "telegram_message_id": result[2],
            "telegram_message_chatid": result[3],
            "open_price": result[4],
            "second_price": result[5],
            "stop_loss": result[6],
            "tp_list": result[7],
            "symbol": result[8],
            "current_time": result[9]
        }

    def get_last_record(self, open_price: float, second_price: Optional[float],
                       stop_loss: float, symbol: str) -> Optional[SignalModel]:
        """Get the last matching signal record"""
        query = """
            SELECT *
            FROM signals
            WHERE open_price = ? AND second_price = ? AND stop_loss = ? AND symbol = ?
            ORDER BY id DESC
            LIMIT 1
        """
        results = self.repository.execute_query(
            query, (open_price, second_price, stop_loss, symbol))
        if not results:
            return None
        return SignalModel.from_tuple(results[0])

    def update_stop_loss(self, signal_id: int, stop_loss: float) -> None:
        """Update stop loss for a signal"""
        self.repository.update(signal_id, {"stop_loss": stop_loss})

    def update_take_profits(self, signal_id: int, take_profits: List[float]) -> None:
        """Update take profit levels for a signal"""
        tp_list = ','.join(map(str, take_profits))
        self.repository.update(signal_id, {"tp_list": tp_list})

    def get_all_signals(self) -> List[SignalModel]:
        """Get all signals"""
        results = self.repository.get_all()
        return [SignalModel.from_tuple(result) for result in results]


# Global instance for backward compatibility
signal_repo = SignalRepository()