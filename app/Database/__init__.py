"""
Database module for SignalTrader

Provides database operations for signals and positions with both
modern repository pattern and legacy compatibility.
"""

from .database_manager import DatabaseManager, db_manager
from .repository.signal_repository import SignalRepository, signal_repo
from .repository.position_repository import PositionRepository, position_repo
from .models import SignalModel, PositionModel, DatabaseSchema
from .repository.Repository import SQLiteRepository

# Legacy imports for backward compatibility
from .Migrations import *

__all__ = [
    # Modern classes
    'DatabaseManager',
    'SignalRepository',
    'PositionRepository',
    'SignalModel',
    'PositionModel',
    'DatabaseSchema',
    'SQLiteRepository',

    # Global instances
    'db_manager',
    'signal_repo',
    'position_repo',

    # Legacy functions (from Migrations)
    'DoMigrations',
    'get_tp_levels',
    'get_last_signal_positions_by_chatid',
    'get_last_signal_positions_by_chatid_and_messageid',
    'get_last_record',
    'get_signal_by_positionId',
    'get_signal_positions_by_positionId',
    'get_positions_by_signalid',
    'get_position_by_signal_id',
    'get_signal_by_chat',
    'get_signal_by_id',
    'update_stoploss',
    'update_takeProfits'
]
