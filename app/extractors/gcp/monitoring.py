from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPMonitoringExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="monitoring",
            version="1.0.0",
            description="Extracts GCP Cloud Monitoring configurations",
            resource_types=[
                "gcp:monitoring:alertpolicy",
                "gcp:monitoring:notificationchannel",
                "gcp:monitoring:uptimecheckconfig",
            ],
            cloud_provider="gcp",
            supports_regions=False,  # Monitoring is a global service
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Monitoring API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError(
                    "Project ID is required for Cloud Monitoring operations"
                )

            api_service = API_SERVICE_MAP["monitoring"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Monitoring API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import monitoring_v3

            alert_client = monitoring_v3.AlertPolicyServiceClient()
            notification_client = monitoring_v3.NotificationChannelServiceClient()
            uptime_check_client = monitoring_v3.UptimeCheckServiceClient()

            parent = f"projects/{project_id}"

            # List alert policies
            try:
                for policy in alert_client.list_alert_policies(name=parent):
                    policy_data = {
                        "name": policy.name,
                        "type": "alertpolicy",
                        "display_name": policy.display_name,
                        "documentation": (
                            {
                                "content": policy.documentation.content,
                                "mime_type": policy.documentation.mime_type,
                            }
                            if policy.documentation
                            else {}
                        ),
                        "conditions": [
                            {
                                "name": cond.name,
                                "display_name": cond.display_name,
                                "condition_threshold": (
                                    {
                                        "filter": cond.condition_threshold.filter,
                                        "duration": str(
                                            cond.condition_threshold.duration
                                        ),
                                        "comparison": cond.condition_threshold.comparison.name,
                                        "threshold_value": cond.condition_threshold.threshold_value,
                                    }
                                    if hasattr(cond, "condition_threshold")
                                    else None
                                ),
                            }
                            for cond in policy.conditions
                        ],
                        "notification_channels": policy.notification_channels,
                        "enabled": policy.enabled,
                        "combiner": policy.combiner.name,
                    }
                    resources.append(self.transform(policy_data))
            except Exception as e:
                logger.warning(f"Error listing alert policies: {e}")

            # List notification channels
            try:
                for channel in notification_client.list_notification_channels(
                    name=parent
                ):
                    channel_data = {
                        "name": channel.name,
                        "type": "notificationchannel",
                        "display_name": channel.display_name,
                        "description": channel.description,
                        "channel_type": channel.type_,
                        "labels": dict(channel.labels),
                        "verification_status": channel.verification_status.name,
                        "enabled": channel.enabled,
                    }
                    resources.append(self.transform(channel_data))
            except Exception as e:
                logger.warning(f"Error listing notification channels: {e}")

            # List uptime check configs
            try:
                for config in uptime_check_client.list_uptime_check_configs(
                    parent=parent
                ):
                    config_data = {
                        "name": config.name,
                        "type": "uptimecheckconfig",
                        "display_name": config.display_name,
                        "monitored_resource": {
                            "type": config.monitored_resource.type_,
                            "labels": dict(config.monitored_resource.labels),
                        },
                        "http_check": (
                            {
                                "use_ssl": config.http_check.use_ssl,
                                "path": config.http_check.path,
                                "port": config.http_check.port,
                            }
                            if config.http_check
                            else None
                        ),
                        "tcp_check": (
                            {
                                "port": config.tcp_check.port,
                            }
                            if config.tcp_check
                            else None
                        ),
                        "period": str(config.period),
                        "timeout": str(config.timeout),
                    }
                    resources.append(self.transform(config_data))
            except Exception as e:
                logger.warning(f"Error listing uptime check configs: {e}")

        except Exception as e:
            logger.error(f"Error extracting Cloud Monitoring resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Monitoring API response to standardized format"""
        resource_type_map = {
            "alertpolicy": "gcp:monitoring:alertpolicy",
            "notificationchannel": "gcp:monitoring:notificationchannel",
            "uptimecheckconfig": "gcp:monitoring:uptimecheckconfig",
        }

        base = {
            "service": "monitoring",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "region": "global",  # Monitoring is a global service
            "project_id": getattr(self.session, "project_id", "unknown"),
            "display_name": raw_data["display_name"],
        }

        if raw_data["type"] == "alertpolicy":
            base.update(
                {
                    "documentation": raw_data["documentation"],
                    "conditions": raw_data["conditions"],
                    "notification_channels": raw_data["notification_channels"],
                    "enabled": raw_data["enabled"],
                    "combiner": raw_data["combiner"],
                }
            )
        elif raw_data["type"] == "notificationchannel":
            base.update(
                {
                    "description": raw_data["description"],
                    "channel_type": raw_data["channel_type"],
                    "labels": raw_data["labels"],
                    "verification_status": raw_data["verification_status"],
                    "enabled": raw_data["enabled"],
                }
            )
        else:  # uptimecheckconfig
            base.update(
                {
                    "monitored_resource": raw_data["monitored_resource"],
                    "http_check": raw_data["http_check"],
                    "tcp_check": raw_data["tcp_check"],
                    "period": raw_data["period"],
                    "timeout": raw_data["timeout"],
                }
            )

        return base
