from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPLoadBalancerExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="loadbalancer",
            version="1.0.0",
            description="Extracts GCP Load Balancer configurations",
            resource_types=[
                "gcp:loadbalancer:urlmap",
                "gcp:loadbalancer:forwardingrule",
                "gcp:loadbalancer:targetproxy",
                "gcp:loadbalancer:backendservice",
            ],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Compute API is enabled (Load Balancer uses Compute API)
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Load Balancer operations")

            api_service = API_SERVICE_MAP["compute"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Compute API is not enabled for project {project_id}. Skipping Load Balancer extraction."
                )
                return []

            from google.cloud import compute_v1

            # Get URL Maps (Load Balancer configurations)
            url_map_client = compute_v1.UrlMapsClient()
            for url_map in url_map_client.list(project=project_id):
                raw_data = {
                    "name": url_map.name,
                    "id": url_map.id,
                    "type": "urlmap",
                    "description": getattr(url_map, "description", ""),
                    "host_rules": [
                        rule.hosts for rule in getattr(url_map, "host_rules", [])
                    ],
                    "default_service": getattr(url_map, "default_service", ""),
                }
                resources.append(self.transform(raw_data))

            # Get Backend Services
            backend_client = compute_v1.BackendServicesClient()
            for backend in backend_client.list(project=project_id):
                raw_data = {
                    "name": backend.name,
                    "id": backend.id,
                    "type": "backendservice",
                    "description": getattr(backend, "description", ""),
                    "protocol": getattr(backend, "protocol", ""),
                    "timeout_sec": getattr(backend, "timeout_sec", 0),
                }
                resources.append(self.transform(raw_data))

            # Get Forwarding Rules
            forwarding_client = compute_v1.ForwardingRulesClient()
            request = compute_v1.AggregatedListForwardingRulesRequest(
                project=project_id
            )
            for (
                scope,
                forwarding_rules_scoped_list,
            ) in forwarding_client.aggregated_list(request=request):
                if not forwarding_rules_scoped_list.forwarding_rules:
                    continue
                for forwarding_rule in forwarding_rules_scoped_list.forwarding_rules:
                    raw_data = {
                        "name": forwarding_rule.name,
                        "id": forwarding_rule.id,
                        "type": "forwardingrule",
                        "description": getattr(forwarding_rule, "description", ""),
                        "ip_address": getattr(forwarding_rule, "ip_address", ""),
                        "port_range": getattr(forwarding_rule, "port_range", ""),
                        "region": scope.split("/")[-1],
                    }
                    resources.append(self.transform(raw_data))

        except Exception as e:
            logger.error(f"Error extracting Load Balancer resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Load Balancer API response to standardized format"""
        resource_type_map = {
            "urlmap": "gcp:loadbalancer:urlmap",
            "backendservice": "gcp:loadbalancer:backendservice",
            "forwardingrule": "gcp:loadbalancer:forwardingrule",
        }

        base = {
            "service": "loadbalancer",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"],
            "id": str(raw_data["id"]),
            "region": raw_data.get("region", "global"),
            "project_id": getattr(self.session, "project_id", "unknown"),
            "description": raw_data.get("description", ""),
        }

        if raw_data["type"] == "urlmap":
            base.update(
                {
                    "host_rules": raw_data["host_rules"],
                    "default_service": raw_data["default_service"],
                }
            )
        elif raw_data["type"] == "backendservice":
            base.update(
                {
                    "protocol": raw_data["protocol"],
                    "timeout_sec": raw_data["timeout_sec"],
                }
            )
        elif raw_data["type"] == "forwardingrule":
            base.update(
                {
                    "ip_address": raw_data["ip_address"],
                    "port_range": raw_data["port_range"],
                }
            )

        return base
