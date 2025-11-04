# app/models/database.py
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    JSON,
    DateTime,
    Boolean,
    func,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os
from typing import Optional, Dict, Any, cast, List

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


class ConfigVersion(Base):
    """Database model for storing versioned configuration with active/inactive status."""

    __tablename__ = "csp_scanner_config_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, nullable=False, index=True)
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DatabaseManager:
    """Manager for database operations."""

    def __init__(self, database_url: Optional[str] = None):
        if not database_url:
            # Construct from CSP_SCANNER_ prefixed components
            db_host = os.getenv("CSP_SCANNER_DATABASE_HOST", "localhost")
            db_port = os.getenv("CSP_SCANNER_DATABASE_PORT", "5432")
            db_name = os.getenv("CSP_SCANNER_DATABASE_NAME", "csp_scanner")
            db_user = os.getenv("CSP_SCANNER_DATABASE_USER")
            db_password = os.getenv("CSP_SCANNER_DATABASE_PASSWORD")
            
            if db_user and db_password:
                database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            else:
                database_url = f"postgresql://{db_host}:{db_port}/{db_name}"

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

    # Versioned Configuration Methods
    
    def create_config_version(
        self, config: Dict[str, Any], description: Optional[str] = None, set_active: bool = True
    ) -> int:
        """
        Create a new configuration version.
        
        Args:
            config: Configuration dictionary
            description: Optional description for this version
            set_active: If True, set this version as active and deactivate others
            
        Returns:
            The version number of the created configuration
        """
        from sqlalchemy import desc
        
        with self.get_session() as session:
            # Get the next version number
            last_version = (
                session.query(ConfigVersion)
                .order_by(desc(ConfigVersion.version))
                .first()
            )
            next_version = last_version.version + 1 if last_version else 1  # type: ignore
            
            # If setting as active, deactivate all other versions
            if set_active:
                session.query(ConfigVersion).update({"is_active": False})
            
            # Create new version
            new_config = ConfigVersion(
                version=next_version,
                config=config,
                is_active=set_active,
                description=description,
            )
            session.add(new_config)
            session.commit()
            
            return next_version  # type: ignore
    
    def get_active_config(self) -> Optional[Dict[str, Any]]:
        """Get the currently active configuration."""
        with self.get_session() as session:
            active_config = (
                session.query(ConfigVersion)
                .filter(ConfigVersion.is_active == True)  # noqa: E712
                .first()
            )
            return cast(Dict[str, Any], active_config.config) if active_config else None
    
    def get_config_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Get a specific configuration version."""
        with self.get_session() as session:
            config = (
                session.query(ConfigVersion)
                .filter(ConfigVersion.version == version)
                .first()
            )
            return cast(Dict[str, Any], config.config) if config else None
    
    def list_config_versions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all configuration versions with metadata."""
        from sqlalchemy import desc
        
        with self.get_session() as session:
            versions = (
                session.query(ConfigVersion)
                .order_by(desc(ConfigVersion.version))
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "id": v.id,
                    "version": v.version,
                    "is_active": v.is_active,
                    "description": v.description,
                    "created_at": v.created_at.isoformat(),
                    "updated_at": v.updated_at.isoformat(),
                    "config": v.config,
                }
                for v in versions
            ]
    
    def activate_config_version(self, version: int) -> bool:
        """
        Activate a specific configuration version.
        
        Args:
            version: The version number to activate
            
        Returns:
            True if successful, False if version not found
        """
        with self.get_session() as session:
            # Check if version exists
            target_config = (
                session.query(ConfigVersion)
                .filter(ConfigVersion.version == version)
                .first()
            )
            
            if not target_config:
                return False
            
            # Deactivate all versions
            session.query(ConfigVersion).update({"is_active": False})
            
            # Activate target version
            target_config.is_active = True  # type: ignore
            target_config.updated_at = func.now()  # type: ignore
            
            session.commit()
            return True
    
    def delete_config_version(self, version: int) -> bool:
        """
        Delete a specific configuration version.
        Cannot delete the active version.
        
        Args:
            version: The version number to delete
            
        Returns:
            True if successful, False if version not found or is active
        """
        with self.get_session() as session:
            config = (
                session.query(ConfigVersion)
                .filter(ConfigVersion.version == version)
                .first()
            )
            
            if not config:
                return False
            
            if config.is_active:  # type: ignore
                # Cannot delete active version
                return False
            
            session.delete(config)
            session.commit()
            return True


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
