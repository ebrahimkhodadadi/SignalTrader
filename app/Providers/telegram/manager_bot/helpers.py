"""
Helper utilities for database queries and signal/position lookups
"""

from typing import Optional
from loguru import logger
from Database.database_manager import db_manager


def find_signal_by_ticket(ticket: int) -> Optional[object]:
    """Find signal linked to MT5 ticket from database"""
    try:
        position_repo = db_manager.get_position_repository()
        db_position = position_repo.get_position_by_ticket(ticket)

        if not db_position:
            return None

        signal_id = db_position.signal_id if hasattr(db_position, 'signal_id') else db_position.get("signal_id")

        signal_repo = db_manager.get_signal_repository()
        signal = signal_repo.get_signal_by_id(signal_id)
        return signal
    except Exception as e:
        logger.error(f"Error finding signal by ticket: {e}")
        return None


def get_position_for_signal(meta_trader, signal_id: int) -> Optional[object]:
    """Get MT5 position linked to a signal"""
    try:
        position_repo = db_manager.get_position_repository()
        db_position = position_repo.get_position_by_signal_id(signal_id)

        if not db_position:
            return None

        ticket = db_position.position_id if hasattr(db_position, 'position_id') else db_position.get("position_id")
        mt5_position = meta_trader.get_position_by_ticket(ticket) if meta_trader else None

        return mt5_position
    except Exception as e:
        logger.error(f"Error getting position for signal: {e}")
        return None
