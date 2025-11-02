from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPDataprocExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="dataproc",
            version="1.0.0",
            description="Extracts GCP Dataproc clusters and jobs",
            resource_types=[
                "gcp:dataproc:cluster",
                "gcp:dataproc:job",
                "gcp:dataproc:workflowtemplate",
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
            # Check if Dataproc API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Dataproc operations")

            api_service = API_SERVICE_MAP["dataproc"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Dataproc API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import dataproc_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Dataproc operations")

            # List clusters in all regions if no specific region is provided
            locations = [region] if region else ["-"]

            for location in locations:
                # Initialize the clients
                cluster_client = dataproc_v1.ClusterControllerClient()
                job_client = dataproc_v1.JobControllerClient()
                workflow_client = dataproc_v1.WorkflowTemplateServiceClient()

                parent = f"projects/{project_id}/regions/{location}"

                # List Dataproc clusters
                try:
                    for cluster in cluster_client.list_clusters(
                        project_id=project_id, region=location
                    ):
                        cluster_data = {
                            "name": cluster.cluster_name,
                            "type": "cluster",
                            "uuid": cluster.cluster_uuid,
                            "status": (
                                cluster.status.state.name
                                if cluster.status and cluster.status.state
                                else "UNKNOWN"
                            ),
                            "status_detail": (
                                cluster.status.detail if cluster.status else ""
                            ),
                            "create_time": getattr(cluster.status, "create_time", None),
                            "labels": dict(cluster.labels),
                            "config": {
                                "master_config": {
                                    "num_instances": cluster.config.master_config.num_instances,
                                    "machine_type": cluster.config.master_config.machine_type_uri,
                                },
                                "worker_config": {
                                    "num_instances": cluster.config.worker_config.num_instances,
                                    "machine_type": cluster.config.worker_config.machine_type_uri,
                                },
                            },
                            "location": location,
                        }
                        resources.append(self.transform(cluster_data))
                except Exception as e:
                    logger.warning(f"Error listing clusters in {location}: {e}")

                # List Dataproc jobs
                try:
                    for job in job_client.list_jobs(
                        project_id=project_id, region=location
                    ):
                        job_data = {
                            "name": job.reference.job_id,
                            "type": "job",
                            "status": (
                                job.status.state.name
                                if job.status and job.status.state
                                else "UNKNOWN"
                            ),
                            "status_detail": job.status.details if job.status else "",
                            "submission_time": getattr(
                                job.status, "submission_time", None
                            ),
                            "start_time": getattr(job.status, "start_time", None),
                            "end_time": getattr(job.status, "end_time", None),
                            "cluster_name": job.placement.cluster_name,
                            "job_type": job.type_.name if job.type_ else "UNKNOWN",
                            "location": location,
                        }
                        resources.append(self.transform(job_data))
                except Exception as e:
                    logger.warning(f"Error listing jobs in {location}: {e}")

                # List Workflow Templates
                try:
                    for template in workflow_client.list_workflow_templates(
                        parent=parent
                    ):
                        template_data = {
                            "name": template.name,
                            "type": "workflowtemplate",
                            "version": template.version,
                            "create_time": template.create_time,
                            "update_time": template.update_time,
                            "labels": dict(template.labels),
                            "location": location,
                        }
                        resources.append(self.transform(template_data))
                except Exception as e:
                    logger.warning(
                        f"Error listing workflow templates in {location}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error extracting Dataproc resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Dataproc API response to standardized format"""
        resource_type_map = {
            "cluster": "gcp:dataproc:cluster",
            "job": "gcp:dataproc:job",
            "workflowtemplate": "gcp:dataproc:workflowtemplate",
        }

        base = {
            "service": "dataproc",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"],
            "id": raw_data.get("uuid", raw_data["name"]),
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "cluster":
            base.update(
                {
                    "status": raw_data["status"],
                    "status_detail": raw_data["status_detail"],
                    "create_time": raw_data["create_time"],
                    "labels": raw_data["labels"],
                    "config": raw_data["config"],
                }
            )
        elif raw_data["type"] == "job":
            base.update(
                {
                    "status": raw_data["status"],
                    "status_detail": raw_data["status_detail"],
                    "submission_time": raw_data["submission_time"],
                    "start_time": raw_data["start_time"],
                    "end_time": raw_data["end_time"],
                    "cluster_name": raw_data["cluster_name"],
                    "job_type": raw_data["job_type"],
                }
            )
        else:  # workflowtemplate
            base.update(
                {
                    "version": raw_data["version"],
                    "create_time": raw_data["create_time"],
                    "update_time": raw_data["update_time"],
                    "labels": raw_data["labels"],
                }
            )

        return base
