# app/main.py
import importlib
import logging
import boto3  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List

from app.api.routes import extraction, schedules, health, config
from app.core.config import get_settings
from app.services.registry import ExtractorRegistry
from app.services.orchestrator import ExtractionOrchestrator
from app.cloud.base import CloudProvider
from app.cloud.aws_session import AWSSession
from app.cloud.azure_session import AzureSession
from app.cloud.gcp_session import GCPSession

from app.api.routes.extraction import custom_openapi

# Ensure transports register themselves with the factory
importlib.import_module("app.transport.http_transport")
importlib.import_module("app.transport.filesystem")
importlib.import_module("app.transport.console")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress Azure SDK HTTP logging that includes Response headers
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global instances
scheduler = AsyncIOScheduler()
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global orchestrator

    # Get settings inside the context manager to allow patching in tests
    settings = get_settings()
    # Startup
    logger.info("Starting Cloud Artifact Extractor")

    # Initialize database if enabled
    if settings.database_enabled:
        logger.info("Initializing database...")
        try:
            from app.models.database import init_database, get_db_manager

            init_database(settings.database_url)
            db_manager = get_db_manager()
            if db_manager.is_database_available():
                logger.info("Database initialized and available")
            else:
                logger.warning(
                    "Database initialized but not accessible - config features will be limited"
                )
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("Database features will not be available")
            # Don't fail startup if DB is optional

    # Initialize cloud sessions based on enabled providers
    sessions: Dict[CloudProvider, Any] = {}

    # Initialize AWS if enabled (multi-account)
    if settings.is_aws_enabled:
        logger.info("Initializing AWS sessions for multiple accounts...")
        aws_sessions = []
        try:
            for aws_acc in settings.aws_accounts_list:
                account_id = aws_acc.get("account_id")
                regions = aws_acc.get("regions", [])
                # Credentials can be global or per-account (extend as needed)
                boto_session = boto3.Session(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=regions[0] if regions else None,
                )
                aws_sessions.append(
                    {
                        "session": AWSSession(boto_session),
                        "account_id": account_id,
                        "regions": regions,
                    }
                )
            if aws_sessions:
                sessions[CloudProvider.AWS] = aws_sessions
                logger.info(f"Initialized {len(aws_sessions)} AWS sessions.")
            else:
                logger.warning("No valid AWS accounts found in config.")
        except Exception as e:
            logger.error(f"Failed to initialize AWS sessions: {e}")
            logger.warning("AWS extractors will not be available")

    # Initialize Azure if enabled (multi-subscription)
    if settings.is_azure_enabled:
        logger.info("Initializing Azure sessions for multiple subscriptions...")
        azure_sessions = []
        try:
            for az_acc in settings.azure_accounts_list:
                subscription_id = az_acc.get("subscription_id")
                locations = az_acc.get("locations", [])
                azure_session = AzureSession(
                    subscription_id=subscription_id or "",
                    tenant_id=settings.azure_tenant_id,
                    client_id=settings.azure_client_id,
                    client_secret=settings.azure_client_secret,
                )
                azure_sessions.append(
                    {
                        "session": azure_session,
                        "subscription_id": subscription_id,
                        "locations": locations,
                    }
                )
            if azure_sessions:
                sessions[CloudProvider.AZURE] = azure_sessions
                logger.info(f"Initialized {len(azure_sessions)} Azure sessions.")
            else:
                logger.warning("No valid Azure subscriptions found in config.")
        except Exception as e:
            logger.error(f"Failed to initialize Azure sessions: {e}")
            logger.warning("Azure extractors will not be available")

    # Initialize GCP if enabled (multi-project)
    if settings.is_gcp_enabled:
        logger.info("Initializing GCP sessions for multiple projects...")
        gcp_sessions = []
        try:
            for gcp_proj in settings.gcp_projects_list:
                project_id = gcp_proj.get("project_id")
                regions = gcp_proj.get("regions", [])
                if not project_id:
                    logger.warning("Missing project_id in GCP config entry, skipping.")
                    continue
                gcp_session = GCPSession(
                    project_id=project_id,
                    credentials_path=settings.gcp_credentials_path,
                )
                gcp_sessions.append(
                    {
                        "session": gcp_session,
                        "project_id": project_id,
                        "regions": regions,
                    }
                )
            if gcp_sessions:
                sessions[CloudProvider.GCP] = gcp_sessions
                logger.info(f"Initialized {len(gcp_sessions)} GCP sessions.")
            else:
                logger.warning("No valid GCP projects found in config.")
        except Exception as e:
            logger.error(f"Failed to initialize GCP sessions: {e}")
            logger.warning("GCP extractors will not be available")

    enabled_requested: List[CloudProvider] = [
        provider
        for provider, enabled in (
            (CloudProvider.AWS, settings.is_aws_enabled),
            (CloudProvider.AZURE, settings.is_azure_enabled),
            (CloudProvider.GCP, settings.is_gcp_enabled),
        )
        if enabled
    ]

    if not sessions:
        if enabled_requested:
            logger.warning(
                "Cloud providers are enabled but have no valid account configurations: %s\n"
                "Please configure accounts/subscriptions/projects via the configuration API or environment variables.",
                ", ".join(provider.name for provider in enabled_requested),
            )
        else:
            logger.warning(
                "No cloud providers enabled at startup. Configuration can be updated via API."
            )

    # Initialize components
    registry = ExtractorRegistry(sessions, settings)

    # Create orchestrator without transport - transport will be created lazily when needed
    orchestrator = ExtractionOrchestrator(
        registry=registry, transport=None, config=settings.orchestrator_config
    )

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")

    # Restore schedules from database if enabled
    if settings.database_enabled:
        try:
            from app.models.database import get_db_manager
            from apscheduler.triggers.cron import CronTrigger

            db_manager = get_db_manager()
            db_schedules = db_manager.list_schedules(active_only=True)

            for schedule_data in db_schedules:
                if not schedule_data.get("paused", False):
                    try:
                        trigger = CronTrigger.from_crontab(
                            schedule_data["cron_expression"]
                        )
                        scheduler.add_job(
                            orchestrator.run_extraction,
                            trigger=trigger,
                            id=schedule_data["id"],
                            name=schedule_data["name"],
                            kwargs={
                                "services": schedule_data.get("services"),
                                "regions": schedule_data.get("regions"),
                                "filters": schedule_data.get("filters"),
                                "batch_size": schedule_data.get("batch_size", 100),
                            },
                            replace_existing=True,
                        )
                        logger.info(
                            f"Restored schedule '{schedule_data['name']}' from database"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to restore schedule '{schedule_data.get('name')}': {e}"
                        )

            logger.info(f"Restored {len(db_schedules)} schedules from database")
        except Exception as e:
            logger.warning(f"Failed to restore schedules from database: {e}")

    # Store in app state
    app.state.orchestrator = orchestrator
    app.state.scheduler = scheduler
    app.state.registry = registry

    yield

    # Shutdown
    logger.info("Shutting down")
    scheduler.shutdown()

    # Cleanup orchestrator resources (including transport)
    if orchestrator:
        await orchestrator.cleanup()


# Custom FastAPI subclass to override openapi method


class CustomOpenAPIFastAPI(FastAPI):
    def openapi(self):
        return custom_openapi(self)


app = CustomOpenAPIFastAPI(
    title="Cloud Artifact Extractor",
    description="Extract AWS and Azure cloud artifacts and send to policy scanner",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware - allowing all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers with versioned API prefix
app.include_router(extraction.router, prefix="/api/v1/extraction", tags=["extraction"])  # type: ignore[attr-defined]
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["schedules"])  # type: ignore[attr-defined]
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])  # type: ignore[attr-defined]
app.include_router(health.router, tags=["health"])  # Register at root level, no prefix


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint used by tests and health checks."""
    return {
        "service": "Cloud Artifact Extractor",
        "version": "1.0.0",
        "status": "running",
    }
