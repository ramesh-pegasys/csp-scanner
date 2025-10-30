from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPSchedulerExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="scheduler",
            version="1.0.0",
            description="Extracts GCP Cloud Scheduler jobs",
            resource_types=["gcp:scheduler:job"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Cloud Scheduler API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError(
                    "Project ID is required for Cloud Scheduler operations"
                )

            api_service = API_SERVICE_MAP["scheduler"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Cloud Scheduler API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import scheduler_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError(
                    "Project ID is required for Cloud Scheduler operations"
                )

            client = scheduler_v1.CloudSchedulerClient()

            # List jobs in all regions if no specific region is provided
            locations = [region] if region else ["-"]

            for location in locations:
                parent = f"projects/{project_id}/locations/{location}"
                for job in client.list_jobs(parent=parent):
                    raw_data = {
                        "name": job.name,
                        "description": getattr(job, "description", ""),
                        "schedule": job.schedule,
                        "time_zone": job.time_zone,
                        "state": job.state.name if job.state else "UNKNOWN",
                        "attempt_deadline": getattr(job, "attempt_deadline", None),
                        "retry_count": getattr(job, "retry_config", {}).get(
                            "retry_count", 0
                        ),
                        "max_retry_duration": getattr(job, "retry_config", {}).get(
                            "max_retry_duration", ""
                        ),
                        "min_backoff": getattr(job, "retry_config", {}).get(
                            "min_backoff_duration", ""
                        ),
                        "max_backoff": getattr(job, "retry_config", {}).get(
                            "max_backoff_duration", ""
                        ),
                        "location": job.name.split("/")[3],
                    }

                    # Add target specific information
                    if hasattr(job, "http_target"):
                        raw_data.update(
                            {
                                "target_type": "http",
                                "url": job.http_target.uri,
                                "http_method": job.http_target.http_method.name,
                            }
                        )
                    elif hasattr(job, "app_engine_http_target"):
                        raw_data.update(
                            {
                                "target_type": "app_engine",
                                "service": job.app_engine_http_target.service,
                                "version": job.app_engine_http_target.version,
                            }
                        )
                    elif hasattr(job, "pubsub_target"):
                        raw_data.update(
                            {
                                "target_type": "pubsub",
                                "topic_name": job.pubsub_target.topic_name,
                            }
                        )

                    resources.append(self.transform(raw_data))

        except Exception as e:
            logger.error(f"Error extracting Cloud Scheduler jobs: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Scheduler API response to standardized format"""
        name = raw_data["name"].split("/")[-1]

        base = {
            "service": "scheduler",
            "resource_type": "gcp:scheduler:job",
            "name": name,
            "id": raw_data["name"],
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
            "description": raw_data["description"],
            "schedule": raw_data["schedule"],
            "time_zone": raw_data["time_zone"],
            "state": raw_data["state"],
            "attempt_deadline": raw_data["attempt_deadline"],
            "retry_config": {
                "retry_count": raw_data["retry_count"],
                "max_retry_duration": raw_data["max_retry_duration"],
                "min_backoff": raw_data["min_backoff"],
                "max_backoff": raw_data["max_backoff"],
            },
        }

        # Add target-specific information
        target_info = {"target_type": raw_data.get("target_type", "unknown")}
        if raw_data.get("target_type") == "http":
            target_info.update(
                {
                    "url": raw_data["url"],
                    "http_method": raw_data["http_method"],
                }
            )
        elif raw_data.get("target_type") == "app_engine":
            target_info.update(
                {
                    "service": raw_data["service"],
                    "version": raw_data["version"],
                }
            )
        elif raw_data.get("target_type") == "pubsub":
            target_info.update(
                {
                    "topic_name": raw_data["topic_name"],
                }
            )

        base["target"] = target_info
        return base
