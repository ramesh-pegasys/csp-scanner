from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPDataflowExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="dataflow",
            version="1.0.0",
            description="Extracts GCP Dataflow jobs",
            resource_types=["gcp:dataflow:job"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Dataflow API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Dataflow operations")

            api_service = API_SERVICE_MAP["dataflow"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Dataflow API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud.dataflow_v1beta3.services.jobs_v1_beta3 import (
                JobsV1Beta3Client,
            )
            from google.cloud.dataflow_v1beta3.types import ListJobsRequest

            jobs_client = JobsV1Beta3Client()

            # List jobs in all regions if no specific region is provided
            locations = (
                [region] if region else ["us-central1"]
            )  # Dataflow requires a specific region, default to us-central1

            for location in locations:
                # List Dataflow jobs
                try:
                    request = ListJobsRequest(project_id=project_id, location=location)
                    for job in jobs_client.list_jobs(request=request):
                        job_data = {
                            "name": job.name,
                            "type": "job",
                            "id": job.id,
                            "job_type": job.type_.name if job.type_ else "UNKNOWN",
                            "state": (
                                job.current_state.name
                                if job.current_state
                                else "UNKNOWN"
                            ),
                            "location": job.location,
                            "start_time": getattr(job, "start_time", None),
                            "create_time": getattr(job, "create_time", None),
                            "current_state_time": getattr(
                                job, "current_state_time", None
                            ),
                            "sdk_version": getattr(job, "sdk_version", {}),
                            "environment": getattr(job, "environment", {}),
                        }
                        resources.append(self.transform(job_data))
                except Exception as e:
                    logger.warning(f"Error listing Dataflow jobs in {location}: {e}")

                # Note: Flex Templates cannot be listed via API - they can only be launched or retrieved individually
                # Skipping Flex Templates extraction as there's no list operation available

        except Exception as e:
            logger.error(f"Error extracting Dataflow resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Dataflow API response to standardized format"""
        resource_type_map = {
            "job": "gcp:dataflow:job",
            "flextemplate": "gcp:dataflow:flextemplate",
        }

        base = {
            "service": "dataflow",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"],
            "id": raw_data.get("id", raw_data["name"]),
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "job":
            base.update(
                {
                    "job_type": raw_data["job_type"],
                    "state": raw_data["state"],
                    "start_time": raw_data["start_time"],
                    "create_time": raw_data["create_time"],
                    "current_state_time": raw_data["current_state_time"],
                    "sdk_version": raw_data["sdk_version"],
                    "environment": raw_data["environment"],
                }
            )
        else:  # flextemplate
            base.update(
                {
                    "container_spec": raw_data["container_spec"],
                    "parameters": raw_data["parameters"],
                }
            )

        return base
