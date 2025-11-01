# app/extractors/azure/containerservice.py
"""
Azure Container Service extractor for AKS clusters.
"""

from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.extractors.azure.utils import execute_azure_api_call
import logging

logger = logging.getLogger(__name__)


class AzureContainerServiceExtractor(BaseExtractor):
    """Extractor for Azure Container Service (AKS) resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="containerservice",
            version="1.0.0",
            description="Extracts Azure Kubernetes Service (AKS) clusters",
            resource_types=["aks-cluster"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure Container Service resources"""
        locations = [region] if region else self.session.list_regions()
        artifacts = []

        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_location, loc, filters)
                for loc in locations
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Azure Container Service extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        return artifacts

    def _extract_location(
        self, location: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract Container Service resources from a specific location"""
        artifacts = []

        try:
            cs_client = self.session.get_client("containerservice")

            # Extract AKS clusters
            try:
                clusters = self._extract_aks_clusters(cs_client, location)
                artifacts.extend(clusters)
            except Exception as e:
                logger.error(f"Failed to extract AKS clusters in {location}: {e}")

        except Exception as e:
            logger.error(f"Failed to get Container Service client for {location}: {e}")

        return artifacts

    def _extract_aks_clusters(
        self, cs_client: Any, location: str
    ) -> List[Dict[str, Any]]:
        """Extract AKS clusters"""
        artifacts = []

        # List all managed clusters with retry
        async def get_clusters():
            return list(cs_client.managed_clusters.list())

        try:
            clusters = asyncio.run(execute_azure_api_call(get_clusters, "get_aks_clusters"))
        except Exception as e:
            logger.error(f"Failed to list AKS clusters after retries: {e}")
            return artifacts

        for cluster in clusters:
            if cluster.location != location:
                continue

            artifact = self.transform(
                {
                    "resource": cluster,
                    "location": location,
                    "resource_type": "aks-cluster",
                }
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure AKS cluster to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]

        resource_group = self._get_resource_group(resource.id)
        tags = resource.tags or {}

        config = {
            "provisioning_state": resource.provisioning_state,
            "kubernetes_version": resource.kubernetes_version,
            "dns_prefix": resource.dns_prefix,
            "fqdn": getattr(resource, "fqdn", None),
        }

        # Add agent pool profiles
        if hasattr(resource, "agent_pool_profiles") and resource.agent_pool_profiles:
            agent_pools = []
            for pool in resource.agent_pool_profiles:
                pool_config = {
                    "name": pool.name,
                    "count": pool.count,
                    "vm_size": pool.vm_size,
                    "os_type": pool.os_type,
                    "orchestrator_version": getattr(pool, "orchestrator_version", None),
                    "mode": getattr(pool, "mode", None),
                }

                # Add additional pool settings
                if hasattr(pool, "enable_auto_scaling") and pool.enable_auto_scaling:
                    pool_config["enable_auto_scaling"] = pool.enable_auto_scaling
                    pool_config["min_count"] = getattr(pool, "min_count", None)
                    pool_config["max_count"] = getattr(pool, "max_count", None)

                if (
                    hasattr(pool, "enable_node_public_ip")
                    and pool.enable_node_public_ip
                ):
                    pool_config["enable_node_public_ip"] = pool.enable_node_public_ip

                agent_pools.append(pool_config)

            config["agent_pool_profiles"] = agent_pools

        # Add network profile
        if hasattr(resource, "network_profile") and resource.network_profile:
            network_config = {
                "network_plugin": getattr(
                    resource.network_profile, "network_plugin", None
                ),
                "network_policy": getattr(
                    resource.network_profile, "network_policy", None
                ),
                "service_cidr": getattr(resource.network_profile, "service_cidr", None),
                "dns_service_ip": getattr(
                    resource.network_profile, "dns_service_ip", None
                ),
                "docker_bridge_cidr": getattr(
                    resource.network_profile, "docker_bridge_cidr", None
                ),
            }
            config["network_profile"] = network_config

        # Add security settings
        if hasattr(resource, "enable_rbac") and resource.enable_rbac is not None:
            config["enable_rbac"] = resource.enable_rbac

        if hasattr(resource, "api_server_access_profile"):
            api_access = resource.api_server_access_profile
            config["api_server_access_profile"] = {
                "enable_private_cluster": getattr(
                    api_access, "enable_private_cluster", False
                ),
                "enable_private_cluster_public_fqdn": getattr(
                    api_access, "enable_private_cluster_public_fqdn", False
                ),
            }

        # Add addons
        if hasattr(resource, "addon_profiles") and resource.addon_profiles:
            addons = {}
            for addon_name, addon_profile in resource.addon_profiles.items():
                addons[addon_name] = {
                    "enabled": getattr(addon_profile, "enabled", False),
                    "config": getattr(addon_profile, "config", None),
                }
            config["addon_profiles"] = addons

        return {
            "cloud_provider": "azure",
            "resource_type": "azure:containerservice:aks-cluster",
            "metadata": self.create_metadata_object(
                resource_id=resource.id,
                service="containerservice",
                region=location,
                subscription_id=self._get_subscription_id(resource.id),
                resource_group=resource_group,
                tags=tags,
            ),
            "configuration": config,
            "raw": self._serialize_azure_resource(resource),
        }

    def _get_resource_group(self, resource_id: str) -> str:
        """Extract resource group from Azure resource ID"""
        # Azure resource ID format: /subscriptions/{sub}/resourceGroups/{rg}/...
        parts = resource_id.split("/")
        try:
            rg_index = parts.index("resourceGroups")
            return parts[rg_index + 1]
        except (ValueError, IndexError):
            return ""

    def _get_subscription_id(self, resource_id: str) -> str:
        """Extract subscription ID from Azure resource ID"""
        parts = resource_id.split("/")
        try:
            sub_index = parts.index("subscriptions")
            return parts[sub_index + 1]
        except (ValueError, IndexError):
            return ""

    def _serialize_azure_resource(self, resource: Any) -> Dict[str, Any]:
        """Convert Azure SDK model to dictionary"""
        # Azure SDK models have as_dict() method
        if hasattr(resource, "as_dict"):
            return resource.as_dict()
        return {}
