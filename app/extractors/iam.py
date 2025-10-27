# app/extractors/iam.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class IAMExtractor(BaseExtractor):
    """Extractor for IAM resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="iam",
            version="1.0.0",
            description="Extracts IAM users, roles, policies, and groups",
            resource_types=["user", "role", "policy", "group"],
            supports_regions=False,  # IAM is global
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract IAM resources"""
        iam_client = self.session.client("iam")
        artifacts = []

        # Extract different IAM resource types concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()

            tasks = [
                loop.run_in_executor(executor, self._extract_users, iam_client),
                loop.run_in_executor(executor, self._extract_roles, iam_client),
                loop.run_in_executor(executor, self._extract_policies, iam_client),
                loop.run_in_executor(executor, self._extract_groups, iam_client),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"IAM extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_users(self, client) -> List[Dict[str, Any]]:
        """Extract IAM users"""
        artifacts = []
        paginator = client.get_paginator("list_users")

        for page in paginator.paginate():
            for user in page["Users"]:
                try:
                    # Get detailed user info
                    user_name = user["UserName"]

                    # Get attached policies
                    attached_policies = client.list_attached_user_policies(
                        UserName=user_name
                    )

                    # Get inline policies
                    inline_policies = client.list_user_policies(UserName=user_name)

                    # Get groups
                    groups = client.list_groups_for_user(UserName=user_name)

                    # Get access keys
                    access_keys = client.list_access_keys(UserName=user_name)

                    # Get MFA devices
                    mfa_devices = client.list_mfa_devices(UserName=user_name)

                    user_data = {
                        **user,
                        "attached_policies": attached_policies.get(
                            "AttachedPolicies", []
                        ),
                        "inline_policies": inline_policies.get("PolicyNames", []),
                        "groups": [g["GroupName"] for g in groups.get("Groups", [])],
                        "access_keys": access_keys.get("AccessKeyMetadata", []),
                        "mfa_devices": mfa_devices.get("MFADevices", []),
                    }

                    artifact = self.transform(
                        {"resource": user_data, "resource_type": "user"}
                    )

                    if self.validate(artifact):
                        artifacts.append(artifact)

                except Exception as e:
                    logger.error(f"Failed to extract user {user.get('UserName')}: {e}")

        return artifacts

    def _extract_roles(self, client) -> List[Dict[str, Any]]:
        """Extract IAM roles"""
        artifacts = []
        paginator = client.get_paginator("list_roles")

        for page in paginator.paginate():
            for role in page["Roles"]:
                try:
                    role_name = role["RoleName"]

                    # Get attached policies
                    attached_policies = client.list_attached_role_policies(
                        RoleName=role_name
                    )

                    # Get inline policies
                    inline_policies = client.list_role_policies(RoleName=role_name)

                    role_data = {
                        **role,
                        "attached_policies": attached_policies.get(
                            "AttachedPolicies", []
                        ),
                        "inline_policies": inline_policies.get("PolicyNames", []),
                    }

                    artifact = self.transform(
                        {"resource": role_data, "resource_type": "role"}
                    )

                    if self.validate(artifact):
                        artifacts.append(artifact)

                except Exception as e:
                    logger.error(f"Failed to extract role {role.get('RoleName')}: {e}")

        return artifacts

    def _extract_policies(self, client) -> List[Dict[str, Any]]:
        """Extract customer-managed IAM policies"""
        artifacts = []
        paginator = client.get_paginator("list_policies")

        for page in paginator.paginate(Scope="Local"):  # Only customer-managed
            for policy in page["Policies"]:
                try:
                    policy_arn = policy["Arn"]

                    # Get policy version
                    policy_version = client.get_policy_version(
                        PolicyArn=policy_arn, VersionId=policy["DefaultVersionId"]
                    )

                    policy_data = {
                        **policy,
                        "policy_document": policy_version["PolicyVersion"]["Document"],
                    }

                    artifact = self.transform(
                        {"resource": policy_data, "resource_type": "policy"}
                    )

                    if self.validate(artifact):
                        artifacts.append(artifact)

                except Exception as e:
                    logger.error(
                        f"Failed to extract policy {policy.get('PolicyName')}: {e}"
                    )

        return artifacts

    def _extract_groups(self, client) -> List[Dict[str, Any]]:
        """Extract IAM groups"""
        artifacts = []
        paginator = client.get_paginator("list_groups")

        for page in paginator.paginate():
            for group in page["Groups"]:
                try:
                    group_name = group["GroupName"]

                    # Get attached policies
                    attached_policies = client.list_attached_group_policies(
                        GroupName=group_name
                    )

                    # Get inline policies
                    inline_policies = client.list_group_policies(GroupName=group_name)

                    group_data = {
                        **group,
                        "attached_policies": attached_policies.get(
                            "AttachedPolicies", []
                        ),
                        "inline_policies": inline_policies.get("PolicyNames", []),
                    }

                    artifact = self.transform(
                        {"resource": group_data, "resource_type": "group"}
                    )

                    if self.validate(artifact):
                        artifacts.append(artifact)

                except Exception as e:
                    logger.error(
                        f"Failed to extract group {group.get('GroupName')}: {e}"
                    )

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform IAM resource to standardized format"""
        resource = raw_data["resource"]
        resource_type = raw_data["resource_type"]

        if resource_type == "user":
            return {
                "resource_id": resource["Arn"],
                "resource_type": "iam:user",
                "service": "iam",
                "account_id": resource["Arn"].split(":")[4],
                "configuration": {
                    "user_name": resource["UserName"],
                    "user_id": resource["UserId"],
                    "path": resource.get("Path"),
                    "create_date": resource.get("CreateDate"),
                    "attached_policies": resource.get("attached_policies", []),
                    "inline_policies": resource.get("inline_policies", []),
                    "groups": resource.get("groups", []),
                    "access_keys": resource.get("access_keys", []),
                    "mfa_enabled": len(resource.get("mfa_devices", [])) > 0,
                    "password_last_used": resource.get("PasswordLastUsed"),
                },
                "raw": resource,
            }
        elif resource_type == "role":
            return {
                "resource_id": resource["Arn"],
                "resource_type": "iam:role",
                "service": "iam",
                "account_id": resource["Arn"].split(":")[4],
                "configuration": {
                    "role_name": resource["RoleName"],
                    "role_id": resource["RoleId"],
                    "path": resource.get("Path"),
                    "assume_role_policy": resource.get("AssumeRolePolicyDocument"),
                    "attached_policies": resource.get("attached_policies", []),
                    "inline_policies": resource.get("inline_policies", []),
                    "max_session_duration": resource.get("MaxSessionDuration"),
                    "create_date": resource.get("CreateDate"),
                },
                "raw": resource,
            }
        elif resource_type == "policy":
            return {
                "resource_id": resource["Arn"],
                "resource_type": "iam:policy",
                "service": "iam",
                "account_id": resource["Arn"].split(":")[4],
                "configuration": {
                    "policy_name": resource["PolicyName"],
                    "policy_id": resource["PolicyId"],
                    "path": resource.get("Path"),
                    "default_version_id": resource.get("DefaultVersionId"),
                    "policy_document": resource.get("policy_document"),
                    "attachment_count": resource.get("AttachmentCount"),
                    "create_date": resource.get("CreateDate"),
                },
                "raw": resource,
            }
        elif resource_type == "group":
            return {
                "resource_id": resource["Arn"],
                "resource_type": "iam:group",
                "service": "iam",
                "account_id": resource["Arn"].split(":")[4],
                "configuration": {
                    "group_name": resource["GroupName"],
                    "group_id": resource["GroupId"],
                    "path": resource.get("Path"),
                    "attached_policies": resource.get("attached_policies", []),
                    "inline_policies": resource.get("inline_policies", []),
                    "create_date": resource.get("CreateDate"),
                },
                "raw": resource,
            }

        return {}
