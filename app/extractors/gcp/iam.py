# app/extractors/gcp/iam.py
"""
GCP Identity and Access Management (IAM) resource extractor.
Extracts service accounts, IAM policies, and roles.
"""

from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.cloud.gcp_session import GCPSession
import logging

logger = logging.getLogger(__name__)


class GCPIAMExtractor(BaseExtractor):
    """
    Extractor for GCP Identity and Access Management (IAM) resources.

    Extracts:
    - Service Accounts
    - IAM Policies (project-level)
    - Custom Roles
    """

    def get_metadata(self) -> ExtractorMetadata:
        """
        Get metadata about the GCP IAM extractor.

        Returns:
            ExtractorMetadata object
        """
        return ExtractorMetadata(
            service_name="iam",
            version="1.0.0",
            description="Extracts GCP IAM service accounts, policies, and roles",
            resource_types=["service-account", "iam-policy", "role"],
            cloud_provider="gcp",
            supports_regions=False,  # IAM is global
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract GCP IAM resources.

        Args:
            region: Not used for IAM (global service)
            filters: Optional filters to apply (not currently used)

        Returns:
            List of raw resource dictionaries from GCP API
        """
        # Cast session to GCPSession for type checking
        gcp_session = cast(GCPSession, self.session)

        logger.info("Extracting GCP IAM resources")

        # Use thread pool for parallel extraction
        artifacts = []
        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor, self._extract_service_accounts, gcp_session
                ),
                loop.run_in_executor(
                    executor, self._extract_project_policy, gcp_session
                ),
                loop.run_in_executor(executor, self._extract_roles, gcp_session),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"GCP IAM extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        logger.info(f"Extracted {len(artifacts)} IAM resources")
        return artifacts

    def _extract_service_accounts(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract service accounts"""
        resources = []
        try:
            from google.cloud import iam_v1  # type: ignore[attr-defined,import-untyped]

            client = gcp_session.get_client("iam")
            parent = f"projects/{gcp_session.project_id}"

            request = iam_v1.ListServiceAccountsRequest(name=parent)
            response = client.list_service_accounts(request=request)

            for service_account in response.accounts:
                sa_dict = {
                    "resource_type": "gcp:iam:service-account",
                    "name": service_account.name,
                    "project_id": service_account.project_id,
                    "unique_id": service_account.unique_id,
                    "email": service_account.email,
                    "display_name": service_account.display_name,
                    "description": service_account.description,
                    "oauth2_client_id": service_account.oauth_2_client_id,
                    "disabled": service_account.disabled,
                }
                resources.append(sa_dict)

        except Exception as e:
            logger.error(f"Error extracting service accounts: {e}")

        return resources

    def _extract_project_policy(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract project-level IAM policy"""
        resources = []
        try:
            from google.cloud import resourcemanager_v3  # type: ignore[import-untyped]

            client = gcp_session.get_client("resource_manager")
            resource = f"projects/{gcp_session.project_id}"

            policy = client.get_iam_policy(request={"resource": resource})

            policy_dict = {
                "resource_type": "gcp:iam:iam-policy",
                "project_id": gcp_session.project_id,
                "version": policy.version,
                "etag": policy.etag,
                "bindings": [
                    {
                        "role": binding.role,
                        "members": [member for member in binding.members],
                        "condition": (
                            {
                                "title": (
                                    binding.condition.title if binding.condition else ""
                                ),
                                "description": (
                                    binding.condition.description
                                    if binding.condition
                                    else ""
                                ),
                                "expression": (
                                    binding.condition.expression
                                    if binding.condition
                                    else ""
                                ),
                            }
                            if binding.condition
                            else {}
                        ),
                    }
                    for binding in policy.bindings
                ],
            }
            resources.append(policy_dict)

        except Exception as e:
            logger.error(f"Error extracting project IAM policy: {e}")

        return resources

    def _extract_roles(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract custom roles"""
        resources = []
        try:
            from google.cloud import iam_v1  # type: ignore[attr-defined,import-untyped]

            client = gcp_session.get_client("iam")
            parent = f"projects/{gcp_session.project_id}"

            request = iam_v1.ListRolesRequest(parent=parent)
            response = client.list_roles(request=request)

            for role in response.roles:
                role_dict = {
                    "resource_type": "gcp:iam:role",
                    "name": role.name,
                    "title": role.title,
                    "description": role.description,
                    "included_permissions": [
                        perm for perm in role.included_permissions
                    ],
                    "stage": role.stage,
                    "etag": role.etag,
                }
                resources.append(role_dict)

        except Exception as e:
            logger.error(f"Error extracting roles: {e}")

        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw GCP IAM data into standardized metadata format.

        Args:
            raw_data: Raw resource dictionary from GCP API

        Returns:
            Standardized artifact dictionary
        """
        try:
            # Extract common fields
            resource_type_suffix = raw_data.get(
                "resource_type", "gcp:iam:service-account"
            )
            resource_id = raw_data.get("name", raw_data.get("email", "unknown"))

            # Get project ID from session
            gcp_session = cast(GCPSession, self.session)
            project_id = gcp_session.project_id

            # Build configuration based on resource type
            config = {}

            if "service-account" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "project_id": raw_data.get("project_id", ""),
                    "unique_id": raw_data.get("unique_id", ""),
                    "email": raw_data.get("email", ""),
                    "display_name": raw_data.get("display_name", ""),
                    "description": raw_data.get("description", ""),
                    "oauth2_client_id": raw_data.get("oauth2_client_id", ""),
                    "disabled": raw_data.get("disabled", False),
                }
            elif "iam-policy" in resource_type_suffix:
                config = {
                    "project_id": raw_data.get("project_id", ""),
                    "version": raw_data.get("version", 1),
                    "etag": raw_data.get("etag", ""),
                    "bindings": raw_data.get("bindings", []),
                }
            elif "role" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "title": raw_data.get("title", ""),
                    "description": raw_data.get("description", ""),
                    "included_permissions": raw_data.get("included_permissions", []),
                    "stage": raw_data.get("stage", ""),
                    "etag": raw_data.get("etag", ""),
                }

            return {
                "cloud_provider": "gcp",
                "resource_type": resource_type_suffix,
                "metadata": self.create_metadata_object(
                    resource_id=resource_id,
                    service="iam",
                    region="global",  # IAM is global
                    project_id=project_id,
                ),
                "configuration": config,
                "raw": raw_data,
            }

        except Exception as e:
            logger.error(f"Error transforming IAM resource: {str(e)}")
            return {}
