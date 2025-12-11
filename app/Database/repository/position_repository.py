"""Position repository for database operations on trading positions"""

from typing import List, Dict, Optional, Any
from .Repository import SQLiteRepository
from ..models import PositionModel


class PositionRepository:
    """Repository for position-related database operations"""

    def __init__(self, db_path: str = "signaltrader.db", enable_cache: bool = True):
        self.repository = SQLiteRepository(db_path, "Positions", enable_cache=enable_cache)

    def create_table(self) -> None:
        """Create the positions table"""
        from ..models import DatabaseSchema
        self.repository.create_table(DatabaseSchema.POSITION_COLUMNS)

    def insert_position(self, position_data: Dict[str, Any]) -> int:
        """Insert a new position into the database"""
        return self.repository.insert(position_data)

    def get_position_by_id(self, position_id: int) -> Optional[PositionModel]:
        """Get position by ID"""
        result = self.repository.get_by_id(position_id)
        return PositionModel.from_tuple(result) if result else None

    def get_positions_by_signal_id(self, signal_id: int) -> List[PositionModel]:
        """Get all positions for a signal"""
        query = """
            SELECT *
            FROM positions
            WHERE signal_id = ?
            ORDER BY id DESC
            LIMIT 2
        """
        results = self.repository.execute_query(query, (signal_id,))
        return [PositionModel.from_tuple(result) for result in results]

    def get_position_by_signal_id(self, signal_id: int, first: bool = False, second: bool = False) -> Optional[PositionModel]:
        """Get position by signal ID with first/second filter"""
        query = """
            SELECT *
            FROM positions
            WHERE signal_id = ? AND is_first = ? AND is_second = ?
            ORDER BY id DESC
            LIMIT 1
        """
        results = self.repository.execute_query(query, (signal_id, first, second))
        if not results:
            return None
        return PositionModel.from_tuple(results[0])

    def get_signal_positions_by_position_id(self, position_id: int) -> List[PositionModel]:
        """Get all positions for the same signal as the given position"""
        query = """
            SELECT *
            FROM positions
            WHERE signal_id = (SELECT signal_id FROM positions WHERE position_id = ?)
            ORDER BY id DESC
            LIMIT 2
        """
        results = self.repository.execute_query(query, (position_id,))
        return [PositionModel.from_tuple(result) for result in results]

    def get_last_signal_positions_by_chat_id(self, chat_id: int) -> List[int]:
        """Get position IDs for the last signal in a chat"""
        query = """
            SELECT p.position_id
            FROM positions p
            INNER JOIN signals s ON p.signal_id = s.id
            WHERE s.telegram_message_chatid = ?
            ORDER BY p.id DESC
            LIMIT 2
        """
        results = self.repository.execute_query(query, (chat_id,))
        return [result[0] for result in results]

    def get_last_signal_positions_by_chat_and_message(self, chat_id: int, message_id: int) -> List[int]:
        """Get position IDs for a specific signal by chat and message"""
        query = """
            SELECT p.position_id
            FROM positions p
            INNER JOIN signals s ON p.signal_id = s.id
            WHERE s.telegram_message_chatid = ? AND s.telegram_message_id = ?
            ORDER BY p.id DESC
            LIMIT 2
        """
        results = self.repository.execute_query(query, (chat_id, message_id))
        return [result[0] for result in results]

    def get_tp_levels(self, position_id: int) -> Optional[List[float]]:
        """Get take profit levels for a position"""
        query = """
            SELECT s.tp_list
            FROM positions p
            INNER JOIN signals s ON p.signal_id = s.id
            WHERE p.position_id = ?
        """
        results = self.repository.execute_query(query, (position_id,))
        if not results:
            return None
        return [float(x) for x in results[0][0].split(',')]

    def get_all_positions(self) -> List[PositionModel]:
        """Get all positions"""
        results = self.repository.get_all()
        return [PositionModel.from_tuple(result) for result in results]


# Global instance for backward compatibility
position_repo = PositionRepository()