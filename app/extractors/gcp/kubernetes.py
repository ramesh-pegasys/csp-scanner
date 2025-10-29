# app/extractors/gcp/kubernetes.py
"""
GCP Kubernetes Engine (GKE) resource extractor.
Extracts GKE clusters and node pools.
"""

from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.cloud.gcp_session import GCPSession
import logging

logger = logging.getLogger(__name__)


class GCPKubernetesExtractor(BaseExtractor):
    """
    Extractor for GCP Kubernetes Engine (GKE) resources.

    Extracts:
    - GKE Clusters
    - Node Pools
    """

    def get_metadata(self) -> ExtractorMetadata:
        """
        Get metadata about the GCP Kubernetes extractor.

        Returns:
            ExtractorMetadata object
        """
        return ExtractorMetadata(
            service_name="kubernetes",
            version="1.0.0",
            description="Extracts GCP Kubernetes Engine clusters and node pools",
            resource_types=["cluster", "node-pool"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract GCP Kubernetes Engine resources.

        Args:
            region: Optional region to filter resources. If None, extracts from all regions.
            filters: Optional filters to apply (not currently used)

        Returns:
            List of raw resource dictionaries from GCP API
        """
        # Cast session to GCPSession for type checking
        gcp_session = cast(GCPSession, self.session)

        # Get list of zones to query (GKE clusters can be zonal or regional)
        zones = []
        if region:
            zones = gcp_session.list_zones(region)
        else:
            # Get all zones across all regions
            regions = gcp_session.list_regions()
            for r in regions:
                zones.extend(gcp_session.list_zones(r))

        logger.info(f"Extracting GCP Kubernetes resources from {len(zones)} zones")

        # Use thread pool for parallel extraction
        artifacts = []
        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_zone_clusters, zone, gcp_session)
                for zone in zones
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"GCP kubernetes extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        logger.info(f"Extracted {len(artifacts)} Kubernetes resources")
        return artifacts

    def _extract_zone_clusters(self, zone: str, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract clusters and node pools from a specific zone"""
        resources = []

        try:
            # Extract GKE clusters
            clusters = self._extract_clusters(zone, gcp_session)
            resources.extend(clusters)

            # Extract node pools for each cluster
            for cluster in clusters:
                cluster_name = cluster.get("name", "")
                if cluster_name:
                    node_pools = self._extract_node_pools(zone, cluster_name, gcp_session)
                    resources.extend(node_pools)

        except Exception as e:
            logger.error(f"Error extracting kubernetes resources for zone {zone}: {e}")

        return resources

    def _extract_clusters(self, zone: str, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract GKE clusters from a specific zone"""
        resources = []
        try:
            from google.cloud import container_v1  # type: ignore[import-untyped]

            client = gcp_session.get_client("container")
            parent = f"projects/{gcp_session.project_id}/locations/{zone}"

            request = container_v1.ListClustersRequest(parent=parent)
            response = client.list_clusters(request=request)

            for cluster in response.clusters:
                cluster_dict = {
                    "resource_type": "gcp:kubernetes:cluster",
                    "name": cluster.name,
                    "self_link": f"https://container.googleapis.com/v1/projects/{gcp_session.project_id}/locations/{zone}/clusters/{cluster.name}",
                    "zone": zone,
                    "description": cluster.description,
                    "initial_cluster_version": cluster.initial_cluster_version,
                    "current_master_version": cluster.current_master_version,
                    "current_node_version": cluster.current_node_version,
                    "status": cluster.status,
                    "status_message": cluster.status_message,
                    "node_ipv4_cidr_size": cluster.node_ipv4_cidr_size,
                    "services_ipv4_cidr": cluster.services_ipv4_cidr,
                    "cluster_ipv4_cidr": cluster.cluster_ipv4_cidr,
                    "addons_config": {
                        "http_load_balancing": {
                            "disabled": cluster.addons_config.http_load_balancing.disabled if cluster.addons_config and cluster.addons_config.http_load_balancing else False,
                        },
                        "horizontal_pod_autoscaling": {
                            "disabled": cluster.addons_config.horizontal_pod_autoscaling.disabled if cluster.addons_config and cluster.addons_config.horizontal_pod_autoscaling else False,
                        },
                        "kubernetes_dashboard": {
                            "disabled": cluster.addons_config.kubernetes_dashboard.disabled if cluster.addons_config and cluster.addons_config.kubernetes_dashboard else False,
                        },
                        "network_policy_config": {
                            "disabled": cluster.addons_config.network_policy_config.disabled if cluster.addons_config and cluster.addons_config.network_policy_config else False,
                        },
                    } if cluster.addons_config else {},
                    "node_pools": [pool.name for pool in cluster.node_pools],
                    "locations": [loc for loc in cluster.locations],
                    "network": cluster.network,
                    "subnetwork": cluster.subnetwork,
                    "cluster_ipv4_cidr": cluster.cluster_ipv4_cidr,
                    "services_ipv4_cidr": cluster.services_ipv4_cidr,
                    "private_cluster_config": {
                        "enable_private_nodes": cluster.private_cluster_config.enable_private_nodes if cluster.private_cluster_config else False,
                        "enable_private_endpoint": cluster.private_cluster_config.enable_private_endpoint if cluster.private_cluster_config else False,
                        "master_ipv4_cidr_block": cluster.private_cluster_config.master_ipv4_cidr_block if cluster.private_cluster_config else "",
                    } if cluster.private_cluster_config else {},
                    "master_auth": {
                        "username": cluster.master_auth.username if cluster.master_auth else "",
                        "client_certificate_config": {
                            "issue_client_certificate": cluster.master_auth.client_certificate_config.issue_client_certificate if cluster.master_auth and cluster.master_auth.client_certificate_config else False,
                        },
                    } if cluster.master_auth else {},
                    "logging_service": cluster.logging_service,
                    "monitoring_service": cluster.monitoring_service,
                    "network_policy": {
                        "provider": cluster.network_policy.provider if cluster.network_policy else "",
                        "enabled": cluster.network_policy.enabled if cluster.network_policy else False,
                    } if cluster.network_policy else {},
                    "ip_allocation_policy": {
                        "use_ip_aliases": cluster.ip_allocation_policy.use_ip_aliases if cluster.ip_allocation_policy else False,
                        "cluster_ipv4_cidr_block": cluster.ip_allocation_policy.cluster_ipv4_cidr_block if cluster.ip_allocation_policy else "",
                        "services_ipv4_cidr_block": cluster.ip_allocation_policy.services_ipv4_cidr_block if cluster.ip_allocation_policy else "",
                    } if cluster.ip_allocation_policy else {},
                    "maintenance_policy": {
                        "window": {
                            "start_time": cluster.maintenance_policy.window.start_time if cluster.maintenance_policy and cluster.maintenance_policy.window else "",
                            "end_time": cluster.maintenance_policy.window.end_time if cluster.maintenance_policy and cluster.maintenance_policy.window else "",
                        },
                    } if cluster.maintenance_policy else {},
                    "autoscaling": {
                        "enable_node_autoprovisioning": cluster.autoscaling.enable_node_autoprovisioning if cluster.autoscaling else False,
                        "resource_limits": [{
                            "resource_type": limit.resource_type,
                            "minimum": limit.minimum,
                            "maximum": limit.maximum,
                        } for limit in cluster.autoscaling.resource_limits] if cluster.autoscaling else [],
                    } if cluster.autoscaling else {},
                }
                resources.append(cluster_dict)

        except Exception as e:
            logger.error(f"Error extracting clusters for zone {zone}: {e}")

        return resources

    def _extract_node_pools(self, zone: str, cluster_name: str, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract node pools for a specific cluster"""
        resources = []
        try:
            from google.cloud import container_v1  # type: ignore[import-untyped]

            client = gcp_session.get_client("container")
            parent = f"projects/{gcp_session.project_id}/locations/{zone}/clusters/{cluster_name}"

            request = container_v1.ListNodePoolsRequest(parent=parent)
            response = client.list_node_pools(request=request)

            for node_pool in response.node_pools:
                node_pool_dict = {
                    "resource_type": "gcp:kubernetes:node-pool",
                    "name": node_pool.name,
                    "self_link": f"https://container.googleapis.com/v1/projects/{gcp_session.project_id}/locations/{zone}/clusters/{cluster_name}/nodePools/{node_pool.name}",
                    "zone": zone,
                    "cluster": cluster_name,
                    "config": {
                        "machine_type": node_pool.config.machine_type if node_pool.config else "",
                        "disk_size_gb": node_pool.config.disk_size_gb if node_pool.config else 0,
                        "oauth_scopes": [scope for scope in node_pool.config.oauth_scopes] if node_pool.config else [],
                        "service_account": node_pool.config.service_account if node_pool.config else "",
                        "metadata": dict(node_pool.config.metadata) if node_pool.config and node_pool.config.metadata else {},
                        "image_type": node_pool.config.image_type if node_pool.config else "",
                        "labels": dict(node_pool.config.labels) if node_pool.config and node_pool.config.labels else {},
                        "tags": [tag for tag in node_pool.config.tags] if node_pool.config and node_pool.config.tags else [],
                        "preemptible": node_pool.config.preemptible if node_pool.config else False,
                        "accelerators": [{
                            "accelerator_count": acc.accelerator_count,
                            "accelerator_type": acc.accelerator_type,
                        } for acc in node_pool.config.accelerators] if node_pool.config and node_pool.config.accelerators else [],
                    } if node_pool.config else {},
                    "initial_node_count": node_pool.initial_node_count,
                    "status": node_pool.status,
                    "status_message": node_pool.status_message,
                    "version": node_pool.version,
                    "instance_group_urls": [url for url in node_pool.instance_group_urls],
                    "autoscaling": {
                        "enabled": node_pool.autoscaling.enabled if node_pool.autoscaling else False,
                        "min_node_count": node_pool.autoscaling.min_node_count if node_pool.autoscaling else 0,
                        "max_node_count": node_pool.autoscaling.max_node_count if node_pool.autoscaling else 0,
                    } if node_pool.autoscaling else {},
                    "management": {
                        "auto_upgrade": node_pool.management.auto_upgrade if node_pool.management else False,
                        "auto_repair": node_pool.management.auto_repair if node_pool.management else False,
                    } if node_pool.management else {},
                }
                resources.append(node_pool_dict)

        except Exception as e:
            logger.error(f"Error extracting node pools for cluster {cluster_name} in zone {zone}: {e}")

        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw GCP Kubernetes data into standardized metadata format.

        Args:
            raw_data: Raw resource dictionary from GCP API

        Returns:
            Standardized artifact dictionary
        """
        try:
            # Extract common fields
            resource_type_suffix = raw_data.get("resource_type", "gcp:kubernetes:cluster")
            resource_id = raw_data.get("self_link", raw_data.get("name", "unknown"))
            zone = raw_data.get("zone", "unknown")

            # Extract region from zone (e.g., us-central1-a -> us-central1)
            region = "-".join(zone.split("-")[:-1]) if zone != "unknown" else "unknown"

            # Get project ID from session
            gcp_session = cast(GCPSession, self.session)
            project_id = gcp_session.project_id

            # Build configuration based on resource type
            config = {}

            if "cluster" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "initial_cluster_version": raw_data.get("initial_cluster_version", ""),
                    "current_master_version": raw_data.get("current_master_version", ""),
                    "current_node_version": raw_data.get("current_node_version", ""),
                    "status": raw_data.get("status", ""),
                    "status_message": raw_data.get("status_message", ""),
                    "node_ipv4_cidr_size": raw_data.get("node_ipv4_cidr_size", ""),
                    "services_ipv4_cidr": raw_data.get("services_ipv4_cidr", ""),
                    "cluster_ipv4_cidr": raw_data.get("cluster_ipv4_cidr", ""),
                    "addons_config": raw_data.get("addons_config", {}),
                    "node_pools": raw_data.get("node_pools", []),
                    "locations": raw_data.get("locations", []),
                    "network": raw_data.get("network", ""),
                    "subnetwork": raw_data.get("subnetwork", ""),
                    "private_cluster_config": raw_data.get("private_cluster_config", {}),
                    "master_auth": raw_data.get("master_auth", {}),
                    "logging_service": raw_data.get("logging_service", ""),
                    "monitoring_service": raw_data.get("monitoring_service", ""),
                    "network_policy": raw_data.get("network_policy", {}),
                    "ip_allocation_policy": raw_data.get("ip_allocation_policy", {}),
                    "maintenance_policy": raw_data.get("maintenance_policy", {}),
                    "autoscaling": raw_data.get("autoscaling", {}),
                }
            elif "node-pool" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "cluster": raw_data.get("cluster", ""),
                    "config": raw_data.get("config", {}),
                    "initial_node_count": raw_data.get("initial_node_count", 0),
                    "status": raw_data.get("status", ""),
                    "status_message": raw_data.get("status_message", ""),
                    "version": raw_data.get("version", ""),
                    "instance_group_urls": raw_data.get("instance_group_urls", []),
                    "autoscaling": raw_data.get("autoscaling", {}),
                    "management": raw_data.get("management", {}),
                }

            return {
                "cloud_provider": "gcp",
                "resource_type": resource_type_suffix,
                "metadata": self.create_metadata_object(
                    resource_id=resource_id,
                    service="kubernetes",
                    region=region,
                    project_id=project_id,
                ),
                "configuration": config,
                "raw": raw_data,
            }

        except Exception as e:
            logger.error(f"Error transforming kubernetes resource: {str(e)}")
            return {}