from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPResourceManagerExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="resourcemanager",
            version="1.0.0",
            description="Extracts GCP Resource Manager resources including projects, folders, and organizations",
            resource_types=[
                "gcp:resourcemanager:project",
                "gcp:resourcemanager:folder",
                "gcp:resourcemanager:organization",
                "gcp:resourcemanager:project-iam-policy",
                "gcp:resourcemanager:folder-iam-policy",
                "gcp:resourcemanager:org-iam-policy",
            ],
            cloud_provider="gcp",
            supports_regions=False,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Resource Manager API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError(
                    "Project ID is required for Resource Manager operations"
                )

            api_service = API_SERVICE_MAP["resourcemanager"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Resource Manager API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import resourcemanager_v3

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError(
                    "Project ID is required for Resource Manager operations"
                )

            projects_client = resourcemanager_v3.ProjectsClient()
            folders_client = resourcemanager_v3.FoldersClient()
            organizations_client = resourcemanager_v3.OrganizationsClient()

            try:
                # List Organizations
                for org in organizations_client.search_organizations():
                    org_data = {
                        "name": org.name,
                        "type": "organization",
                        "display_name": org.display_name,
                        "create_time": org.create_time,
                        "update_time": org.update_time,
                        "state": org.state.name if org.state else "UNKNOWN",
                        "directory_customer_id": org.directory_customer_id,
                    }
                    resources.append(self.transform(org_data))

                    # Get organization IAM policy
                    try:
                        org_policy = organizations_client.get_iam_policy(
                            request={"resource": org.name}
                        )
                        org_policy_data = {
                            "name": f"{org.name}/iam-policy",
                            "type": "org-iam-policy",
                            "resource_name": org.name,
                            "bindings": [
                                {
                                    "role": binding.role,
                                    "members": list(binding.members),
                                    "condition": (
                                        {
                                            "title": binding.condition.title,
                                            "description": binding.condition.description,
                                            "expression": binding.condition.expression,
                                        }
                                        if binding.condition
                                        else None
                                    ),
                                }
                                for binding in org_policy.bindings
                            ],
                            "etag": org_policy.etag,
                            "version": org_policy.version,
                        }
                        resources.append(self.transform(org_policy_data))
                    except Exception as e:
                        logger.warning(
                            f"Error getting IAM policy for organization {org.name}: {e}"
                        )

                # List Folders
                for folder in folders_client.search_folders():
                    folder_data = {
                        "name": folder.name,
                        "type": "folder",
                        "display_name": folder.display_name,
                        "create_time": folder.create_time,
                        "update_time": folder.update_time,
                        "state": folder.state.name if folder.state else "UNKNOWN",
                        "parent": folder.parent,
                    }
                    resources.append(self.transform(folder_data))

                    # Get folder IAM policy
                    try:
                        folder_policy = folders_client.get_iam_policy(
                            request={"resource": folder.name}
                        )
                        folder_policy_data = {
                            "name": f"{folder.name}/iam-policy",
                            "type": "folder-iam-policy",
                            "resource_name": folder.name,
                            "bindings": [
                                {
                                    "role": binding.role,
                                    "members": list(binding.members),
                                    "condition": (
                                        {
                                            "title": binding.condition.title,
                                            "description": binding.condition.description,
                                            "expression": binding.condition.expression,
                                        }
                                        if binding.condition
                                        else None
                                    ),
                                }
                                for binding in folder_policy.bindings
                            ],
                            "etag": folder_policy.etag,
                            "version": folder_policy.version,
                        }
                        resources.append(self.transform(folder_policy_data))
                    except Exception as e:
                        logger.warning(
                            f"Error getting IAM policy for folder {folder.name}: {e}"
                        )

                # List Projects
                for project in projects_client.search_projects():
                    project_data = {
                        "name": project.name,
                        "type": "project",
                        "display_name": project.display_name,
                        "create_time": project.create_time,
                        "update_time": project.update_time,
                        "state": project.state.name if project.state else "UNKNOWN",
                        "parent": project.parent,
                        "project_id": project.project_id,
                        "project_number": project.name.split("/")[-1],
                        "labels": dict(project.labels),
                    }
                    resources.append(self.transform(project_data))

                    # Get project IAM policy
                    try:
                        project_policy = projects_client.get_iam_policy(
                            request={"resource": project.name}
                        )
                        project_policy_data = {
                            "name": f"{project.name}/iam-policy",
                            "type": "project-iam-policy",
                            "resource_name": project.name,
                            "bindings": [
                                {
                                    "role": binding.role,
                                    "members": list(binding.members),
                                    "condition": (
                                        {
                                            "title": binding.condition.title,
                                            "description": binding.condition.description,
                                            "expression": binding.condition.expression,
                                        }
                                        if binding.condition
                                        else None
                                    ),
                                }
                                for binding in project_policy.bindings
                            ],
                            "etag": project_policy.etag,
                            "version": project_policy.version,
                        }
                        resources.append(self.transform(project_policy_data))
                    except Exception as e:
                        logger.warning(
                            f"Error getting IAM policy for project {project.name}: {e}"
                        )

            except Exception as e:
                logger.warning(f"Error listing Resource Manager resources: {e}")

        except Exception as e:
            logger.error(f"Error extracting Resource Manager resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Resource Manager API response to standardized format"""
        resource_type_map = {
            "project": "gcp:resourcemanager:project",
            "folder": "gcp:resourcemanager:folder",
            "organization": "gcp:resourcemanager:organization",
            "project-iam-policy": "gcp:resourcemanager:project-iam-policy",
            "folder-iam-policy": "gcp:resourcemanager:folder-iam-policy",
            "org-iam-policy": "gcp:resourcemanager:org-iam-policy",
        }

        base = {
            "service": "resourcemanager",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] in ["project", "folder", "organization"]:
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "create_time": raw_data["create_time"],
                    "update_time": raw_data["update_time"],
                    "state": raw_data["state"],
                }
            )

            if raw_data["type"] == "project":
                base.update(
                    {
                        "parent": raw_data["parent"],
                        "project_id": raw_data["project_id"],
                        "project_number": raw_data["project_number"],
                        "labels": raw_data["labels"],
                    }
                )
            elif raw_data["type"] == "folder":
                base.update(
                    {
                        "parent": raw_data["parent"],
                    }
                )
            else:  # organization
                base.update(
                    {
                        "directory_customer_id": raw_data["directory_customer_id"],
                    }
                )
        else:  # IAM policies
            base.update(
                {
                    "resource_name": raw_data["resource_name"],
                    "bindings": raw_data["bindings"],
                    "etag": raw_data["etag"],
                    "version": raw_data["version"],
                }
            )

        return base
