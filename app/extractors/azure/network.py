# app/extractors/azure/network.py
"""
Azure Network extractor for NSGs, VNets, and Load Balancers.
"""

from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class AzureNetworkExtractor(BaseExtractor):
    """Extractor for Azure Network resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="network",
            version="1.0.0",
            description="Extracts Azure Network Security Groups, Virtual Networks, and Load Balancers",
            resource_types=["nsg", "vnet", "load-balancer"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure network resources"""
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
                logger.error(f"Azure network extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        return artifacts

    def _extract_location(
        self, location: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract network resources from a specific location"""
        artifacts = []

        try:
            network_client = self.session.get_client("network", location)

            # Extract Network Security Groups
            if self.config.get("include_nsg_rules", True):
                try:
                    nsgs = self._extract_nsgs(network_client, location)
                    artifacts.extend(nsgs)
                except Exception as e:
                    logger.error(f"Failed to extract NSGs in {location}: {e}")

            # Extract Virtual Networks
            try:
                vnets = self._extract_vnets(network_client, location)
                artifacts.extend(vnets)
            except Exception as e:
                logger.error(f"Failed to extract VNets in {location}: {e}")

            # Extract Load Balancers
            try:
                lbs = self._extract_load_balancers(network_client, location)
                artifacts.extend(lbs)
            except Exception as e:
                logger.error(f"Failed to extract Load Balancers in {location}: {e}")

        except Exception as e:
            logger.error(f"Failed to get network client for {location}: {e}")

        return artifacts

    def _extract_nsgs(self, network_client: Any, location: str) -> List[Dict[str, Any]]:
        """Extract Network Security Groups"""
        artifacts = []

        nsgs = network_client.network_security_groups.list_all()

        for nsg in nsgs:
            if nsg.location != location:
                continue

            artifact = self.transform(
                {"resource": nsg, "location": location, "resource_type": "nsg"}
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def _extract_vnets(
        self, network_client: Any, location: str
    ) -> List[Dict[str, Any]]:
        """Extract Virtual Networks"""
        artifacts = []

        vnets = network_client.virtual_networks.list_all()

        for vnet in vnets:
            if vnet.location != location:
                continue

            artifact = self.transform(
                {"resource": vnet, "location": location, "resource_type": "vnet"}
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def _extract_load_balancers(
        self, network_client: Any, location: str
    ) -> List[Dict[str, Any]]:
        """Extract Load Balancers"""
        artifacts = []

        lbs = network_client.load_balancers.list_all()

        for lb in lbs:
            if lb.location != location:
                continue

            artifact = self.transform(
                {"resource": lb, "location": location, "resource_type": "load-balancer"}
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure network resource to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]
        resource_type = raw_data["resource_type"]

        resource_group = self._get_resource_group(resource.id)
        tags = resource.tags or {}

        if resource_type == "nsg":
            # Network Security Group
            config: Dict[str, Any] = {
                "provisioning_state": resource.provisioning_state,
                "security_rules": [],
                "default_security_rules": [],
            }

            # Add security rules
            if resource.security_rules:
                config["security_rules"] = [
                    {
                        "name": rule.name,
                        "priority": rule.priority,
                        "direction": rule.direction,
                        "access": rule.access,
                        "protocol": rule.protocol,
                        "source_port_range": rule.source_port_range,
                        "destination_port_range": rule.destination_port_range,
                        "source_address_prefix": rule.source_address_prefix,
                        "destination_address_prefix": rule.destination_address_prefix,
                    }
                    for rule in resource.security_rules
                ]

            # Add default security rules
            if resource.default_security_rules:
                config["default_security_rules"] = [
                    {
                        "name": rule.name,
                        "priority": rule.priority,
                        "direction": rule.direction,
                        "access": rule.access,
                    }
                    for rule in resource.default_security_rules
                ]

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:network:nsg",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="network",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        elif resource_type == "vnet":
            # Virtual Network
            config = {
                "provisioning_state": resource.provisioning_state,
                "address_space": [],
                "subnets": [],
            }

            # Add address space
            if resource.address_space and resource.address_space.address_prefixes:
                config["address_space"] = resource.address_space.address_prefixes

            # Add subnets
            if resource.subnets:
                config["subnets"] = [
                    {
                        "name": subnet.name,
                        "address_prefix": subnet.address_prefix,
                        "nsg_id": subnet.network_security_group.id
                        if subnet.network_security_group
                        else None,
                    }
                    for subnet in resource.subnets
                ]

            # Add DDoS protection
            if hasattr(resource, "enable_ddos_protection"):
                config["ddos_protection_enabled"] = resource.enable_ddos_protection

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:network:vnet",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="network",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        elif resource_type == "load-balancer":
            # Load Balancer
            config = {
                "provisioning_state": resource.provisioning_state,
                "frontend_ip_configurations": [],
                "backend_address_pools": [],
                "load_balancing_rules": [],
            }

            # Add SKU
            if resource.sku:
                config["sku"] = {
                    "name": resource.sku.name,
                    "tier": resource.sku.tier,
                }

            # Add frontend IPs
            if resource.frontend_ip_configurations:
                config["frontend_ip_configurations"] = [
                    {
                        "name": fe.name,
                        "private_ip": fe.private_ip_address,
                        "public_ip_id": fe.public_ip_address.id
                        if fe.public_ip_address
                        else None,
                    }
                    for fe in resource.frontend_ip_configurations
                ]

            # Add backend pools
            if resource.backend_address_pools:
                config["backend_address_pools"] = [
                    {"name": pool.name, "id": pool.id}
                    for pool in resource.backend_address_pools
                ]

            # Add load balancing rules
            if resource.load_balancing_rules:
                config["load_balancing_rules"] = [
                    {
                        "name": rule.name,
                        "protocol": rule.protocol,
                        "frontend_port": rule.frontend_port,
                        "backend_port": rule.backend_port,
                    }
                    for rule in resource.load_balancing_rules
                ]

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:network:load-balancer",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="network",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        return {}

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
