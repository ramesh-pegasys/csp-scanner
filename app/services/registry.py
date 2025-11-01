# app/services/registry.py
from typing import Dict, List, Type, Optional, Any, Union, cast
from app.extractors.base import BaseExtractor
from app.core.config import Settings
from app.cloud.base import CloudProvider, CloudSession
import logging

logger = logging.getLogger(__name__)

# Protocol describing extractor constructor signature so mypy
# doesn't require the passed class to be a non-abstract concrete
# subclass of BaseExtractor. We only need the constructor shape
# for instantiation here.
# Use a permissive type for extractor classes. Mypy raises
# "type-abstract" when a potentially-abstract class is passed
# where Type[BaseExtractor] is expected. We accept any class
# here and cast after instantiation to BaseExtractor.
ConcreteExtractor = Type[Any]


class ExtractorRegistry:
    """Registry for managing extractors across multiple cloud providers"""

    def __init__(
        self, sessions: Union[Any, Dict[CloudProvider, CloudSession]], config: Settings
    ):
        # Support both old single session and new multi-session dict
        if isinstance(sessions, dict):
            self.sessions = sessions
        else:
            # Backward compatibility: wrap single session as AWS
            from app.cloud.aws_session import AWSSession
            import boto3  # type: ignore[import-untyped]

            if isinstance(sessions, boto3.Session):
                self.sessions = {CloudProvider.AWS: AWSSession(sessions)}
            else:
                self.sessions = {CloudProvider.AWS: sessions}

        self.config = config
        self._extractors: Dict[str, BaseExtractor] = {}
        self._register_default_extractors()

    def _register_default_extractors(self):
        """Register all available extractors for enabled cloud providers"""
        # Register AWS extractors if AWS is enabled
        if CloudProvider.AWS in self.sessions:
            self._register_aws_extractors()

        # Register Azure extractors if Azure is enabled
        if CloudProvider.AZURE in self.sessions:
            self._register_azure_extractors()

        # Register GCP extractors if GCP is enabled
        if CloudProvider.GCP in self.sessions:
            self._register_gcp_extractors()

    def _register_aws_extractors(self):
        """Register AWS extractors"""
        from app.extractors.aws.ec2 import EC2Extractor
        from app.extractors.aws.s3 import S3Extractor
        from app.extractors.aws.rds import RDSExtractor
        from app.extractors.aws.lambda_extractor import LambdaExtractor
        from app.extractors.aws.iam import IAMExtractor
        from app.extractors.aws.vpc import VPCExtractor
        from app.extractors.aws.apprunner import AppRunnerExtractor
        from app.extractors.aws.ecs import ECSExtractor
        from app.extractors.aws.eks import EKSExtractor
        from app.extractors.aws.elb import ELBExtractor
        from app.extractors.aws.cloudfront import CloudFrontExtractor
        from app.extractors.aws.apigateway import APIGatewayExtractor
        from app.extractors.aws.kms import KMSExtractor

        extractor_classes = [
            EC2Extractor,
            S3Extractor,
            RDSExtractor,
            LambdaExtractor,
            IAMExtractor,
            VPCExtractor,
            AppRunnerExtractor,
            ECSExtractor,
            EKSExtractor,
            ELBExtractor,
            CloudFrontExtractor,
            APIGatewayExtractor,
            KMSExtractor,
        ]

        aws_sessions = self.sessions[CloudProvider.AWS]
        aws_config = self.config.extractors.get("aws", {})

        # Handle both list and single session
        if isinstance(aws_sessions, list):
            session_entries = aws_sessions
        else:
            # Fallback: single session object, wrap in list
            session_entries = [
                {
                    "session": aws_sessions,
                    "account_id": getattr(aws_sessions, "account_id", "unknown"),
                    "regions": getattr(aws_sessions, "regions", ["us-west-2"]),
                }
            ]

        for aws_entry in session_entries:
            aws_session = aws_entry["session"]
            for extractor_class in extractor_classes:
                # Key includes account_id for uniqueness if needed
                self._register_extractor(
                    extractor_class, aws_session, aws_config, CloudProvider.AWS
                )

    def _register_azure_extractors(self):
        """Register Azure extractors"""
        try:
            from app.extractors.azure.compute import AzureComputeExtractor
            from app.extractors.azure.storage import AzureStorageExtractor
            from app.extractors.azure.network import AzureNetworkExtractor
            from app.extractors.azure.authorization import AzureAuthorizationExtractor
            from app.extractors.azure.containerservice import (
                AzureContainerServiceExtractor,
            )
            from app.extractors.azure.keyvault import AzureKeyVaultExtractor
            from app.extractors.azure.sql import AzureSQLExtractor
            from app.extractors.azure.web import AzureWebExtractor

            extractor_classes = [
                AzureComputeExtractor,  # type: ignore[type-abstract]
                AzureStorageExtractor,  # type: ignore[type-abstract]
                AzureNetworkExtractor,  # type: ignore[type-abstract]
                AzureAuthorizationExtractor,  # type: ignore[type-abstract]
                AzureContainerServiceExtractor,  # type: ignore[type-abstract]
                AzureKeyVaultExtractor,  # type: ignore[type-abstract]
                AzureSQLExtractor,  # type: ignore[type-abstract]
                AzureWebExtractor,  # type: ignore[type-abstract]
            ]

            azure_sessions = self.sessions[CloudProvider.AZURE]
            azure_config = self.config.extractors.get("azure", {})

            # Handle both list and single session
            if isinstance(azure_sessions, list):
                session_entries = azure_sessions
            else:
                # Fallback: single session object, wrap in list
                session_entries = [
                    {
                        "session": azure_sessions,
                        "subscription_id": getattr(
                            azure_sessions, "subscription_id", "unknown"
                        ),
                        "locations": getattr(azure_sessions, "locations", ["eastus"]),
                    }
                ]

            for az_entry in session_entries:
                azure_session = az_entry["session"]
                for extractor_class in extractor_classes:
                    # Key includes subscription_id for uniqueness if needed
                    self._register_extractor(
                        extractor_class,
                        azure_session,
                        azure_config,
                        CloudProvider.AZURE,
                    )  # type: ignore[type-abstract]
        except ImportError as e:
            logger.warning(f"Azure extractors not available: {e}")

    def _register_gcp_extractors(self):
        """Register GCP extractors for each project/session"""
        try:
            from app.extractors.gcp.compute import GCPComputeExtractor
            from app.extractors.gcp.storage import GCPStorageExtractor
            from app.extractors.gcp.iam import GCPIAMExtractor
            from app.extractors.gcp.bigquery import GCPBigQueryExtractor
            from app.extractors.gcp.cloudbuild import GCPCloudBuildExtractor
            from app.extractors.gcp.cloudrun import GCPCloudRunExtractor
            from app.extractors.gcp.kubernetes import GCPKubernetesExtractor
            from app.extractors.gcp.networking import GCPNetworkingExtractor
            from app.extractors.gcp.firestore import GCPFirestoreExtractor
            from app.extractors.gcp.bigtable import GCPBigtableExtractor
            from app.extractors.gcp.pubsub import GCPPubSubExtractor
            from app.extractors.gcp.dataflow import GCPDataflowExtractor
            from app.extractors.gcp.dataproc import GCPDataprocExtractor
            from app.extractors.gcp.spanner import GCPSpannerExtractor
            from app.extractors.gcp.memorystore import GCPMemorystoreExtractor
            from app.extractors.gcp.dns import GCPDNSExtractor
            from app.extractors.gcp.logging import GCPLoggingExtractor
            from app.extractors.gcp.monitoring import GCPMonitoringExtractor
            from app.extractors.gcp.filestore import GCPFilestoreExtractor
            from app.extractors.gcp.iap import GCPIAPExtractor
            from app.extractors.gcp.resource_manager import GCPResourceManagerExtractor
            from app.extractors.gcp.billing import GCPBillingExtractor
            from app.extractors.gcp.tasks import GCPTasksExtractor
            from app.extractors.gcp.scheduler import GCPSchedulerExtractor
            from app.extractors.gcp.functions import GCPFunctionsExtractor
            from app.extractors.gcp.armor import GCPArmorExtractor
            from app.extractors.gcp.interconnect import GCPInterconnectExtractor
            from app.extractors.gcp.loadbalancer import GCPLoadBalancerExtractor

            extractor_classes = [
                GCPComputeExtractor,
                GCPStorageExtractor,
                GCPIAMExtractor,
                GCPBigQueryExtractor,
                GCPCloudBuildExtractor,
                GCPCloudRunExtractor,
                GCPKubernetesExtractor,
                GCPNetworkingExtractor,
                GCPFirestoreExtractor,
                GCPBigtableExtractor,
                GCPPubSubExtractor,
                GCPDataflowExtractor,
                GCPDataprocExtractor,
                GCPSpannerExtractor,
                GCPMemorystoreExtractor,
                GCPDNSExtractor,
                GCPLoggingExtractor,
                GCPMonitoringExtractor,
                GCPFilestoreExtractor,
                GCPIAPExtractor,
                GCPResourceManagerExtractor,
                GCPBillingExtractor,
                GCPTasksExtractor,
                GCPSchedulerExtractor,
                GCPFunctionsExtractor,
                GCPArmorExtractor,
                GCPInterconnectExtractor,
                GCPLoadBalancerExtractor,
            ]

            gcp_sessions = self.sessions[CloudProvider.GCP]
            gcp_config = self.config.extractors.get("gcp", {})

            # Handle both list and single session
            if isinstance(gcp_sessions, list):
                session_entries = gcp_sessions
            else:
                # Fallback: single session object, wrap in list
                session_entries = [
                    {
                        "session": gcp_sessions,
                        "project_id": getattr(gcp_sessions, "project_id", "unknown"),
                        "regions": getattr(gcp_sessions, "regions", ["us-central1"]),
                    }
                ]

            for gcp_entry in session_entries:
                gcp_session = gcp_entry["session"]
                for extractor_class in extractor_classes:
                    # Key includes project_id for uniqueness
                    self._register_extractor(
                        extractor_class, gcp_session, gcp_config, CloudProvider.GCP
                    )
        except ImportError as e:
            logger.warning(f"GCP extractors not available: {e}")

    def register(self, extractor_class: ConcreteExtractor) -> None:
        """Register an extractor class (deprecated, use _register_extractor)"""
        # Backward compatibility method
        if CloudProvider.AWS in self.sessions:
            extractor_config = self.config.extractors.get(
                extractor_class.__name__.replace("Extractor", "").lower(), {}
            )
            self._register_extractor(
                extractor_class,  # type: ignore[type-abstract]
                self.sessions[CloudProvider.AWS],
                {"aws": extractor_config},
                CloudProvider.AWS,
            )

    def _register_extractor(
        self,
        extractor_class: ConcreteExtractor,
        session: CloudSession,
        provider_config: Dict[str, Any],
        provider: CloudProvider,
    ) -> None:
        """Register a single extractor"""
        try:
            service_name = extractor_class.__name__.replace("Extractor", "").lower()
            # Remove provider prefixes like "Azure" or "AWS"
            service_name = service_name.replace("azure", "").replace("aws", "")

            extractor_config = provider_config.get(service_name, {})

            instance = extractor_class(session, extractor_config)
            # mypy: cast to BaseExtractor since extractor_class may be
            # a non-final/static reference that mypy cannot verify is
            # a concrete subclass at type-check time.
            instance = cast(BaseExtractor, instance)
            # Create unique key: provider:service
            key = f"{provider.value}:{instance.metadata.service_name}"

            self._extractors[key] = instance
            logger.info(f"Registered extractor: {key}")

        except Exception as e:
            logger.error(f"Failed to register {extractor_class.__name__}: {e}")

    def get(
        self, service_name: str, provider: Optional[CloudProvider] = None
    ) -> Optional[BaseExtractor]:
        """
        Get extractor by service name and optionally provider.

        Args:
            service_name: Service name (e.g., 'ec2', 'compute')
            provider: Cloud provider (optional, searches all if not specified)

        Returns:
            BaseExtractor instance or None
        """
        if provider:
            key = f"{provider.value}:{service_name}"
            return self._extractors.get(key)

        # Search all providers for this service
        for key, extractor in self._extractors.items():
            if key.endswith(f":{service_name}") or key == service_name:
                return extractor
        return None

    def get_extractors(
        self,
        services: Optional[List[str]] = None,
        provider: Optional[CloudProvider] = None,
    ) -> List[BaseExtractor]:
        """
        Get multiple extractors, optionally filtered by provider.

        Args:
            services: List of service names (None = all services)
            provider: Cloud provider filter (None = all providers)

        Returns:
            List of BaseExtractor instances
        """
        extractors = list(self._extractors.values())

        # Filter by provider if specified
        if provider:
            extractors = [e for e in extractors if e.cloud_provider == provider.value]

        # Filter by services if specified
        if services:
            extractors = [e for e in extractors if e.metadata.service_name in services]

        return extractors

    def list_services(self, provider: Optional[CloudProvider] = None) -> List[str]:
        """
        List all registered services, optionally filtered by provider.

        Args:
            provider: Cloud provider filter (None = all providers)

        Returns:
            List of service names with provider prefix (e.g., 'aws:ec2', 'azure:compute')
        """
        if provider:
            return [
                key
                for key in self._extractors.keys()
                if key.startswith(f"{provider.value}:")
            ]
        return list(self._extractors.keys())
