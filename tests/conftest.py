import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
import sys
import os
import uuid

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI


@pytest.fixture
def client(mock_orchestrator, mock_registry, mock_scheduler):
    """Test client fixture"""
    from app.api.routes import extraction, schedules, health

    test_app = FastAPI(
        title="Test Cloud Artifact Extractor", description="Test API", version="1.0.0"
    )

    # Include the same routers
    test_app.include_router(
        extraction.router, prefix="/api/v1/extraction", tags=["extraction"]
    )
    test_app.include_router(
        schedules.router, prefix="/api/v1/schedules", tags=["schedules"]
    )
    test_app.include_router(health.router, prefix="/api/v1/health", tags=["health"])

    @test_app.get("/")
    async def root():
        return {
            "service": "Cloud Artifact Extractor",
            "version": "1.0.0",
            "status": "running",
        }

    test_app.state.orchestrator = mock_orchestrator
    test_app.state.registry = mock_registry
    test_app.state.scheduler = mock_scheduler
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator fixture"""
    from app.models.job import Job, JobStatus
    from datetime import datetime

    mock = Mock()
    mock.run_extraction = AsyncMock(return_value=str(uuid.uuid4()))
    mock.get_job_status = Mock(
        return_value=Job(
            id="test-job",
            status=JobStatus.COMPLETED,
            started_at=datetime(2023, 1, 1, 0, 0, 0),
            services=["s3"],
            total_artifacts=10,
            successful_artifacts=10,
            failed_artifacts=0,
            errors=[],
        )
    )
    mock.list_jobs = Mock(
        return_value=[
            Job(
                id="job1",
                status=JobStatus.COMPLETED,
                started_at=datetime(2023, 1, 1, 0, 0, 0),
                services=["s3"],
                total_artifacts=5,
                successful_artifacts=5,
                failed_artifacts=0,
                errors=[],
            )
        ]
    )
    return mock


@pytest.fixture
def mock_registry():
    """Mock registry fixture"""
    mock = Mock()
    mock.list_services = Mock(return_value=["s3", "ec2", "lambda"])
    return mock


@pytest.fixture
def mock_scheduler():
    """Mock scheduler fixture"""
    mock_job = Mock()
    mock_job.id = "schedule1"
    mock_job.name = "Daily Backup"
    mock_job.next_run_time = None

    mock = Mock()
    mock.get_jobs = Mock(return_value=[mock_job])
    mock.add_job = Mock()
    mock.remove_job = Mock()
    mock.pause_job = Mock()
    mock.resume_job = Mock()
    return mock
