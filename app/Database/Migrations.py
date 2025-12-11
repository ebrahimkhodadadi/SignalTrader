"""
Database migrations and legacy compatibility layer

This module provides backward compatibility for existing code
while using the new modular database architecture.
"""

from .database_manager import db_manager, DoMigrations as _DoMigrations
from .repository.signal_repository import signal_repo as _signal_repo
from .repository.position_repository import position_repo as _position_repo

# Legacy global variables for backward compatibility
db_path = "signaltrader.db"
signal_columns = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "telegram_channel_title": "TEXT NOT NULL",
    "telegram_message_id": "INTEGER",
    "telegram_message_chatid": "INTEGER",
    "open_price": "REAL NOT NULL",
    "second_price": "REAL",
    "stop_loss": "REAL NOT NULL",
    "tp_list": "TEXT NOT NULL",
    "symbol": "TEXT NOT NULL",
    "current_time": "TEXT NOT NULL"
}
position_columns = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "signal_id": "INTEGER NOT NULL",
    "position_id": "INTEGER NOT NULL",
    "user_id": "INTEGER NOT NULL",
    "is_first": "BOOLEAN NULL",
    "is_second": "BOOLEAN NULL",
    "FOREIGN KEY(signal_id)": "REFERENCES Signals(id) ON DELETE CASCADE"
}

# Legacy repository instances
signal_repo = _signal_repo.repository
position_repo = _position_repo.repository

# Legacy migration function
def DoMigrations(config=None):
    """Legacy migration function"""
    _DoMigrations(config)


# Legacy query functions for backward compatibility
def get_tp_levels(ticket_id):
    """Read Take Profit values from the database"""
    return _position_repo.get_tp_levels(ticket_id)


def get_last_signal_positions_by_chatid(chat_id):
    """Read last signal positions from the database"""
    return _position_repo.get_last_signal_positions_by_chat_id(chat_id)


def get_last_signal_positions_by_chatid_and_messageid(chat_id, message_id):
    """Read last signal positions from the database"""
    return _position_repo.get_last_signal_positions_by_chat_and_message(chat_id, message_id)


def get_last_record(open_price, second_price, stop_loss, symbol):
    """Get last matching signal record"""
    return _signal_repo.get_last_record(open_price, second_price, stop_loss, symbol)


def get_signal_by_positionId(ticket_id):
    """Get signal by position ID"""
    signal = _signal_repo.get_signal_by_position_id(ticket_id)
    return signal.to_dict() if signal else None


def get_signal_positions_by_positionId(ticket_id):
    """Get signal positions by position ID"""
    positions = _position_repo.get_signal_positions_by_position_id(ticket_id)
    return [pos.to_dict() for pos in positions]


def get_positions_by_signalid(signal_id):
    """Get positions by signal ID"""
    positions = _position_repo.get_positions_by_signal_id(signal_id)
    return [pos.to_dict() for pos in positions]


def get_position_by_signal_id(signal_id, first=False, second=False):
    """Get position by signal ID with filters"""
    position = _position_repo.get_position_by_signal_id(signal_id, first, second)
    return position.to_dict() if position else None


def get_signal_by_chat(chat_id, message_id):
    """Get signal by chat and message ID"""
    return _signal_repo.get_signal_by_chat(chat_id, message_id)


def get_signal_by_id(signal_id):
    """Get signal by ID"""
    signal = _signal_repo.get_signal_by_id(signal_id)
    return signal.to_dict() if signal else None


def update_stoploss(signal_id, stoploss):
    """Update stop loss for signal"""
    _signal_repo.update_stop_loss(signal_id, stoploss)


def update_takeProfits(signal_id, takeProfits):
    """Update take profits for signal"""
    _signal_repo.update_take_profits(signal_id, takeProfits)


def get_active_signals():
    """Get all active signals with linked positions"""
    return _signal_repo.get_active_signals()


def get_all_signals(limit=50):
    """Get all signals with pagination"""
    return _signal_repo.get_all_signals_paginated(limit=limit, offset=0)


def get_active_positions_with_details():
    """Get all active positions with signal details and P&L"""
    return _position_repo.get_active_positions_with_signals()


def get_positions_by_signal(signal_id):
    """Get all positions for a specific signal"""
    return _position_repo.get_positions_by_signal_id_with_details(signal_id)


def get_signal(signal_id):
    """Get signal by ID"""
    signal = _signal_repo.get_signal_by_id(signal_id)
    return signal.to_dict() if signal else None
