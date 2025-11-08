"""Tests for main application module."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.cloud.base import CloudProvider
from app.core.config import Settings
from app.main import app, lifespan, root


@pytest.mark.asyncio
async def test_lifespan_startup_initializes_components():
    mock_app = Mock()
    mock_app.state = Mock()

    settings = Settings(
        enabled_providers=["aws"],
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        aws_accounts=[{"account_id": "acct-1", "regions": ["us-east-1"]}],
        max_concurrent_extractors=4,
    )

    with patch(
        "app.main.get_settings", return_value=settings
    ) as mock_get_settings, patch("app.main.boto3.Session") as mock_boto_session, patch(
        "app.main.AWSSession"
    ) as mock_aws_session, patch(
        "app.main.ExtractorRegistry"
    ) as mock_registry, patch(
        "app.main.ExtractionOrchestrator"
    ) as mock_orchestrator, patch(
        "app.main.scheduler"
    ) as mock_scheduler:
        mock_boto_session.return_value = Mock()
        mock_aws_session.return_value = Mock()
        mock_registry.return_value = Mock()
        orchestrator_instance = Mock()
        orchestrator_instance.cleanup = AsyncMock()
        mock_orchestrator.return_value = orchestrator_instance
        mock_scheduler.start = Mock()
        mock_scheduler.shutdown = Mock()

        async with lifespan(mock_app):
            pass

        mock_get_settings.assert_called_once()
        mock_boto_session.assert_called_once_with(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            region_name="us-east-1",
        )
        mock_aws_session.assert_called_once()
        mock_registry.assert_called_once()
        registry_args, registry_kwargs = mock_registry.call_args
        assert len(registry_args) == 2
        assert registry_kwargs == {}
        sessions_arg = registry_args[0]
        assert list(sessions_arg.keys()) == [CloudProvider.AWS]
        aws_session_entry = sessions_arg[CloudProvider.AWS][0]
        assert aws_session_entry["account_id"] == "acct-1"
        assert aws_session_entry["regions"] == ["us-east-1"]
        assert registry_args[1] is settings

        mock_orchestrator.assert_called_once_with(
            registry=mock_registry.return_value,
            transport=None,
            config=settings.orchestrator_config,
        )

        assert mock_app.state.orchestrator is orchestrator_instance
        assert mock_app.state.scheduler is mock_scheduler
        assert mock_app.state.registry is mock_registry.return_value

        mock_scheduler.start.assert_called_once()
        mock_scheduler.shutdown.assert_called_once()
        orchestrator_instance.cleanup.assert_awaited_once()


def test_app_metadata_and_routes():
    assert app.title == "Cloud Artifact Extractor"
    assert (
        app.description
        == "Extract AWS and Azure cloud artifacts and send to policy scanner"
    )
    assert app.version == "2.0.0"
    # Ensure routers registered
    route_paths = {route.path for route in app.routes}
    assert "/api/v1/extraction/trigger" in route_paths
    assert "/api/v1/config/" in route_paths


@pytest.mark.asyncio
async def test_root_endpoint():
    data = await root()
    assert data == {
        "service": "Cloud Artifact Extractor",
        "version": "1.0.0",
        "status": "running",
    }


@pytest.mark.asyncio
async def test_lifespan_with_database_and_schedules():
    mock_app = Mock()
    mock_app.state = Mock()

    settings = Settings(
        database_enabled=True,
        enabled_providers=["aws"],
        aws_access_key_id="key",
        aws_secret_access_key="secret",
        aws_accounts=[{"account_id": "acct-1", "regions": ["us-east-1"]}],
    )

    db_manager = Mock()
    db_manager.is_database_available.return_value = True
    db_manager.list_schedules.return_value = [
        {
            "id": "sched-1",
            "name": "Schedule",
            "cron_expression": "*/5 * * * *",
            "services": ["s3"],
            "regions": ["us-east-1"],
            "filters": {},
            "batch_size": 50,
            "paused": False,
        }
    ]

    with patch("app.main.get_settings", return_value=settings), patch(
        "app.main.boto3.Session"
    ) as boto_session, patch("app.main.AWSSession"), patch(
        "app.main.ExtractorRegistry"
    ) as registry_cls, patch(
        "app.main.ExtractionOrchestrator"
    ) as orchestrator_cls, patch(
        "app.main.scheduler"
    ) as scheduler_mock, patch(
        "app.models.database.init_database"
    ) as init_db, patch(
        "app.models.database.get_db_manager", return_value=db_manager
    ), patch(
        "apscheduler.triggers.cron.CronTrigger.from_crontab"
    ) as cron_trigger:
        scheduler_mock.add_job = Mock()
        cron_trigger.return_value = Mock()
        scheduler_mock.start = Mock()
        scheduler_mock.shutdown = Mock()
        orchestrator_instance = Mock()
        orchestrator_instance.cleanup = AsyncMock()
        orchestrator_cls.return_value = orchestrator_instance

        async with lifespan(mock_app):
            pass

        init_db.assert_called_once()
        boto_session.assert_called()
        registry_cls.assert_called_once()
        orchestrator_cls.assert_called_once()
        scheduler_mock.add_job.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_initializes_azure_and_gcp():
    mock_app = Mock()
    mock_app.state = Mock()

    settings = Settings(
        enabled_providers=["azure", "gcp"],
        azure_tenant_id="tenant",
        azure_client_id="client",
        azure_client_secret="secret",
        azure_accounts=[{"subscription_id": "sub-1", "locations": ["eastus"]}],
        gcp_projects=[{"project_id": "proj-1", "regions": ["us-central1"]}],
        gcp_credentials_path="/tmp/creds.json",
    )

    with patch("app.main.get_settings", return_value=settings), patch(
        "app.main.AzureSession"
    ) as azure_session_cls, patch("app.main.GCPSession") as gcp_session_cls, patch(
        "app.main.ExtractorRegistry"
    ) as registry_cls, patch(
        "app.main.scheduler"
    ) as scheduler_mock:
        azure_session_cls.return_value = Mock()
        gcp_session_cls.return_value = Mock()
        registry_instance = Mock()
        registry_cls.return_value = registry_instance
        scheduler_mock.start = Mock()
        scheduler_mock.shutdown = Mock()

        async with lifespan(mock_app):
            pass

        azure_session_cls.assert_called_once()
        gcp_session_cls.assert_called_once()
        registry_cls.assert_called_once()
