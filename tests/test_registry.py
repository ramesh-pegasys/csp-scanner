"""Tests for ExtractorRegistry."""

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.services.registry import ExtractorRegistry


class DummyExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="dummy",
            version="1.0",
            description="Dummy extractor",
            resource_types=["dummy"],
        )

    async def extract(self, region=None, filters=None):
        return [{"resource_id": "dummy"}]

    def transform(self, raw_data):
        return {
            "resource_id": "dummy",
            "resource_type": "dummy",
            "service": "dummy",
            "configuration": {},
        }


@pytest.fixture
def registry(tmp_path):
    session = SimpleNamespace()
    settings = Settings()
    with patch.object(
        ExtractorRegistry, "_register_default_extractors", lambda self: None
    ):
        reg = ExtractorRegistry(session, settings)
    extractor_config = tmp_path / "extractors.yaml"
    extractor_config.write_text("dummy:\n  option: value\n")
    reg.config.extractor_config_path = str(extractor_config)
    return reg


def test_register_and_retrieve_extractor(registry):
    registry.register(DummyExtractor)

    extractor = registry.get("dummy")
    assert extractor is not None
    assert extractor.metadata.service_name == "dummy"

    all_services = registry.list_services()
    assert "aws:dummy" in all_services

    multiple = registry.get_extractors(["dummy"])
    assert len(multiple) == 1


def test_register_invalid_extractor(caplog, registry):
    class ExplodingExtractor(DummyExtractor):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="exploding",
                version="1.0",
                description="Exploding extractor",
                resource_types=["boom"],
            )

    with caplog.at_level("ERROR"):
        registry.register(ExplodingExtractor)
    assert any("Failed to register" in message for message in caplog.messages)


def make_dummy_extractor(service_name):
    class _Extractor(DummyExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name=service_name,
                version="1.0",
                description=f"{service_name} extractor",
                resource_types=[service_name],
            )

    return _Extractor


def test_register_default_extractors(monkeypatch, registry):
    modules = {
        "app.extractors.aws.ec2": SimpleNamespace(
            EC2Extractor=make_dummy_extractor("ec2")
        ),
        "app.extractors.aws.s3": SimpleNamespace(
            S3Extractor=make_dummy_extractor("s3")
        ),
        "app.extractors.aws.rds": SimpleNamespace(
            RDSExtractor=make_dummy_extractor("rds")
        ),
        "app.extractors.aws.lambda_extractor": SimpleNamespace(
            LambdaExtractor=make_dummy_extractor("lambda")
        ),
        "app.extractors.aws.iam": SimpleNamespace(
            IAMExtractor=make_dummy_extractor("iam")
        ),
        "app.extractors.aws.vpc": SimpleNamespace(
            VPCExtractor=make_dummy_extractor("vpc")
        ),
        "app.extractors.aws.apprunner": SimpleNamespace(
            AppRunnerExtractor=make_dummy_extractor("apprunner")
        ),
        "app.extractors.aws.ecs": SimpleNamespace(
            ECSExtractor=make_dummy_extractor("ecs")
        ),
        "app.extractors.aws.eks": SimpleNamespace(
            EKSExtractor=make_dummy_extractor("eks")
        ),
        "app.extractors.aws.elb": SimpleNamespace(
            ELBExtractor=make_dummy_extractor("elb")
        ),
        "app.extractors.aws.cloudfront": SimpleNamespace(
            CloudFrontExtractor=make_dummy_extractor("cloudfront")
        ),
        "app.extractors.aws.apigateway": SimpleNamespace(
            APIGatewayExtractor=make_dummy_extractor("apigateway")
        ),
        "app.extractors.aws.kms": SimpleNamespace(
            KMSExtractor=make_dummy_extractor("kms")
        ),
    }

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    registry._register_default_extractors()
    services = registry.list_services()

    expected_services = [
        "ec2",
        "s3",
        "rds",
        "lambda",
        "iam",
        "vpc",
        "apprunner",
        "ecs",
        "eks",
        "elb",
        "cloudfront",
        "apigateway",
        "kms",
    ]
    for service_name in expected_services:
        assert f"aws:{service_name}" in services

    assert len(registry.get_extractors()) == len(services)


def test_registry_with_boto3_session_backward_compat(tmp_path):
    """Test registry with boto3.Session for backward compatibility"""
    import boto3
    from unittest.mock import MagicMock

    mock_boto_session = MagicMock(spec=boto3.Session)
    settings = Settings()

    with patch.object(
        ExtractorRegistry, "_register_default_extractors", lambda self: None
    ):
        reg = ExtractorRegistry(mock_boto_session, settings)

    # Should have wrapped the boto3 session as AWS session
    from app.cloud.base import CloudProvider

    assert CloudProvider.AWS in reg.sessions


def test_registry_with_cloud_session_dict():
    """Test registry with CloudSession dict"""
    from app.cloud.base import CloudProvider

    aws_session = SimpleNamespace()
    azure_session = SimpleNamespace()

    sessions = {
        CloudProvider.AWS: aws_session,
        CloudProvider.AZURE: azure_session,
    }

    settings = Settings()
    with patch.object(
        ExtractorRegistry, "_register_default_extractors", lambda self: None
    ):
        reg = ExtractorRegistry(sessions, settings)

    assert CloudProvider.AWS in reg.sessions
    assert CloudProvider.AZURE in reg.sessions
    assert reg.sessions[CloudProvider.AWS] == aws_session
    assert reg.sessions[CloudProvider.AZURE] == azure_session


def test_register_azure_extractors_import_error(registry, monkeypatch, caplog):
    """Test Azure extractor registration when imports fail"""
    from app.cloud.base import CloudProvider

    # Add Azure session
    registry.sessions[CloudProvider.AZURE] = SimpleNamespace()

    # Mock the import to fail
    def mock_import(name, *args, **kwargs):
        if "azure" in name:
            raise ImportError("Azure SDK not installed")
        return __import__(name, *args, **kwargs)

    with caplog.at_level("WARNING"):
        with patch("builtins.__import__", side_effect=mock_import):
            registry._register_azure_extractors()

    assert any(
        "Azure extractors not available" in message for message in caplog.messages
    )


def test_register_gcp_extractors_import_error(registry, monkeypatch, caplog):
    """Test GCP extractor registration when imports fail"""
    from app.cloud.base import CloudProvider

    # Add GCP session
    registry.sessions[CloudProvider.GCP] = SimpleNamespace()

    # Mock the import to fail
    def mock_import(name, *args, **kwargs):
        if "gcp" in name:
            raise ImportError("GCP SDK not installed")
        return __import__(name, *args, **kwargs)

    with caplog.at_level("WARNING"):
        with patch("builtins.__import__", side_effect=mock_import):
            registry._register_gcp_extractors()

    assert any("GCP extractors not available" in message for message in caplog.messages)


def test_get_extractor_with_provider(registry):
    """Test getting extractor with specific provider"""
    from app.cloud.base import CloudProvider

    registry.register(DummyExtractor)

    # Get with provider specified
    extractor = registry.get("dummy", provider=CloudProvider.AWS)
    assert extractor is not None
    assert extractor.metadata.service_name == "dummy"

    # Try to get with wrong provider
    extractor = registry.get("dummy", provider=CloudProvider.AZURE)
    assert extractor is None


def test_get_extractors_filtered_by_provider(registry):
    """Test getting extractors filtered by provider"""
    from app.cloud.base import CloudProvider
    from unittest.mock import MagicMock

    # Create extractors for different providers
    class AzureDummyExtractor(DummyExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="azuredummy",
                version="1.0",
                description="Azure dummy",
                resource_types=["azuredummy"],
                cloud_provider="azure",
            )

    registry.register(DummyExtractor)

    # Manually add Azure extractor
    mock_azure_session = MagicMock()
    registry.sessions[CloudProvider.AZURE] = mock_azure_session
    azure_extractor = AzureDummyExtractor(mock_azure_session, {})
    registry._extractors["azure:azuredummy"] = azure_extractor

    # Get all extractors
    all_extractors = registry.get_extractors()
    assert len(all_extractors) == 2

    # Get only AWS extractors
    aws_extractors = registry.get_extractors(provider=CloudProvider.AWS)
    assert len(aws_extractors) == 1
    assert aws_extractors[0].metadata.service_name == "dummy"

    # Get only Azure extractors
    azure_extractors = registry.get_extractors(provider=CloudProvider.AZURE)
    assert len(azure_extractors) == 1
    assert azure_extractors[0].metadata.service_name == "azuredummy"


def test_list_services_filtered_by_provider(registry):
    """Test listing services filtered by provider"""
    from app.cloud.base import CloudProvider
    from unittest.mock import MagicMock

    class AzureDummyExtractor(DummyExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="azuredummy",
                version="1.0",
                description="Azure dummy",
                resource_types=["azuredummy"],
                cloud_provider="azure",
            )

    registry.register(DummyExtractor)

    # Manually add Azure extractor
    mock_azure_session = MagicMock()
    registry.sessions[CloudProvider.AZURE] = mock_azure_session
    azure_extractor = AzureDummyExtractor(mock_azure_session, {})
    registry._extractors["azure:azuredummy"] = azure_extractor

    # List all services
    all_services = registry.list_services()
    assert len(all_services) == 2
    assert "aws:dummy" in all_services
    assert "azure:azuredummy" in all_services

    # List only AWS services
    aws_services = registry.list_services(provider=CloudProvider.AWS)
    assert len(aws_services) == 1
    assert "aws:dummy" in aws_services

    # List only Azure services
    azure_services = registry.list_services(provider=CloudProvider.AZURE)
    assert len(azure_services) == 1
    assert "azure:azuredummy" in azure_services


def test_register_azure_extractors_success(monkeypatch, tmp_path):
    """Test Azure extractor registration when Azure session is available"""
    from app.cloud.base import CloudProvider

    # Create registry with Azure session
    azure_session = SimpleNamespace()
    sessions = {CloudProvider.AZURE: azure_session}
    settings = Settings()

    # Mock Azure extractors
    azure_modules = {
        "app.extractors.azure.compute": SimpleNamespace(
            AzureComputeExtractor=make_dummy_extractor("compute")
        ),
        "app.extractors.azure.storage": SimpleNamespace(
            AzureStorageExtractor=make_dummy_extractor("storage")
        ),
        "app.extractors.azure.network": SimpleNamespace(
            AzureNetworkExtractor=make_dummy_extractor("network")
        ),
        "app.extractors.azure.authorization": SimpleNamespace(
            AzureAuthorizationExtractor=make_dummy_extractor("authorization")
        ),
        "app.extractors.azure.containerservice": SimpleNamespace(
            AzureContainerServiceExtractor=make_dummy_extractor("containerservice")
        ),
        "app.extractors.azure.keyvault": SimpleNamespace(
            AzureKeyVaultExtractor=make_dummy_extractor("keyvault")
        ),
        "app.extractors.azure.sql": SimpleNamespace(
            AzureSQLExtractor=make_dummy_extractor("sql")
        ),
        "app.extractors.azure.web": SimpleNamespace(
            AzureWebExtractor=make_dummy_extractor("web")
        ),
    }

    for name, module in azure_modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    with patch.object(
        ExtractorRegistry, "_register_default_extractors", lambda self: None
    ):
        reg = ExtractorRegistry(sessions, settings)

    # Manually call Azure registration
    reg._register_azure_extractors()

    services = reg.list_services()
    expected_azure_services = [
        "azure:compute",
        "azure:storage",
        "azure:network",
        "azure:authorization",
        "azure:containerservice",
        "azure:keyvault",
        "azure:sql",
        "azure:web",
    ]

    for service in expected_azure_services:
        assert service in services


def test_register_gcp_extractors_success(monkeypatch, tmp_path):
    """Test GCP extractor registration when GCP session is available"""
    from app.cloud.base import CloudProvider

    # Create registry with GCP session
    gcp_session = SimpleNamespace()
    sessions = {CloudProvider.GCP: gcp_session}
    settings = Settings()

    # Mock GCP extractors (just a few key ones for coverage)
    gcp_modules = {
        "app.extractors.gcp.compute": SimpleNamespace(
            GCPComputeExtractor=make_dummy_extractor("compute")
        ),
        "app.extractors.gcp.storage": SimpleNamespace(
            GCPStorageExtractor=make_dummy_extractor("storage")
        ),
        "app.extractors.gcp.iam": SimpleNamespace(
            GCPIAMExtractor=make_dummy_extractor("iam")
        ),
        "app.extractors.gcp.bigquery": SimpleNamespace(
            GCPBigQueryExtractor=make_dummy_extractor("bigquery")
        ),
        "app.extractors.gcp.cloudbuild": SimpleNamespace(
            GCPCloudBuildExtractor=make_dummy_extractor("cloudbuild")
        ),
        "app.extractors.gcp.cloudrun": SimpleNamespace(
            GCPCloudRunExtractor=make_dummy_extractor("cloudrun")
        ),
        "app.extractors.gcp.kubernetes": SimpleNamespace(
            GCPKubernetesExtractor=make_dummy_extractor("kubernetes")
        ),
        "app.extractors.gcp.networking": SimpleNamespace(
            GCPNetworkingExtractor=make_dummy_extractor("networking")
        ),
        "app.extractors.gcp.firestore": SimpleNamespace(
            GCPFirestoreExtractor=make_dummy_extractor("firestore")
        ),
        "app.extractors.gcp.bigtable": SimpleNamespace(
            GCPBigtableExtractor=make_dummy_extractor("bigtable")
        ),
        "app.extractors.gcp.pubsub": SimpleNamespace(
            GCPPubSubExtractor=make_dummy_extractor("pubsub")
        ),
        "app.extractors.gcp.dataflow": SimpleNamespace(
            GCPDataflowExtractor=make_dummy_extractor("dataflow")
        ),
        "app.extractors.gcp.dataproc": SimpleNamespace(
            GCPDataprocExtractor=make_dummy_extractor("dataproc")
        ),
        "app.extractors.gcp.spanner": SimpleNamespace(
            GCPSpannerExtractor=make_dummy_extractor("spanner")
        ),
        "app.extractors.gcp.memorystore": SimpleNamespace(
            GCPMemorystoreExtractor=make_dummy_extractor("memorystore")
        ),
        "app.extractors.gcp.dns": SimpleNamespace(
            GCPDNSExtractor=make_dummy_extractor("dns")
        ),
        "app.extractors.gcp.logging": SimpleNamespace(
            GCPLoggingExtractor=make_dummy_extractor("logging")
        ),
        "app.extractors.gcp.monitoring": SimpleNamespace(
            GCPMonitoringExtractor=make_dummy_extractor("monitoring")
        ),
        "app.extractors.gcp.filestore": SimpleNamespace(
            GCPFilestoreExtractor=make_dummy_extractor("filestore")
        ),
        "app.extractors.gcp.iap": SimpleNamespace(
            GCPIAPExtractor=make_dummy_extractor("iap")
        ),
        "app.extractors.gcp.resource_manager": SimpleNamespace(
            GCPResourceManagerExtractor=make_dummy_extractor("resource_manager")
        ),
        "app.extractors.gcp.billing": SimpleNamespace(
            GCPBillingExtractor=make_dummy_extractor("billing")
        ),
        "app.extractors.gcp.tasks": SimpleNamespace(
            GCPTasksExtractor=make_dummy_extractor("tasks")
        ),
        "app.extractors.gcp.scheduler": SimpleNamespace(
            GCPSchedulerExtractor=make_dummy_extractor("scheduler")
        ),
        "app.extractors.gcp.functions": SimpleNamespace(
            GCPFunctionsExtractor=make_dummy_extractor("functions")
        ),
        "app.extractors.gcp.armor": SimpleNamespace(
            GCPArmorExtractor=make_dummy_extractor("armor")
        ),
        "app.extractors.gcp.interconnect": SimpleNamespace(
            GCPInterconnectExtractor=make_dummy_extractor("interconnect")
        ),
        "app.extractors.gcp.loadbalancer": SimpleNamespace(
            GCPLoadBalancerExtractor=make_dummy_extractor("loadbalancer")
        ),
    }

    for name, module in gcp_modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    with patch.object(
        ExtractorRegistry, "_register_default_extractors", lambda self: None
    ):
        reg = ExtractorRegistry(sessions, settings)

    # Manually call GCP registration
    reg._register_gcp_extractors()

    services = reg.list_services()
    # Check that some GCP services are registered
    assert any(service.startswith("gcp:") for service in services)


def test_get_extractor_fallback_search(registry):
    """Test get method fallback search when no provider specified"""
    from app.cloud.base import CloudProvider
    from unittest.mock import MagicMock

    # Register extractors for different providers
    registry.register(DummyExtractor)

    # Manually add Azure extractor with same service name
    class AzureDummyExtractor(DummyExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="dummy",
                version="1.0",
                description="Azure dummy",
                resource_types=["dummy"],
                cloud_provider="azure",
            )

    mock_azure_session = MagicMock()
    mock_azure_session.provider = CloudProvider.AZURE
    registry.sessions[CloudProvider.AZURE] = mock_azure_session
    azure_extractor = AzureDummyExtractor(mock_azure_session, {})
    registry._extractors["azure:dummy"] = azure_extractor

    # Manually add an extractor with key exactly matching service name
    registry._extractors["dummy"] = azure_extractor

    # Get without provider should return one of them (first match)
    extractor = registry.get("dummy")
    assert extractor is not None
    assert extractor.metadata.service_name == "dummy"


def test_register_deprecated_method(registry):
    """Test the deprecated register method"""
    # The register method should work for backward compatibility
    registry.register(DummyExtractor)

    extractor = registry.get("dummy")
    assert extractor is not None
    assert extractor.metadata.service_name == "dummy"


def test_register_extractor_edge_cases(registry, caplog):
    """Test edge cases in _register_extractor method"""
    from app.cloud.base import CloudProvider
    from unittest.mock import MagicMock

    # Test with extractor that has no config
    class NoConfigExtractor(DummyExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="noconfig",
                version="1.0",
                description="No config extractor",
                resource_types=["noconfig"],
            )

    mock_session = MagicMock()
    mock_session.provider = CloudProvider.AWS
    reg = ExtractorRegistry({CloudProvider.AWS: mock_session}, Settings())

    # Should handle missing config gracefully
    reg._register_extractor(NoConfigExtractor, mock_session, {}, CloudProvider.AWS)

    extractor = reg.get("noconfig", CloudProvider.AWS)
    assert extractor is not None
