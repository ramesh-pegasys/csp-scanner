# app/models/database.py
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    JSON,
    DateTime,
    func,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os
from typing import Optional, Dict, Any, cast

Base = declarative_base()


class ConfigEntry(Base):
    """Database model for storing configuration entries as JSON."""

    __tablename__ = "csp_scanner_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DatabaseManager:
    """Manager for database operations."""

    def __init__(self, database_url: Optional[str] = None):
        if not database_url:
            database_url = os.getenv(
                "DATABASE_URL", "postgresql://localhost/csp_scanner"
            )

        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create tables if they don't exist
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Ensure database tables exist, creating them if necessary."""
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            # Log the error but don't fail - the application can still run without DB
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create database tables: {e}")
            logger.info("Application will continue without database functionality")

    def is_database_available(self) -> bool:
        """Check if the database is accessible."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def get_config_value(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a configuration value by key from the global config."""
        global_config = self.get_global_config()
        return global_config.get(key) if global_config else None

    def set_config_value(
        self, key: str, value: Dict[str, Any], description: Optional[str] = None
    ):
        """Set or update a configuration value in the global config."""
        global_config = self.get_global_config() or {}
        global_config[key] = value
        self.set_global_config(global_config)

    def delete_config_value(self, key: str) -> bool:
        """Delete a configuration value by key from the global config."""
        global_config = self.get_global_config()
        if global_config and key in global_config:
            del global_config[key]
            self.set_global_config(global_config)
            return True
        return False

    def get_all_config(self) -> Dict[str, Dict[str, Any]]:
        """Get all configuration entries from the global config."""
        global_config = self.get_global_config()
        return global_config if global_config else {}

    def get_global_config(self) -> Optional[Dict[str, Any]]:
        """Get the global configuration JSON."""
        with self.get_session() as session:
            entry = (
                session.query(ConfigEntry)
                .filter(ConfigEntry.key == "global_config")
                .first()
            )
            return cast(Dict[str, Any], entry.value) if entry else None

    def set_global_config(self, config: Dict[str, Any]):
        """Set the global configuration JSON."""
        with self.get_session() as session:
            entry = (
                session.query(ConfigEntry)
                .filter(ConfigEntry.key == "global_config")
                .first()
            )
            if entry:
                entry.value = config  # type: ignore
            else:
                entry = ConfigEntry(
                    key="global_config",
                    value=config,
                    description="Global application configuration",
                )
                session.add(entry)
            session.commit()

    def close(self):
        """Close the database connection."""
        self.engine.dispose()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(database_url: Optional[str] = None):
    """Initialize the database and create tables."""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.create_tables()
