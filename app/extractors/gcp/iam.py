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
    # --- BEGIN: Top GCP Services Extraction Stubs ---
    def _extract_compute_engine(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Compute Engine instances"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use googleapiclient.discovery or google-cloud-compute
            pass
        except Exception as e:
            logger.error(f"Error extracting Compute Engine instances: {e}")
        return resources

    def _extract_storage_buckets(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Cloud Storage buckets"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-storage
            pass
        except Exception as e:
            logger.error(f"Error extracting Storage buckets: {e}")
        return resources

    def _extract_bigquery_datasets(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract BigQuery datasets"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-bigquery
            pass
        except Exception as e:
            logger.error(f"Error extracting BigQuery datasets: {e}")
        return resources

    def _extract_pubsub_topics(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Pub/Sub topics"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-pubsub
            pass
        except Exception as e:
            logger.error(f"Error extracting Pub/Sub topics: {e}")
        return resources

    def _extract_kubernetes_clusters(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Kubernetes Engine clusters"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-container
            pass
        except Exception as e:
            logger.error(f"Error extracting Kubernetes clusters: {e}")
        return resources

    def _extract_cloud_functions(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Cloud Functions"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-functions
            pass
        except Exception as e:
            logger.error(f"Error extracting Cloud Functions: {e}")
        return resources

    def _extract_spanner_instances(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Cloud Spanner instances"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-spanner
            pass
        except Exception as e:
            logger.error(f"Error extracting Spanner instances: {e}")
        return resources

    def _extract_dataproc_clusters(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Dataproc clusters"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-dataproc
            pass
        except Exception as e:
            logger.error(f"Error extracting Dataproc clusters: {e}")
        return resources

    def _extract_dataflow_jobs(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Dataflow jobs"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-dataflow
            pass
        except Exception as e:
            logger.error(f"Error extracting Dataflow jobs: {e}")
        return resources

    def _extract_firestore_databases(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Firestore databases"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-firestore
            pass
        except Exception as e:
            logger.error(f"Error extracting Firestore databases: {e}")
        return resources

    def _extract_memorystore_instances(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Memorystore instances"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-redis
            pass
        except Exception as e:
            logger.error(f"Error extracting Memorystore instances: {e}")
        return resources

    def _extract_bigtable_instances(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Bigtable instances"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-bigtable
            pass
        except Exception as e:
            logger.error(f"Error extracting Bigtable instances: {e}")
        return resources

    def _extract_dns_managed_zones(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract DNS managed zones"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-dns
            pass
        except Exception as e:
            logger.error(f"Error extracting DNS managed zones: {e}")
        return resources

    def _extract_load_balancers(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Load Balancers"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-compute
            pass
        except Exception as e:
            logger.error(f"Error extracting Load Balancers: {e}")
        return resources

    def _extract_interconnects(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Interconnects"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-compute
            pass
        except Exception as e:
            logger.error(f"Error extracting Interconnects: {e}")
        return resources

    def _extract_armor_policies(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Cloud Armor policies"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-compute
            pass
        except Exception as e:
            logger.error(f"Error extracting Armor policies: {e}")
        return resources

    def _extract_scheduler_jobs(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Cloud Scheduler jobs"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-scheduler
            pass
        except Exception as e:
            logger.error(f"Error extracting Scheduler jobs: {e}")
        return resources

    def _extract_tasks_queues(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Cloud Tasks queues"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-tasks
            pass
        except Exception as e:
            logger.error(f"Error extracting Tasks queues: {e}")
        return resources

    def _extract_logging_sinks(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Logging sinks"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-logging
            pass
        except Exception as e:
            logger.error(f"Error extracting Logging sinks: {e}")
        return resources

    def _extract_monitoring_alerts(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Monitoring alerts"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-monitoring
            pass
        except Exception as e:
            logger.error(f"Error extracting Monitoring alerts: {e}")
        return resources

    def _extract_filestore_instances(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Filestore instances"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-filestore
            pass
        except Exception as e:
            logger.error(f"Error extracting Filestore instances: {e}")
        return resources

    def _extract_iap_resources(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract Identity-Aware Proxy resources"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-iap
            pass
        except Exception as e:
            logger.error(f"Error extracting IAP resources: {e}")
        return resources

    def _extract_resource_manager_projects(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Resource Manager projects"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-resource-manager
            pass
        except Exception as e:
            logger.error(f"Error extracting Resource Manager projects: {e}")
        return resources

    def _extract_billing_accounts(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Billing accounts"""
        resources: List[Dict[str, Any]] = []
        try:
            # TODO: Use google-cloud-billing
            pass
        except Exception as e:
            logger.error(f"Error extracting Billing accounts: {e}")
        return resources

    # --- END: Top GCP Services Extraction Stubs ---
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
            description="Extracts GCP IAM service accounts, policies, roles, Cloud Run, and Cloud SQL instances",
            resource_types=[
                "service-account",
                "iam-policy",
                "role",
                "run-service",
                "sql-instance",
            ],
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

        # Check if IAM API is enabled
        from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

        project_id = gcp_session.project_id
        api_service = API_SERVICE_MAP["iam"]
        if not is_gcp_api_enabled(project_id, api_service, gcp_session.credentials):
            logger.warning(
                f"GCP IAM API is not enabled for project {project_id}. Skipping extraction."
            )
            return []

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
                loop.run_in_executor(
                    executor, self._extract_cloud_run_services, gcp_session
                ),
                loop.run_in_executor(
                    executor, self._extract_cloud_sql_instances, gcp_session
                ),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"GCP IAM extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        logger.info(f"Extracted {len(artifacts)} IAM resources")
        return artifacts

    def _extract_cloud_run_services(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Cloud Run services"""
        resources: List[Dict[str, Any]] = []
        try:
            from google.cloud import run_v2

            client = run_v2.ServicesClient()
            parent = f"projects/{gcp_session.project_id}/locations/-"
            for service in client.list_services(parent=parent):
                resources.append(
                    {
                        "service": "run",
                        "resource_type": "gcp:run:service",
                        "resource_id": service.name,
                        "name": service.name,
                        "location": service.name.split("/")[3],
                        "description": getattr(service, "description", ""),
                        "ingress": getattr(service, "ingress", ""),
                        "template": getattr(service, "template", {}),
                    }
                )
        except Exception as e:
            logger.error(f"Error extracting Cloud Run services: {e}")
        return resources

    def _extract_cloud_sql_instances(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract Cloud SQL instances"""
        resources: List[Dict[str, Any]] = []
        try:
            from googleapiclient.discovery import build

            credentials = getattr(gcp_session, "credentials", None)
            service = build(
                "sqladmin", "v1beta4", credentials=credentials, cache_discovery=False
            )
            project = gcp_session.project_id
            request = service.instances().list(project=project)
            response = request.execute()
            for instance in response.get("items", []):
                resources.append(
                    {
                        "service": "sql",
                        "resource_type": "gcp:sql:instance",
                        "resource_id": instance.get("name"),
                        "name": instance.get("name"),
                        "region": instance.get("region"),
                        "database_version": instance.get("databaseVersion"),
                        "state": instance.get("state"),
                        "settings": instance.get("settings", {}),
                    }
                )
        except Exception as e:
            logger.error(f"Error extracting Cloud SQL instances: {e}")
        return resources

    def _extract_service_accounts(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract service accounts"""
        resources = []
        try:
            from google.cloud import iam_admin_v1

            client = iam_admin_v1.IAMClient(credentials=gcp_session.credentials)
            parent = f"projects/{gcp_session.project_id}"

            request = iam_admin_v1.ListServiceAccountsRequest(name=parent)
            response = client.list_service_accounts(request=request)

            for service_account in response.accounts:
                sa_dict = {
                    "service": "iam",
                    "resource_type": "gcp:iam:service-account",
                    "resource_id": service_account.unique_id or service_account.email,
                    "name": service_account.name,
                    "project_id": service_account.project_id,
                    "unique_id": service_account.unique_id,
                    "email": service_account.email,
                    "display_name": service_account.display_name,
                    "description": service_account.description,
                    "oauth2_client_id": service_account.oauth2_client_id,
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
            client = gcp_session.get_client("resource_manager")
            resource = f"projects/{gcp_session.project_id}"

            policy = client.get_iam_policy(request={"resource": resource})

            policy_dict = {
                "service": "iam",
                "resource_type": "gcp:iam:iam-policy",
                "resource_id": gcp_session.project_id,
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
            from google.cloud import iam_admin_v1

            client = iam_admin_v1.IAMClient(credentials=gcp_session.credentials)
            parent = f"projects/{gcp_session.project_id}"

            request = iam_admin_v1.ListRolesRequest(parent=parent)
            response = client.list_roles(request=request)

            for role in response.roles:
                role_dict = {
                    "service": "iam",
                    "resource_type": "gcp:iam:role",
                    "resource_id": role.name,
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
