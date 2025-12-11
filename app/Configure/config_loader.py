"""
Configuration loader for JSON-based settings

This module loads configuration from JSON files and provides easy access
to customizable keywords and regex patterns.
"""

from typing import Dict, List, Any, Union, Optional
from loguru import logger
from .file_loader import get_file_loader
from .settings.Settings import Settings


class ConfigLoader:
    """Loads and manages JSON configuration files"""

    def __init__(self, config_dir: str = None):
        """
        Initialize config loader

        Args:
            config_dir: Directory containing configuration files (optional, uses FileLoaderService)
        """
        self.file_loader = get_file_loader()

        # If a specific config directory is provided, add it with higher priority
        if config_dir is not None:
            self.file_loader.add_search_path(config_dir)

        self._keywords_config = None
        self._regex_config = None
        self._load_configurations()
    
    def _load_configurations(self):
        """Load all configuration files"""
        self._load_keywords_config()
        self._load_regex_config()
    
    def _load_keywords_config(self):
        """Load keywords configuration from JSON file using FileLoaderService"""
        self._keywords_config = self.file_loader.load_json_file("keywords.json")

    def _load_regex_config(self):
        """Load regex patterns configuration from JSON file using FileLoaderService"""
        self._regex_config = self.file_loader.load_json_file("regex_patterns.json")
    
    def get_keywords(self) -> Dict[str, List[str]]:
        """Get all message command keywords"""
        if self._keywords_config:
            return self._keywords_config.get("message_commands", {})
        return {}
    
    def get_keyword_list(self, keyword_type: str) -> List[str]:
        """Get specific keyword list"""
        keywords = self.get_keywords()
        return keywords.get(keyword_type, [])
    
    def get_regex_patterns(self) -> Dict[str, Any]:
        """Get all regex patterns configuration"""
        if self._regex_config:
            return self._regex_config.get("price_extraction_patterns", {})
        return {}
    
    def reload_configurations(self):
        """Reload all configuration files"""
        logger.info("Reloading configuration files...")
        self._load_configurations()
    
    @property
    def edit_keywords(self) -> List[str]:
        """Get edit command keywords"""
        return self.get_keyword_list("edit_keywords")
    
    @property
    def delete_keywords(self) -> List[str]:
        """Get delete command keywords"""
        return self.get_keyword_list("delete_keywords")
    
    @property
    def risk_free_keywords(self) -> List[str]:
        """Get risk-free command keywords"""
        return self.get_keyword_list("risk_free_keywords")
    
    @property
    def tp_keywords(self) -> List[str]:
        """Get take profit command keywords"""
        return self.get_keyword_list("tp_keywords")


# Global configuration loader instance
_config_loader = None


def get_config_loader() -> ConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_keywords() -> Dict[str, List[str]]:
    """Get all keywords configuration"""
    return get_config_loader().get_keywords()


def get_keyword_list(keyword_type: str) -> List[str]:
    """Get specific keyword list"""
    return get_config_loader().get_keyword_list(keyword_type)


def get_regex_patterns() -> Dict[str, Any]:
    """Get all regex patterns configuration"""
    return get_config_loader().get_regex_patterns()


def reload_configs():
    """Reload all configurations"""
    get_config_loader().reload_configurations()


# Settings helpers
def get_providers_cfg() -> Dict[str, Any]:
    """Return the providers configuration dict from the active settings file.

    This reads via `Settings` (SafeConfig) so it respects ENV and search paths.
    Example keys: `telegram`, `discord`, `telegram_bot`.
    """
    try:
        providers = Settings.get_instance().Providers
        return providers if isinstance(providers, dict) else {}
    except Exception:
        return {}