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
    ) as mock_scheduler:
        # Setup mocks
        from app.core.config import Settings

        mock_settings = Settings(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            aws_account_id="test-account",
            aws_default_region="us-east-1",
            scanner_endpoint_url="http://localhost:8000",
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
            "scanner_endpoint_url",
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

    with patch("app.main.get_settings") as mock_get_settings, patch(
        "app.main.boto3.Session"
    ) as mock_session_class, patch("app.main.ExtractorRegistry"), patch(
        "app.main.TransportFactory.create"
    ), patch(
        "app.main.ExtractionOrchestrator"
    ), patch(
        "app.main.scheduler"
    ):
        # Setup mocks
        from app.core.config import Settings

        mock_settings = Settings(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            aws_account_id="test-account",
            aws_default_region="us-east-1",
        )
        mock_get_settings.return_value = mock_settings

        # Make boto3.Session raise an exception
        mock_session_class.side_effect = Exception("Session creation failed")

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

        # Test startup with no providers - should raise RuntimeError
        with pytest.raises(
            RuntimeError, match="At least one cloud provider must be enabled"
        ):
            async with lifespan(mock_app):
                pass
