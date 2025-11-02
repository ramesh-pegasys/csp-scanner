from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPSpannerExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="spanner",
            version="1.0.0",
            description="Extracts GCP Cloud Spanner instances and databases",
            resource_types=["gcp:spanner:instance", "gcp:spanner:database"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Spanner API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Spanner operations")

            api_service = API_SERVICE_MAP["spanner"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Spanner API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import spanner_admin_instance_v1
            from google.cloud import spanner_admin_database_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Spanner operations")

            instance_client = spanner_admin_instance_v1.InstanceAdminClient()
            parent = f"projects/{project_id}"

            # List Spanner instances
            for instance in instance_client.list_instances(parent=parent):
                instance_data = {
                    "name": instance.name,
                    "type": "instance",
                    "display_name": instance.display_name,
                    "node_count": instance.node_count,
                    "config": instance.config,
                    "state": instance.state.name if instance.state else "UNKNOWN",
                    "labels": dict(instance.labels),
                    "processing_units": instance.processing_units,
                }
                resources.append(self.transform(instance_data))

                # List databases in each instance
                database_client = spanner_admin_database_v1.DatabaseAdminClient()
                try:
                    for database in database_client.list_databases(
                        parent=instance.name
                    ):
                        database_data = {
                            "name": database.name,
                            "type": "database",
                            "instance_name": instance.name,
                            "state": (
                                database.state.name if database.state else "UNKNOWN"
                            ),
                            "create_time": getattr(database, "create_time", None),
                            "restore_info": getattr(database, "restore_info", None),
                            "encryption_config": getattr(
                                database, "encryption_config", None
                            ),
                            "version_retention_period": getattr(
                                database, "version_retention_period", None
                            ),
                            "earliest_version_time": getattr(
                                database, "earliest_version_time", None
                            ),
                            "default_leader": getattr(database, "default_leader", None),
                        }
                        resources.append(self.transform(database_data))
                except Exception as e:
                    logger.warning(
                        f"Error listing databases for instance {instance.name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error extracting Cloud Spanner resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Spanner API response to standardized format"""
        resource_type_map = {
            "instance": "gcp:spanner:instance",
            "database": "gcp:spanner:database",
        }

        base = {
            "service": "spanner",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "instance":
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "node_count": raw_data["node_count"],
                    "config": raw_data["config"],
                    "state": raw_data["state"],
                    "labels": raw_data["labels"],
                    "processing_units": raw_data["processing_units"],
                    "region": raw_data["config"].split("/")[
                        -1
                    ],  # Extract region from config path
                }
            )
        else:  # database
            base.update(
                {
                    "instance_name": raw_data["instance_name"].split("/")[-1],
                    "state": raw_data["state"],
                    "create_time": raw_data["create_time"],
                    "restore_info": raw_data["restore_info"],
                    "encryption_config": raw_data["encryption_config"],
                    "version_retention_period": raw_data["version_retention_period"],
                    "earliest_version_time": raw_data["earliest_version_time"],
                    "default_leader": raw_data["default_leader"],
                    "region": raw_data["instance_name"].split("/")[
                        -3
                    ],  # Extract region from instance path
                }
            )

        return base
