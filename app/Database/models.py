"""Database models and schema definitions for SignalTrader"""

from typing import Dict


class DatabaseSchema:
    """Database schema definitions"""

    # Signals table schema
    SIGNAL_COLUMNS = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "provider": "TEXT NOT NULL DEFAULT 'telegram'",
        "signal_type": "TEXT NOT NULL DEFAULT 'BUY'",
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

    # Positions table schema
    POSITION_COLUMNS = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "signal_id": "INTEGER NOT NULL",
        "position_id": "INTEGER NOT NULL",
        "user_id": "INTEGER NOT NULL",
        "is_first": "BOOLEAN NULL",
        "is_second": "BOOLEAN NULL",
        "FOREIGN KEY(signal_id)": "REFERENCES Signals(id) ON DELETE CASCADE"
    }


class SignalModel:
    """Signal data model"""

    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.provider = data.get('provider', 'telegram')
        self.signal_type = data.get('signal_type', 'BUY')
        self.telegram_channel_title = data.get('telegram_channel_title')
        self.telegram_message_id = data.get('telegram_message_id')
        self.telegram_message_chatid = data.get('telegram_message_chatid')
        self.open_price = data.get('open_price')
        self.second_price = data.get('second_price')
        self.stop_loss = data.get('stop_loss')
        self.tp_list = data.get('tp_list')
        self.symbol = data.get('symbol')
        self.current_time = data.get('current_time')

    @classmethod
    def from_tuple(cls, data_tuple: tuple) -> 'SignalModel':
        """Create SignalModel from database tuple"""
        return cls({
            "id": data_tuple[0],
            "provider": data_tuple[1],
            "signal_type": data_tuple[2],
            "telegram_channel_title": data_tuple[3],
            "telegram_message_id": data_tuple[4],
            "telegram_message_chatid": data_tuple[5],
            "open_price": data_tuple[6],
            "second_price": data_tuple[7],
            "stop_loss": data_tuple[8],
            "tp_list": data_tuple[9],
            "symbol": data_tuple[10],
            "current_time": data_tuple[11]
        })

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "provider": self.provider,
            "signal_type": self.signal_type,
            "telegram_channel_title": self.telegram_channel_title,
            "telegram_message_id": self.telegram_message_id,
            "telegram_message_chatid": self.telegram_message_chatid,
            "open_price": self.open_price,
            "second_price": self.second_price,
            "stop_loss": self.stop_loss,
            "tp_list": self.tp_list,
            "symbol": self.symbol,
            "current_time": self.current_time
        }


class PositionModel:
    """Position data model"""

    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.signal_id = data.get('signal_id')
        self.position_id = data.get('position_id')
        self.user_id = data.get('user_id')
        self.is_first = data.get('is_first')
        self.is_second = data.get('is_second')

    @classmethod
    def from_tuple(cls, data_tuple: tuple) -> 'PositionModel':
        """Create PositionModel from database tuple"""
        return cls({
            "id": data_tuple[0],
            "signal_id": data_tuple[1],
            "position_id": data_tuple[2],
            "user_id": data_tuple[3],
            "is_first": data_tuple[4],
            "is_second": data_tuple[5]
        })

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "position_id": self.position_id,
            "user_id": self.user_id,
            "is_first": self.is_first,
            "is_second": self.is_second
        }