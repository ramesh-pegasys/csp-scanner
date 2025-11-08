"""Tests for services"""

import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch, AsyncMock
from app.cloud.base import CloudProvider
from app.services.registry import ExtractorRegistry
from app.services.orchestrator import ExtractionOrchestrator
from app.services.scheduler import SchedulerService
from app.core.exceptions import TransportError
from app.models.job import Job, JobStatus
from datetime import datetime, timezone


@pytest.fixture
def mock_session():
    """Mock AWS session"""
    return Mock()


@pytest.fixture
def mock_config():
    """Mock configuration"""

    class ConfigMock:
        def __init__(self):
            self.extractors = {
                "aws": {"ec2": {"enabled": True}, "s3": {"enabled": True}}
            }
            self.database_enabled = False
            self.max_workers = 4
            self.batch_delay_seconds = 0.1

        def get(self, key, default=None):
            return getattr(self, key, default)

    return ConfigMock()


@pytest.fixture
def mock_transport():
    """Mock transport"""
    transport = Mock()
    transport.send = AsyncMock()
    return transport


def test_registry_initialization(mock_session, mock_config):
    """Test registry initialization"""
    with patch("app.services.registry.ExtractorRegistry._register_default_extractors"):
        registry = ExtractorRegistry(mock_session, mock_config)
        assert registry.config == mock_config
        assert isinstance(registry.sessions, dict)
        assert CloudProvider.AWS in registry.sessions
        assert isinstance(registry._extractors, dict)


def test_registry_get_extractor(mock_session, mock_config):
    """Test getting an extractor"""
    with patch("app.services.registry.ExtractorRegistry._register_default_extractors"):
        registry = ExtractorRegistry(mock_session, mock_config)
        # Manually add an extractor
        mock_extractor = Mock()
        mock_extractor.metadata.service_name = "ec2"
        registry._extractors["aws:ec2"] = mock_extractor

        extractor = registry.get("ec2")
        assert extractor == mock_extractor


def test_registry_get_nonexistent_extractor(mock_session, mock_config):
    """Test getting a non-existent extractor"""
    with patch("app.services.registry.ExtractorRegistry._register_default_extractors"):
        registry = ExtractorRegistry(mock_session, mock_config)
        extractor = registry.get("nonexistent")
        assert extractor is None


def test_registry_list_services(mock_session, mock_config):
    """Test listing services"""
    with patch("app.services.registry.ExtractorRegistry._register_default_extractors"):
        registry = ExtractorRegistry(mock_session, mock_config)
        # Manually add extractors
        mock_ec2 = Mock()
        mock_ec2.metadata.service_name = "ec2"
        registry._extractors["aws:ec2"] = mock_ec2

        mock_s3 = Mock()
        mock_s3.metadata.service_name = "s3"
        registry._extractors["aws:s3"] = mock_s3

        services = registry.list_services()
        assert "aws:ec2" in services
        assert "aws:s3" in services


def test_registry_get_extractors(mock_session, mock_config):
    """Test getting multiple extractors"""
    with patch("app.services.registry.ExtractorRegistry._register_default_extractors"):
        registry = ExtractorRegistry(mock_session, mock_config)
        # Manually add extractors
        mock_ec2 = Mock()
        mock_ec2.metadata.service_name = "ec2"
        registry._extractors["aws:ec2"] = mock_ec2

        mock_s3 = Mock()
        mock_s3.metadata.service_name = "s3"
        registry._extractors["aws:s3"] = mock_s3

        extractors = registry.get_extractors(["ec2", "s3"])
        assert len(extractors) == 2
        assert mock_ec2 in extractors
        assert mock_s3 in extractors


def test_orchestrator_initialization(mock_session, mock_config, mock_transport):
    """Test orchestrator initialization"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config=mock_config
    )

    assert orchestrator.registry is not None
    assert orchestrator.transport == mock_transport
    assert orchestrator.config == mock_config
    assert isinstance(orchestrator.jobs, dict)


def test_scheduler_initialization():
    """Test scheduler initialization"""
    scheduler = SchedulerService()
    assert scheduler.scheduler is not None


@pytest.mark.asyncio
async def test_orchestrator_run_extraction(mock_session, mock_config, mock_transport):
    """Test orchestrator run_extraction method"""
    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry, transport=mock_transport, config=mock_config
    )

    # Mock registry
    mock_extractor = Mock()
    mock_extractor.metadata.service_name = "s3"
    mock_registry.list_services.return_value = ["s3"]
    mock_registry.get_extractors.return_value = [mock_extractor]

    # Mock extractor
    mock_extractor.extract = AsyncMock(
        return_value=[{"resource_id": "bucket1", "service": "s3"}]
    )

    # Mock transport
    mock_transport.send = AsyncMock(return_value={"status": "accepted"})

    import uuid

    with patch(
        "app.services.orchestrator.uuid.uuid4",
        return_value=uuid.UUID("12345678-1234-5678-1234-567812345678"),
    ):
        job_id = await orchestrator.run_extraction(services=["s3"], batch_size=10)
        assert job_id == "12345678-1234-5678-1234-567812345678"

        # Check job was created
        assert job_id in orchestrator.jobs
        job = orchestrator.jobs[job_id]
        assert job.status == JobStatus.RUNNING
        assert job.services == ["s3"]


@pytest.mark.asyncio
async def test_orchestrator_execute_job_success(
    mock_session, mock_config, mock_transport
):
    """Test successful job execution"""
    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry, transport=mock_transport, config=mock_config
    )

    # Create a job
    job = Job(
        id="test-job",
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=["s3"],
    )

    # Mock registry and extractor
    mock_extractor = Mock()
    mock_extractor.metadata.service_name = "s3"
    mock_extractor.metadata.supports_regions = True
    mock_registry.get_extractors.return_value = [mock_extractor]
    mock_extractor.extract = AsyncMock(
        return_value=[{"resource_id": "bucket1", "service": "s3"}]
    )

    # Mock transport
    mock_transport.send = AsyncMock(return_value={"status": "accepted"})

    await orchestrator._execute_job(job, ["s3"], None, None, 10)

    assert job.status == JobStatus.COMPLETED
    assert job.total_artifacts == 1


def test_orchestrator_reinitialize_transport_replaces_transport(
    monkeypatch, mock_config
):
    """Ensure reinitializing transport closes the old transport and loads a new one."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    original_transport = Mock()
    original_transport.close = AsyncMock()

    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=original_transport, config=mock_config
    )

    new_transport = Mock()

    def _fake_create(transport_type, transport_config):
        assert transport_type == "console"
        assert transport_config == {"type": "console"}
        return new_transport

    monkeypatch.setattr(
        "app.services.orchestrator.TransportFactory.create", _fake_create
    )

    orchestrator.reinitialize_transport({"type": "console"})
    original_transport.close.assert_awaited()
    assert orchestrator.transport is new_transport

    loop.close()
    asyncio.set_event_loop(None)


def test_orchestrator_db_initialization_failure(monkeypatch, mock_config):
    """Database manager failures disable DB usage."""
    monkeypatch.setattr(
        "app.services.orchestrator.get_db_manager",
        Mock(side_effect=Exception("db init fail")),
    )
    config = {"database_enabled": True, "batch_delay_seconds": 0.0}
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=Mock(), config=config
    )
    assert orchestrator.use_db is False


def test_orchestrator_transport_lazy_initialization(monkeypatch, mock_config):
    """Lazily create transport when accessed."""

    class SettingsStub:
        transport_config = {"type": "console", "param": "value"}

    import app.services.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module, "get_settings", lambda: SettingsStub(), raising=False
    )

    created_transport = Mock()
    monkeypatch.setattr(
        "app.services.orchestrator.TransportFactory.create",
        lambda transport_type, config: created_transport,
    )

    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=None, config=mock_config
    )

    assert orchestrator.transport is created_transport


def test_orchestrator_reinitialize_transport_close_error(monkeypatch, mock_config):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    failing_transport = Mock()
    failing_transport.close = AsyncMock(side_effect=RuntimeError("close failure"))

    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=failing_transport, config=mock_config
    )

    monkeypatch.setattr(
        "app.services.orchestrator.TransportFactory.create", lambda t, c: Mock()
    )

    orchestrator.reinitialize_transport({"type": "console"})
    failing_transport.close.assert_awaited()

    loop.close()
    asyncio.set_event_loop(None)


def test_orchestrator_reinitialize_transport_disconnect_error(monkeypatch, mock_config):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    transport = SimpleNamespace(disconnect=AsyncMock(side_effect=RuntimeError("boom")))
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=transport, config=mock_config
    )

    monkeypatch.setattr(
        "app.services.orchestrator.TransportFactory.create", lambda t, c: Mock()
    )

    orchestrator.reinitialize_transport({"type": "filesystem"})
    transport.disconnect.assert_awaited()

    loop.close()
    asyncio.set_event_loop(None)


@pytest.mark.asyncio
async def test_orchestrator_send_artifacts_tracks_results(mock_config):
    success = Mock()
    failing_transport = Mock()
    failing_transport.send = AsyncMock(side_effect=[success, Exception("boom")])

    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=failing_transport, config=mock_config
    )

    job = Job(
        id="job-123",
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=["svc"],
    )

    await orchestrator._send_artifacts(
        job,
        [{"resource_id": "ok"}, {"resource_id": "bad"}],
        batch_size=1,
    )

    assert job.successful_artifacts == 1
    assert job.failed_artifacts == 1

    assert job.errors

    extractor = Mock()
    extractor.extract = AsyncMock(side_effect=[Exception("fail"), [{"id": 1}]])

    artifacts = await orchestrator._extract_service(
        extractor, ["us-west-1", "us-east-1"], filters=None
    )

    assert artifacts == [{"id": 1}]


@pytest.mark.asyncio
async def test_orchestrator_execute_job_handles_azure(mock_config):
    transport = Mock()
    transport.send = AsyncMock(return_value={"status": "ok"})

    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry, transport=transport, config=mock_config
    )

    azure_extractor = Mock()
    azure_extractor.cloud_provider = "azure"
    azure_extractor.metadata = Mock()
    azure_extractor.metadata.service_name = "azure-service"
    azure_extractor.metadata.supports_regions = True
    azure_extractor.session = Mock()
    azure_extractor.session.locations = ["eastus"]
    azure_extractor.extract = AsyncMock(return_value=[{"resource_id": "azure"}])
    mock_registry.get_extractors.return_value = [azure_extractor]

    job = Job(
        id="azure-job",
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=["azure-service"],
    )

    orchestrator.use_db = True
    orchestrator.db_manager = Mock()
    orchestrator.db_manager.update_job.side_effect = Exception("db fail")

    await orchestrator._execute_job(job, None, None, None, batch_size=5)

    azure_extractor.extract.assert_awaited()
    assert job.status == JobStatus.COMPLETED
    assert job.successful_artifacts == 1
    assert orchestrator.db_manager.update_job.called


def test_orchestrator_get_job_status_from_db(mock_config):
    config_dict = {
        "batch_delay_seconds": mock_config.batch_delay_seconds,
        "database_enabled": True,
    }
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=Mock(), config=config_dict
    )
    orchestrator.use_db = True
    orchestrator.db_manager = Mock()
    orchestrator.db_manager.get_job.return_value = {
        "id": "db-job",
        "status": "completed",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "services": ["svc"],
        "total_artifacts": 1,
        "successful_artifacts": 1,
        "failed_artifacts": 0,
        "errors": [],
    }

    job = orchestrator.get_job_status("db-job")
    assert job is not None
    assert job.status == JobStatus.COMPLETED


def test_orchestrator_list_jobs_from_db(mock_config):
    config_dict = {
        "batch_delay_seconds": mock_config.batch_delay_seconds,
        "database_enabled": True,
    }
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=Mock(), config=config_dict
    )
    orchestrator.use_db = True
    orchestrator.db_manager = Mock()
    orchestrator.db_manager.list_jobs.return_value = [
        {
            "id": "db-job",
            "status": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "services": ["svc"],
            "total_artifacts": 1,
            "successful_artifacts": 1,
            "failed_artifacts": 0,
            "errors": [],
        }
    ]

    jobs = orchestrator.list_jobs(limit=5)
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_orchestrator_cleanup_closes_transport(mock_config):
    transport = Mock()
    transport.close = AsyncMock()

    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=transport, config=mock_config
    )

    await orchestrator.cleanup()
    transport.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_cleanup_disconnects_transport(mock_config):
    transport = SimpleNamespace(disconnect=AsyncMock())

    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=transport, config=mock_config
    )

    await orchestrator.cleanup()
    transport.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_execute_job_failure(
    mock_session, mock_config, mock_transport
):
    """Test job execution with failure"""
    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry, transport=mock_transport, config=mock_config
    )

    # Create a job
    job = Job(
        id="test-job",
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=["s3"],
    )

    # Mock registry to raise exception
    mock_registry.get_extractors.side_effect = Exception("Registry error")

    await orchestrator._execute_job(job, ["s3"], None, None, 10)

    assert job.status == JobStatus.FAILED
    assert "Registry error" in job.errors[0]
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_orchestrator_execute_job_partial_failure(
    mock_session, mock_config, mock_transport
):
    """Partial extractor failure still processes remaining artifacts"""
    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry, transport=mock_transport, config=mock_config
    )

    job = Job(
        id="partial-job",
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=["ec2"],
    )

    extractor_a = Mock()
    extractor_b = Mock()
    mock_registry.get_extractors.return_value = [extractor_a, extractor_b]
    orchestrator._extract_service = AsyncMock(
        side_effect=[Exception("extract fail"), [{"resource_id": "good"}]]
    )
    orchestrator._send_artifacts = AsyncMock()

    await orchestrator._execute_job(job, ["ec2"], None, None, 5)

    assert any("extract fail" in error for error in job.errors)
    assert job.total_artifacts == 1
    orchestrator._send_artifacts.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_extract_service_single_region(
    mock_session, mock_config, mock_transport
):
    """Test extracting from a service in a single region"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config=mock_config
    )

    mock_extractor = Mock()
    mock_extractor.metadata.supports_regions = True
    mock_extractor.extract = AsyncMock(return_value=[{"resource_id": "bucket1"}])

    artifacts = await orchestrator._extract_service(mock_extractor, ["us-east-1"], None)

    assert len(artifacts) == 1
    assert artifacts[0]["resource_id"] == "bucket1"
    mock_extractor.extract.assert_called_once_with("us-east-1", None)


@pytest.mark.asyncio
async def test_orchestrator_extract_service_multiple_regions(
    mock_session, mock_config, mock_transport
):
    """Test extracting from a service in multiple regions"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config=mock_config
    )

    mock_extractor = Mock()
    mock_extractor.metadata.supports_regions = True
    mock_extractor.extract = AsyncMock(
        side_effect=[[{"resource_id": "bucket1"}], [{"resource_id": "bucket2"}]]
    )

    artifacts = await orchestrator._extract_service(
        mock_extractor, ["us-east-1", "us-west-2"], None
    )

    assert len(artifacts) == 2
    assert mock_extractor.extract.call_count == 2


@pytest.mark.asyncio
async def test_orchestrator_extract_service_region_errors(
    mock_session, mock_config, mock_transport
):
    """Extraction continues when a region fails"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config=mock_config
    )

    mock_extractor = Mock()
    mock_extractor.metadata.supports_regions = True
    mock_extractor.extract = AsyncMock(
        side_effect=[Exception("boom"), [{"resource_id": "bucket-ok"}]]
    )

    artifacts = await orchestrator._extract_service(
        mock_extractor, ["us-east-1", "us-west-2"], None
    )

    assert len(artifacts) == 1
    assert artifacts[0]["resource_id"] == "bucket-ok"


@pytest.mark.asyncio
async def test_orchestrator_send_artifacts(mock_session, mock_config, mock_transport):
    """Test sending artifacts in batches"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config={"batch_delay_seconds": 0.01}
    )

    job = Job(
        id="test-job",
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=["s3"],
    )

    artifacts = [{"resource_id": f"bucket{i}", "service": "s3"} for i in range(5)]

    mock_transport.send = AsyncMock(return_value={"status": "accepted"})

    await orchestrator._send_artifacts(job, artifacts, 2)

    assert mock_transport.send.call_count == 5
    assert job.successful_artifacts == 5
    assert job.failed_artifacts == 0


@pytest.mark.asyncio
async def test_orchestrator_send_artifacts_handles_errors(
    mock_session, mock_config, mock_transport
):
    """Send failures are captured in job metrics"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config={"batch_delay_seconds": 0.0}
    )

    job = Job(
        id="job-send",
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=["s3"],
    )
    artifacts = [
        {"resource_id": "one", "service": "s3"},
        {"resource_id": "two", "service": "s3"},
    ]

    mock_transport.send = AsyncMock(
        side_effect=[TransportError("send fail"), {"status": "accepted"}]
    )

    await orchestrator._send_artifacts(job, artifacts, 2)

    assert job.failed_artifacts == 1
    assert job.successful_artifacts == 1
    assert any("send fail" in error for error in job.errors)


def test_orchestrator_get_job_status(mock_session, mock_config, mock_transport):
    """Test getting job status"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config=mock_config
    )

    job = Job(
        id="test-job",
        status=JobStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        services=["s3"],
    )
    orchestrator.jobs["test-job"] = job

    result = orchestrator.get_job_status("test-job")
    assert result == job

    result = orchestrator.get_job_status("non-existent")
    assert result is None


def test_orchestrator_get_job_status_db_exception(mock_config):
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=Mock(), config={"database_enabled": True}
    )
    orchestrator.use_db = True
    orchestrator.db_manager = Mock()
    orchestrator.db_manager.get_job.side_effect = RuntimeError("db unavailable")

    assert orchestrator.get_job_status("db-job") is None


def test_orchestrator_list_jobs(mock_session, mock_config, mock_transport):
    """Test listing jobs"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=mock_transport, config=mock_config
    )

    # Create jobs with different timestamps
    job1 = Job(
        id="job1",
        status=JobStatus.COMPLETED,
        started_at=datetime(2023, 1, 2),
        services=["s3"],
    )
    job2 = Job(
        id="job2",
        status=JobStatus.RUNNING,
        started_at=datetime(2023, 1, 1),
        services=["ec2"],
    )

    orchestrator.jobs = {"job1": job1, "job2": job2}

    jobs = orchestrator.list_jobs(10)
    assert len(jobs) == 2
    assert jobs[0].id == "job1"  # Should be sorted by started_at desc
    assert jobs[1].id == "job2"


def test_orchestrator_list_jobs_db_exception(mock_config):
    orchestrator = ExtractionOrchestrator(
        registry=Mock(), transport=Mock(), config={"database_enabled": True}
    )
    orchestrator.use_db = True
    orchestrator.db_manager = Mock()
    orchestrator.db_manager.list_jobs.side_effect = RuntimeError("db fail")

    assert orchestrator.list_jobs(limit=10) == []
