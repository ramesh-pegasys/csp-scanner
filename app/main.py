# app/main.py
import importlib
import logging
import boto3  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Any, Dict

from app.api.routes import extraction, schedules, health
from app.core.config import get_settings
from app.services.registry import ExtractorRegistry
from app.services.orchestrator import ExtractionOrchestrator
from app.transport.base import TransportFactory
from app.cloud.base import CloudProvider, CloudSession
from app.cloud.aws_session import AWSSession
from app.cloud.azure_session import AzureSession
from app.cloud.gcp_session import GCPSession

# Ensure transports register themselves with the factory
importlib.import_module("app.transport.http_transport")
importlib.import_module("app.transport.filesystem")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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

    # Initialize cloud sessions based on enabled providers
    sessions: Dict[CloudProvider, CloudSession] = {}

    # Initialize AWS if enabled
    if settings.is_aws_enabled:
        logger.info("Initializing AWS session...")
        boto_session = boto3.Session(
            aws_access_key_id=(
                settings.aws_access_key_id
                if hasattr(settings, "aws_access_key_id")
                else None
            ),
            aws_secret_access_key=(
                settings.aws_secret_access_key
                if hasattr(settings, "aws_secret_access_key")
                else None
            ),
            region_name=(
                settings.aws_default_region
                if hasattr(settings, "aws_default_region")
                else None
            ),
        )
        sessions[CloudProvider.AWS] = AWSSession(boto_session)
        logger.info("AWS session initialized")

    # Initialize Azure if enabled
    if settings.is_azure_enabled:
        logger.info("Initializing Azure session...")
        try:
            azure_session = AzureSession(
                subscription_id=settings.azure_subscription_id or "",
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
            )
            sessions[CloudProvider.AZURE] = azure_session
            logger.info("Azure session initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Azure session: {e}")
            logger.warning("Azure extractors will not be available")

    # Initialize GCP if enabled
    if settings.is_gcp_enabled:
        logger.info("Initializing GCP session...")
        try:
            gcp_session = GCPSession(
                project_id=settings.gcp_project_id or "",
                credentials_path=settings.gcp_credentials_path,
            )
            sessions[CloudProvider.GCP] = gcp_session
            logger.info("GCP session initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GCP session: {e}")
            logger.warning("GCP extractors will not be available")

    if not sessions:
        logger.error("No cloud providers enabled! Check your configuration.")
        raise RuntimeError("At least one cloud provider must be enabled")

    # Initialize components
    registry = ExtractorRegistry(sessions, settings)

    # Create transport based on configuration
    transport: Any = TransportFactory.create(
        settings.transport_type, settings.transport_config
    )

    orchestrator = ExtractionOrchestrator(
        registry=registry, transport=transport, config=settings.orchestrator_config
    )

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")

    # Store in app state
    app.state.orchestrator = orchestrator
    app.state.scheduler = scheduler
    app.state.registry = registry

    yield

    # Shutdown
    logger.info("Shutting down")
    scheduler.shutdown()

    # Close transport if it has a close method (HTTP transport), otherwise disconnect
    if hasattr(transport, "close"):
        await transport.close()
    elif hasattr(transport, "disconnect"):
        await transport.disconnect()


# Create FastAPI app
app = FastAPI(  # type: ignore[assignment]
    title="Cloud Artifact Extractor",
    description="Extract AWS and Azure cloud artifacts and send to policy scanner",
    version="2.0.0",
    lifespan=lifespan,
)

# Include routes
app.include_router(extraction.router)
app.include_router(schedules.router)
app.include_router(health.router)

# Include routers
app.include_router(extraction.router, prefix="/api/v1/extraction", tags=["extraction"])  # type: ignore[attr-defined]
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["schedules"])  # type: ignore[attr-defined]
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])  # type: ignore[attr-defined]


@app.get("/")  # type: ignore[attr-defined]
async def root():
    return {
        "service": "Cloud Artifact Extractor",
        "version": "1.0.0",
        "status": "running",
    }
