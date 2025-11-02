from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPBigtableExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="bigtable",
            version="1.0.0",
            description="Extracts GCP Cloud Bigtable instances and clusters",
            resource_types=[
                "gcp:bigtable:instance",
                "gcp:bigtable:cluster",
                "gcp:bigtable:table",
            ],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Bigtable API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Bigtable operations")

            api_service = API_SERVICE_MAP["bigtable"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Bigtable API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import bigtable_admin_v2

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Bigtable operations")

            instance_client = bigtable_admin_v2.BigtableInstanceAdminClient()
            parent = f"projects/{project_id}"

            # List Bigtable instances
            for instance in instance_client.list_instances(parent=parent).instances:
                instance_data = {
                    "name": instance.name,
                    "type": "instance",
                    "display_name": instance.display_name,
                    "state": instance.state.name if instance.state else "UNKNOWN",
                    "instance_type": (
                        instance.type_.name if instance.type_ else "UNKNOWN"
                    ),
                    "labels": dict(instance.labels),
                }
                resources.append(self.transform(instance_data))

                # List clusters for each instance
                for cluster in instance.clusters:
                    cluster_data = {
                        "name": cluster.name,
                        "type": "cluster",
                        "instance_name": instance.name,
                        "location": cluster.location,
                        "serve_nodes": cluster.serve_nodes,
                        "state": cluster.state.name if cluster.state else "UNKNOWN",
                    }
                    resources.append(self.transform(cluster_data))

                # List tables in each instance
                table_client = bigtable_admin_v2.BigtableTableAdminClient()
                instance_path = f"{parent}/instances/{instance.name.split('/')[-1]}"

                try:
                    for table in table_client.list_tables(parent=instance_path):
                        table_data = {
                            "name": table.name,
                            "type": "table",
                            "instance_name": instance.name,
                            "granularity": (
                                table.granularity.name
                                if table.granularity
                                else "UNKNOWN"
                            ),
                        }
                        resources.append(self.transform(table_data))
                except Exception as e:
                    logger.warning(
                        f"Error listing tables for instance {instance.name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error extracting Cloud Bigtable resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Bigtable API response to standardized format"""
        resource_type_map = {
            "instance": "gcp:bigtable:instance",
            "cluster": "gcp:bigtable:cluster",
            "table": "gcp:bigtable:table",
        }

        base = {
            "service": "bigtable",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "instance":
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "state": raw_data["state"],
                    "instance_type": raw_data["instance_type"],
                    "labels": raw_data["labels"],
                    "region": "global",  # Instances are global resources
                }
            )
        elif raw_data["type"] == "cluster":
            base.update(
                {
                    "instance_name": raw_data["instance_name"].split("/")[-1],
                    "location": raw_data["location"],
                    "serve_nodes": raw_data["serve_nodes"],
                    "state": raw_data["state"],
                    "region": raw_data["location"].split("/")[-1],
                }
            )
        else:  # table
            base.update(
                {
                    "instance_name": raw_data["instance_name"].split("/")[-1],
                    "granularity": raw_data["granularity"],
                    "region": "global",  # Tables inherit instance's global scope
                }
            )

        return base
