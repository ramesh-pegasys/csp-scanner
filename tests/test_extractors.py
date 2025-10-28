"""Tests for extractors"""

import pytest
from unittest.mock import Mock, patch
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.extractors.s3 import S3Extractor
from app.extractors.ec2 import EC2Extractor
from app.extractors.apigateway import APIGatewayExtractor
from app.extractors.apprunner import AppRunnerExtractor
from app.extractors.cloudfront import CloudFrontExtractor
from app.extractors.ecs import ECSExtractor
from app.extractors.eks import EKSExtractor
from app.extractors.elb import ELBExtractor
from app.extractors.iam import IAMExtractor
from app.extractors.kms import KMSExtractor
from app.extractors.lambda_extractor import LambdaExtractor
from app.extractors.rds import RDSExtractor
from app.extractors.vpc import VPCExtractor


def test_extractor_metadata():
    """Test ExtractorMetadata dataclass"""
    metadata = ExtractorMetadata(
        service_name="test-service",
        version="1.0.0",
        description="Test extractor",
        resource_types=["bucket", "object"],
        supports_regions=True,
        requires_pagination=False,
    )

    assert metadata.service_name == "test-service"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Test extractor"
    assert metadata.resource_types == ["bucket", "object"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is False


def test_base_extractor_validation_valid():
    """Test base extractor validation with valid artifact"""
    mock_session = Mock()
    mock_config = {}

    # Create a concrete implementation for testing
    class TestExtractor(BaseExtractor):
        def get_metadata(self):
            return ExtractorMetadata(
                service_name="test",
                version="1.0.0",
                description="Test",
                resource_types=["test"],
            )

        async def extract(self, region=None, filters=None):
            return []

        def transform(self, raw_data):
            return {}

    extractor = TestExtractor(mock_session, mock_config)

    valid_artifact = {
        "resource_id": "test-123",
        "resource_type": "test",
        "service": "test",
        "configuration": {"key": "value"},
    }

    assert extractor.validate(valid_artifact) is True


def test_base_extractor_validation_invalid():
    """Test base extractor validation with invalid artifact"""
    mock_session = Mock()
    mock_config = {}

    class TestExtractor(BaseExtractor):
        def get_metadata(self):
            return ExtractorMetadata(
                service_name="test",
                version="1.0.0",
                description="Test",
                resource_types=["test"],
            )

        async def extract(self, region=None, filters=None):
            return []

        def transform(self, raw_data):
            return {}

    extractor = TestExtractor(mock_session, mock_config)

    invalid_artifact = {
        "resource_id": "test-123",
        "resource_type": "test",
        # Missing service and configuration
    }

    assert extractor.validate(invalid_artifact) is False


def test_s3_extractor_metadata():
    """Test S3 extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = S3Extractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "s3"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Extracts S3 buckets and their configurations"
    assert metadata.resource_types == ["bucket"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is False


def test_s3_extractor_initialization():
    """Test S3 extractor initialization"""
    mock_session = Mock()
    mock_config = {"enabled": True}

    extractor = S3Extractor(mock_session, mock_config)

    assert extractor.session == mock_session
    assert extractor.config == mock_config
    assert extractor.metadata.service_name == "s3"


def test_ec2_extractor_metadata():
    """Test EC2 extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = EC2Extractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "ec2"
    assert metadata.version == "1.0.0"
    assert (
        metadata.description
        == "Extracts EC2 instances, security groups, and network interfaces"
    )
    assert metadata.resource_types == [
        "instance",
        "security-group",
        "network-interface",
    ]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


def test_ec2_extractor_initialization():
    """Test EC2 extractor initialization"""
    mock_session = Mock()
    mock_config = {"max_workers": 5}

    extractor = EC2Extractor(mock_session, mock_config)

    assert extractor.session == mock_session
    assert extractor.config == mock_config


@pytest.mark.asyncio
async def test_ec2_extractor_extract_single_region():
    """Test EC2 extraction from single region"""
    mock_session = Mock()
    mock_config = {}

    extractor = EC2Extractor(mock_session, mock_config)

    # Mock the _extract_region method
    mock_instances = [{"resource_id": "i-123", "resource_type": "instance"}]
    with patch.object(
        extractor, "_extract_region", return_value=mock_instances
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "i-123"
        mock_extract.assert_called_once_with("us-east-1", None)


@pytest.mark.asyncio
async def test_ec2_extractor_extract_multiple_regions():
    """Test EC2 extraction from multiple regions"""
    mock_session = Mock()
    mock_config = {}

    extractor = EC2Extractor(mock_session, mock_config)

    # Mock _get_all_regions and _extract_region
    with patch.object(
        extractor, "_get_all_regions", return_value=["us-east-1", "us-west-2"]
    ), patch.object(extractor, "_extract_region") as mock_extract:
        mock_extract.side_effect = [
            [{"resource_id": "i-123", "resource_type": "instance"}],
            [{"resource_id": "i-456", "resource_type": "instance"}],
        ]

        artifacts = await extractor.extract()

        assert len(artifacts) == 2
        assert mock_extract.call_count == 2


def test_ec2_extractor_get_all_regions():
    """Test getting all regions"""
    mock_session = Mock()
    mock_config = {}

    extractor = EC2Extractor(mock_session, mock_config)

    # Mock EC2 client
    mock_client = Mock()
    mock_session.client.return_value = mock_client
    mock_client.describe_regions.return_value = {
        "Regions": [
            {"RegionName": "us-east-1"},
            {"RegionName": "us-west-2"},
            {"RegionName": "eu-west-1"},
        ]
    }

    regions = extractor._get_all_regions()
    assert regions == ["us-east-1", "us-west-2", "eu-west-1"]
    mock_session.client.assert_called_once_with("ec2")


# API Gateway Extractor Tests
def test_apigateway_extractor_metadata():
    """Test API Gateway extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = APIGatewayExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "apigateway"
    assert metadata.version == "1.0.0"
    assert (
        metadata.description
        == "Extracts API Gateway REST APIs, resources, methods, and deployments"
    )
    assert metadata.resource_types == [
        "rest-api",
        "resource",
        "method",
        "deployment",
        "stage",
    ]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_apigateway_extractor_extract_no_region():
    """Test API Gateway extraction without region"""
    mock_session = Mock()
    mock_config = {}

    extractor = APIGatewayExtractor(mock_session, mock_config)

    artifacts = await extractor.extract()
    assert artifacts == []


@pytest.mark.asyncio
async def test_apigateway_extractor_extract_with_region():
    """Test API Gateway extraction with region"""
    mock_session = Mock()
    mock_config = {}

    extractor = APIGatewayExtractor(mock_session, mock_config)

    # Mock the _extract_rest_apis method
    mock_apis = [{"resource_id": "api1", "resource_type": "apigateway:rest-api"}]
    with patch.object(
        extractor, "_extract_rest_apis", return_value=mock_apis
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "api1"
        mock_extract.assert_called_once_with("us-east-1", None)


def test_apigateway_extractor_transform_rest_api():
    """Test API Gateway REST API transformation"""
    mock_session = Mock()
    mock_config = {}

    extractor = APIGatewayExtractor(mock_session, mock_config)

    raw_data = {
        "resource": {
            "id": "api123",
            "name": "Test API",
            "description": "Test description",
            "createdDate": "2023-01-01T00:00:00Z",
            "apiKeySourceType": "HEADER",
            "endpointConfiguration": {"types": ["REGIONAL"]},
            "version": "1.0",
        },
        "resource_type": "rest-api",
        "region": "us-east-1",
    }

    result = extractor.transform(raw_data)

    assert result["resource_id"] == "api123"
    assert result["resource_type"] == "apigateway:rest-api"
    assert result["service"] == "apigateway"
    assert result["region"] == "us-east-1"
    assert result["configuration"]["name"] == "Test API"
    assert result["configuration"]["version"] == "1.0"


# App Runner Extractor Tests
def test_apprunner_extractor_metadata():
    """Test App Runner extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = AppRunnerExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "apprunner"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Extracts App Runner services and configurations"
    assert metadata.resource_types == ["service", "connection"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_apprunner_extractor_extract():
    """Test App Runner extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = AppRunnerExtractor(mock_session, mock_config)

    # Mock the _extract_services method
    mock_services = [{"resource_id": "service1", "resource_type": "apprunner:service"}]
    with patch.object(
        extractor, "_extract_services", return_value=mock_services
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "service1"
        mock_extract.assert_called_once_with("us-east-1", None)


# CloudFront Extractor Tests
def test_cloudfront_extractor_metadata():
    """Test CloudFront extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = CloudFrontExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "cloudfront"
    assert metadata.version == "1.0.0"
    assert (
        metadata.description
        == "Extracts CloudFront distributions, origins, and cache behaviors"
    )
    assert metadata.resource_types == ["distribution", "origin-access-identity"]
    assert metadata.supports_regions is False
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_cloudfront_extractor_extract():
    """Test CloudFront extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = CloudFrontExtractor(mock_session, mock_config)

    # Mock the _extract_distributions method
    mock_distributions = [
        {"resource_id": "dist1", "resource_type": "cloudfront:distribution"}
    ]
    with patch.object(
        extractor, "_extract_distributions", return_value=mock_distributions
    ) as mock_extract:
        artifacts = await extractor.extract()

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "dist1"
        mock_extract.assert_called_once_with(None)


# ECS Extractor Tests
def test_ecs_extractor_metadata():
    """Test ECS extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = ECSExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "ecs"
    assert metadata.version == "1.0.0"
    assert (
        metadata.description
        == "Extracts ECS clusters, services, tasks, and task definitions"
    )
    assert metadata.resource_types == ["cluster", "service", "task", "task-definition"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_ecs_extractor_extract():
    """Test ECS extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = ECSExtractor(mock_session, mock_config)

    # Mock the _extract_clusters method
    mock_clusters = [{"resource_id": "cluster1", "resource_type": "ecs:cluster"}]
    with patch.object(
        extractor, "_extract_clusters", return_value=mock_clusters
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "cluster1"
        mock_extract.assert_called_once_with("us-east-1", None)


# EKS Extractor Tests
def test_eks_extractor_metadata():
    """Test EKS extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = EKSExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "eks"
    assert metadata.version == "1.0.0"
    assert (
        metadata.description
        == "Extracts EKS clusters, node groups, and Fargate profiles"
    )
    assert metadata.resource_types == ["cluster", "nodegroup", "fargate-profile"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_eks_extractor_extract():
    """Test EKS extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = EKSExtractor(mock_session, mock_config)

    # Mock the _extract_clusters method
    mock_clusters = [{"resource_id": "cluster1", "resource_type": "eks:cluster"}]
    with patch.object(
        extractor, "_extract_clusters", return_value=mock_clusters
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "cluster1"
        mock_extract.assert_called_once_with("us-east-1", None)


# ELB Extractor Tests
def test_elb_extractor_metadata():
    """Test ELB extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = ELBExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "elb"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Extracts ELB load balancers (ALB, NLB, CLB)"
    assert metadata.resource_types == ["load-balancer", "target-group"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_elb_extractor_extract():
    """Test ELB extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = ELBExtractor(mock_session, mock_config)

    # Mock the _extract_load_balancers method
    mock_lbs = [{"resource_id": "lb1", "resource_type": "elb:load-balancer"}]
    with patch.object(
        extractor, "_extract_load_balancers", return_value=mock_lbs
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "lb1"
        mock_extract.assert_called_once_with("us-east-1", None)


# IAM Extractor Tests
def test_iam_extractor_metadata():
    """Test IAM extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = IAMExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "iam"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Extracts IAM users, roles, policies, and groups"
    assert metadata.resource_types == ["user", "role", "policy", "group"]
    assert metadata.supports_regions is False
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_iam_extractor_extract():
    """Test IAM extraction"""
    mock_session = Mock()
    mock_config = {}
    mock_client = Mock()
    mock_session.client.return_value = mock_client

    extractor = IAMExtractor(mock_session, mock_config)

    # Mock the _extract_users method
    mock_users = [{"resource_id": "user1", "resource_type": "iam:user"}]
    with patch.object(
        extractor, "_extract_users", return_value=mock_users
    ) as mock_extract:
        artifacts = await extractor.extract()

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "user1"
        mock_extract.assert_called_once_with(mock_client)


# KMS Extractor Tests
def test_kms_extractor_metadata():
    """Test KMS extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = KMSExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "kms"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Extracts KMS keys, aliases, and grants"
    assert metadata.resource_types == ["key", "alias", "grant"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_kms_extractor_extract():
    """Test KMS extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = KMSExtractor(mock_session, mock_config)

    # Mock the _extract_keys method
    mock_keys = [{"resource_id": "key1", "resource_type": "kms:key"}]
    with patch.object(
        extractor, "_extract_keys", return_value=mock_keys
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "key1"
        mock_extract.assert_called_once_with("us-east-1", None)


# Lambda Extractor Tests
def test_lambda_extractor_metadata():
    """Test Lambda extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = LambdaExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "lambda"
    assert metadata.version == "1.0.0"
    assert (
        metadata.description
        == "Extracts Lambda functions, layers, and event source mappings"
    )
    assert metadata.resource_types == ["function", "layer", "event-source-mapping"]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_lambda_extractor_extract():
    """Test Lambda extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = LambdaExtractor(mock_session, mock_config)

    # Mock the _extract_region method
    mock_functions = [{"resource_id": "func1", "resource_type": "lambda:function"}]
    with patch.object(
        extractor, "_extract_region", return_value=mock_functions
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "func1"
        mock_extract.assert_called_once_with("us-east-1", None)


# RDS Extractor Tests
def test_rds_extractor_metadata():
    """Test RDS extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = RDSExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "rds"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Extracts RDS DB instances, clusters, and snapshots"
    assert metadata.resource_types == [
        "db-instance",
        "db-cluster",
        "db-snapshot",
        "db-cluster-snapshot",
    ]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_rds_extractor_extract():
    """Test RDS extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = RDSExtractor(mock_session, mock_config)

    # Mock the _extract_region method
    mock_instances = [{"resource_id": "db1", "resource_type": "rds:db-instance"}]
    with patch.object(
        extractor, "_extract_region", return_value=mock_instances
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "db1"
        mock_extract.assert_called_once_with("us-east-1", None)


# VPC Extractor Tests
def test_vpc_extractor_metadata():
    """Test VPC extractor metadata"""
    mock_session = Mock()
    mock_config = {}

    extractor = VPCExtractor(mock_session, mock_config)

    metadata = extractor.metadata
    assert metadata.service_name == "vpc"
    assert metadata.version == "1.0.0"
    assert (
        metadata.description
        == "Extracts VPCs, subnets, internet gateways, NAT gateways, route tables, and network ACLs"
    )
    assert metadata.resource_types == [
        "vpc",
        "subnet",
        "internet-gateway",
        "nat-gateway",
        "route-table",
        "network-acl",
    ]
    assert metadata.supports_regions is True
    assert metadata.requires_pagination is True


@pytest.mark.asyncio
async def test_vpc_extractor_extract():
    """Test VPC extraction"""
    mock_session = Mock()
    mock_config = {}

    extractor = VPCExtractor(mock_session, mock_config)

    # Mock the _extract_region method
    mock_vpcs = [{"resource_id": "vpc1", "resource_type": "vpc:vpc"}]
    with patch.object(
        extractor, "_extract_region", return_value=mock_vpcs
    ) as mock_extract:
        artifacts = await extractor.extract(region="us-east-1")

        assert len(artifacts) == 1
        assert artifacts[0]["resource_id"] == "vpc1"
        mock_extract.assert_called_once_with("us-east-1", None)
