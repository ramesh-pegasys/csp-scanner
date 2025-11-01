# app/extractors/azure/compute.py
"""
Azure Compute extractor for Virtual Machines and VM Scale Sets.
"""

from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.extractors.azure.utils import execute_azure_api_call
import logging

logger = logging.getLogger(__name__)


class AzureComputeExtractor(BaseExtractor):
    """Extractor for Azure Virtual Machines and related resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="compute",
            version="1.0.0",
            description="Extracts Azure Virtual Machines and VM Scale Sets",
            resource_types=["virtual-machine", "vmss"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure compute resources"""
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
                logger.error(f"Azure compute extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        return artifacts

    def _extract_location(
        self, location: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract compute resources from a specific location"""
        artifacts = []

        try:
            compute_client = self.session.get_client("compute", location)

            # Extract Virtual Machines
            try:
                vms = self._extract_virtual_machines(compute_client, location)
                artifacts.extend(vms)
            except Exception as e:
                logger.error(f"Failed to extract VMs in {location}: {e}")

            # Extract VM Scale Sets if configured
            if self.config.get("include_vmss", True):
                try:
                    vmss = self._extract_vmss(compute_client, location)
                    artifacts.extend(vmss)
                except Exception as e:
                    logger.error(f"Failed to extract VMSS in {location}: {e}")

        except Exception as e:
            logger.error(f"Failed to get compute client for {location}: {e}")

        return artifacts

    def _extract_virtual_machines(
        self, compute_client: Any, location: str
    ) -> List[Dict[str, Any]]:
        """Extract Virtual Machines"""
        artifacts: List[Dict[str, Any]] = []

        # List all VMs in subscription with retry
        async def get_vms():
            return list(compute_client.virtual_machines.list_all())

        try:
            vms = asyncio.run(execute_azure_api_call(get_vms, "get_virtual_machines"))
        except Exception as e:
            logger.error(f"Failed to list VMs after retries: {e}")
            return artifacts

        for vm in vms:
            # Filter by location if needed
            if vm.location != location:
                continue

            # Get instance view for runtime information
            instance_view = None
            try:
                resource_group = self._get_resource_group(vm.id)

                async def get_instance_view():
                    return compute_client.virtual_machines.instance_view(
                        resource_group_name=resource_group, vm_name=vm.name
                    )

                instance_view = asyncio.run(
                    execute_azure_api_call(
                        get_instance_view,
                        f"get_instance_view_{vm.name}",
                        max_attempts=3,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to get instance view for VM {vm.name}: {e}")

            artifact = self.transform(
                {
                    "resource": vm,
                    "instance_view": instance_view,
                    "location": location,
                    "resource_type": "virtual-machine",
                }
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def _extract_vmss(self, compute_client: Any, location: str) -> List[Dict[str, Any]]:
        """Extract VM Scale Sets"""
        artifacts: List[Dict[str, Any]] = []

        # List all VMSS with retry
        async def get_vmss():
            return list(compute_client.virtual_machine_scale_sets.list_all())

        try:
            vmss_list = asyncio.run(
                execute_azure_api_call(get_vmss, "get_vm_scale_sets")
            )
        except Exception as e:
            logger.error(f"Failed to list VMSS after retries: {e}")
            return artifacts

        for vmss in vmss_list:
            if vmss.location != location:
                continue

            artifact = self.transform(
                {"resource": vmss, "location": location, "resource_type": "vmss"}
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure VM resource to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]
        resource_type = raw_data["resource_type"]

        if resource_type == "virtual-machine":
            # Extract resource group from resource ID
            resource_group = self._get_resource_group(resource.id)

            # Get tags
            tags = resource.tags or {}

            # Build configuration
            config: Dict[str, Any] = {
                "vm_size": (
                    resource.hardware_profile.vm_size
                    if resource.hardware_profile
                    else None
                ),
                "provisioning_state": resource.provisioning_state,
            }

            # Add storage profile
            if resource.storage_profile:
                config["os_disk"] = {
                    "name": (
                        resource.storage_profile.os_disk.name
                        if resource.storage_profile.os_disk
                        else None
                    ),
                    "os_type": (
                        resource.storage_profile.os_disk.os_type
                        if resource.storage_profile.os_disk
                        else None
                    ),
                    "disk_size_gb": (
                        resource.storage_profile.os_disk.disk_size_gb
                        if resource.storage_profile.os_disk
                        else None
                    ),
                    "managed_disk_id": (
                        resource.storage_profile.os_disk.managed_disk.id
                        if resource.storage_profile.os_disk
                        and resource.storage_profile.os_disk.managed_disk
                        else None
                    ),
                }

            # Add network profile
            if resource.network_profile and resource.network_profile.network_interfaces:
                config["network_interfaces"] = [
                    nic.id for nic in resource.network_profile.network_interfaces
                ]

            # Add instance view data if available
            if "instance_view" in raw_data and raw_data["instance_view"]:
                instance_view = raw_data["instance_view"]
                config["power_state"] = self._get_power_state(instance_view)
                if instance_view.statuses:
                    config["statuses"] = [
                        {"code": status.code, "display_status": status.display_status}
                        for status in instance_view.statuses
                    ]

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:compute:virtual-machine",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="compute",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        elif resource_type == "vmss":
            resource_group = self._get_resource_group(resource.id)
            tags = resource.tags or {}

            config = {
                "provisioning_state": resource.provisioning_state,
            }

            # Add SKU information
            if resource.sku:
                config["sku"] = {
                    "name": resource.sku.name,
                    "tier": resource.sku.tier,
                    "capacity": resource.sku.capacity,
                }

            # Add upgrade policy
            if resource.upgrade_policy:
                config["upgrade_policy"] = resource.upgrade_policy.mode

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:compute:vmss",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="compute",
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

    def _get_power_state(self, instance_view: Any) -> str:
        """Extract power state from instance view"""
        if not instance_view or not instance_view.statuses:
            return "unknown"

        for status in instance_view.statuses:
            if status.code and status.code.startswith("PowerState/"):
                return status.code.split("/")[1]
        return "unknown"

    def _serialize_azure_resource(self, resource: Any) -> Dict[str, Any]:
        """Convert Azure SDK model to dictionary"""
        # Azure SDK models have as_dict() method
        if hasattr(resource, "as_dict"):
            return resource.as_dict()
        return {}
