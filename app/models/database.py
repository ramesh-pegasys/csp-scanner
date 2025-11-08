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


class ExtractionJob(Base):
    """Database model for storing extraction job information."""

    __tablename__ = "csp_scanner_extraction_jobs"

    id = Column(String(255), primary_key=True)  # UUID
    status = Column(
        String(50), nullable=False, index=True
    )  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    services = Column(JSON, nullable=False)  # List of services
    regions = Column(JSON, nullable=True)  # List of regions
    filters = Column(JSON, nullable=True)  # Filter parameters
    batch_size = Column(Integer, nullable=False, default=100)
    total_artifacts = Column(Integer, nullable=False, default=0)
    successful_artifacts = Column(Integer, nullable=False, default=0)
    failed_artifacts = Column(Integer, nullable=False, default=0)
    errors = Column(JSON, nullable=True)  # List of error messages
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Schedule(Base):
    """Database model for storing extraction schedules."""

    __tablename__ = "csp_scanner_schedules"

    id = Column(String(255), primary_key=True)  # Schedule name/ID
    name = Column(String(255), nullable=False, index=True)
    cron_expression = Column(String(100), nullable=False)
    services = Column(JSON, nullable=True)  # List of services
    regions = Column(JSON, nullable=True)  # List of regions
    filters = Column(JSON, nullable=True)  # Filter parameters
    batch_size = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    paused = Column(Boolean, nullable=False, default=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
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
        self,
        config: Dict[str, Any],
        description: Optional[str] = None,
        set_active: bool = True,
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
        from app.core.config import mask_sensitive_config

        # Mask sensitive values before storing
        masked_config = mask_sensitive_config(config)

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

            # Create new version with masked config
            new_config = ConfigVersion(
                version=next_version,
                config=masked_config,
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
                    "created_at": (
                        v.created_at.isoformat() if v.created_at is not None else None
                    ),
                    "updated_at": (
                        v.updated_at.isoformat() if v.updated_at is not None else None
                    ),
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

    # Extraction Job Methods

    def create_job(
        self,
        job_id: str,
        services: List[str],
        regions: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
    ) -> str:
        """
        Create a new extraction job in the database.

        Args:
            job_id: Unique job identifier (UUID)
            services: List of services to extract
            regions: Optional list of regions
            filters: Optional filter parameters
            batch_size: Batch size for processing

        Returns:
            The job ID
        """
        from datetime import datetime, timezone

        with self.get_session() as session:
            job = ExtractionJob(
                id=job_id,
                status="running",
                started_at=datetime.now(timezone.utc),
                services=services,
                regions=regions,
                filters=filters,
                batch_size=batch_size,
                errors=[],
            )
            session.add(job)
            session.commit()
            return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID.

        Args:
            job_id: The job ID

        Returns:
            Job data dictionary or None if not found
        """
        with self.get_session() as session:
            job = (
                session.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
            )
            if not job:
                return None

            return {
                "id": job.id,
                "status": job.status,
                "started_at": (
                    job.started_at.isoformat() if job.started_at is not None else None
                ),
                "completed_at": (
                    job.completed_at.isoformat()
                    if job.completed_at is not None
                    else None
                ),
                "services": job.services,
                "regions": job.regions,
                "filters": job.filters,
                "batch_size": job.batch_size,
                "total_artifacts": job.total_artifacts,
                "successful_artifacts": job.successful_artifacts,
                "failed_artifacts": job.failed_artifacts,
                "errors": job.errors or [],
            }

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        completed_at: Optional[Any] = None,
        total_artifacts: Optional[int] = None,
        successful_artifacts: Optional[int] = None,
        failed_artifacts: Optional[int] = None,
        errors: Optional[List[str]] = None,
    ) -> bool:
        """
        Update a job's fields.

        Args:
            job_id: The job ID
            status: New status
            completed_at: Completion timestamp
            total_artifacts: Total artifact count
            successful_artifacts: Successful artifact count
            failed_artifacts: Failed artifact count
            errors: List of error messages

        Returns:
            True if successful, False if job not found
        """
        with self.get_session() as session:
            job = (
                session.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
            )
            if not job:
                return False

            if status is not None:
                job.status = status  # type: ignore
            if completed_at is not None:
                job.completed_at = completed_at  # type: ignore
            if total_artifacts is not None:
                job.total_artifacts = total_artifacts  # type: ignore
            if successful_artifacts is not None:
                job.successful_artifacts = successful_artifacts  # type: ignore
            if failed_artifacts is not None:
                job.failed_artifacts = failed_artifacts  # type: ignore
            if errors is not None:
                job.errors = errors  # type: ignore

            session.commit()
            return True

    def list_jobs(
        self, limit: int = 100, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List extraction jobs.

        Args:
            limit: Maximum number of jobs to return
            status: Optional status filter

        Returns:
            List of job dictionaries
        """
        from sqlalchemy import desc

        with self.get_session() as session:
            query = session.query(ExtractionJob)

            if status:
                query = query.filter(ExtractionJob.status == status)

            jobs = query.order_by(desc(ExtractionJob.started_at)).limit(limit).all()

            return [
                {
                    "id": j.id,
                    "status": j.status,
                    "started_at": (
                        j.started_at.isoformat() if j.started_at is not None else None
                    ),
                    "completed_at": (
                        j.completed_at.isoformat()
                        if j.completed_at is not None
                        else None
                    ),
                    "services": j.services,
                    "regions": j.regions,
                    "filters": j.filters,
                    "batch_size": j.batch_size,
                    "total_artifacts": j.total_artifacts,
                    "successful_artifacts": j.successful_artifacts,
                    "failed_artifacts": j.failed_artifacts,
                    "errors": j.errors or [],
                }
                for j in jobs
            ]

    def delete_old_jobs(self, days: int = 30) -> int:
        """
        Delete jobs older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of jobs deleted
        """
        from datetime import datetime, timezone, timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        with self.get_session() as session:
            result = (
                session.query(ExtractionJob)
                .filter(ExtractionJob.started_at < cutoff_date)
                .delete()
            )
            session.commit()
            return result

    # Schedule Methods

    def create_schedule(
        self,
        schedule_id: str,
        name: str,
        cron_expression: str,
        services: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
        description: Optional[str] = None,
    ) -> str:
        """
        Create a new extraction schedule.

        Args:
            schedule_id: Unique schedule identifier
            name: Schedule name
            cron_expression: Cron expression for scheduling
            services: Optional list of services
            regions: Optional list of regions
            filters: Optional filter parameters
            batch_size: Batch size for processing
            description: Optional description

        Returns:
            The schedule ID
        """
        with self.get_session() as session:
            schedule = Schedule(
                id=schedule_id,
                name=name,
                cron_expression=cron_expression,
                services=services,
                regions=regions,
                filters=filters,
                batch_size=batch_size,
                description=description,
                is_active=True,
                paused=False,
            )
            session.add(schedule)
            session.commit()
            return schedule_id

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a schedule by ID.

        Args:
            schedule_id: The schedule ID

        Returns:
            Schedule data dictionary or None if not found
        """
        with self.get_session() as session:
            schedule = (
                session.query(Schedule).filter(Schedule.id == schedule_id).first()
            )
            if not schedule:
                return None

            return {
                "id": schedule.id,
                "name": schedule.name,
                "cron_expression": schedule.cron_expression,
                "services": schedule.services,
                "regions": schedule.regions,
                "filters": schedule.filters,
                "batch_size": schedule.batch_size,
                "is_active": schedule.is_active,
                "paused": schedule.paused,
                "last_run_at": (
                    schedule.last_run_at.isoformat()
                    if schedule.last_run_at is not None
                    else None
                ),
                "next_run_at": (
                    schedule.next_run_at.isoformat()
                    if schedule.next_run_at is not None
                    else None
                ),
                "description": schedule.description,
                "created_at": (
                    schedule.created_at.isoformat()
                    if schedule.created_at is not None
                    else None
                ),
                "updated_at": (
                    schedule.updated_at.isoformat()
                    if schedule.updated_at is not None
                    else None
                ),
            }

    def update_schedule(
        self,
        schedule_id: str,
        name: Optional[str] = None,
        cron_expression: Optional[str] = None,
        services: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        is_active: Optional[bool] = None,
        paused: Optional[bool] = None,
        last_run_at: Optional[Any] = None,
        next_run_at: Optional[Any] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        Update a schedule's fields.

        Args:
            schedule_id: The schedule ID
            name: New name
            cron_expression: New cron expression
            services: New services list
            regions: New regions list
            filters: New filters
            batch_size: New batch size
            is_active: Active status
            paused: Paused status
            last_run_at: Last run timestamp
            next_run_at: Next run timestamp
            description: New description

        Returns:
            True if successful, False if schedule not found
        """
        with self.get_session() as session:
            schedule = (
                session.query(Schedule).filter(Schedule.id == schedule_id).first()
            )
            if not schedule:
                return False

            if name is not None:
                schedule.name = name  # type: ignore
            if cron_expression is not None:
                schedule.cron_expression = cron_expression  # type: ignore
            if services is not None:
                schedule.services = services  # type: ignore
            if regions is not None:
                schedule.regions = regions  # type: ignore
            if filters is not None:
                schedule.filters = filters  # type: ignore
            if batch_size is not None:
                schedule.batch_size = batch_size  # type: ignore
            if is_active is not None:
                schedule.is_active = is_active  # type: ignore
            if paused is not None:
                schedule.paused = paused  # type: ignore
            if last_run_at is not None:
                schedule.last_run_at = last_run_at  # type: ignore
            if next_run_at is not None:
                schedule.next_run_at = next_run_at  # type: ignore
            if description is not None:
                schedule.description = description  # type: ignore

            session.commit()
            return True

    def list_schedules(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all schedules.

        Args:
            active_only: If True, only return active schedules

        Returns:
            List of schedule dictionaries
        """
        with self.get_session() as session:
            query = session.query(Schedule)

            if active_only:
                query = query.filter(Schedule.is_active == True)  # noqa: E712

            schedules = query.order_by(Schedule.name).all()

            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "cron_expression": s.cron_expression,
                    "services": s.services,
                    "regions": s.regions,
                    "filters": s.filters,
                    "batch_size": s.batch_size,
                    "is_active": s.is_active,
                    "paused": s.paused,
                    "last_run_at": (
                        s.last_run_at.isoformat() if s.last_run_at is not None else None
                    ),
                    "next_run_at": (
                        s.next_run_at.isoformat() if s.next_run_at is not None else None
                    ),
                    "description": s.description,
                    "created_at": (
                        s.created_at.isoformat() if s.created_at is not None else None
                    ),
                    "updated_at": (
                        s.updated_at.isoformat() if s.updated_at is not None else None
                    ),
                }
                for s in schedules
            ]

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: The schedule ID

        Returns:
            True if successful, False if schedule not found
        """
        with self.get_session() as session:
            schedule = (
                session.query(Schedule).filter(Schedule.id == schedule_id).first()
            )
            if not schedule:
                return False

            session.delete(schedule)
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
