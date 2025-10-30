from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPArmorExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="armor",
            version="1.0.0",
            description="Extracts GCP Cloud Armor security policies",
            resource_types=["gcp:armor:securitypolicy", "gcp:armor:securityrule"],
            cloud_provider="gcp",
            supports_regions=False,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Compute API is enabled (Cloud Armor uses Compute API)
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Armor operations")

            api_service = API_SERVICE_MAP["compute"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Compute API is not enabled for project {project_id}. Skipping Cloud Armor extraction."
                )
                return []

            from google.cloud import compute_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud Armor operations")

            security_policies_client = compute_v1.SecurityPoliciesClient()
            for policy in security_policies_client.list(project=project_id):
                raw_data = {
                    "name": policy.name,
                    "id": policy.id,
                    "type": "securitypolicy",
                    "description": getattr(policy, "description", ""),
                    "fingerprint": getattr(policy, "fingerprint", ""),
                    "rules": [
                        {
                            "action": rule.action,
                            "priority": rule.priority,
                            "description": getattr(rule, "description", ""),
                            "preview": getattr(rule, "preview", False),
                        }
                        for rule in getattr(policy, "rules", [])
                    ],
                }
                resources.append(self.transform(raw_data))

                # Add each rule as a separate resource
                for rule in getattr(policy, "rules", []):
                    rule_data = {
                        "name": f"{policy.name}/rules/{rule.priority}",
                        "id": f"{policy.id}/rules/{rule.priority}",
                        "type": "securityrule",
                        "policy_name": policy.name,
                        "action": rule.action,
                        "priority": rule.priority,
                        "description": getattr(rule, "description", ""),
                        "preview": getattr(rule, "preview", False),
                    }
                    resources.append(self.transform(rule_data))

        except Exception as e:
            logger.error(f"Error extracting Cloud Armor resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Armor API response to standardized format"""
        resource_type_map = {
            "securitypolicy": "gcp:armor:securitypolicy",
            "securityrule": "gcp:armor:securityrule",
        }

        base = {
            "service": "armor",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"],
            "id": str(raw_data["id"]),
            "region": "global",  # Cloud Armor is a global service
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "securitypolicy":
            base.update(
                {
                    "description": raw_data["description"],
                    "fingerprint": raw_data["fingerprint"],
                    "rules_count": len(raw_data.get("rules", [])),
                    "rules": raw_data.get("rules", []),
                }
            )
        else:  # securityrule
            base.update(
                {
                    "policy_name": raw_data["policy_name"],
                    "action": raw_data["action"],
                    "priority": raw_data["priority"],
                    "description": raw_data["description"],
                    "preview": raw_data["preview"],
                }
            )

        return base
