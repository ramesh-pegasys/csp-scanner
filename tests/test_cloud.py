"""Tests for cloud base classes and utilities"""

import pytest
from unittest.mock import Mock, patch
from app.cloud.base import CloudProvider
from app.cloud.gcp_api_check import (
    get_gcp_access_token,
    is_gcp_api_enabled,
    API_SERVICE_MAP,
)


def test_cloud_provider_enum():
    """Test CloudProvider enum values"""
    assert CloudProvider.AWS == "aws"
    assert CloudProvider.AZURE == "azure"
    assert CloudProvider.GCP == "gcp"

    # Test that all expected values are present
    assert len(CloudProvider) == 3
    assert "aws" in [p.value for p in CloudProvider]
    assert "azure" in [p.value for p in CloudProvider]
    assert "gcp" in [p.value for p in CloudProvider]


def test_api_service_map():
    """Test that API_SERVICE_MAP contains expected services"""
    assert "compute" in API_SERVICE_MAP
    assert "storage" in API_SERVICE_MAP
    assert "iam" in API_SERVICE_MAP
    assert API_SERVICE_MAP["compute"] == "compute.googleapis.com"
    assert API_SERVICE_MAP["storage"] == "storage.googleapis.com"


@pytest.mark.parametrize(
    "service,expected_api",
    [
        ("compute", "compute.googleapis.com"),
        ("storage", "storage.googleapis.com"),
        ("iam", "iam.googleapis.com"),
        ("kubernetes", "container.googleapis.com"),
    ],
)
def test_api_service_map_values(service, expected_api):
    """Test specific API service mappings"""
    assert API_SERVICE_MAP[service] == expected_api


def test_get_gcp_access_token_success():
    """Test successful GCP access token retrieval"""
    mock_credentials = Mock()
    mock_credentials.token = "test-token"
    mock_credentials.refresh = Mock()

    token = get_gcp_access_token(mock_credentials)
    assert token == "test-token"
    mock_credentials.refresh.assert_called_once()


def test_get_gcp_access_token_failure():
    """Test GCP access token retrieval failure"""
    mock_credentials = Mock()
    mock_credentials.refresh.side_effect = Exception("Refresh failed")

    token = get_gcp_access_token(mock_credentials)
    assert token is None


def test_is_gcp_api_enabled_success():
    """Test successful GCP API check"""
    with patch("app.cloud.gcp_api_check.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "ENABLED"}
        mock_get.return_value = mock_response

        result = is_gcp_api_enabled("test-project", "compute.googleapis.com")
        assert result is True
        mock_get.assert_called_once()


def test_is_gcp_api_enabled_disabled():
    """Test GCP API check when API is disabled"""
    with patch("app.cloud.gcp_api_check.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "DISABLED"}
        mock_get.return_value = mock_response

        result = is_gcp_api_enabled("test-project", "compute.googleapis.com")
        assert result is False


def test_is_gcp_api_enabled_request_failure():
    """Test GCP API check when request fails"""
    with patch("app.cloud.gcp_api_check.requests.get") as mock_get:
        mock_get.side_effect = Exception("Request failed")

        result = is_gcp_api_enabled("test-project", "compute.googleapis.com")
        assert result is False


def test_is_gcp_api_enabled_bad_status():
    """Test GCP API check with bad HTTP status"""
    with patch("app.cloud.gcp_api_check.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = is_gcp_api_enabled("test-project", "compute.googleapis.com")
        assert result is False


def test_is_gcp_api_enabled_with_credentials():
    """Test GCP API check with credentials"""
    mock_credentials = Mock()
    mock_credentials.token = "test-token"

    with patch("app.cloud.gcp_api_check.requests.get") as mock_get, patch(
        "app.cloud.gcp_api_check.get_gcp_access_token"
    ) as mock_get_token:
        mock_get_token.return_value = "test-token"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"state": "ENABLED"}
        mock_get.return_value = mock_response

        result = is_gcp_api_enabled(
            "test-project", "compute.googleapis.com", mock_credentials
        )
        assert result is True

        # Check that Authorization header was set
        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-token"


def test_azure_session_provider():
    """Test that Azure session returns correct provider"""
    from app.cloud.azure_session import AzureSession

    session = AzureSession("test-subscription")
    assert session.provider == CloudProvider.AZURE


def test_gcp_session_provider():
    """Test that GCP session returns correct provider"""
    from app.cloud.gcp_session import GCPSession

    session = GCPSession("test-project")
    assert session.provider == CloudProvider.GCP
