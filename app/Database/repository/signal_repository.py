"""Signal repository for database operations on trading signals"""

from typing import List, Dict, Optional, Any
from loguru import logger
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
            FROM Signals s
            INNER JOIN Positions p ON p.signal_id = s.id
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
            FROM Signals
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
            "provider": result[1],
            "signal_type": result[2],
            "telegram_channel_title": result[3],
            "telegram_message_id": result[4],
            "telegram_message_chatid": result[5],
            "open_price": result[6],
            "second_price": result[7],
            "stop_loss": result[8],
            "tp_list": result[9],
            "symbol": result[10],
            "current_time": result[11]
        }

    def get_last_record(self, open_price: float, second_price: Optional[float],
                       stop_loss: float, symbol: str) -> Optional[SignalModel]:
        """Get the last matching signal record"""
        query = """
            SELECT *
            FROM Signals
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

    def get_active_signals(self) -> List[Dict]:
        """Get all active signals with linked positions"""
        query = """
            SELECT DISTINCT
                s.id,
                s.provider,
                s.signal_type,
                s.telegram_channel_title,
                s.telegram_message_id,
                s.telegram_message_chatid as chat_id,
                s.open_price,
                s.second_price,
                s.stop_loss,
                s.tp_list,
                s.symbol,
                s.current_time as created_at
            FROM Signals s
            INNER JOIN Positions p ON p.signal_id = s.id
            ORDER BY s.id DESC
        """
        results = self.repository.execute_query(query)
        if not results:
            return []

        signals = []
        for result in results:
            signals.append({
                "id": result[0],
                "provider": result[1],
                "signal_type": result[2],
                "telegram_channel_title": result[3],
                "message_id": result[4],
                "chat_id": result[5],
                "open_price": result[6],
                "second_price": result[7],
                "stop_loss": result[8],
                "take_profits": result[9],
                "symbol": result[10],
                "created_at": result[11]
            })
        return signals

    def get_all_signals_paginated(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get all signals with pagination"""
        query = """
            SELECT
                s.id,
                s.provider,
                s.signal_type,
                s.telegram_channel_title,
                s.telegram_message_id,
                s.telegram_message_chatid as chat_id,
                s.open_price,
                s.second_price,
                s.stop_loss,
                s.tp_list,
                s.symbol,
                s.current_time as created_at
            FROM Signals s
            ORDER BY s.id DESC
            LIMIT ? OFFSET ?
        """
        results = self.repository.execute_query(query, (limit, offset))
        if not results:
            return []

        signals = []
        for result in results:
            signals.append({
                "id": result[0],
                "provider": result[1],
                "signal_type": result[2],
                "telegram_channel_title": result[3],
                "message_id": result[4],
                "chat_id": result[5],
                "open_price": result[6],
                "second_price": result[7],
                "stop_loss": result[8],
                "take_profits": result[9],
                "symbol": result[10],
                "created_at": result[11]
            })
        return signals

    def get_distinct_channels(self) -> List[Dict[str, str]]:
        """Get list of distinct channels with signals"""
        query = """
            SELECT DISTINCT
                telegram_channel_title,
                provider,
                telegram_message_chatid
            FROM Signals
            WHERE telegram_channel_title IS NOT NULL
            ORDER BY telegram_channel_title
        """
        results = self.repository.execute_query(query)
        if not results:
            return []

        channels = []
        for result in results:
            channels.append({
                "channel_name": result[0],
                "provider": result[1] if result[1] else "telegram",
                "chat_id": result[2]
            })
        return channels

    def get_position_ids_by_channel(
        self,
        channel_name: str
    ) -> List[int]:
        """
        Get all position IDs linked to a specific channel

        Args:
            channel_name: Name of the Telegram channel

        Returns:
            List of position IDs
        """
        # Debug query: show signal_id and channel for each position
        debug_query = """
            SELECT p.position_id, s.id as signal_id, s.telegram_channel_title
            FROM Positions p
            INNER JOIN Signals s ON p.signal_id = s.id
            WHERE s.telegram_channel_title = ?
            ORDER BY p.position_id DESC
        """
        debug_results = self.repository.execute_query(debug_query, (channel_name,))

        logger.debug(f"[DB] Query for channel '{channel_name}' returned {len(debug_results) if debug_results else 0} results:")
        if debug_results:
            for row in debug_results:
                logger.debug(f"  Position ID: {row[0]}, Signal ID: {row[1]}, Channel: {row[2]}")

        query = """
            SELECT DISTINCT p.position_id
            FROM Positions p
            INNER JOIN Signals s ON p.signal_id = s.id
            WHERE s.telegram_channel_title = ?
            ORDER BY p.position_id DESC
        """
        results = self.repository.execute_query(query, (channel_name,))
        if not results:
            return []

        return [result[0] for result in results if result[0]]


# Global instance for backward compatibility
signal_repo = SignalRepository()