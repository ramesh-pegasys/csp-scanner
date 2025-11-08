# tests/test_provider_registration.py
import pytest
from unittest.mock import Mock, patch
from app.services.registry import ExtractorRegistry
from app.cloud.base import CloudProvider
from app.core.config import Settings


class TestProviderRegistration:
    """Test dynamic provider registration and unregistration"""

    def test_unregister_provider_extractors(self):
        """Test unregistering all extractors for a provider"""
        # Create mock sessions
        mock_aws_session = Mock()
        mock_aws_session.account_id = "123456789012"
        mock_aws_session.regions = ["us-east-1"]

        sessions = {
            CloudProvider.AWS: [
                {
                    "session": mock_aws_session,
                    "account_id": "123456789012",
                    "regions": ["us-east-1"],
                }
            ]
        }

        # Create registry with AWS enabled
        settings = Settings(
            enabled_providers=["aws"],
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        registry = ExtractorRegistry(sessions, settings)

        # Verify AWS extractors are registered
        aws_services = registry.list_services(provider=CloudProvider.AWS)
        assert len(aws_services) > 0, "AWS extractors should be registered"

        # Unregister AWS extractors
        count = registry.unregister_provider_extractors(CloudProvider.AWS)

        # Verify extractors were removed
        assert count > 0, "Should have unregistered some extractors"
        aws_services_after = registry.list_services(provider=CloudProvider.AWS)
        assert len(aws_services_after) == 0, "AWS extractors should be unregistered"

        # Verify sessions were removed
        assert CloudProvider.AWS not in registry.sessions

    def test_register_provider(self):
        """Test registering extractors for a new provider"""
        # Start with empty registry
        settings = Settings(enabled_providers=[])
        registry = ExtractorRegistry({}, settings)

        # Verify no extractors initially
        initial_count = len(registry.list_services())
        assert initial_count == 0, "Registry should start empty"

        # Create mock AWS session
        mock_aws_session = Mock()
        mock_aws_session.account_id = "123456789012"
        mock_aws_session.regions = ["us-east-1"]

        aws_sessions = [
            {
                "session": mock_aws_session,
                "account_id": "123456789012",
                "regions": ["us-east-1"],
            }
        ]

        # Register AWS provider
        count = registry.register_provider(CloudProvider.AWS, aws_sessions)

        # Verify extractors were added
        assert count > 0, "Should have registered some extractors"
        aws_services = registry.list_services(provider=CloudProvider.AWS)
        assert len(aws_services) > 0, "AWS extractors should be registered"

        # Verify sessions were added
        assert CloudProvider.AWS in registry.sessions

    def test_register_and_unregister_cycle(self):
        """Test registering and unregistering a provider multiple times"""
        settings = Settings(enabled_providers=[])
        registry = ExtractorRegistry({}, settings)

        # Create mock AWS session
        mock_aws_session = Mock()
        mock_aws_session.account_id = "123456789012"
        mock_aws_session.regions = ["us-east-1"]

        aws_sessions = [
            {
                "session": mock_aws_session,
                "account_id": "123456789012",
                "regions": ["us-east-1"],
            }
        ]

        # Cycle 1: Register
        count1 = registry.register_provider(CloudProvider.AWS, aws_sessions)
        assert count1 > 0

        # Cycle 1: Unregister
        unregister_count1 = registry.unregister_provider_extractors(CloudProvider.AWS)
        assert unregister_count1 == count1

        # Cycle 2: Register again
        count2 = registry.register_provider(CloudProvider.AWS, aws_sessions)
        assert count2 == count1, "Should register same number of extractors"

        # Cycle 2: Unregister again
        unregister_count2 = registry.unregister_provider_extractors(CloudProvider.AWS)
        assert unregister_count2 == count2

    def test_register_multiple_providers(self):
        """Test registering multiple providers"""
        settings = Settings(enabled_providers=[])
        registry = ExtractorRegistry({}, settings)

        # Create mock sessions for both providers
        mock_aws_session = Mock()
        mock_aws_session.account_id = "123456789012"
        mock_aws_session.regions = ["us-east-1"]

        mock_azure_session = Mock()
        mock_azure_session.subscription_id = "sub-123"
        mock_azure_session.locations = ["eastus"]

        aws_sessions = [
            {
                "session": mock_aws_session,
                "account_id": "123456789012",
                "regions": ["us-east-1"],
            }
        ]

        azure_sessions = [
            {
                "session": mock_azure_session,
                "subscription_id": "sub-123",
                "locations": ["eastus"],
            }
        ]

        # Register both providers
        aws_count = registry.register_provider(CloudProvider.AWS, aws_sessions)
        azure_count = registry.register_provider(CloudProvider.AZURE, azure_sessions)

        # Verify both registered
        assert aws_count > 0, "AWS extractors should be registered"
        assert azure_count > 0, "Azure extractors should be registered"

        # Verify they're independent
        aws_services = registry.list_services(provider=CloudProvider.AWS)
        azure_services = registry.list_services(provider=CloudProvider.AZURE)

        assert len(aws_services) == aws_count
        assert len(azure_services) == azure_count

        # Unregister AWS only
        registry.unregister_provider_extractors(CloudProvider.AWS)

        # Verify Azure still exists
        azure_services_after = registry.list_services(provider=CloudProvider.AZURE)
        assert (
            len(azure_services_after) == azure_count
        ), "Azure should remain registered"

        aws_services_after = registry.list_services(provider=CloudProvider.AWS)
        assert len(aws_services_after) == 0, "AWS should be unregistered"


class TestConfigAPIProviderChanges:
    """Test config API handling of provider changes"""

    @pytest.mark.asyncio
    async def test_handle_provider_changes_enable(self):
        """Test enabling a new provider through config API"""
        from app.api.routes.config import _handle_provider_changes

        # from unittest.mock import AsyncMock

        # Create mock request with registry
        mock_request = Mock()
        mock_registry = Mock()
        mock_registry.register_provider = Mock(return_value=5)
        mock_request.app.state.registry = mock_registry

        # Mock settings
        with patch("app.api.routes.config.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_aws_enabled = True
            mock_settings.aws_accounts_list = [
                {"account_id": "123456789012", "regions": ["us-east-1"]}
            ]
            mock_settings.aws_access_key_id = "test_key"
            mock_settings.aws_secret_access_key = "test_secret"
            mock_get_settings.return_value = mock_settings

            # Mock session initialization
            with patch("app.api.routes.config._initialize_cloud_sessions") as mock_init:
                mock_init.return_value = [{"session": Mock(), "account_id": "123"}]

                # Enable AWS
                _handle_provider_changes(mock_request, [], ["aws"])

                # Verify session initialization was called
                mock_init.assert_called_once()

                # Verify register_provider was called
                mock_registry.register_provider.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_provider_changes_disable(self):
        """Test disabling a provider through config API"""
        from app.api.routes.config import _handle_provider_changes

        # Create mock request with registry
        mock_request = Mock()
        mock_registry = Mock()
        mock_registry.unregister_provider_extractors = Mock(return_value=5)
        mock_request.app.state.registry = mock_registry

        # Mock settings
        with patch("app.api.routes.config.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_get_settings.return_value = mock_settings

            # Disable AWS
            _handle_provider_changes(mock_request, ["aws"], [])

            # Verify unregister was called
            mock_registry.unregister_provider_extractors.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_provider_changes_mixed(self):
        """Test enabling and disabling providers simultaneously"""
        from app.api.routes.config import _handle_provider_changes

        # Create mock request with registry
        mock_request = Mock()
        mock_registry = Mock()
        mock_registry.unregister_provider_extractors = Mock(return_value=5)
        mock_registry.register_provider = Mock(return_value=8)
        mock_request.app.state.registry = mock_registry

        # Mock settings
        with patch("app.api.routes.config.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_azure_enabled = True
            mock_settings.azure_accounts_list = [
                {"subscription_id": "sub-123", "locations": ["eastus"]}
            ]
            mock_settings.azure_tenant_id = "tenant"
            mock_settings.azure_client_id = "client"
            mock_settings.azure_client_secret = "secret"
            mock_get_settings.return_value = mock_settings

            # Mock session initialization
            with patch("app.api.routes.config._initialize_cloud_sessions") as mock_init:
                mock_init.return_value = [{"session": Mock(), "subscription_id": "sub"}]

                # Switch from AWS to Azure
                _handle_provider_changes(mock_request, ["aws"], ["azure"])

                # Verify unregister AWS was called
                assert mock_registry.unregister_provider_extractors.called

                # Verify register Azure was called
                assert mock_registry.register_provider.called
