from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPCloudBuildExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="cloudbuild",
            version="1.0.0",
            description="Extracts GCP Cloud Build resources",
            resource_types=["gcp:cloudbuild:build", "gcp:cloudbuild:trigger"],
            cloud_provider="gcp",
            supports_regions=False,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Cloud Build API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Build operations")

            api_service = API_SERVICE_MAP["cloudbuild"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Cloud Build API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud.devtools import cloudbuild_v1

            client = cloudbuild_v1.CloudBuildClient()

            # Note: Cloud Build API can be slow. Consider filtering for specific regions if needed.
            for build in client.list_builds(project_id=project_id, filter=""):
                raw_data = {
                    "id": build.id,
                    "status": build.status.name,  # Use .name for enum
                    "create_time": build.create_time,
                    "steps": [step.name for step in build.steps],
                    "source": build.source,
                    "substitutions": dict(build.substitutions),
                    "tags": list(build.tags),
                }
                resources.append(self.transform(raw_data))

        except Exception as e:
            logger.error(f"Error extracting Cloud Build resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Build API response to standardized format"""
        return {
            "service": "cloudbuild",
            "resource_type": "gcp:cloudbuild:build",
            "name": raw_data["id"],
            "id": raw_data["id"],
            "region": "global",  # Cloud Build is a global service
            "project_id": getattr(self.session, "project_id", "unknown"),
            "status": raw_data["status"],
            "create_time": raw_data["create_time"],
            "steps": raw_data["steps"],
            "source": raw_data["source"],
            "substitutions": raw_data["substitutions"],
            "tags": raw_data["tags"],
        }
