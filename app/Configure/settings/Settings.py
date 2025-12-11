"""Configuration management for SignalTrader with safe property access"""

import os
from typing import Any, Dict, Optional, List
from loguru import logger
from config import config_from_json
from dotenv import load_dotenv
from ..file_loader import get_file_loader


class SafeConfig:
    """Provides safe access to configuration properties with defaults"""

    def __init__(self, config_data=None):
        self._config = config_data or {}
        self._defaults = self._get_defaults()

    def _get_defaults(self) -> Dict[str, Any]:
        """Define default values for all configuration properties"""
        return {
            # Telegram defaults
            'telegram_api_id': 0,
            'telegram_api_hash': '',
            'telegram_channels_whitelist': [],
            'telegram_channels_blacklist': [],

            # Notification defaults
            'notification_token': '',
            'notification_chat_id': 0,

            # Main config defaults
            'disable_cache': False,

            # MetaTrader defaults
            'mt_server': '',
            'mt_username': 0,
            'mt_password': '',
            'mt_path': os.path.join(os.getcwd(), 'terminal64.exe'),
            'mt_lot': '1%',
            'mt_high_risk': False,
            'mt_save_profits': [25, 25, 25, 25],
            'mt_account_size': None,
            'mt_closer_price': 0.0,
            'mt_expire_pending_orders_minutes': None,
            'mt_close_positions_on_trail': True,
            'mt_symbol_mappings': {},
            'mt_symbols_whitelist': [],
            'mt_symbols_blacklist': [],

            # Timer defaults
            'timer_start': None,
            'timer_end': None,
        }

    def _get_nested_value(self, *keys, default=None):
        """Safely get nested configuration value"""
        current = self._config
        try:
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key, {})
                elif hasattr(current, key):
                    current = getattr(current, key, {})
                else:
                    return default
            return current if current != {} else default
        except (AttributeError, KeyError, TypeError):
            return default

    # Telegram properties (check new providers structure first, then legacy)
    @property
    def telegram_api_id(self) -> int:
        # Try new structure first (providers.telegram)
        val = self._get_nested_value('providers', 'telegram', 'api_id')
        if not val:
            # Fall back to legacy structure
            val = self._get_nested_value('Telegram', 'api_id')
        return val or self._defaults['telegram_api_id']

    @property
    def telegram_api_hash(self) -> str:
        # Try new structure first (providers.telegram)
        val = self._get_nested_value('providers', 'telegram', 'api_hash')
        if not val:
            # Fall back to legacy structure
            val = self._get_nested_value('Telegram', 'api_hash')
        return val or self._defaults['telegram_api_hash']

    @property
    def telegram_channels_whitelist(self) -> List[str]:
        # Try new structure first (providers.telegram.channels)
        val = self._get_nested_value('providers', 'telegram', 'channels', 'whiteList')
        if not val:
            # Fall back to legacy structure
            val = self._get_nested_value('Telegram', 'channels', 'whiteList')
        return val or self._defaults['telegram_channels_whitelist']

    @property
    def telegram_channels_blacklist(self) -> List[str]:
        # Try new structure first (providers.telegram.channels)
        val = self._get_nested_value('providers', 'telegram', 'channels', 'blackList')
        if not val:
            # Fall back to legacy structure
            val = self._get_nested_value('Telegram', 'channels', 'blackList')
        return val or self._defaults['telegram_channels_blacklist']

    # Notification properties
    @property
    def notification_token(self) -> str:
        return self._get_nested_value('Notification', 'token') or self._defaults['notification_token']

    @property
    def notification_chat_id(self) -> int:
        return self._get_nested_value('Notification', 'chatId') or self._defaults['notification_chat_id']

    # MetaTrader properties
    @property
    def mt_server(self) -> str:
        return self._get_nested_value('MetaTrader', 'server') or self._defaults['mt_server']

    @property
    def mt_username(self) -> int:
        return self._get_nested_value('MetaTrader', 'username') or self._defaults['mt_username']

    @property
    def mt_password(self) -> str:
        return self._get_nested_value('MetaTrader', 'password') or self._defaults['mt_password']

    @property
    def mt_path(self) -> str:
        path = self._get_nested_value('MetaTrader', 'path') or self._defaults['mt_path']
        if not path or not os.path.exists(path):
            current_dir = os.getcwd()
            default_path = os.path.join(current_dir, 'terminal64.exe')
            if os.path.exists(default_path):
                return default_path
        return path

    @property
    def mt_lot(self) -> str:
        return self._get_nested_value('MetaTrader', 'lot') or self._defaults['mt_lot']

    @property
    def mt_high_risk(self) -> bool:
        result = self._get_nested_value('MetaTrader', 'HighRisk')
        return result if result is not None else self._defaults['mt_high_risk']

    @property
    def mt_save_profits(self) -> List[int]:
        return self._get_nested_value('MetaTrader', 'SaveProfits') or self._defaults['mt_save_profits']

    @property
    def mt_account_size(self) -> Optional[float]:
        return self._get_nested_value('MetaTrader', 'AccountSize') or self._defaults['mt_account_size']

    @property
    def mt_closer_price(self) -> float:
        result = self._get_nested_value('MetaTrader', 'CloserPrice')
        return result if result is not None else self._defaults['mt_closer_price']

    @property
    def mt_expire_pending_orders_minutes(self) -> Optional[int]:
        return self._get_nested_value('MetaTrader', 'expirePendinOrderInMinutes') or self._defaults['mt_expire_pending_orders_minutes']

    @property
    def mt_close_positions_on_trail(self) -> bool:
        result = self._get_nested_value('MetaTrader', 'ClosePositionsOnTrail')
        return result if result is not None else self._defaults['mt_close_positions_on_trail']

    @property
    def mt_symbol_mappings(self) -> Dict[str, str]:
        return self._get_nested_value('MetaTrader', 'SymbolMappings') or self._defaults['mt_symbol_mappings']

    @property
    def mt_symbols_whitelist(self) -> List[str]:
        return self._get_nested_value('MetaTrader', 'symbols', 'whiteList') or self._defaults['mt_symbols_whitelist']

    @property
    def mt_symbols_blacklist(self) -> List[str]:
        return self._get_nested_value('MetaTrader', 'symbols', 'blackList') or self._defaults['mt_symbols_blacklist']

    # Main config properties
    @property
    def disable_cache(self) -> bool:
        result = self._get_nested_value('disableCache')
        return result if result is not None else self._defaults['disable_cache']

    # Timer properties
    @property
    def timer_start(self) -> Optional[str]:
        return self._get_nested_value('Timer', 'start') or self._defaults['timer_start']

    @property
    def timer_end(self) -> Optional[str]:
        return self._get_nested_value('Timer', 'end') or self._defaults['timer_end']

    # Legacy compatibility properties
    @property
    def Providers(self):
        """Access providers configuration (Telegram, Discord, etc.)"""
        return self._get_nested_value('providers', {})

    @property
    def Telegram(self):
        """Telegram config access (from providers section)"""
        class TelegramConfig:
            def __init__(self, parent):
                self._parent = parent
                providers = parent._get_nested_value('providers', {})
                telegram_config = providers.get('telegram', {}) if isinstance(providers, dict) else {}
                if not telegram_config:
                    telegram_config = parent._get_nested_value('Telegram', {})
                
                self.api_id = telegram_config.get('api_id') if isinstance(telegram_config, dict) else getattr(telegram_config, 'api_id', parent.telegram_api_id)
                self.api_hash = telegram_config.get('api_hash') if isinstance(telegram_config, dict) else getattr(telegram_config, 'api_hash', parent.telegram_api_hash)
                
            @property
            def channels(self):
                class ChannelsConfig:
                    def __init__(self, parent):
                        self._parent = parent
                        self.whiteList = parent.telegram_channels_whitelist
                        self.blackList = parent.telegram_channels_blacklist
                return ChannelsConfig(self._parent)
        return TelegramConfig(self)

    @property
    def Notification(self):
        """Legacy Notification config access"""
        class NotificationConfig:
            def __init__(self, parent):
                self.token = parent.notification_token
                self.chatId = parent.notification_chat_id
        return NotificationConfig(self)

    @property
    def MetaTrader(self):
        """Legacy MetaTrader config access"""
        class MetaTraderConfig:
            def __init__(self, parent):
                self._parent = parent
                self.server = parent.mt_server
                self.username = parent.mt_username
                self.password = parent.mt_password
                self.path = parent.mt_path
                self.lot = parent.mt_lot
                self.HighRisk = parent.mt_high_risk
                self.SaveProfits = parent.mt_save_profits
                self.AccountSize = parent.mt_account_size
                self.CloserPrice = parent.mt_closer_price
                self.expirePendinOrderInMinutes = parent.mt_expire_pending_orders_minutes
                self.ClosePositionsOnTrail = parent.mt_close_positions_on_trail
                self.SymbolMappings = parent.mt_symbol_mappings
                
            @property
            def symbols(self):
                class SymbolsConfig:
                    def __init__(self, parent):
                        self._parent = parent
                        self.whiteList = parent.mt_symbols_whitelist
                        self.blackList = parent.mt_symbols_blacklist
                return SymbolsConfig(self._parent)
        return MetaTraderConfig(self)

    @property
    def Timer(self):
        """Legacy Timer config access"""
        class TimerConfig:
            def __init__(self, parent):
                self.start = parent.timer_start
                self.end = parent.timer_end
        return TimerConfig(self)

    @property
    def Discord(self):
        """Discord provider config access (from providers section)"""
        class DiscordConfig:
            def __init__(self, parent):
                self._parent = parent
                providers = parent._get_nested_value('providers', {})
                discord_config = providers.get('discord', {}) if isinstance(providers, dict) else {}
                if not discord_config:
                    discord_config = parent._get_nested_value('Discord', {})
                
                self.bot_token = discord_config.get('bot_token') if isinstance(discord_config, dict) else getattr(discord_config, 'bot_token', None)
                self.channel_ids = (discord_config.get('channel_ids') if isinstance(discord_config, dict) else getattr(discord_config, 'channel_ids', [])) or []
                self.mention_mode = (discord_config.get('mention_mode') if isinstance(discord_config, dict) else getattr(discord_config, 'mention_mode', False)) or False
        return DiscordConfig(self)

    @property
    def TelegramBot(self):
        """Telegram Bot (manager) config access from providers section"""
        class TelegramBotConfig:
            def __init__(self, parent):
                self._parent = parent
                # Access raw config to get providers -> telegram_bot
                raw_config = parent._config
                providers = raw_config.get('providers', {}) if isinstance(raw_config, dict) else {}
                tg_bot_config = providers.get('telegram_bot', {}) if isinstance(providers, dict) else {}
                
                # Extract values directly from the dict
                self.enabled = tg_bot_config.get('enabled', True) if isinstance(tg_bot_config, dict) else True
                self.bot_token = tg_bot_config.get('bot_token') if isinstance(tg_bot_config, dict) else None
                self.allowed_users = tg_bot_config.get('allowed_users', []) if isinstance(tg_bot_config, dict) else []
                self.button_labels = tg_bot_config.get('button_labels', {}) if isinstance(tg_bot_config, dict) else {}
        return TelegramBotConfig(self)


class SettingsManager:
    """Static settings manager for global access"""

    _instance: Optional[SafeConfig] = None

    @classmethod
    def get_instance(cls) -> SafeConfig:
        """Get singleton instance of settings"""
        if cls._instance is None:
            raw_config = cls._load_raw_config()
            cls._instance = SafeConfig(raw_config)
            logger.info("Configuration loaded successfully")
        return cls._instance

    @classmethod
    def reload(cls):
        """Force reload configuration"""
        cls._instance = None
        return cls.get_instance()

    @classmethod
    def _load_raw_config(cls):
        """Load raw configuration from file using FileLoaderService"""
        # Load environment variables
        load_dotenv()

        # Get file loader service (use override if set for testing)
        if hasattr(cls, '_file_loader_override'):
            file_loader = cls._file_loader_override
        else:
            file_loader = get_file_loader()

        # Determine configuration file name based on environment
        config_filename = cls._get_config_filename()

        # Try to load the configuration file
        config_data = file_loader.load_json_file(config_filename)

        if config_data is None:
            error_msg = f"Configuration file '{config_filename}' not found in any search path. The application cannot run without a valid settings file. Please create a settings file and try again."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Load and parse configuration
        logger.info(f"Configuration loaded successfully from '{config_filename}'")
        return config_data

    @classmethod
    def _get_config_filename(cls) -> str:
        """Determine the configuration filename based on environment"""
        env = os.getenv("ENV", "").lower()

        if env == "development":
            return "development.json"
        elif env == "production":
            return "production.json"
        else:
            # Default to settings.json
            return "settings.json"

    # Static method accessors (these call the instance)
    @classmethod
    def telegram_api_id(cls) -> int:
        return cls.get_instance().telegram_api_id

    @classmethod
    def telegram_api_hash(cls) -> str:
        return cls.get_instance().telegram_api_hash

    @classmethod
    def telegram_channels_whitelist(cls) -> List[str]:
        return cls.get_instance().telegram_channels_whitelist

    @classmethod
    def telegram_channels_blacklist(cls) -> List[str]:
        return cls.get_instance().telegram_channels_blacklist

    @classmethod
    def notification_token(cls) -> str:
        return cls.get_instance().notification_token

    @classmethod
    def notification_chat_id(cls) -> int:
        return cls.get_instance().notification_chat_id

    @classmethod
    def mt_server(cls) -> str:
        return cls.get_instance().mt_server

    @classmethod
    def mt_username(cls) -> int:
        return cls.get_instance().mt_username

    @classmethod
    def mt_password(cls) -> str:
        return cls.get_instance().mt_password

    @classmethod
    def mt_path(cls) -> str:
        return cls.get_instance().mt_path

    @classmethod
    def mt_lot(cls) -> str:
        return cls.get_instance().mt_lot

    @classmethod
    def mt_high_risk(cls) -> bool:
        return cls.get_instance().mt_high_risk

    @classmethod
    def mt_save_profits(cls) -> List[int]:
        return cls.get_instance().mt_save_profits

    @classmethod
    def mt_account_size(cls) -> Optional[float]:
        return cls.get_instance().mt_account_size

    @classmethod
    def mt_closer_price(cls) -> float:
        return cls.get_instance().mt_closer_price

    @classmethod
    def mt_expire_pending_orders_minutes(cls) -> Optional[int]:
        return cls.get_instance().mt_expire_pending_orders_minutes

    @classmethod
    def mt_close_positions_on_trail(cls) -> bool:
        return cls.get_instance().mt_close_positions_on_trail

    @classmethod
    def mt_symbol_mappings(cls) -> Dict[str, str]:
        return cls.get_instance().mt_symbol_mappings

    @classmethod
    def mt_symbols_whitelist(cls) -> List[str]:
        return cls.get_instance().mt_symbols_whitelist

    @classmethod
    def mt_symbols_blacklist(cls) -> List[str]:
        return cls.get_instance().mt_symbols_blacklist

    @classmethod
    def disable_cache(cls) -> bool:
        return cls.get_instance().disable_cache

    @classmethod
    def timer_start(cls) -> Optional[str]:
        return cls.get_instance().timer_start

    @classmethod
    def timer_end(cls) -> Optional[str]:
        return cls.get_instance().timer_end


# Create module-level aliases for backward compatibility
Settings = SettingsManager

# Global instance for easy access
settings = SettingsManager.get_instance()

# Backward compatibility functions
@logger.catch
def GetSettings():
    """Legacy function for backward compatibility"""
    return SettingsManager.get_instance()