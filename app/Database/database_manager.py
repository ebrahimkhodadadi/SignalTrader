"""Database manager for initialization and migrations"""

from typing import Optional
from loguru import logger
from .repository.signal_repository import SignalRepository
from .repository.position_repository import PositionRepository
from Configure.settings.Settings import Settings

class DatabaseManager:
    """Manages database initialization and migrations"""

    def __init__(self, db_path: str = "signaltrader.db", config=None):
        self.db_path = db_path
        self.config = config

        # Check cache settings using the new Settings class
        disable_cache = Settings.disable_cache()

        # Initialize repositories with cache settings
        enable_cache = not disable_cache
        self.signal_repo = SignalRepository(db_path, enable_cache=enable_cache)
        self.position_repo = PositionRepository(db_path, enable_cache=enable_cache)

    def initialize_database(self) -> None:
        """Initialize database tables"""
        try:
            logger.info("Initializing database tables...")
            self.signal_repo.create_table()
            self.position_repo.create_table()
            logger.success("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def run_migrations(self) -> None:
        """Run database migrations (alias for initialize_database)"""
        self.initialize_database()

    def get_signal_repository(self) -> SignalRepository:
        """Get signal repository instance"""
        return self.signal_repo

    def get_position_repository(self) -> PositionRepository:
        """Get position repository instance"""
        return self.position_repo


# Global instance for backward compatibility
db_manager = DatabaseManager()

# Backward compatibility functions
def DoMigrations(config=None):
    """Legacy function for running migrations"""
    if config:
        # Reinitialize with config if provided
        global db_manager
        db_manager = DatabaseManager(config=config)
    db_manager.run_migrations()

# Global repositories for backward compatibility
signal_repo = db_manager.signal_repo.repository
position_repo = db_manager.position_repo.repository