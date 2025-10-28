# app/main.py
import importlib
import logging
import boto3  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Any

from app.api.routes import extraction, schedules, health
from app.core.config import get_settings
from app.services.registry import ExtractorRegistry
from app.services.orchestrator import ExtractionOrchestrator
from app.transport.base import TransportFactory

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

    # Initialize AWS session
    session = boto3.Session(
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

    # Initialize components
    registry = ExtractorRegistry(session, settings)

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
    description="Extract AWS cloud artifacts and send to policy scanner",
    version="1.0.0",
    lifespan=lifespan,
)

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
