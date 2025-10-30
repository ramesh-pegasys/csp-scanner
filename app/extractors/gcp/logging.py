from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPLoggingExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="logging",
            version="1.0.0",
            description="Extracts GCP Cloud Logging configurations",
            resource_types=[
                "gcp:logging:sink",
                "gcp:logging:metric",
                "gcp:logging:exclusion",
            ],
            cloud_provider="gcp",
            supports_regions=False,  # Logging is a global service
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Logging API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Logging operations")

            api_service = API_SERVICE_MAP["logging"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Logging API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud.logging_v2.services.config_service_v2 import (
                ConfigServiceV2Client,
            )
            from google.cloud.logging_v2.services.metrics_service_v2 import (
                MetricsServiceV2Client,
            )

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Logging operations")

            config_client = ConfigServiceV2Client()
            metrics_client = MetricsServiceV2Client()
            parent = f"projects/{project_id}"

            # List logging sinks
            try:
                for sink in config_client.list_sinks(parent=parent):
                    sink_data = {
                        "name": sink.name,
                        "type": "sink",
                        "destination": sink.destination,
                        "filter": sink.filter,
                        "description": sink.description,
                        "disabled": sink.disabled,
                        "exclusions": (
                            [
                                {
                                    "name": excl.name,
                                    "description": excl.description,
                                    "filter": excl.filter,
                                    "disabled": excl.disabled,
                                }
                                for excl in sink.exclusions
                            ]
                            if hasattr(sink, "exclusions")
                            else []
                        ),
                        "writer_identity": sink.writer_identity,
                    }
                    resources.append(self.transform(sink_data))
            except Exception as e:
                logger.warning(f"Error listing logging sinks: {e}")

            # List logging metrics
            try:
                for metric in metrics_client.list_log_metrics(parent=parent):
                    metric_data = {
                        "name": metric.name,
                        "type": "metric",
                        "description": metric.description,
                        "filter": metric.filter,
                        "metric_descriptor": (
                            {
                                "type": metric.metric_descriptor.type,
                                "labels": [
                                    {"key": label.key, "description": label.description}
                                    for label in metric.metric_descriptor.labels
                                ],
                            }
                            if metric.metric_descriptor
                            else {}
                        ),
                        "value_extractor": metric.value_extractor,
                        "bucket_options": metric.bucket_options,
                        "disabled": getattr(metric, "disabled", False),
                    }
                    resources.append(self.transform(metric_data))
            except Exception as e:
                logger.warning(f"Error listing logging metrics: {e}")

            # List logging exclusions
            try:
                for exclusion in config_client.list_exclusions(parent=parent):
                    exclusion_data = {
                        "name": exclusion.name,
                        "type": "exclusion",
                        "description": exclusion.description,
                        "filter": exclusion.filter,
                        "disabled": exclusion.disabled,
                        "create_time": exclusion.create_time,
                        "update_time": exclusion.update_time,
                    }
                    resources.append(self.transform(exclusion_data))
            except Exception as e:
                logger.warning(f"Error listing logging exclusions: {e}")

        except Exception as e:
            logger.error(f"Error extracting Cloud Logging resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Logging API response to standardized format"""
        resource_type_map = {
            "sink": "gcp:logging:sink",
            "metric": "gcp:logging:metric",
            "exclusion": "gcp:logging:exclusion",
        }

        base = {
            "service": "logging",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"],
            "id": raw_data["name"],
            "region": "global",  # Logging is a global service
            "project_id": getattr(self.session, "project_id", "unknown"),
            "description": raw_data.get("description", ""),
        }

        if raw_data["type"] == "sink":
            base.update(
                {
                    "destination": raw_data["destination"],
                    "filter": raw_data["filter"],
                    "disabled": raw_data["disabled"],
                    "exclusions": raw_data["exclusions"],
                    "writer_identity": raw_data["writer_identity"],
                }
            )
        elif raw_data["type"] == "metric":
            base.update(
                {
                    "filter": raw_data["filter"],
                    "metric_descriptor": raw_data["metric_descriptor"],
                    "value_extractor": raw_data["value_extractor"],
                    "bucket_options": raw_data["bucket_options"],
                    "disabled": raw_data["disabled"],
                }
            )
        else:  # exclusion
            base.update(
                {
                    "filter": raw_data["filter"],
                    "disabled": raw_data["disabled"],
                    "create_time": raw_data["create_time"],
                    "update_time": raw_data["update_time"],
                }
            )

        return base
