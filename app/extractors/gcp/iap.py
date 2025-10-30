from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPIAPExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="iap",
            version="1.0.0",
            description="Extracts GCP Identity-Aware Proxy (IAP) settings and web configurations",
            resource_types=["gcp:iap:web", "gcp:iap:tunnel", "gcp:iap:oauth-client"],
            cloud_provider="gcp",
            supports_regions=False,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if IAP API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for IAP operations")

            api_service = API_SERVICE_MAP["iap"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP IAP API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import iap_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for IAP operations")

            client = iap_v1.IdentityAwareProxyClient()

            try:
                # List IAP web configurations
                parent = f"projects/{project_id}/iap_web"
                web_configs = client.list_identity_aware_proxy_clients(parent=parent)

                for web_config in web_configs:
                    config_data = {
                        "name": web_config.name,
                        "type": "web",
                        "display_name": web_config.display_name,
                        "secret": web_config.secret,
                        "create_time": web_config.create_time,
                        "update_time": web_config.update_time,
                    }
                    resources.append(self.transform(config_data))

                # List IAP OAuth clients
                try:
                    oauth_parent = (
                        f"projects/{project_id}/brands/-/identityAwareProxyClients"
                    )
                    oauth_clients = client.list_identity_aware_proxy_clients(
                        parent=oauth_parent
                    )

                    for oauth_client in oauth_clients:
                        oauth_data = {
                            "name": oauth_client.name,
                            "type": "oauth-client",
                            "display_name": oauth_client.display_name,
                            "client_id": oauth_client.name.split("/")[-1],
                            "create_time": oauth_client.create_time,
                            "update_time": oauth_client.update_time,
                        }
                        resources.append(self.transform(oauth_data))
                except Exception as e:
                    logger.warning(f"Error listing IAP OAuth clients: {e}")

                # List IAP tunnel instances
                try:
                    tunnel_parent = f"projects/{project_id}/iap_tunnel"
                    tunnels = client.list_tunnel_instances(parent=tunnel_parent)

                    for tunnel in tunnels:
                        tunnel_data = {
                            "name": tunnel.name,
                            "type": "tunnel",
                            "zone": tunnel.zone,
                            "instance_id": tunnel.instance_id,
                            "enabled": tunnel.enabled,
                            "service_account": tunnel.service_account,
                        }
                        resources.append(self.transform(tunnel_data))
                except Exception as e:
                    logger.warning(f"Error listing IAP tunnels: {e}")

            except Exception as e:
                logger.warning(f"Error listing IAP resources: {e}")

        except Exception as e:
            logger.error(f"Error extracting IAP resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw IAP API response to standardized format"""
        resource_type_map = {
            "web": "gcp:iap:web",
            "tunnel": "gcp:iap:tunnel",
            "oauth-client": "gcp:iap:oauth-client",
        }

        base = {
            "service": "iap",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "web":
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "secret": raw_data["secret"],
                    "create_time": raw_data["create_time"],
                    "update_time": raw_data["update_time"],
                }
            )
        elif raw_data["type"] == "tunnel":
            base.update(
                {
                    "zone": raw_data["zone"],
                    "instance_id": raw_data["instance_id"],
                    "enabled": raw_data["enabled"],
                    "service_account": raw_data["service_account"],
                }
            )
        else:  # oauth-client
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "client_id": raw_data["client_id"],
                    "create_time": raw_data["create_time"],
                    "update_time": raw_data["update_time"],
                }
            )

        return base
