"""Logging configuration for SignalTrader"""
"""Logging configuration for SignalTrader"""

import sys
import os
from datetime import datetime
from typing import Any, Dict
from loguru import logger


class LoggerManager:
    """Manages logging configuration and setup"""

    @staticmethod
    def add_mt5_time(record: Dict[str, Any]) -> str:
        """Add MT5 server time to log records

        Args:
            record: Loguru log record

        Returns:
            MT5 time string for filtering
        """
        try:
            # Import here to avoid circular imports
            from MetaTrader import MetaTrader
            mt5_time = MetaTrader.get_mt5_time()
            record["extra"]["mt5_time"] = mt5_time.strftime("%H:%M:%S") if mt5_time else "N/A"
        except Exception:
            record["extra"]["mt5_time"] = "N/A"

        return record["extra"]["mt5_time"]

    @staticmethod
    def configure_logger() -> None:
        """Configure logging with console and file outputs

        Sets up:
        - Colored console logging
        - Daily rotating file logs
        - MT5 time integration
        - 7-day log retention
        """
        # Remove default handler
        logger.remove()

        # Configure log levels with colors
        logger.level("DEBUG", color="<blue>")
        logger.level("INFO", color="<green>")
        logger.level("SUCCESS", color="<bold green>")
        logger.level("WARNING", color="<yellow>")
        logger.level("ERROR", color="<red>")
        logger.level("CRITICAL", color="<bold red>")

        # Ensure log directory exists
        log_folder = "log"
        os.makedirs(log_folder, exist_ok=True)

        # Create daily log filename
        log_filename = datetime.now().strftime("%Y-%m-%d") + ".log"
        log_path = os.path.join(log_folder, log_filename)

        # Console handler with colors and MT5 time
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <cyan>{extra[mt5_time]}</cyan> | <level>{level: <8}</level> | <level>{message}</level>",
            filter=LoggerManager.add_mt5_time,
            enqueue=True,
            level="DEBUG"
        )

        # File handler with rotation and retention
        logger.add(
            log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | {extra[mt5_time]} | {level: <8} | {message}",
            filter=LoggerManager.add_mt5_time,
            rotation="00:00",  # Rotate at midnight
            retention="7 days",  # Keep logs for 7 days
            compression="zip",  # Compress old logs
            enqueue=True,
            level="DEBUG"
        )

        logger.success("Logger configured successfully")


# Backward compatibility function
def add_mt5_time(record):
    """Legacy function for backward compatibility"""
    return LoggerManager.add_mt5_time(record)


def ConfigLogger():
    """Legacy function for backward compatibility"""
    LoggerManager.configure_logger()
