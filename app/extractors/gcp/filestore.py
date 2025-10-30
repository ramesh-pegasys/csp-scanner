from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPFilestoreExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="filestore",
            version="1.0.0",
            description="Extracts GCP Filestore instances and backups",
            resource_types=["gcp:filestore:instance", "gcp:filestore:backup"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Filestore API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Filestore operations")

            api_service = API_SERVICE_MAP["filestore"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Filestore API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import filestore_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Filestore operations")

            client = filestore_v1.CloudFilestoreManagerClient()

            # List instances in all regions if no specific region is provided
            locations = [region] if region else ["-"]

            for location in locations:
                parent = f"projects/{project_id}/locations/{location}"

                try:
                    # List Filestore instances
                    for instance in client.list_instances(parent=parent):
                        instance_data = {
                            "name": instance.name,
                            "type": "instance",
                            "state": (
                                instance.state.name if instance.state else "UNKNOWN"
                            ),
                            "create_time": instance.create_time,
                            "tier": instance.tier,
                            "labels": dict(instance.labels),
                            "file_shares": [
                                {
                                    "name": share.name,
                                    "capacity_gb": share.capacity_gb,
                                    "source_backup": share.source_backup,
                                }
                                for share in instance.file_shares
                            ],
                            "networks": [
                                {
                                    "network": net.network,
                                    "modes": [mode.name for mode in net.modes],
                                    "reserved_ip_range": net.reserved_ip_range,
                                    "ip_addresses": list(net.ip_addresses),
                                }
                                for net in instance.networks
                            ],
                            "location": (
                                location
                                if location != "-"
                                else instance.name.split("/")[3]
                            ),
                        }
                        resources.append(self.transform(instance_data))

                    # List backups
                    for backup in client.list_backups(parent=parent):
                        backup_data = {
                            "name": backup.name,
                            "type": "backup",
                            "state": backup.state.name if backup.state else "UNKNOWN",
                            "create_time": backup.create_time,
                            "source_instance": backup.source_instance,
                            "source_file_share": backup.source_file_share,
                            "size_gb": backup.size_gb,
                            "labels": dict(backup.labels),
                            "location": (
                                location
                                if location != "-"
                                else backup.name.split("/")[3]
                            ),
                        }
                        resources.append(self.transform(backup_data))

                except Exception as e:
                    logger.warning(
                        f"Error listing Filestore resources in {location}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error extracting Filestore resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Filestore API response to standardized format"""
        resource_type_map = {
            "instance": "gcp:filestore:instance",
            "backup": "gcp:filestore:backup",
        }

        base = {
            "service": "filestore",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "instance":
            base.update(
                {
                    "state": raw_data["state"],
                    "create_time": raw_data["create_time"],
                    "tier": raw_data["tier"],
                    "labels": raw_data["labels"],
                    "file_shares": raw_data["file_shares"],
                    "networks": raw_data["networks"],
                }
            )
        else:  # backup
            base.update(
                {
                    "state": raw_data["state"],
                    "create_time": raw_data["create_time"],
                    "source_instance": raw_data["source_instance"].split("/")[-1],
                    "source_file_share": raw_data["source_file_share"],
                    "size_gb": raw_data["size_gb"],
                    "labels": raw_data["labels"],
                }
            )

        return base
