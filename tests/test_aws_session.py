"""Tests for AWS session wrapper"""

import pytest  # noqa: F401
from unittest.mock import Mock
from app.cloud.aws_session import AWSSession
from app.cloud.base import CloudProvider


@pytest.fixture
def mock_boto_session():
    """Create a mock boto3.Session"""
    session = Mock()
    session.client = Mock()
    return session


def test_aws_session_provider(mock_boto_session):
    """Test that AWS session returns correct provider"""
    aws_session = AWSSession(mock_boto_session)
    assert aws_session.provider == CloudProvider.AWS


def test_aws_session_get_client(mock_boto_session):
    """Test getting a client from AWS session"""
    mock_client = Mock()
    mock_boto_session.client.return_value = mock_client

    aws_session = AWSSession(mock_boto_session)
    client = aws_session.get_client("ec2", region="us-east-1")

    assert client == mock_client
    mock_boto_session.client.assert_called_once_with("ec2", region_name="us-east-1")


def test_aws_session_get_client_no_region(mock_boto_session):
    """Test getting a client without specifying region"""
    mock_client = Mock()
    mock_boto_session.client.return_value = mock_client

    aws_session = AWSSession(mock_boto_session)
    client = aws_session.get_client("s3")

    assert client == mock_client
    mock_boto_session.client.assert_called_once_with("s3", region_name=None)


def test_aws_session_list_regions_success(mock_boto_session):
    """Test listing regions successfully"""
    mock_ec2_client = Mock()
    mock_ec2_client.describe_regions.return_value = {
        "Regions": [
            {"RegionName": "us-east-1"},
            {"RegionName": "us-west-2"},
            {"RegionName": "eu-west-1"},
        ]
    }
    mock_boto_session.client.return_value = mock_ec2_client

    aws_session = AWSSession(mock_boto_session)
    regions = aws_session.list_regions()

    assert len(regions) == 3
    assert "us-east-1" in regions
    assert "us-west-2" in regions
    assert "eu-west-1" in regions

    # Test caching - second call should not call describe_regions again
    mock_ec2_client.describe_regions.reset_mock()
    regions2 = aws_session.list_regions()
    assert regions == regions2
    mock_ec2_client.describe_regions.assert_not_called()


def test_aws_session_list_regions_failure(mock_boto_session):
    """Test listing regions when describe_regions fails"""
    mock_ec2_client = Mock()
    mock_ec2_client.describe_regions.side_effect = Exception("API Error")
    mock_boto_session.client.return_value = mock_ec2_client

    aws_session = AWSSession(mock_boto_session)
    regions = aws_session.list_regions()

    # Should return default regions on failure
    assert len(regions) == 8
    assert "us-east-1" in regions
    assert "us-west-2" in regions
    assert "eu-west-1" in regions


def test_aws_session_boto_session_property(mock_boto_session):
    """Test boto_session property for backward compatibility"""
    aws_session = AWSSession(mock_boto_session)
    assert aws_session.boto_session == mock_boto_session
