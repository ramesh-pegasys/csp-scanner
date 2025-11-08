# tests/test_aegis_policy_override.py
"""
Tests for Aegis Policy Scanner Transport policy name override hierarchy.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.transport.aegis_policy_scanner_transport import AegisPolicyScannerTransport


@pytest.fixture
def transport_config():
    """Sample transport configuration with policy hierarchy"""
    return {
        "type": "aegis_policy_scanner",
        "aegis_host": "aegis.example.com",
        "policy_name": "default-cloud-policy",  # Default fallback
        "max_concurrent_requests": 5,
        "max_retries": 3,
        "allow_insecure_ssl": True,
        "labels": {"env": "test"},
        # AWS with all hierarchy levels
        "aws_accounts": [
            {
                "account_id": "123456789012",
                "policy_name": "aws-account-123-policy",  # Account-level
                "regions": [
                    {
                        "name": "us-west-2",
                        "policy_name": "aws-us-west-2-policy",  # Region-level
                    },
                    {
                        "name": "us-east-1",
                        # No region-level policy
                    },
                ],
            },
            {
                "account_id": "987654321098",
                # No account-level policy
                "regions": [
                    {
                        "name": "eu-west-1",
                        "policy_name": "aws-eu-west-1-policy",
                    },
                ],
            },
        ],
        "aws_policy_name": "aws-cloud-policy",  # Cloud-level
        # GCP
        "gcp_projects": [
            {
                "project_id": "test-project-1",
                "policy_name": "gcp-project-1-policy",  # Project-level
                "regions": [
                    {
                        "name": "us-central1",
                        "policy_name": "gcp-us-central1-policy",  # Region-level
                    },
                ],
            },
        ],
        "gcp_policy_name": "gcp-cloud-policy",  # Cloud-level
        # Azure
        "azure_subscriptions": [
            {
                "subscription_id": "sub-123",
                "policy_name": "azure-sub-123-policy",  # Subscription-level
                "locations": [
                    {
                        "name": "eastus",
                        "policy_name": "azure-eastus-policy",  # Location-level
                    },
                ],
            },
        ],
        "azure_policy_name": "azure-cloud-policy",  # Cloud-level
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("AEGIS_TOKEN", "test-token-12345")


class TestPolicyOverrideHierarchy:
    """Test policy name resolution hierarchy"""

    def test_aws_region_level_policy(self, transport_config, mock_env_vars):
        """Test that region-level policy has highest priority for AWS"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "aws",
            "metadata": {
                "account_id": "123456789012",
                "region": "us-west-2",
                "resource_id": "i-12345",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "aws-us-west-2-policy"

    def test_aws_account_level_policy(self, transport_config, mock_env_vars):
        """Test that account-level policy is used when region-level is not defined"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "aws",
            "metadata": {
                "account_id": "123456789012",
                "region": "us-east-1",  # No region-level policy
                "resource_id": "i-12345",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "aws-account-123-policy"

    def test_aws_cloud_level_policy(self, transport_config, mock_env_vars):
        """Test that cloud-level policy is used when account-level is not defined"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "aws",
            "metadata": {
                "account_id": "987654321098",  # No account-level policy
                "region": "us-east-2",  # No region-level policy
                "resource_id": "i-12345",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "aws-cloud-policy"

    def test_aws_default_policy(self, transport_config, mock_env_vars):
        """Test that default transport policy is used as final fallback"""
        # Remove AWS cloud policy
        config = transport_config.copy()
        del config["aws_policy_name"]

        transport = AegisPolicyScannerTransport(config)

        artifact = {
            "cloud_provider": "aws",
            "metadata": {
                "account_id": "999999999999",  # Unknown account
                "region": "ap-south-1",
                "resource_id": "i-12345",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "default-cloud-policy"

    def test_gcp_region_level_policy(self, transport_config, mock_env_vars):
        """Test that region-level policy has highest priority for GCP"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "gcp",
            "metadata": {
                "project_id": "test-project-1",
                "region": "us-central1",
                "resource_id": "instance-123",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "gcp-us-central1-policy"

    def test_gcp_project_level_policy(self, transport_config, mock_env_vars):
        """Test that project-level policy is used when region-level is not defined"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "gcp",
            "metadata": {
                "project_id": "test-project-1",
                "region": "us-east1",  # No region-level policy
                "resource_id": "instance-123",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "gcp-project-1-policy"

    def test_gcp_cloud_level_policy(self, transport_config, mock_env_vars):
        """Test that cloud-level policy is used when project-level is not defined"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "gcp",
            "metadata": {
                "project_id": "unknown-project",
                "region": "europe-west1",
                "resource_id": "instance-123",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "gcp-cloud-policy"

    def test_azure_location_level_policy(self, transport_config, mock_env_vars):
        """Test that location-level policy has highest priority for Azure"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "azure",
            "metadata": {
                "subscription_id": "sub-123",
                "location": "eastus",
                "resource_id": "vm-123",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "azure-eastus-policy"

    def test_azure_subscription_level_policy(self, transport_config, mock_env_vars):
        """Test that subscription-level policy is used when location-level is not defined"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "azure",
            "metadata": {
                "subscription_id": "sub-123",
                "location": "westus",  # No location-level policy
                "resource_id": "vm-123",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "azure-sub-123-policy"

    def test_azure_cloud_level_policy(self, transport_config, mock_env_vars):
        """Test that cloud-level policy is used when subscription-level is not defined"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "azure",
            "metadata": {
                "subscription_id": "sub-unknown",
                "location": "northeurope",
                "resource_id": "vm-123",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "azure-cloud-policy"

    def test_unknown_cloud_provider_uses_default(self, transport_config, mock_env_vars):
        """Test that unknown cloud provider uses default policy"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "oracle",
            "metadata": {
                "resource_id": "something",
            },
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "default-cloud-policy"

    def test_missing_metadata_uses_default(self, transport_config, mock_env_vars):
        """Test that artifacts with missing metadata use default policy"""
        transport = AegisPolicyScannerTransport(transport_config)

        artifact = {
            "cloud_provider": "aws",
            "metadata": {},  # No account_id or region
        }

        policy = transport._resolve_policy_name(artifact)
        assert policy == "default-cloud-policy"

    @pytest.mark.asyncio
    async def test_send_uses_resolved_policy(self, transport_config, mock_env_vars):
        """Test that send method uses the resolved policy name in the endpoint"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            transport = AegisPolicyScannerTransport(transport_config)
            transport.client = mock_client

            artifact = {
                "cloud_provider": "aws",
                "metadata": {
                    "account_id": "123456789012",
                    "region": "us-west-2",
                    "resource_id": "i-12345",
                },
                "artifact_id": "test-artifact",
            }

            await transport.send(artifact)

            # Verify the correct endpoint was called
            expected_url = (
                "https://aegis.example.com/api/eval/policies/aws-us-west-2-policy"
            )
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert (
                call_args[0][0] == expected_url
                or call_args.kwargs.get("url") == expected_url
            )


class TestPolicyLookupBuilder:
    """Test policy lookup table builder"""

    def test_build_policy_lookup_structure(self, transport_config, mock_env_vars):
        """Test that policy lookup table is built correctly"""
        transport = AegisPolicyScannerTransport(transport_config)

        # Check AWS structure
        assert "aws" in transport.policy_lookup
        aws_data = transport.policy_lookup["aws"]
        assert aws_data["cloud_level"] == "aws-cloud-policy"
        assert "123456789012" in aws_data["accounts"]
        assert (
            aws_data["accounts"]["123456789012"]["account_level"]
            == "aws-account-123-policy"
        )
        assert (
            aws_data["accounts"]["123456789012"]["regions"]["us-west-2"]
            == "aws-us-west-2-policy"
        )

        # Check GCP structure
        assert "gcp" in transport.policy_lookup
        gcp_data = transport.policy_lookup["gcp"]
        assert gcp_data["cloud_level"] == "gcp-cloud-policy"
        assert "test-project-1" in gcp_data["projects"]
        assert (
            gcp_data["projects"]["test-project-1"]["project_level"]
            == "gcp-project-1-policy"
        )

        # Check Azure structure
        assert "azure" in transport.policy_lookup
        azure_data = transport.policy_lookup["azure"]
        assert azure_data["cloud_level"] == "azure-cloud-policy"
        assert "sub-123" in azure_data["subscriptions"]
        assert (
            azure_data["subscriptions"]["sub-123"]["subscription_level"]
            == "azure-sub-123-policy"
        )

    def test_build_policy_lookup_without_cloud_level(self, mock_env_vars):
        """Test policy lookup without cloud-level policies"""
        config = {
            "type": "aegis_policy_scanner",
            "aegis_host": "aegis.example.com",
            "policy_name": "default-policy",
            "aws_accounts": [
                {
                    "account_id": "123456789012",
                    "regions": [{"name": "us-east-1"}],
                }
            ],
        }

        transport = AegisPolicyScannerTransport(config)

        assert "aws" in transport.policy_lookup
        aws_data = transport.policy_lookup["aws"]
        assert "cloud_level" not in aws_data
        assert "123456789012" in aws_data["accounts"]
