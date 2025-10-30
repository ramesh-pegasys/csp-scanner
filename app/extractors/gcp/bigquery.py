from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPBigQueryExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="bigquery",
            version="1.0.0",
            description="Extracts GCP BigQuery datasets and tables",
            resource_types=["gcp:bigquery:dataset", "gcp:bigquery:table"],
            cloud_provider="gcp",
            supports_regions=False,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if BigQuery API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for BigQuery operations")

            api_service = API_SERVICE_MAP["bigquery"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP BigQuery API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import bigquery

            # Get the project ID from the session
            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for BigQuery operations")

            client = bigquery.Client(
                project=project_id,
                credentials=getattr(self.session, "credentials", None),
            )
            for dataset in client.list_datasets():
                dataset_resource = self.transform(
                    {
                        "dataset_id": dataset.dataset_id,
                        "project": dataset.project,
                        "resource_type": "dataset",
                    }
                )
                resources.append(dataset_resource)

                # List all tables in the dataset
                for table in client.list_tables(dataset.reference):
                    table_resource = self.transform(
                        {
                            "table_id": table.table_id,
                            "dataset_id": dataset.dataset_id,
                            "project": dataset.project,
                            "resource_type": "table",
                        }
                    )
                    resources.append(table_resource)

        except Exception as e:
            logger.error(f"Error extracting BigQuery resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw BigQuery API response to standardized format"""
        resource_type = raw_data["resource_type"]
        base = {
            "service": "bigquery",
            "region": "global",
            "project_id": raw_data["project"],
        }

        if resource_type == "dataset":
            return {
                **base,
                "resource_type": "gcp:bigquery:dataset",
                "name": raw_data["dataset_id"],
                "id": raw_data["dataset_id"],
            }
        else:  # table
            return {
                **base,
                "resource_type": "gcp:bigquery:table",
                "name": raw_data["table_id"],
                "id": raw_data["table_id"],
                "dataset_id": raw_data["dataset_id"],
            }
