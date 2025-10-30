from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPCloudRunExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="run",
            version="1.0.0",
            description="Extracts GCP Cloud Run services",
            resource_types=["gcp:run:service"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Cloud Run API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Run operations")

            api_service = API_SERVICE_MAP["run"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Cloud Run API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import run_v2

            client = run_v2.ServicesClient()
            # Get the project ID from the session
            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Run operations")

            parent = f"projects/{project_id}/locations/-"
            for service in client.list_services(parent=parent):
                raw_data = {
                    "name": service.name,
                    "location": service.name.split("/")[3],
                    "description": getattr(service, "description", ""),
                    "ingress": getattr(service, "ingress", ""),
                    "uri": getattr(service, "uri", ""),
                    "creator": getattr(service, "creator", ""),
                    "last_modifier": getattr(service, "last_modifier", ""),
                    "client": getattr(service, "client", ""),
                    "binary_authorization": getattr(
                        service, "binary_authorization", None
                    ),
                }
                resources.append(self.transform(raw_data))
        except Exception as e:
            logger.error(f"Error extracting Cloud Run services: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Run API response to standardized format"""
        return {
            "service": "run",
            "resource_type": "gcp:run:service",
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
            "description": raw_data["description"],
            "uri": raw_data["uri"],
            "ingress": raw_data["ingress"],
            "creator": raw_data["creator"],
            "last_modifier": raw_data["last_modifier"],
            "client": raw_data["client"],
            "binary_authorization": (
                raw_data["binary_authorization"].evaluation_mode
                if raw_data["binary_authorization"]
                else None
            ),
        }
