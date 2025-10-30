from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging
import google.cloud.pubsub_v1 as pubsub_v1

logger = logging.getLogger(__name__)


class GCPPubSubExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="pubsub",
            version="1.0.0",
            description="Extracts GCP Pub/Sub topics and subscriptions",
            resource_types=["gcp:pubsub:topic", "gcp:pubsub:subscription"],
            cloud_provider="gcp",
            supports_regions=False,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Pub/Sub API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Pub/Sub operations")

            api_service = API_SERVICE_MAP["pubsub"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Pub/Sub API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Pub/Sub operations")

            # List topics
            publisher = pubsub_v1.PublisherClient()
            project_path = f"projects/{project_id}"

            for topic in publisher.list_topics(project=project_path):
                topic_data = {
                    "name": topic.name,
                    "type": "topic",
                    "labels": dict(topic.labels),
                    "kms_key_name": topic.kms_key_name,
                    "message_retention_duration": getattr(
                        topic, "message_retention_duration", None
                    ),
                    "message_storage_policy": (
                        {
                            "allowed_persistence_regions": getattr(
                                topic.message_storage_policy,
                                "allowed_persistence_regions",
                                [],
                            )
                        }
                        if getattr(topic, "message_storage_policy", None)
                        else {}
                    ),
                }
                resources.append(self.transform(topic_data))

                # List subscriptions for each topic
                try:
                    for subscription in publisher.list_topic_subscriptions(
                        topic=topic.name
                    ):
                        sub_client = pubsub_v1.SubscriberClient()
                        sub_details = sub_client.get_subscription(
                            subscription=subscription
                        )
                        sub_data = {
                            "name": sub_details.name,
                            "type": "subscription",
                            "topic": topic.name,
                            "labels": dict(sub_details.labels),
                            "ack_deadline_seconds": sub_details.ack_deadline_seconds,
                            "message_retention_duration": getattr(
                                sub_details, "message_retention_duration", None
                            ),
                            "retain_acked_messages": sub_details.retain_acked_messages,
                            "enable_message_ordering": sub_details.enable_message_ordering,
                            "expiration_policy": (
                                {
                                    "ttl": getattr(
                                        sub_details.expiration_policy, "ttl", None
                                    )
                                }
                                if getattr(sub_details, "expiration_policy", None)
                                else {}
                            ),
                        }
                        resources.append(self.transform(sub_data))
                except Exception as e:
                    logger.warning(
                        f"Error listing subscriptions for topic {topic.name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error extracting Pub/Sub resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Pub/Sub API response to standardized format"""
        resource_type_map = {
            "topic": "gcp:pubsub:topic",
            "subscription": "gcp:pubsub:subscription",
        }

        base = {
            "service": "pubsub",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "region": "global",  # Pub/Sub is a global service
            "project_id": getattr(self.session, "project_id", "unknown"),
            "labels": raw_data.get("labels", {}),
        }

        if raw_data["type"] == "topic":
            base.update(
                {
                    "kms_key_name": raw_data["kms_key_name"],
                    "message_retention_duration": raw_data[
                        "message_retention_duration"
                    ],
                    "message_storage_policy": raw_data["message_storage_policy"],
                }
            )
        else:  # subscription
            base.update(
                {
                    "topic": raw_data["topic"].split("/")[-1],
                    "ack_deadline_seconds": raw_data["ack_deadline_seconds"],
                    "message_retention_duration": raw_data[
                        "message_retention_duration"
                    ],
                    "retain_acked_messages": raw_data["retain_acked_messages"],
                    "enable_message_ordering": raw_data["enable_message_ordering"],
                    "expiration_policy": raw_data["expiration_policy"],
                }
            )

        return base
