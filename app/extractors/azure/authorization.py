# app/extractors/azure/authorization.py
"""
Azure Authorization extractor for RBAC roles and role assignments.
"""

from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.cloud.azure_session import AzureSession
import logging

logger = logging.getLogger(__name__)


class AzureAuthorizationExtractor(BaseExtractor):
    """Extractor for Azure Authorization (RBAC) resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="authorization",
            version="1.0.0",
            description="Extracts Azure RBAC roles and role assignments",
            resource_types=["role-definition", "role-assignment"],
            cloud_provider="azure",
            supports_regions=False,  # RBAC is global
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure Authorization resources"""
        artifacts = []

        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor, self._extract_authorization_resources, filters
            )

        if isinstance(result, list):
            artifacts.extend(result)

        return artifacts

    def _extract_authorization_resources(
        self, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract Authorization resources"""
        artifacts = []

        try:
            auth_client = self.session.get_client("authorization")

            # Get role definitions at subscription scope
            azure_session = cast(AzureSession, self.session)
            role_definitions = auth_client.role_definitions.list(
                scope=f"/subscriptions/{azure_session.subscription_id}"
            )

            for role_def in role_definitions:
                # Skip built-in roles (they have Microsoft.Authorization prefix)
                if hasattr(role_def, "id") and "Microsoft.Authorization" in role_def.id:
                    continue

                artifact = self.transform(
                    {"resource": role_def, "resource_type": "role-definition"}
                )

                if self.validate(artifact):
                    artifacts.append(artifact)

            # Extract role assignments
            try:
                # Get role assignments at subscription scope
                role_assignments = auth_client.role_assignments.list_for_scope(
                    scope=f"/subscriptions/{azure_session.subscription_id}"
                )
                artifacts.extend(self._extract_role_assignments(role_assignments))
            except Exception as e:
                logger.error(f"Failed to extract role assignments: {e}")

        except Exception as e:
            logger.error(f"Failed to get Authorization client: {e}")

        return artifacts

    def _extract_role_assignments(self, role_assignments) -> List[Dict[str, Any]]:
        """Extract role assignments"""
        artifacts = []

        for assignment in role_assignments:
            artifact = self.transform(
                {"resource": assignment, "resource_type": "role-assignment"}
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure Authorization resource to standardized format"""
        resource = raw_data["resource"]
        resource_type = raw_data["resource_type"]

        # For authorization resources, we don't have location
        # Use a placeholder or extract from scope if available
        location = "global"

        if resource_type == "role-definition":
            config = {
                "role_name": resource.role_name,
                "description": getattr(resource, "description", None),
                "type": resource.type,
                "permissions": [],
            }

            # Add permissions
            if hasattr(resource, "permissions") and resource.permissions:
                for perm in resource.permissions:
                    perm_config = {}

                    if hasattr(perm, "actions") and perm.actions:
                        perm_config["actions"] = [action for action in perm.actions]

                    if hasattr(perm, "not_actions") and perm.not_actions:
                        perm_config["not_actions"] = [
                            action for action in perm.not_actions
                        ]

                    if hasattr(perm, "data_actions") and perm.data_actions:
                        perm_config["data_actions"] = [
                            action for action in perm.data_actions
                        ]

                    if hasattr(perm, "not_data_actions") and perm.not_data_actions:
                        perm_config["not_data_actions"] = [
                            action for action in perm.not_data_actions
                        ]

                    if perm_config:
                        config["permissions"].append(perm_config)

            # Add assignable scopes
            if hasattr(resource, "assignable_scopes") and resource.assignable_scopes:
                config["assignable_scopes"] = [
                    scope for scope in resource.assignable_scopes
                ]

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:authorization:role-definition",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="authorization",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        elif resource_type == "role-assignment":
            config = {
                "role_definition_id": resource.role_definition_id,
                "principal_id": resource.principal_id,
                "principal_type": getattr(resource, "principal_type", None),
                "scope": resource.scope,
            }

            # Extract role name from role definition ID
            if resource.role_definition_id:
                role_name = self._extract_role_name_from_id(resource.role_definition_id)
                config["role_name"] = role_name

            # Extract scope information
            scope_info = self._parse_scope(resource.scope)
            config.update(scope_info)

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:authorization:role-assignment",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="authorization",
                    region=location,
                    subscription_id=self._get_subscription_id_from_scope(
                        resource.scope
                    ),
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        return {}

    def _extract_role_name_from_id(self, role_definition_id: str) -> str:
        """Extract role name from role definition ID"""
        # Role definition ID format: /subscriptions/{sub}/providers/Microsoft.Authorization/roleDefinitions/{role-id}
        parts = role_definition_id.split("/")
        if len(parts) >= 2:
            role_id = parts[-1]
            # Common role IDs to names mapping
            role_names = {
                "8e3af657-a8ff-443c-a75c-2fe8c4bcb635": "Owner",
                "b24988ac-6180-42a0-ab88-20f7382dd24c": "Contributor",
                "acdd72a7-3385-48ef-bd42-f606fba81ae7": "Reader",
                "7f951dda-4ed3-4680-a7ca-43fe172d538d": "Virtual Machine Administrator Login",
                "fb879df8-f326-4884-b1cf-06f3ad86be52": "Virtual Machine User Login",
            }
            return role_names.get(role_id, role_id)
        return role_definition_id

    def _parse_scope(self, scope: str) -> Dict[str, Any]:
        """Parse Azure scope to extract meaningful information"""
        scope_info = {"scope_type": "unknown"}

        if scope.startswith("/subscriptions/"):
            scope_info["scope_type"] = "subscription"
            parts = scope.split("/")
            if len(parts) >= 3:
                scope_info["subscription_id"] = parts[2]

            if "resourceGroups" in parts:
                rg_index = parts.index("resourceGroups")
                if rg_index + 1 < len(parts):
                    scope_info["scope_type"] = "resource-group"
                    scope_info["resource_group"] = parts[rg_index + 1]

            if "providers" in parts:
                provider_index = parts.index("providers")
                if provider_index + 2 < len(parts):
                    scope_info["scope_type"] = "resource"
                    scope_info["provider"] = parts[provider_index + 1]
                    scope_info["resource_type"] = parts[provider_index + 2]

        elif scope.startswith("/providers/Microsoft.Management/managementGroups/"):
            scope_info["scope_type"] = "management-group"
            parts = scope.split("/")
            if len(parts) >= 5:
                scope_info["management_group_id"] = parts[4]

        return scope_info

    def _get_subscription_id_from_scope(self, scope: str) -> str:
        """Extract subscription ID from scope"""
        if scope.startswith("/subscriptions/"):
            parts = scope.split("/")
            if len(parts) >= 3:
                return parts[2]
        return ""

    def _get_subscription_id(self, resource_id: str) -> str:
        """Extract subscription ID from Azure resource ID"""
        parts = resource_id.split("/")
        try:
            sub_index = parts.index("subscriptions")
            return parts[sub_index + 1]
        except (ValueError, IndexError):
            return ""

    def _serialize_azure_resource(self, resource: Any) -> Dict[str, Any]:
        """Convert Azure SDK model to dictionary"""
        # Azure SDK models have as_dict() method
        if hasattr(resource, "as_dict"):
            return resource.as_dict()
        return {}
