# app/extractors/ecs.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class ECSExtractor(BaseExtractor):
    """Extractor for AWS ECS (Elastic Container Service) resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="ecs",
            version="1.0.0",
            description="Extracts ECS clusters, services, tasks, and task definitions",
            resource_types=["cluster", "service", "task", "task-definition"],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract ECS resources"""
        # Use us-east-1 as default region if none provided
        region = region or "us-east-1"

        artifacts = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_clusters, region, filters),
                loop.run_in_executor(
                    executor, self._extract_task_definitions, region, filters
                ),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"ECS extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_clusters(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract ECS clusters and their services/tasks"""
        artifacts = []
        client = self.session.client("ecs", region_name=region)

        try:
            # List clusters
            paginator = client.get_paginator("list_clusters")
            for page in paginator.paginate():
                for cluster_arn in page["clusterArns"]:
                    try:
                        # Get cluster details
                        cluster_response = client.describe_clusters(
                            clusters=[cluster_arn],
                            include=[
                                "ATTACHMENTS",
                                "CONFIGURATIONS",
                                "SETTINGS",
                                "STATISTICS",
                                "TAGS",
                            ],
                        )

                        if cluster_response["clusters"]:
                            cluster = cluster_response["clusters"][0]

                            # Extract cluster
                            cluster_artifact = self.transform(
                                {
                                    "resource": cluster,
                                    "resource_type": "cluster",
                                    "region": region,
                                }
                            )
                            if self.validate(cluster_artifact):
                                artifacts.append(cluster_artifact)

                            # Extract services in this cluster
                            services_artifacts = self._extract_services_in_cluster(
                                client, cluster["clusterName"], region
                            )
                            artifacts.extend(services_artifacts)

                            # Extract tasks in this cluster
                            tasks_artifacts = self._extract_tasks_in_cluster(
                                client, cluster["clusterName"], region
                            )
                            artifacts.extend(tasks_artifacts)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract ECS cluster {cluster_arn}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list ECS clusters: {e}")

        return artifacts

    def _extract_services_in_cluster(
        self, client, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Extract services within a cluster"""
        artifacts = []

        try:
            paginator = client.get_paginator("list_services")
            for page in paginator.paginate(cluster=cluster_name):
                if page["serviceArns"]:
                    services_response = client.describe_services(
                        cluster=cluster_name,
                        services=page["serviceArns"],
                        include=["TAGS"],
                    )

                    for service in services_response["services"]:
                        service_artifact = self.transform(
                            {
                                "resource": service,
                                "resource_type": "service",
                                "region": region,
                                "cluster_name": cluster_name,
                            }
                        )
                        if self.validate(service_artifact):
                            artifacts.append(service_artifact)

        except Exception as e:
            logger.error(f"Failed to extract services for cluster {cluster_name}: {e}")

        return artifacts

    def _extract_tasks_in_cluster(
        self, client, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Extract tasks within a cluster"""
        artifacts = []

        try:
            paginator = client.get_paginator("list_tasks")
            for page in paginator.paginate(cluster=cluster_name):
                if page["taskArns"]:
                    tasks_response = client.describe_tasks(
                        cluster=cluster_name, tasks=page["taskArns"], include=["TAGS"]
                    )

                    for task in tasks_response["tasks"]:
                        task_artifact = self.transform(
                            {
                                "resource": task,
                                "resource_type": "task",
                                "region": region,
                                "cluster_name": cluster_name,
                            }
                        )
                        if self.validate(task_artifact):
                            artifacts.append(task_artifact)

        except Exception as e:
            logger.error(f"Failed to extract tasks for cluster {cluster_name}: {e}")

        return artifacts

    def _extract_task_definitions(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract ECS task definitions"""
        artifacts = []
        client = self.session.client("ecs", region_name=region)

        try:
            paginator = client.get_paginator("list_task_definitions")
            for page in paginator.paginate():
                for task_def_arn in page["taskDefinitionArns"]:
                    try:
                        # Get task definition details
                        response = client.describe_task_definition(
                            taskDefinition=task_def_arn, include=["TAGS"]
                        )

                        task_def = response["taskDefinition"]
                        artifact = self.transform(
                            {
                                "resource": task_def,
                                "resource_type": "task-definition",
                                "region": region,
                            }
                        )

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract task definition {task_def_arn}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list task definitions: {e}")

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ECS resource to standardized format"""
        resource = raw_data["resource"]
        resource_type = raw_data["resource_type"]
        region = raw_data.get("region")

        if resource_type == "cluster":
            return {
                "resource_id": resource["clusterName"],
                "resource_type": "ecs:cluster",
                "service": "ecs",
                "region": region,
                "account_id": None,
                "configuration": {
                    "cluster_name": resource["clusterName"],
                    "cluster_arn": resource["clusterArn"],
                    "status": resource["status"],
                    "registered_container_instances_count": resource.get(
                        "registeredContainerInstancesCount", 0
                    ),
                    "running_tasks_count": resource.get("runningTasksCount", 0),
                    "pending_tasks_count": resource.get("pendingTasksCount", 0),
                    "active_services_count": resource.get("activeServicesCount", 0),
                    "statistics": resource.get("statistics", []),
                    "settings": resource.get("settings", []),
                    "configurations": resource.get("configuration", {}),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        elif resource_type == "service":
            return {
                "resource_id": f"{raw_data.get('cluster_name', 'unknown')}/{resource['serviceName']}",
                "resource_type": "ecs:service",
                "service": "ecs",
                "region": region,
                "account_id": None,
                "configuration": {
                    "service_name": resource["serviceName"],
                    "service_arn": resource["serviceArn"],
                    "cluster_arn": resource["clusterArn"],
                    "task_definition": resource.get("taskDefinition"),
                    "desired_count": resource.get("desiredCount", 0),
                    "running_count": resource.get("runningCount", 0),
                    "pending_count": resource.get("pendingCount", 0),
                    "launch_type": resource.get("launchType"),
                    "platform_version": resource.get("platformVersion"),
                    "network_configuration": resource.get("networkConfiguration", {}),
                    "load_balancers": resource.get("loadBalancers", []),
                    "service_registries": resource.get("serviceRegistries", []),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        elif resource_type == "task":
            return {
                "resource_id": resource["taskArn"].split("/")[-1],
                "resource_type": "ecs:task",
                "service": "ecs",
                "region": region,
                "account_id": None,
                "configuration": {
                    "task_arn": resource["taskArn"],
                    "cluster_arn": resource["clusterArn"],
                    "task_definition_arn": resource.get("taskDefinitionArn"),
                    "container_instance_arn": resource.get("containerInstanceArn"),
                    "overrides": resource.get("overrides", {}),
                    "last_status": resource.get("lastStatus"),
                    "desired_status": resource.get("desiredStatus"),
                    "cpu": resource.get("cpu"),
                    "memory": resource.get("memory"),
                    "containers": resource.get("containers", []),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        elif resource_type == "task-definition":
            return {
                "resource_id": f"{resource['family']}:{resource['revision']}",
                "resource_type": "ecs:task-definition",
                "service": "ecs",
                "region": region,
                "account_id": None,
                "configuration": {
                    "family": resource["family"],
                    "revision": resource["revision"],
                    "task_definition_arn": resource["taskDefinitionArn"],
                    "status": resource["status"],
                    "compatibilities": resource.get("compatibilities", []),
                    "requires_compatibilities": resource.get(
                        "requiresCompatibilities", []
                    ),
                    "cpu": resource.get("cpu"),
                    "memory": resource.get("memory"),
                    "container_definitions": resource.get("containerDefinitions", []),
                    "volumes": resource.get("volumes", []),
                    "network_mode": resource.get("networkMode"),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        return {}
