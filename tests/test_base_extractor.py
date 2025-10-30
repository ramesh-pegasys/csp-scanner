"""Tests for base extractor functionality"""

import pytest
from unittest.mock import Mock, MagicMock
from app.extractors.base import BaseExtractor, ExtractorMetadata


class TestExtractor(BaseExtractor):
    """Test implementation of BaseExtractor"""
    
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="test",
            version="1.0.0",
            description="Test extractor",
            resource_types=["test-resource"],
            cloud_provider="aws",
        )
    
    async def extract(self, region=None, filters=None):
        return [{"id": "test-1"}]
    
    def transform(self, raw_data):
        return {
            "cloud_provider": "aws",
            "resource_type": "test-resource",
            "metadata": {
                "resource_id": raw_data.get("id"),
            },
            "configuration": raw_data,
        }


def test_base_extractor_with_cloud_session():
    """Test BaseExtractor with CloudSession"""
    mock_session = Mock()
    mock_session.get_client = Mock(return_value=Mock())
    
    extractor = TestExtractor(mock_session, {})
    
    assert extractor.session == mock_session
    assert extractor.cloud_provider == "aws"
    assert extractor.metadata.service_name == "test"


def test_base_extractor_with_boto3_session():
    """Test BaseExtractor with boto3.Session for backward compatibility"""
    import boto3
    
    mock_boto_session = MagicMock(spec=boto3.Session)
    mock_boto_session.client = Mock()
    
    extractor = TestExtractor(mock_boto_session, {})
    
    # Should have wrapped the boto3 session
    from app.cloud.aws_session import AWSSession
    assert isinstance(extractor.session, AWSSession)
    assert extractor.cloud_provider == "aws"


def test_base_extractor_get_client():
    """Test _get_client helper method"""
    mock_session = Mock()
    mock_client = Mock()
    mock_session.get_client = Mock(return_value=mock_client)
    
    extractor = TestExtractor(mock_session, {})
    client = extractor._get_client("ec2", region="us-east-1")
    
    assert client == mock_client
    mock_session.get_client.assert_called_once_with("ec2", "us-east-1")


def test_validate_artifact_success():
    """Test artifact validation with valid artifact"""
    mock_session = Mock()
    extractor = TestExtractor(mock_session, {})
    
    artifact = {
        "cloud_provider": "aws",
        "resource_type": "test-resource",
        "metadata": {
            "resource_id": "test-123",
        },
        "configuration": {},
    }
    
    assert extractor.validate(artifact) is True


def test_validate_artifact_missing_required_fields():
    """Test artifact validation with missing required fields"""
    mock_session = Mock()
    extractor = TestExtractor(mock_session, {})
    
    # Missing cloud_provider
    artifact = {
        "resource_type": "test-resource",
        "metadata": {"resource_id": "test-123"},
        "configuration": {},
    }
    assert extractor.validate(artifact) is False
    
    # Missing resource_type
    artifact = {
        "cloud_provider": "aws",
        "metadata": {"resource_id": "test-123"},
        "configuration": {},
    }
    assert extractor.validate(artifact) is False
    
    # Missing metadata
    artifact = {
        "cloud_provider": "aws",
        "resource_type": "test-resource",
        "configuration": {},
    }
    assert extractor.validate(artifact) is False
    
    # Missing configuration
    artifact = {
        "cloud_provider": "aws",
        "resource_type": "test-resource",
        "metadata": {"resource_id": "test-123"},
    }
    assert extractor.validate(artifact) is False


def test_validate_artifact_missing_resource_id():
    """Test artifact validation with missing resource_id in metadata"""
    mock_session = Mock()
    extractor = TestExtractor(mock_session, {})
    
    artifact = {
        "cloud_provider": "aws",
        "resource_type": "test-resource",
        "metadata": {},  # Missing resource_id
        "configuration": {},
    }
    
    assert extractor.validate(artifact) is False


def test_create_metadata_object_aws():
    """Test creating metadata object for AWS resources"""
    mock_session = Mock()
    extractor = TestExtractor(mock_session, {})
    
    metadata = extractor.create_metadata_object(
        resource_id="i-1234567890",
        service="ec2",
        region="us-east-1",
        account_id="123456789012",
        tags={"Name": "test-instance", "Environment": "dev"},
    )
    
    assert metadata["resource_id"] == "i-1234567890"
    assert metadata["service"] == "ec2"
    assert metadata["region"] == "us-east-1"
    assert metadata["account_id"] == "123456789012"
    assert metadata["labels"]["Name"] == "test-instance"
    assert metadata["labels"]["Environment"] == "dev"


def test_create_metadata_object_azure():
    """Test creating metadata object for Azure resources"""
    mock_session = Mock()
    
    class AzureTestExtractor(TestExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="compute",
                version="1.0.0",
                description="Azure compute",
                resource_types=["vm"],
                cloud_provider="azure",
            )
    
    extractor = AzureTestExtractor(mock_session, {})
    
    metadata = extractor.create_metadata_object(
        resource_id="/subscriptions/sub-123/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-1",
        service="compute",
        region="eastus",
        subscription_id="sub-123",
        resource_group="rg-1",
        tags={"owner": "team-a"},
    )
    
    assert metadata["resource_id"] == "/subscriptions/sub-123/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-1"
    assert metadata["service"] == "compute"
    assert metadata["location"] == "eastus"
    assert metadata["subscription_id"] == "sub-123"
    assert metadata["resource_group"] == "rg-1"
    assert metadata["labels"]["owner"] == "team-a"


def test_create_metadata_object_gcp():
    """Test creating metadata object for GCP resources"""
    mock_session = Mock()
    
    class GCPTestExtractor(TestExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="compute",
                version="1.0.0",
                description="GCP compute",
                resource_types=["instance"],
                cloud_provider="gcp",
            )
    
    extractor = GCPTestExtractor(mock_session, {})
    
    metadata = extractor.create_metadata_object(
        resource_id="projects/my-project/zones/us-central1-a/instances/instance-1",
        service="compute",
        region="us-central1-a",
        project_id="my-project",
        labels={"env": "prod"},
    )
    
    assert metadata["resource_id"] == "projects/my-project/zones/us-central1-a/instances/instance-1"
    assert metadata["service"] == "compute"
    assert metadata["region"] == "us-central1-a"
    assert metadata["project_id"] == "my-project"
    assert metadata["labels"]["env"] == "prod"


def test_create_metadata_object_minimal():
    """Test creating metadata object with only required fields"""
    mock_session = Mock()
    extractor = TestExtractor(mock_session, {})
    
    metadata = extractor.create_metadata_object(resource_id="minimal-resource")
    
    assert metadata["resource_id"] == "minimal-resource"
    assert metadata["labels"] == {}  # labels is always included, even if empty
    assert "service" not in metadata
    assert "region" not in metadata


def test_create_metadata_object_merge_tags_and_labels():
    """Test that tags and labels are merged properly"""
    mock_session = Mock()
    extractor = TestExtractor(mock_session, {})
    
    metadata = extractor.create_metadata_object(
        resource_id="test-resource",
        tags={"tag1": "value1", "tag2": "value2"},
        labels={"label1": "labelvalue1", "tag1": "overridden"},  # label should override tag
    )
    
    assert metadata["resource_id"] == "test-resource"
    assert metadata["labels"]["tag1"] == "overridden"  # labels override tags
    assert metadata["labels"]["tag2"] == "value2"
    assert metadata["labels"]["label1"] == "labelvalue1"
