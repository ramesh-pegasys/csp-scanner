# app/extractors/azure/storage.py
"""
Azure Storage extractor for Storage Accounts.
"""

from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class AzureStorageExtractor(BaseExtractor):
    """Extractor for Azure Storage Accounts"""
    
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="storage",
            version="1.0.0",
            description="Extracts Azure Storage Accounts and configurations",
            resource_types=["storage-account"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )
    
    async def extract(
        self,
        region: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure storage resources"""
        artifacts = []
        
        with ThreadPoolExecutor(max_workers=self.config.get("max_workers", 20)) as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                self._extract_storage_accounts,
                region,
                filters
            )
        
        if isinstance(result, list):
            artifacts.extend(result)
        
        return artifacts
    
    def _extract_storage_accounts(
        self,
        location: Optional[str],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract storage accounts"""
        artifacts = []
        
        try:
            storage_client = self.session.get_client("storage")
            
            # List all storage accounts in subscription
            storage_accounts = storage_client.storage_accounts.list()
            
            for account in storage_accounts:
                # Filter by location if specified
                if location and account.location != location:
                    continue
                
                # Get additional properties
                resource_group = self._get_resource_group(account.id)
                
                # Get blob service properties if configured
                blob_properties = None
                if self.config.get("check_blob_encryption", True):
                    try:
                        blob_properties = storage_client.blob_services.get_service_properties(
                            resource_group_name=resource_group,
                            account_name=account.name
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get blob properties for {account.name}: {e}")
                
                artifact = self.transform({
                    "resource": account,
                    "blob_properties": blob_properties,
                    "location": account.location,
                    "resource_type": "storage-account"
                })
                
                if self.validate(artifact):
                    artifacts.append(artifact)
        
        except Exception as e:
            logger.error(f"Failed to extract storage accounts: {e}")
        
        return artifacts
    
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure Storage Account to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]
        
        resource_group = self._get_resource_group(resource.id)
        tags = resource.tags or {}
        
        # Build configuration
        config: Dict[str, Any] = {
            "kind": resource.kind,
            "provisioning_state": resource.provisioning_state,
            "creation_time": str(resource.creation_time) if resource.creation_time else None,
        }
        
        # Add SKU
        if resource.sku:
            config["sku"] = {
                "name": resource.sku.name,
                "tier": resource.sku.tier,
            }
        
        # Add access tier
        if hasattr(resource, "access_tier") and resource.access_tier:
            config["access_tier"] = resource.access_tier
        
        # Add security settings
        if hasattr(resource, "enable_https_traffic_only"):
            config["https_only"] = resource.enable_https_traffic_only
        
        if hasattr(resource, "allow_blob_public_access"):
            config["allow_blob_public_access"] = resource.allow_blob_public_access
        
        if hasattr(resource, "minimum_tls_version"):
            config["minimum_tls_version"] = resource.minimum_tls_version
        
        # Add encryption
        if resource.encryption:
            config["encryption"] = {
                "key_source": resource.encryption.key_source,
                "services": {}
            }
            
            if resource.encryption.services:
                if hasattr(resource.encryption.services, "blob") and resource.encryption.services.blob:
                    config["encryption"]["services"]["blob"] = {
                        "enabled": resource.encryption.services.blob.enabled
                    }
                if hasattr(resource.encryption.services, "file") and resource.encryption.services.file:
                    config["encryption"]["services"]["file"] = {
                        "enabled": resource.encryption.services.file.enabled
                    }
        
        # Add network rules
        if hasattr(resource, "network_rule_set") and resource.network_rule_set:
            config["network_rule_set"] = self._get_network_rules(resource)
        
        # Add blob properties if available
        if raw_data.get("blob_properties"):
            blob_props = raw_data["blob_properties"]
            config["blob_properties"] = {}
            
            if hasattr(blob_props, "delete_retention_policy") and blob_props.delete_retention_policy:
                config["blob_properties"]["delete_retention_policy"] = {
                    "enabled": blob_props.delete_retention_policy.enabled,
                    "days": blob_props.delete_retention_policy.days,
                }
        
        return {
            "cloud_provider": "azure",
            "resource_type": "azure:storage:account",
            "metadata": self.create_metadata_object(
                resource_id=resource.id,
                service="storage",
                region=location,
                subscription_id=self._get_subscription_id(resource.id),
                resource_group=resource_group,
                tags=tags,
            ),
            "configuration": config,
            "raw": self._serialize_azure_resource(resource),
        }
    
    def _get_network_rules(self, resource: Any) -> Dict[str, Any]:
        """Extract network rules from storage account"""
        network_rules: Dict[str, Any] = {}
        
        if not hasattr(resource, "network_rule_set") or not resource.network_rule_set:
            return network_rules
        
        nrs = resource.network_rule_set
        
        if hasattr(nrs, "default_action"):
            network_rules["default_action"] = nrs.default_action
        
        if hasattr(nrs, "bypass"):
            network_rules["bypass"] = nrs.bypass
        
        if hasattr(nrs, "ip_rules") and nrs.ip_rules:
            network_rules["ip_rules"] = [
                {"value": rule.ip_address_or_range, "action": rule.action}
                for rule in nrs.ip_rules
            ]
        
        if hasattr(nrs, "virtual_network_rules") and nrs.virtual_network_rules:
            network_rules["virtual_network_rules"] = [
                {"id": rule.virtual_network_resource_id, "action": rule.action}
                for rule in nrs.virtual_network_rules
            ]
        
        return network_rules
    
    def _get_resource_group(self, resource_id: str) -> str:
        """Extract resource group from Azure resource ID"""
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
        if hasattr(resource, "as_dict"):
            return resource.as_dict()
        return {}
