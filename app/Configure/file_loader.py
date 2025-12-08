"""
File Loading Service

This module provides a centralized file loading service with multi-path search capability.
It follows the Single Responsibility Principle by handling all file discovery and loading operations.

Features:
- Multi-path search for configuration files
- JSON file loading with error handling
- Flexible path configuration
- Comprehensive logging
"""

import json
import os
from typing import Dict, List, Any, Optional, Union
from loguru import logger


class FileLoaderService:
    """Centralized service for loading files with multi-path search capability"""

    def __init__(self, search_paths: Optional[List[str]] = None):
        """
        Initialize file loader service

        Args:
            search_paths: List of paths to search for files (defaults to standard paths)
        """
        if search_paths is None:
            self.search_paths = self._get_default_search_paths()
        else:
            self.search_paths = search_paths

    def _get_default_search_paths(self) -> List[str]:
        """
        Get default search paths for configuration files

        Returns:
            List of paths to search in order of preference
        """
        # Get the project root directory
        module_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(module_dir))

        # Get current working directory
        current_dir = os.getcwd()

        # Possible config directory names and locations
        return [
            current_dir,                               # Current working directory (highest priority)
            os.path.join(current_dir, "config"),       # cwd/config/
            os.path.join(current_dir, "configs"),      # cwd/configs/
            os.path.join(current_dir, "settings"),     # cwd/settings/
            os.path.join(project_root, "config"),      # project_root/config/
            os.path.join(project_root, "configs"),     # project_root/configs/
            os.path.join(project_root, "settings"),    # project_root/settings/
            project_root,                              # project_root/ (files directly in root)
        ]

    def find_file(self, filename: str) -> Optional[str]:
        """
        Find a file in the search paths

        Args:
            filename: Name of the file to find

        Returns:
            Full path to the file if found, None otherwise
        """
        for path in self.search_paths:
            file_path = os.path.join(path, filename)
            if os.path.isfile(file_path):
                return file_path
        return None

    def load_json_file(self, filename: str, default_value: Any = None) -> Optional[Dict[str, Any]]:
        """
        Load a JSON file from the search paths

        Args:
            filename: Name of the JSON file to load
            default_value: Value to return if file not found or invalid

        Returns:
            Parsed JSON data or default_value if file not found/invalid
        """
        file_path = self.find_file(filename)

        if not file_path:
            logger.warning(f"File '{filename}' not found in any search path")
            return default_value

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Successfully loaded '{filename}' from {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON file '{filename}': {e}")
            return default_value
        except Exception as e:
            logger.error(f"Error loading file '{filename}': {e}")
            return default_value

    def load_text_file(self, filename: str, default_value: str = "") -> str:
        """
        Load a text file from the search paths

        Args:
            filename: Name of the text file to load
            default_value: Value to return if file not found

        Returns:
            File contents as string or default_value if not found
        """
        file_path = self.find_file(filename)

        if not file_path:
            logger.warning(f"Text file '{filename}' not found in any search path")
            return default_value

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(f"Successfully loaded text file '{filename}' from {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error loading text file '{filename}': {e}")
            return default_value

    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in any of the search paths

        Args:
            filename: Name of the file to check

        Returns:
            True if file exists, False otherwise
        """
        return self.find_file(filename) is not None

    def get_search_paths(self) -> List[str]:
        """
        Get the current search paths

        Returns:
            List of search paths
        """
        return self.search_paths.copy()

    def add_search_path(self, path: str):
        """
        Add a new search path (inserted at the beginning for higher priority)

        Args:
            path: Path to add to search list
        """
        if path not in self.search_paths:
            self.search_paths.insert(0, path)
            logger.debug(f"Added search path: {path}")

    def set_search_paths(self, paths: List[str]):
        """
        Set the search paths list

        Args:
            paths: New list of search paths
        """
        self.search_paths = paths.copy()
        logger.debug(f"Updated search paths: {self.search_paths}")


# Global file loader instance
_file_loader = None


def get_file_loader() -> FileLoaderService:
    """Get global file loader instance"""
    global _file_loader
    if _file_loader is None:
        _file_loader = FileLoaderService()
    return _file_loader


def load_json_config(filename: str, default_value: Any = None) -> Optional[Dict[str, Any]]:
    """Convenience function to load JSON config files"""
    return get_file_loader().load_json_file(filename, default_value)


def load_text_file(filename: str, default_value: str = "") -> str:
    """Convenience function to load text files"""
    return get_file_loader().load_text_file(filename, default_value)


def find_config_file(filename: str) -> Optional[str]:
    """Convenience function to find config files"""
    return get_file_loader().find_file(filename)