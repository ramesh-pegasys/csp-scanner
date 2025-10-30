# app/extractors/gcp/compute.py
"""
GCP Compute Engine resource extractor.
Extracts VM instances and instance groups.
"""

from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.cloud.gcp_session import GCPSession
import logging

logger = logging.getLogger(__name__)


class GCPComputeExtractor(BaseExtractor):
    """
    Extractor for GCP Compute Engine resources.

    Extracts:
    - VM Instances
    - Instance Groups (Managed and Unmanaged)
    """

    def get_metadata(self) -> ExtractorMetadata:
        """
        Get metadata about the GCP Compute extractor.

        Returns:
            ExtractorMetadata object
        """
        return ExtractorMetadata(
            service_name="compute",
            version="1.0.0",
            description="Extracts GCP Compute Engine VM instances and instance groups",
            resource_types=["instance", "instance-group"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract GCP Compute Engine resources.

        Args:
            region: Optional region to filter resources. If None, extracts from all regions.
            filters: Optional filters to apply (not currently used)

        Returns:
            List of raw resource dictionaries from GCP API
        """
        # Cast session to GCPSession for type checking
        gcp_session = cast(GCPSession, self.session)

        # Get list of zones to query
        zones = []
        if region:
            zones = gcp_session.list_zones(region)
        else:
            # Get all zones across all regions
            regions = gcp_session.list_regions()
            for r in regions:
                zones.extend(gcp_session.list_zones(r))

        logger.info(f"Extracting GCP Compute resources from {len(zones)} zones")

        # Use thread pool for parallel extraction
        artifacts = []
        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_zone, zone, gcp_session)
                for zone in zones
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"GCP compute extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        logger.info(f"Extracted {len(artifacts)} Compute resources")
        return artifacts

    def _extract_zone(self, zone: str, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract resources from a specific zone"""
        resources = []

        try:
            # Extract VM instances
            instances = self._extract_instances(zone, gcp_session)
            resources.extend(instances)
        except Exception as e:
            logger.error(f"Error extracting instances from zone {zone}: {str(e)}")

        # Extract managed instance groups if configured
        if self.config.get("include_instance_groups", True):
            try:
                migs = self._extract_managed_instance_groups(zone, gcp_session)
                resources.extend(migs)
            except Exception as e:
                logger.error(
                    f"Error extracting managed instance groups from zone {zone}: {str(e)}"
                )

        return resources

    def _extract_instances(
        self, zone: str, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """
        Extract VM instances from a specific zone.

        Args:
            zone: Zone name (e.g., 'us-central1-a')
            gcp_session: GCP session object

        Returns:
            List of instance dictionaries
        """
        instances_client = gcp_session.get_client("instances", zone)

        try:
            # List instances in the zone
            request = instances_client.list(project=gcp_session.project_id, zone=zone)

            instances = []
            for instance in request:
                instance_dict = {
                    "id": instance.id,
                    "name": instance.name,
                    "zone": zone,
                    "self_link": instance.self_link,
                    "machine_type": instance.machine_type,
                    "status": instance.status,
                    "creation_timestamp": instance.creation_timestamp,
                    "network_interfaces": [],
                    "disks": [],
                    "service_accounts": [],
                    "metadata": {},
                    "tags": [],
                    "labels": dict(instance.labels) if instance.labels else {},
                    "resource_type": "gcp:compute:instance",
                }

                # Extract network interfaces
                if instance.network_interfaces:
                    for nic in instance.network_interfaces:
                        nic_dict = {
                            "network": nic.network,
                            "subnetwork": nic.subnetwork,
                            "network_ip": nic.network_i_p,
                            "access_configs": [],
                        }

                        # Extract access configs (external IPs)
                        if nic.access_configs:
                            for ac in nic.access_configs:
                                nic_dict["access_configs"].append(
                                    {
                                        "name": ac.name,
                                        "nat_ip": ac.nat_i_p,
                                        "type": ac.type_,
                                    }
                                )

                        instance_dict["network_interfaces"].append(nic_dict)

                # Extract disks
                if instance.disks:
                    for disk in instance.disks:
                        disk_dict = {
                            "device_name": disk.device_name,
                            "source": disk.source,
                            "boot": disk.boot,
                            "auto_delete": disk.auto_delete,
                            "mode": disk.mode,
                        }
                        instance_dict["disks"].append(disk_dict)

                # Extract service accounts
                if instance.service_accounts:
                    for sa in instance.service_accounts:
                        instance_dict["service_accounts"].append(
                            {
                                "email": sa.email,
                                "scopes": list(sa.scopes) if sa.scopes else [],
                            }
                        )

                # Extract metadata
                if instance.metadata and instance.metadata.items:
                    for item in instance.metadata.items:
                        instance_dict["metadata"][item.key] = item.value

                # Extract tags
                if instance.tags and instance.tags.items:
                    instance_dict["tags"] = list(instance.tags.items)

                instances.append(instance_dict)

            logger.debug(f"Extracted {len(instances)} instances from zone {zone}")
            return instances

        except Exception as e:
            logger.error(f"Error listing instances in zone {zone}: {str(e)}")
            return []

    def _extract_managed_instance_groups(
        self, zone: str, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """
        Extract managed instance groups from a specific zone.

        Args:
            zone: Zone name (e.g., 'us-central1-a')
            gcp_session: GCP session object

        Returns:
            List of managed instance group dictionaries
        """
        migs_client = gcp_session.get_client("instance_group_managers", zone)

        try:
            # List managed instance groups in the zone
            request = migs_client.list(project=gcp_session.project_id, zone=zone)

            migs = []
            for mig in request:
                mig_dict = {
                    "id": mig.id,
                    "name": mig.name,
                    "zone": zone,
                    "self_link": mig.self_link,
                    "instance_template": mig.instance_template,
                    "base_instance_name": mig.base_instance_name,
                    "target_size": mig.target_size,
                    "current_actions": {},
                    "named_ports": [],
                    "auto_healing_policies": [],
                    "resource_type": "gcp:compute:instance-group",
                }

                # Extract current actions (scaling status)
                if mig.current_actions:
                    actions = mig.current_actions
                    mig_dict["current_actions"] = {
                        "abandoning": actions.abandoning,
                        "creating": actions.creating,
                        "creating_without_retries": actions.creating_without_retries,
                        "deleting": actions.deleting,
                        "recreating": actions.recreating,
                        "refreshing": actions.refreshing,
                        "restarting": actions.restarting,
                    }

                # Extract named ports
                if mig.named_ports:
                    for port in mig.named_ports:
                        mig_dict["named_ports"].append(
                            {
                                "name": port.name,
                                "port": port.port,
                            }
                        )

                # Extract auto-healing policies
                if mig.auto_healing_policies:
                    for policy in mig.auto_healing_policies:
                        mig_dict["auto_healing_policies"].append(
                            {
                                "health_check": policy.health_check,
                                "initial_delay_sec": policy.initial_delay_sec,
                            }
                        )

                migs.append(mig_dict)

            logger.debug(
                f"Extracted {len(migs)} managed instance groups from zone {zone}"
            )
            return migs

        except Exception as e:
            logger.error(
                f"Error listing managed instance groups in zone {zone}: {str(e)}"
            )
            return []

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw GCP Compute data into standardized metadata format.

        Args:
            raw_data: Raw resource dictionary from GCP API

        Returns:
            Standardized artifact dictionary
        """
        try:
            # Extract common fields
            resource_type_suffix = raw_data.get("resource_type", "gcp:compute:instance")
            resource_id = raw_data.get("self_link", raw_data.get("name", "unknown"))
            zone = raw_data.get("zone", "unknown")

            # Extract region from zone (e.g., us-central1-a -> us-central1)
            region = "-".join(zone.split("-")[:-1]) if zone != "unknown" else "unknown"

            # Get project ID from session
            gcp_session = cast(GCPSession, self.session)
            project_id = gcp_session.project_id

            # Get labels/tags
            labels = raw_data.get("labels", {})

            # Build configuration
            config = {
                "zone": zone,
                "status": raw_data.get("status", "unknown"),
                "machine_type": raw_data.get("machine_type", ""),
                "creation_timestamp": raw_data.get("creation_timestamp", ""),
            }

            # Add type-specific configuration
            if "instance" in resource_type_suffix:
                config.update(
                    {
                        "network_interfaces": raw_data.get("network_interfaces", []),
                        "disks": raw_data.get("disks", []),
                        "service_accounts": raw_data.get("service_accounts", []),
                        "metadata": raw_data.get("metadata", {}),
                        "tags": raw_data.get("tags", []),
                    }
                )
            elif "instance-group" in resource_type_suffix:
                config.update(
                    {
                        "instance_template": raw_data.get("instance_template", ""),
                        "target_size": raw_data.get("target_size", 0),
                        "current_actions": raw_data.get("current_actions", {}),
                        "named_ports": raw_data.get("named_ports", []),
                        "auto_healing_policies": raw_data.get(
                            "auto_healing_policies", []
                        ),
                    }
                )

            return {
                "cloud_provider": "gcp",
                "resource_type": resource_type_suffix,
                "metadata": self.create_metadata_object(
                    resource_id=resource_id,
                    service="compute",
                    region=region,
                    project_id=project_id,
                    labels=labels,
                ),
                "configuration": config,
                "raw": raw_data,
            }

        except Exception as e:
            logger.error(f"Error transforming resource: {str(e)}")
            return {}
