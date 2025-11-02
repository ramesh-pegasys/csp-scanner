# app/extractors/azure/keyvault.py
"""
Azure Key Vault extractor for Key Vaults and secrets/keys/certificates.
"""

from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.extractors.azure.utils import execute_azure_api_call
import logging

logger = logging.getLogger(__name__)


class AzureKeyVaultExtractor(BaseExtractor):
    """Extractor for Azure Key Vault resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="keyvault",
            version="1.0.0",
            description="Extracts Azure Key Vaults and their configurations",
            resource_types=["key-vault"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure Key Vault resources"""
        artifacts = []

        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor, self._extract_key_vaults, region, filters
            )

        if isinstance(result, list):
            artifacts.extend(result)

        return artifacts

    def _extract_key_vaults(
        self, location: Optional[str], filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract Key Vaults"""
        artifacts: List[Dict[str, Any]] = []

        try:
            kv_client = self.session.get_client("keyvault")

            # List all vaults with retry
            async def get_vaults():
                return list(kv_client.vaults.list())

            try:
                vaults = asyncio.run(
                    execute_azure_api_call(get_vaults, "get_key_vaults")
                )
            except Exception as e:
                logger.error(f"Failed to list Key Vaults after retries: {e}")
                return artifacts

            for vault in vaults:
                # Filter by location if specified
                if location and vault.location != location:
                    continue

                artifact = self.transform(
                    {
                        "resource": vault,
                        "location": vault.location,
                        "resource_type": "key-vault",
                    }
                )

                if self.validate(artifact):
                    artifacts.append(artifact)

        except Exception as e:
            logger.error(f"Failed to extract Key Vaults: {e}")

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure Key Vault to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]

        resource_group = self._get_resource_group(resource.id)
        tags = resource.tags or {}

        # Build configuration
        config: Dict[str, Any] = {
            "vault_uri": (
                resource.properties.vault_uri
                if hasattr(resource, "properties") and resource.properties
                else None
            ),
            "enabled_for_deployment": (
                getattr(resource.properties, "enabled_for_deployment", False)
                if hasattr(resource, "properties") and resource.properties
                else False
            ),
            "enabled_for_disk_encryption": (
                getattr(resource.properties, "enabled_for_disk_encryption", False)
                if hasattr(resource, "properties") and resource.properties
                else False
            ),
            "enabled_for_template_deployment": (
                getattr(resource.properties, "enabled_for_template_deployment", False)
                if hasattr(resource, "properties") and resource.properties
                else False
            ),
            "enable_soft_delete": (
                getattr(resource.properties, "enable_soft_delete", True)
                if hasattr(resource, "properties") and resource.properties
                else True
            ),
            "soft_delete_retention_in_days": (
                getattr(resource.properties, "soft_delete_retention_in_days", 90)
                if hasattr(resource, "properties") and resource.properties
                else 90
            ),
        }

        # Add SKU information
        if (
            hasattr(resource, "properties")
            and resource.properties
            and hasattr(resource.properties, "sku")
        ):
            sku = resource.properties.sku
            config["sku"] = {
                "family": sku.family if hasattr(sku, "family") else None,
                "name": sku.name if hasattr(sku, "name") else None,
            }

        # Add network ACLs if available
        if (
            hasattr(resource, "properties")
            and resource.properties
            and hasattr(resource.properties, "network_acls")
        ):
            network_acls = resource.properties.network_acls
            config["network_acls"] = {
                "default_action": getattr(network_acls, "default_action", None),
                "bypass": getattr(network_acls, "bypass", None),
            }

            # Add IP rules
            if hasattr(network_acls, "ip_rules") and network_acls.ip_rules:
                config["network_acls"]["ip_rules"] = [
                    rule for rule in network_acls.ip_rules
                ]

            # Add virtual network rules
            if (
                hasattr(network_acls, "virtual_network_rules")
                and network_acls.virtual_network_rules
            ):
                config["network_acls"]["virtual_network_rules"] = [
                    {
                        "id": rule.id if hasattr(rule, "id") else None,
                        "ignore_missing_vnet_service_endpoint": getattr(
                            rule, "ignore_missing_vnet_service_endpoint", False
                        ),
                    }
                    for rule in network_acls.virtual_network_rules
                ]

        return {
            "cloud_provider": "azure",
            "resource_type": "azure:keyvault:key-vault",
            "metadata": self.create_metadata_object(
                resource_id=resource.id,
                service="keyvault",
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
