# app/extractors/eks.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class EKSExtractor(BaseExtractor):
    """Extractor for AWS EKS (Elastic Kubernetes Service) resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="eks",
            version="1.0.0",
            description="Extracts EKS clusters, node groups, and Fargate profiles",
            resource_types=["cluster", "nodegroup", "fargate-profile"],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract EKS resources"""
        # Use us-east-1 as default region if none provided
        region = region or "us-east-1"

        artifacts = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_clusters, region, filters)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"EKS extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_clusters(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract EKS clusters and their associated resources"""
        artifacts = []
        client = self._get_client("eks", region_name=region)

        try:
            paginator = client.get_paginator("list_clusters")
            for page in paginator.paginate():
                for cluster_name in page["clusters"]:
                    try:
                        # Get cluster details
                        cluster_response = client.describe_cluster(name=cluster_name)
                        cluster = cluster_response["cluster"]

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

                        # Extract node groups for this cluster
                        nodegroups_artifacts = self._extract_nodegroups(
                            client, cluster_name, region
                        )
                        artifacts.extend(nodegroups_artifacts)

                        # Extract Fargate profiles for this cluster
                        fargate_artifacts = self._extract_fargate_profiles(
                            client, cluster_name, region
                        )
                        artifacts.extend(fargate_artifacts)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract EKS cluster {cluster_name}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list EKS clusters: {e}")

        return artifacts

    def _extract_nodegroups(
        self, client, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Extract node groups for a cluster"""
        artifacts = []

        try:
            paginator = client.get_paginator("list_nodegroups")
            for page in paginator.paginate(clusterName=cluster_name):
                for nodegroup_name in page["nodegroups"]:
                    try:
                        # Get node group details
                        response = client.describe_nodegroup(
                            clusterName=cluster_name, nodegroupName=nodegroup_name
                        )

                        nodegroup = response["nodegroup"]
                        artifact = self.transform(
                            {
                                "resource": nodegroup,
                                "resource_type": "nodegroup",
                                "region": region,
                                "cluster_name": cluster_name,
                            }
                        )

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract nodegroup {nodegroup_name} in cluster {cluster_name}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list nodegroups for cluster {cluster_name}: {e}")

        return artifacts

    def _extract_fargate_profiles(
        self, client, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Extract Fargate profiles for a cluster"""
        artifacts = []

        try:
            paginator = client.get_paginator("list_fargate_profiles")
            for page in paginator.paginate(clusterName=cluster_name):
                for profile_name in page["fargateProfileNames"]:
                    try:
                        # Get Fargate profile details
                        response = client.describe_fargate_profile(
                            clusterName=cluster_name, fargateProfileName=profile_name
                        )

                        profile = response["fargateProfile"]
                        artifact = self.transform(
                            {
                                "resource": profile,
                                "resource_type": "fargate-profile",
                                "region": region,
                                "cluster_name": cluster_name,
                            }
                        )

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract Fargate profile {profile_name} in cluster {cluster_name}: {e}"
                        )

        except Exception as e:
            logger.error(
                f"Failed to list Fargate profiles for cluster {cluster_name}: {e}"
            )

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform EKS resource to standardized format"""
        resource = raw_data["resource"]
        resource_type = raw_data["resource_type"]
        region = raw_data.get("region")

        if resource_type == "cluster":
            return {
                "resource_id": resource["name"],
                "resource_type": "eks:cluster",
                "service": "eks",
                "region": region,
                "account_id": None,
                "configuration": {
                    "name": resource["name"],
                    "arn": resource["arn"],
                    "created_at": resource.get("createdAt"),
                    "version": resource.get("version"),
                    "endpoint": resource.get("endpoint"),
                    "role_arn": resource.get("roleArn"),
                    "resources_vpc_config": resource.get("resourcesVpcConfig", {}),
                    "kubernetes_network_config": resource.get(
                        "kubernetesNetworkConfig", {}
                    ),
                    "logging": resource.get("logging", {}),
                    "identity": resource.get("identity", {}),
                    "status": resource.get("status"),
                    "platform_version": resource.get("platformVersion"),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        elif resource_type == "nodegroup":
            return {
                "resource_id": f"{raw_data.get('cluster_name', 'unknown')}/{resource['nodegroupName']}",
                "resource_type": "eks:nodegroup",
                "service": "eks",
                "region": region,
                "account_id": None,
                "configuration": {
                    "nodegroup_name": resource["nodegroupName"],
                    "cluster_name": resource.get("clusterName"),
                    "nodegroup_arn": resource.get("nodegroupArn"),
                    "status": resource.get("status"),
                    "created_at": resource.get("createdAt"),
                    "modified_at": resource.get("modifiedAt"),
                    "instance_types": resource.get("instanceTypes", []),
                    "ami_type": resource.get("amiType"),
                    "node_role": resource.get("nodeRole"),
                    "subnets": resource.get("subnets", []),
                    "remote_access": resource.get("remoteAccess", {}),
                    "scaling_config": resource.get("scalingConfig", {}),
                    "labels": resource.get("labels", {}),
                    "taints": resource.get("taints", []),
                    "resources": resource.get("resources", {}),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        elif resource_type == "fargate-profile":
            return {
                "resource_id": f"{raw_data.get('cluster_name', 'unknown')}/{resource['fargateProfileName']}",
                "resource_type": "eks:fargate-profile",
                "service": "eks",
                "region": region,
                "account_id": None,
                "configuration": {
                    "fargate_profile_name": resource["fargateProfileName"],
                    "cluster_name": resource.get("clusterName"),
                    "fargate_profile_arn": resource.get("fargateProfileArn"),
                    "created_at": resource.get("createdAt"),
                    "pod_execution_role_arn": resource.get("podExecutionRoleArn"),
                    "subnets": resource.get("subnets", []),
                    "selectors": resource.get("selectors", []),
                    "status": resource.get("status"),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        return {}
