from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPTasksExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="tasks",
            version="1.0.0",
            description="Extracts GCP Cloud Tasks queues and tasks",
            resource_types=["gcp:tasks:queue", "gcp:tasks:task"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Cloud Tasks API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Tasks operations")

            api_service = API_SERVICE_MAP["tasks"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Cloud Tasks API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import tasks_v2

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Tasks operations")

            client = tasks_v2.CloudTasksClient()

            # List queues in all regions if no specific region is provided
            locations = [region] if region else ["-"]

            for location in locations:
                parent = f"projects/{project_id}/locations/{location}"

                # List all queues in the location
                for queue in client.list_queues(parent=parent):
                    queue_data = {
                        "name": queue.name,
                        "type": "queue",
                        "state": queue.state.name if queue.state else "UNKNOWN",
                        "rate_limits": {
                            "max_concurrent_dispatches": getattr(
                                queue.rate_limits, "max_concurrent_dispatches", 0
                            ),
                            "max_dispatches_per_second": getattr(
                                queue.rate_limits, "max_dispatches_per_second", 0
                            ),
                        },
                        "retry_config": {
                            "max_attempts": getattr(
                                queue.retry_config, "max_attempts", 0
                            ),
                            "max_retry_duration": getattr(
                                queue.retry_config, "max_retry_duration", ""
                            ),
                            "min_backoff": getattr(
                                queue.retry_config, "min_backoff", ""
                            ),
                            "max_backoff": getattr(
                                queue.retry_config, "max_backoff", ""
                            ),
                            "max_doublings": getattr(
                                queue.retry_config, "max_doublings", 0
                            ),
                        },
                        "location": queue.name.split("/")[3],
                    }
                    resources.append(self.transform(queue_data))

                    # List tasks in the queue
                    queue_path = queue.name
                    try:
                        for task in client.list_tasks(parent=queue_path):
                            task_data = {
                                "name": task.name,
                                "type": "task",
                                "queue_name": queue.name,
                                "schedule_time": getattr(task, "schedule_time", None),
                                "create_time": getattr(task, "create_time", None),
                                "status": task.view.name if task.view else "UNKNOWN",
                                "location": queue.name.split("/")[3],
                            }
                            resources.append(self.transform(task_data))
                    except Exception as e:
                        logger.warning(
                            f"Error listing tasks in queue {queue.name}: {e}"
                        )

        except Exception as e:
            logger.error(f"Error extracting Cloud Tasks resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Tasks API response to standardized format"""
        resource_type_map = {
            "queue": "gcp:tasks:queue",
            "task": "gcp:tasks:task",
        }

        name = raw_data["name"].split("/")[-1]
        base = {
            "service": "tasks",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": name,
            "id": raw_data["name"],
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "queue":
            base.update(
                {
                    "state": raw_data["state"],
                    "rate_limits": raw_data["rate_limits"],
                    "retry_config": raw_data["retry_config"],
                }
            )
        else:  # task
            base.update(
                {
                    "queue_name": raw_data["queue_name"],
                    "schedule_time": raw_data["schedule_time"],
                    "create_time": raw_data["create_time"],
                    "status": raw_data["status"],
                }
            )

        return base
