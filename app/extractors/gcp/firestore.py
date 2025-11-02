from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPFirestoreExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="firestore",
            version="1.0.0",
            description="Extracts GCP Firestore databases and collections",
            resource_types=["gcp:firestore:database", "gcp:firestore:collection"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Firestore API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Firestore operations")

            api_service = API_SERVICE_MAP["firestore"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Firestore API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import firestore_admin_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Firestore operations")

            client = firestore_admin_v1.FirestoreAdminClient()

            # List Firestore databases
            response = client.list_databases(parent=f"projects/{project_id}")
            for database in response.databases:
                raw_data = {
                    "name": database.name,
                    "type": "database",
                    "create_time": getattr(database, "create_time", None),
                    "update_time": getattr(database, "update_time", None),
                    "location_id": getattr(database, "location_id", ""),
                    "database_type": getattr(database, "type", ""),
                    "concurrency_mode": getattr(database, "concurrency_mode", ""),
                }
                resources.append(self.transform(raw_data))

        except Exception as e:
            logger.error(f"Error extracting Firestore resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Firestore API response to standardized format"""
        name = raw_data["name"].split("/")[-1]
        return {
            "service": "firestore",
            "resource_type": "gcp:firestore:database",
            "name": name,
            "id": raw_data["name"],
            "region": raw_data.get("location_id", "global"),
            "project_id": getattr(self.session, "project_id", "unknown"),
            "create_time": raw_data.get("create_time"),
            "update_time": raw_data.get("update_time"),
            "database_type": raw_data.get("database_type"),
            "concurrency_mode": raw_data.get("concurrency_mode"),
        }
