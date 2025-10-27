"""Tests for services"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.registry import ExtractorRegistry
from app.services.orchestrator import ExtractionOrchestrator
from app.services.scheduler import SchedulerService
from app.core.config import Settings
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
    config = Mock(spec=Settings)
    config.extractors = {
        'ec2': {'enabled': True},
        's3': {'enabled': True}
    }
    return config


@pytest.fixture
def mock_transport():
    """Mock transport"""
    return Mock()


def test_registry_initialization(mock_session, mock_config):
    """Test registry initialization"""
    with patch('app.services.registry.ExtractorRegistry._register_default_extractors'):
        registry = ExtractorRegistry(mock_session, mock_config)
        assert registry.session == mock_session
        assert registry.config == mock_config
        assert isinstance(registry._extractors, dict)


def test_registry_get_extractor(mock_session, mock_config):
    """Test getting an extractor"""
    with patch('app.services.registry.ExtractorRegistry._register_default_extractors'):
        registry = ExtractorRegistry(mock_session, mock_config)
        # Manually add an extractor
        mock_extractor = Mock()
        mock_extractor.metadata.service_name = 'ec2'
        registry._extractors['ec2'] = mock_extractor
        
        extractor = registry.get('ec2')
        assert extractor == mock_extractor


def test_registry_get_nonexistent_extractor(mock_session, mock_config):
    """Test getting a non-existent extractor"""
    with patch('app.services.registry.ExtractorRegistry._register_default_extractors'):
        registry = ExtractorRegistry(mock_session, mock_config)
        extractor = registry.get('nonexistent')
        assert extractor is None


def test_registry_list_services(mock_session, mock_config):
    """Test listing services"""
    with patch('app.services.registry.ExtractorRegistry._register_default_extractors'):
        registry = ExtractorRegistry(mock_session, mock_config)
        # Manually add extractors
        mock_ec2 = Mock()
        mock_ec2.metadata.service_name = 'ec2'
        registry._extractors['ec2'] = mock_ec2
        
        mock_s3 = Mock()
        mock_s3.metadata.service_name = 's3'
        registry._extractors['s3'] = mock_s3
        
        services = registry.list_services()
        assert 'ec2' in services
        assert 's3' in services


def test_registry_get_extractors(mock_session, mock_config):
    """Test getting multiple extractors"""
    with patch('app.services.registry.ExtractorRegistry._register_default_extractors'):
        registry = ExtractorRegistry(mock_session, mock_config)
        # Manually add extractors
        mock_ec2 = Mock()
        mock_ec2.metadata.service_name = 'ec2'
        registry._extractors['ec2'] = mock_ec2
        
        mock_s3 = Mock()
        mock_s3.metadata.service_name = 's3'
        registry._extractors['s3'] = mock_s3
        
        extractors = registry.get_extractors(['ec2', 's3'])
        assert len(extractors) == 2
        assert mock_ec2 in extractors
        assert mock_s3 in extractors


def test_orchestrator_initialization(mock_session, mock_config, mock_transport):
    """Test orchestrator initialization"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config=mock_config
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
        registry=mock_registry,
        transport=mock_transport,
        config=mock_config
    )
    
    # Mock registry
    mock_extractor = Mock()
    mock_extractor.metadata.service_name = 's3'
    mock_registry.list_services.return_value = ['s3']
    mock_registry.get_extractors.return_value = [mock_extractor]
    
    # Mock extractor
    mock_extractor.extract = AsyncMock(return_value=[{'resource_id': 'bucket1', 'service': 's3'}])
    
    # Mock transport
    mock_transport.send = AsyncMock(return_value={'status': 'accepted'})
    
    import uuid
    with patch('app.services.orchestrator.uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
        job_id = await orchestrator.run_extraction(services=['s3'], batch_size=10)
        assert job_id == '12345678-1234-5678-1234-567812345678'
        
        # Check job was created
        assert job_id in orchestrator.jobs
        job = orchestrator.jobs[job_id]
        assert job.status == JobStatus.RUNNING
        assert job.services == ['s3']


@pytest.mark.asyncio
async def test_orchestrator_execute_job_success(mock_session, mock_config, mock_transport):
    """Test successful job execution"""
    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry,
        transport=mock_transport,
        config=mock_config
    )
    
    # Create a job
    job = Job(
        id='test-job',
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=['s3']
    )
    
    # Mock registry and extractor
    mock_extractor = Mock()
    mock_extractor.metadata.service_name = 's3'
    mock_extractor.metadata.supports_regions = True
    mock_registry.get_extractors.return_value = [mock_extractor]
    mock_extractor.extract = AsyncMock(return_value=[{'resource_id': 'bucket1', 'service': 's3'}])
    
    # Mock transport
    mock_transport.send = AsyncMock(return_value={'status': 'accepted'})
    
    await orchestrator._execute_job(job, ['s3'], None, None, 10)
    
    assert job.status == JobStatus.COMPLETED
    assert job.total_artifacts == 1
    assert job.successful_artifacts == 1
    assert job.failed_artifacts == 0
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_orchestrator_execute_job_failure(mock_session, mock_config, mock_transport):
    """Test job execution with failure"""
    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry,
        transport=mock_transport,
        config=mock_config
    )
    
    # Create a job
    job = Job(
        id='test-job',
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=['s3']
    )
    
    # Mock registry to raise exception
    mock_registry.get_extractors.side_effect = Exception("Registry error")
    
    await orchestrator._execute_job(job, ['s3'], None, None, 10)
    
    assert job.status == JobStatus.FAILED
    assert "Registry error" in job.errors[0]
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_orchestrator_execute_job_partial_failure(mock_session, mock_config, mock_transport):
    """Partial extractor failure still processes remaining artifacts"""
    mock_registry = Mock()
    orchestrator = ExtractionOrchestrator(
        registry=mock_registry,
        transport=mock_transport,
        config=mock_config
    )

    job = Job(
        id='partial-job',
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        services=['ec2']
    )

    extractor_a = Mock()
    extractor_b = Mock()
    mock_registry.get_extractors.return_value = [extractor_a, extractor_b]
    orchestrator._extract_service = AsyncMock(side_effect=[Exception("extract fail"), [{'resource_id': 'good'}]])
    orchestrator._send_artifacts = AsyncMock()

    await orchestrator._execute_job(job, ['ec2'], None, None, 5)

    assert any("extract fail" in error for error in job.errors)
    assert job.total_artifacts == 1
    orchestrator._send_artifacts.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_extract_service_single_region(mock_session, mock_config, mock_transport):
    """Test extracting from a service in a single region"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config=mock_config
    )
    
    mock_extractor = Mock()
    mock_extractor.metadata.supports_regions = True
    mock_extractor.extract = AsyncMock(return_value=[{'resource_id': 'bucket1'}])
    
    artifacts = await orchestrator._extract_service(mock_extractor, ['us-east-1'], None)
    
    assert len(artifacts) == 1
    assert artifacts[0]['resource_id'] == 'bucket1'
    mock_extractor.extract.assert_called_once_with('us-east-1', None)


@pytest.mark.asyncio
async def test_orchestrator_extract_service_multiple_regions(mock_session, mock_config, mock_transport):
    """Test extracting from a service in multiple regions"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config=mock_config
    )
    
    mock_extractor = Mock()
    mock_extractor.metadata.supports_regions = True
    mock_extractor.extract = AsyncMock(side_effect=[
        [{'resource_id': 'bucket1'}],
        [{'resource_id': 'bucket2'}]
    ])
    
    artifacts = await orchestrator._extract_service(mock_extractor, ['us-east-1', 'us-west-2'], None)
    
    assert len(artifacts) == 2
    assert mock_extractor.extract.call_count == 2


@pytest.mark.asyncio
async def test_orchestrator_extract_service_region_errors(mock_session, mock_config, mock_transport):
    """Extraction continues when a region fails"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config=mock_config
    )

    mock_extractor = Mock()
    mock_extractor.metadata.supports_regions = True
    mock_extractor.extract = AsyncMock(side_effect=[Exception("boom"), [{'resource_id': 'bucket-ok'}]])

    artifacts = await orchestrator._extract_service(mock_extractor, ['us-east-1', 'us-west-2'], None)

    assert len(artifacts) == 1
    assert artifacts[0]['resource_id'] == 'bucket-ok'


@pytest.mark.asyncio
async def test_orchestrator_send_artifacts(mock_session, mock_config, mock_transport):
    """Test sending artifacts in batches"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config={'batch_delay_seconds': 0.01}
    )
    
    job = Job(id='test-job', status=JobStatus.RUNNING, started_at=datetime.now(timezone.utc), services=['s3'])
    
    artifacts = [
        {'resource_id': f'bucket{i}', 'service': 's3'} for i in range(5)
    ]
    
    mock_transport.send = AsyncMock(return_value={'status': 'accepted'})
    
    await orchestrator._send_artifacts(job, artifacts, 2)

    assert mock_transport.send.call_count == 5
    assert job.successful_artifacts == 5
    assert job.failed_artifacts == 0


@pytest.mark.asyncio
async def test_orchestrator_send_artifacts_handles_errors(mock_session, mock_config, mock_transport):
    """Send failures are captured in job metrics"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config={'batch_delay_seconds': 0.0}
    )

    job = Job(id='job-send', status=JobStatus.RUNNING, started_at=datetime.now(timezone.utc), services=['s3'])
    artifacts = [{'resource_id': 'one', 'service': 's3'}, {'resource_id': 'two', 'service': 's3'}]

    mock_transport.send = AsyncMock(side_effect=[TransportError("send fail"), {'status': 'accepted'}])

    await orchestrator._send_artifacts(job, artifacts, 2)

    assert job.failed_artifacts == 1
    assert job.successful_artifacts == 1
    assert any("send fail" in error for error in job.errors)


def test_orchestrator_get_job_status(mock_session, mock_config, mock_transport):
    """Test getting job status"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config=mock_config
    )
    
    job = Job(id='test-job', status=JobStatus.COMPLETED, started_at=datetime.now(timezone.utc), services=['s3'])
    orchestrator.jobs['test-job'] = job
    
    result = orchestrator.get_job_status('test-job')
    assert result == job
    
    result = orchestrator.get_job_status('non-existent')
    assert result is None


def test_orchestrator_list_jobs(mock_session, mock_config, mock_transport):
    """Test listing jobs"""
    orchestrator = ExtractionOrchestrator(
        registry=Mock(),
        transport=mock_transport,
        config=mock_config
    )
    
    # Create jobs with different timestamps
    job1 = Job(id='job1', status=JobStatus.COMPLETED, started_at=datetime(2023, 1, 2), services=['s3'])
    job2 = Job(id='job2', status=JobStatus.RUNNING, started_at=datetime(2023, 1, 1), services=['ec2'])
    
    orchestrator.jobs = {'job1': job1, 'job2': job2}
    
    jobs = orchestrator.list_jobs(10)
    assert len(jobs) == 2
    assert jobs[0].id == 'job1'  # Should be sorted by started_at desc
    assert jobs[1].id == 'job2'
