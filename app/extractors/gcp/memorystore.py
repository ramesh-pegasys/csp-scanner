from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPMemorystoreExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="memorystore",
            version="1.0.0",
            description="Extracts GCP Memorystore (Redis) instances",
            resource_types=["gcp:memorystore:instance", "gcp:memorystore:backup"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Memorystore API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Memorystore operations")

            api_service = API_SERVICE_MAP["memorystore"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Memorystore API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import redis_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Memorystore operations")

            # List instances in all regions if no specific region is provided
            locations = [region] if region else ["-"]

            for location in locations:
                cloud_redis = redis_v1.CloudRedisClient()
                parent = f"projects/{project_id}/locations/{location}"

                # List Redis instances
                try:
                    for instance in cloud_redis.list_instances(parent=parent):
                        instance_data = {
                            "name": instance.name,
                            "type": "instance",
                            "display_name": instance.display_name,
                            "host": instance.host,
                            "port": instance.port,
                            "current_location_id": instance.current_location_id,
                            "redis_version": instance.redis_version,
                            "redis_configs": dict(instance.redis_configs),
                            "tier": instance.tier.name if instance.tier else "UNKNOWN",
                            "memory_size_gb": instance.memory_size_gb,
                            "authorized_network": instance.authorized_network,
                            "persistence_mode": instance.persistence_iam_identity,
                            "state": (
                                instance.state.name if instance.state else "UNKNOWN"
                            ),
                            "status_message": getattr(instance, "status_message", ""),
                            "create_time": instance.create_time,
                            "labels": dict(instance.labels),
                            "location": location,
                        }
                        resources.append(self.transform(instance_data))

                except Exception as e:
                    logger.warning(
                        f"Error listing Memorystore resources in {location}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error extracting Memorystore resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Memorystore API response to standardized format"""
        resource_type_map = {
            "instance": "gcp:memorystore:instance",
            "backup": "gcp:memorystore:backup",
        }

        base = {
            "service": "memorystore",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "instance":
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "host": raw_data["host"],
                    "port": raw_data["port"],
                    "location_id": raw_data["current_location_id"],
                    "redis_version": raw_data["redis_version"],
                    "redis_configs": raw_data["redis_configs"],
                    "tier": raw_data["tier"],
                    "memory_size_gb": raw_data["memory_size_gb"],
                    "authorized_network": raw_data["authorized_network"],
                    "persistence_mode": raw_data["persistence_mode"],
                    "state": raw_data["state"],
                    "status_message": raw_data["status_message"],
                    "create_time": raw_data["create_time"],
                    "labels": raw_data["labels"],
                }
            )
        else:  # backup
            base.update(
                {
                    "source_instance": raw_data["source_instance"],
                    "create_time": raw_data["create_time"],
                    "status": raw_data["status"],
                    "size_bytes": raw_data["size_bytes"],
                    "source_instance_tier": raw_data["source_instance_tier"],
                }
            )

        return base
