"""Tests for main application"""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch, AsyncMock
from app.main import app, lifespan, root
from app.core.config import Settings
from app.cloud.base import CloudProvider


@pytest.mark.asyncio
async def test_lifespan_startup():
    """Test application lifespan startup"""
    mock_app = Mock()
    mock_app.state = Mock()  # Use Mock instead of dict for attribute access

    with patch("app.main.get_settings") as mock_get_settings, \
         patch("boto3.Session") as mock_session_class, \
         patch("app.main.ExtractorRegistry") as mock_registry_class, \
         patch("app.main.TransportFactory.create") as mock_transport_factory, \
         patch("app.main.ExtractionOrchestrator") as mock_orchestrator_class, \
         patch("app.main.scheduler") as mock_scheduler:
        # Setup mocks
        from app.core.config import Settings

        mock_settings = Settings(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            aws_account_id="test-account",
            aws_default_region="us-east-1",
            enabled_providers=["aws"],
            aws_accounts=[
                {
                    "account_id": "test-account",
                    "regions": ["us-east-1"],
                }
            ],
            http_endpoint_url="http://localhost:8000",
            transport_timeout_seconds=30,
            transport_max_retries=3,
            max_concurrent_extractors=10,
            batch_size=100,
            batch_delay_seconds=0.1,
            api_key_enabled=False,
        )
        # Patch all attributes to ensure correct access
        for attr in [
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_account_id",
            "aws_default_region",
            "http_endpoint_url",
            "transport_timeout_seconds",
            "transport_max_retries",
            "max_concurrent_extractors",
            "batch_size",
            "batch_delay_seconds",
            "api_key_enabled",
        ]:
            setattr(mock_settings, attr, getattr(mock_settings, attr))
        mock_get_settings.return_value = mock_settings

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_transport = Mock()
        mock_transport.close = AsyncMock()
        mock_transport_factory.return_value = mock_transport

        mock_orchestrator = Mock()
        mock_orchestrator.stop = AsyncMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        # Test startup
        async with lifespan(mock_app):
            print(f"Mock settings aws_access_key_id: {mock_settings.aws_access_key_id}")
            print(f"Mock session call args: {mock_session_class.call_args}")
            print(f"Mock session call count: {mock_session_class.call_count}")
            # Verify components were initialized
            mock_session_class.assert_called_once_with(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
                region_name="us-east-1",
            )
            mock_registry_class.assert_called_once()
            registry_args, registry_kwargs = mock_registry_class.call_args
            assert registry_kwargs == {}
            assert len(registry_args) == 2
            sessions_arg = registry_args[0]
            assert isinstance(sessions_arg, dict)
            assert list(sessions_arg.keys()) == [CloudProvider.AWS]
            assert registry_args[1] == mock_settings
            mock_transport_factory.assert_called_once_with(
                mock_settings.transport_type, mock_settings.transport_config
            )
            mock_orchestrator_class.assert_called_once_with(
                registry=mock_registry,
                transport=mock_transport,
                config=mock_settings.orchestrator_config,
            )
            mock_scheduler.start.assert_called_once()

            # Verify app state was set
            assert mock_app.state.orchestrator == mock_orchestrator
            assert mock_app.state.scheduler == mock_scheduler
            assert mock_app.state.registry == mock_registry

        # Verify shutdown
        mock_scheduler.shutdown.assert_called_once()
        mock_transport.close.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_shutdown_disconnect():
    """Ensure transports with disconnect are handled"""
    mock_app = Mock()
    mock_app.state = Mock()

    with patch("app.main.get_settings") as mock_get_settings, patch(
        "app.main.boto3.Session"
    ) as mock_session_class, patch(
        "app.main.ExtractorRegistry"
    ) as mock_registry_class, patch(
        "app.main.TransportFactory.create"
    ) as mock_transport_factory, patch(
        "app.main.ExtractionOrchestrator"
    ) as mock_orchestrator_class, patch(
        "app.main.scheduler"
    ):
        mock_settings = Settings(aws_account_id="test")
        mock_get_settings.return_value = mock_settings

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        transport = SimpleNamespace(disconnect=AsyncMock())
        mock_transport_factory.return_value = transport

        mock_orchestrator = Mock()
        mock_orchestrator.stop = AsyncMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler = Mock()
        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        async with lifespan(mock_app):
            pass

        transport.disconnect.assert_called_once()


def test_app_creation():
    """Test FastAPI app creation"""
    assert app.title == "Cloud Artifact Extractor"
    assert (
        app.description
        == "Extract AWS and Azure cloud artifacts and send to policy scanner"
    )
    assert app.version == "2.0.0"
    assert len(app.routes) > 1  # Should have multiple routes


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint"""
    data = await root()
    assert data["service"] == "Cloud Artifact Extractor"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_lifespan_startup_failure():
    """Test application lifespan startup failure"""
    mock_app = Mock()
    mock_app.state = Mock()

    with patch("app.main.get_settings") as mock_get_settings, \
         patch("boto3.Session") as mock_session_class, \
         patch("app.main.ExtractorRegistry") as mock_registry_class, \
         patch("app.main.TransportFactory.create") as mock_transport_factory, \
         patch("app.main.ExtractionOrchestrator") as mock_orchestrator_class, \
         patch("app.main.scheduler") as mock_scheduler:
        # Setup mocks
        from app.core.config import Settings

        mock_settings = Settings(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            aws_account_id="test-account",
            aws_default_region="us-east-1",
            enabled_providers=["aws"],
            aws_accounts=[
                {
                    "account_id": "test-account",
                    "regions": ["us-east-1"],
                }
            ],
        )
        mock_get_settings.return_value = mock_settings

        # Make boto3.Session raise an exception
        mock_session_class.side_effect = Exception("Session creation failed")

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_transport = Mock()
        mock_transport.close = AsyncMock()
        mock_transport_factory.return_value = mock_transport

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        # Test startup failure - should raise RuntimeError since no providers succeed
        with pytest.raises(
            RuntimeError, match="At least one cloud provider must be enabled"
        ):
            async with lifespan(mock_app):
                pass


@pytest.mark.asyncio
async def test_lifespan_no_providers_enabled():
    """Test application lifespan when no providers are enabled"""
    mock_app = Mock()
    mock_app.state = Mock()

    with patch("app.main.get_settings") as mock_get_settings, patch(
        "app.main.ExtractorRegistry"
    ) as mock_registry_class, patch(
        "app.main.TransportFactory.create"
    ) as mock_transport_factory, patch(
        "app.main.ExtractionOrchestrator"
    ) as mock_orchestrator_class, patch(
        "app.main.scheduler"
    ) as mock_scheduler:
        # Setup mocks
        from app.core.config import Settings

        # Settings with no providers enabled
        mock_settings = Settings(enabled_providers=[])
        mock_get_settings.return_value = mock_settings

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_transport = Mock()
        mock_transport.close = AsyncMock()
        mock_transport_factory.return_value = mock_transport

        mock_orchestrator = Mock()
        mock_orchestrator.stop = AsyncMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler = Mock()
        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        # Test startup with no providers - should log a warning, not raise
        with patch("app.main.logger") as mock_logger:
            async with lifespan(mock_app):
                pass
            mock_logger.warning.assert_any_call("No cloud providers enabled at startup. Configuration can be updated via API.")


@pytest.mark.asyncio
async def test_lifespan_with_database():
    """Test application lifespan with database enabled"""
    mock_app = Mock()
    mock_app.state = Mock()

    with patch("app.main.get_settings") as mock_get_settings, \
         patch("app.models.database.init_database") as mock_init_database, \
         patch("app.models.database.get_db_manager") as mock_get_db_manager, \
         patch("app.main.ExtractorRegistry") as mock_registry_class, \
         patch("app.main.TransportFactory.create") as mock_transport_factory, \
         patch("app.main.ExtractionOrchestrator") as mock_orchestrator_class, \
         patch("app.main.scheduler") as mock_scheduler:
        # Setup mocks
        from app.core.config import Settings

        mock_settings = Settings(
            database_enabled=True,
            database_host="localhost",
            database_port=5432,
            database_name="test",
            database_user="user",
            database_password="pass",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            aws_account_id="test-account",
            aws_default_region="us-east-1",
            enabled_providers=["aws"],
            aws_accounts=[
                {
                    "account_id": "test-account",
                    "regions": ["us-east-1"],
                }
            ],
            http_endpoint_url="http://localhost:8000",
            transport_timeout_seconds=30,
            transport_max_retries=3,
            max_concurrent_extractors=10,
            batch_size=100,
            batch_delay_seconds=0.1,
            api_key_enabled=False,
        )
        mock_get_settings.return_value = mock_settings

        mock_db_manager = Mock()
        mock_db_manager.is_database_available.return_value = True
        mock_get_db_manager.return_value = mock_db_manager

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_transport = Mock()
        mock_transport.close = AsyncMock()
        mock_transport_factory.return_value = mock_transport

        mock_orchestrator = Mock()
        mock_orchestrator.stop = AsyncMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        # Test startup
        async with lifespan(mock_app):
            # Verify database init was called
            mock_init_database.assert_called_once_with("postgresql://user:pass@localhost:5432/test")
            mock_get_db_manager.assert_called_once()
            mock_db_manager.is_database_available.assert_called_once()

            # Verify components were initialized
            mock_registry_class.assert_called_once()
            mock_transport_factory.assert_called_once_with(
                mock_settings.transport_type, mock_settings.transport_config
            )
            mock_orchestrator_class.assert_called_once_with(
                registry=mock_registry,
                transport=mock_transport,
                config=mock_settings.orchestrator_config,
            )
            mock_scheduler.start.assert_called_once()

        # Verify shutdown
        mock_scheduler.shutdown.assert_called_once()
        mock_transport.close.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_database_unavailable_warning():
    mock_app = Mock()
    mock_app.state = Mock()

    with patch("app.main.get_settings") as mock_get_settings, \
         patch("app.models.database.init_database") as mock_init_database, \
         patch("app.models.database.get_db_manager") as mock_get_db_manager, \
         patch("app.main.ExtractorRegistry") as mock_registry_class, \
         patch("app.main.TransportFactory.create") as mock_transport_factory, \
         patch("app.main.ExtractionOrchestrator") as mock_orchestrator_class, \
         patch("app.main.scheduler") as mock_scheduler:
        mock_settings = Settings(database_enabled=True, enabled_providers=[])
        mock_get_settings.return_value = mock_settings

        db_manager = Mock()
        db_manager.is_database_available.return_value = False
        mock_get_db_manager.return_value = db_manager

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        transport = SimpleNamespace(close=AsyncMock())
        mock_transport_factory.return_value = transport

        mock_orchestrator = Mock()
        mock_orchestrator.stop = AsyncMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        with patch("app.main.logger") as mock_logger:
            async with lifespan(mock_app):
                pass

        mock_logger.warning.assert_any_call(
            "Database initialized but not accessible - config features will be limited"
        )


@pytest.mark.asyncio
async def test_lifespan_database_initialization_failure():
    mock_app = Mock()
    mock_app.state = Mock()

    with patch("app.main.get_settings") as mock_get_settings, \
         patch("app.models.database.init_database") as mock_init_database, \
         patch("app.models.database.get_db_manager") as mock_get_db_manager, \
         patch("app.main.ExtractorRegistry") as mock_registry_class, \
         patch("app.main.TransportFactory.create") as mock_transport_factory, \
         patch("app.main.ExtractionOrchestrator") as mock_orchestrator_class, \
         patch("app.main.scheduler") as mock_scheduler:
        mock_settings = Settings(database_enabled=True, enabled_providers=[])
        mock_get_settings.return_value = mock_settings

        mock_init_database.side_effect = RuntimeError("boom")
        mock_get_db_manager.return_value = Mock()

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        transport = SimpleNamespace(close=AsyncMock())
        mock_transport_factory.return_value = transport

        mock_orchestrator = Mock()
        mock_orchestrator.stop = AsyncMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        with patch("app.main.logger") as mock_logger:
            async with lifespan(mock_app):
                pass

        mock_logger.error.assert_any_call("Failed to initialize database: boom")
        mock_logger.warning.assert_any_call("Database features will not be available")


@pytest.mark.asyncio
async def test_lifespan_initializes_multi_cloud_sessions():
    mock_app = Mock()
    mock_app.state = Mock()

    with patch("app.main.get_settings") as mock_get_settings, \
         patch("app.main.boto3.Session") as mock_boto_session, \
         patch("app.main.AWSSession") as mock_aws_session, \
         patch("app.main.AzureSession") as mock_azure_session, \
         patch("app.main.GCPSession") as mock_gcp_session, \
         patch("app.main.ExtractorRegistry") as mock_registry_class, \
         patch("app.main.TransportFactory.create") as mock_transport_factory, \
         patch("app.main.ExtractionOrchestrator") as mock_orchestrator_class, \
         patch("app.main.scheduler") as mock_scheduler:
        mock_settings = Settings(
            enabled_providers=["aws", "azure", "gcp"],
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            aws_accounts=[
                {
                    "account_id": "123456789012",
                    "regions": ["us-east-1", "us-west-2"],
                }
            ],
            azure_tenant_id="tenant",
            azure_client_id="client",
            azure_client_secret="secret",
            azure_accounts=[
                {
                    "subscription_id": "sub-1",
                    "locations": [
                        {"name": "eastus", "policy_name": "east-policy"},
                        "westus",
                    ],
                }
            ],
            gcp_projects=[
                {
                    "project_id": "proj-1",
                    "regions": [{"name": "us-central1", "policy_name": "central"}],
                },
                {
                    "regions": ["us-west1"],
                },
            ],
            gcp_credentials_path="/tmp/creds.json",
        )
        mock_get_settings.return_value = mock_settings

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_transport = Mock()
        mock_transport.close = AsyncMock()
        mock_transport_factory.return_value = mock_transport

        mock_orchestrator = Mock()
        mock_orchestrator.stop = AsyncMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        mock_boto_session.return_value = Mock()
        mock_aws_session.side_effect = lambda session: SimpleNamespace(session=session)
        mock_azure_session.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
        mock_gcp_session.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)

        with patch("app.main.logger") as mock_logger:
            async with lifespan(mock_app):
                pass

        registry_args, _ = mock_registry_class.call_args
        sessions = registry_args[0]
        assert CloudProvider.AWS in sessions
        assert CloudProvider.AZURE in sessions
        assert CloudProvider.GCP in sessions

        mock_logger.warning.assert_any_call(
            "Missing project_id in GCP config entry, skipping."
        )


def test_custom_fastapi_openapi_override(monkeypatch):
    sentinel = {"openapi": "custom"}

    def fake_openapi(app_instance):
        return sentinel

    monkeypatch.setattr("app.main.custom_openapi", fake_openapi)
    assert app.openapi() == sentinel
