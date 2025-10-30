# app/extractors/gcp/networking.py
"""
GCP Networking resource extractor.
Extracts VPC networks, subnets, firewalls, and load balancers.
"""

from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.cloud.gcp_session import GCPSession
import logging

logger = logging.getLogger(__name__)


class GCPNetworkingExtractor(BaseExtractor):
    """
    Extractor for GCP Networking resources.

    Extracts:
    - VPC Networks
    - Subnets
    - Firewall rules
    - Load balancers (backend services, URL maps, target proxies, forwarding rules)
    """

    def get_metadata(self) -> ExtractorMetadata:
        """
        Get metadata about the GCP Networking extractor.

        Returns:
            ExtractorMetadata object
        """
        return ExtractorMetadata(
            service_name="networking",
            version="1.0.0",
            description="Extracts GCP VPC networks, subnets, firewalls, and load balancers",
            resource_types=[
                "network",
                "subnetwork",
                "firewall",
                "backend-service",
                "url-map",
                "target-proxy",
                "forwarding-rule",
            ],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract GCP Networking resources.

        Args:
            region: Optional region to filter resources. If None, extracts global and regional resources.

        # Cast session to GCPSession for type checking
        gcp_session = cast(GCPSession, self.session)

        # Check if Networking (Compute) API is enabled
        from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP
        project_id = gcp_session.project_id
        api_service = API_SERVICE_MAP["networking"]
        if not is_gcp_api_enabled(project_id, api_service, gcp_session.credentials):
            logger.warning(
                f"GCP Networking (Compute) API is not enabled for project {project_id}. "
                "Skipping extraction."
            )
            return []

        filters: Optional filters to apply (not currently used)

        Returns:
            List of raw resource dictionaries from GCP API
        """
        # Cast session to GCPSession for type checking
        gcp_session = cast(GCPSession, self.session)

        logger.info("Extracting GCP Networking resources")

        # Use thread pool for parallel extraction
        artifacts = []
        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()

            # Global resources (networks, firewalls, global load balancers)
            global_tasks = [
                loop.run_in_executor(executor, self._extract_networks, gcp_session),
                loop.run_in_executor(executor, self._extract_firewalls, gcp_session),
                loop.run_in_executor(
                    executor, self._extract_global_backend_services, gcp_session
                ),
                loop.run_in_executor(
                    executor, self._extract_global_url_maps, gcp_session
                ),
                loop.run_in_executor(
                    executor, self._extract_global_target_proxies, gcp_session
                ),
            ]

            # Regional resources
            regions_to_query = [region] if region else gcp_session.list_regions()
            regional_tasks = []
            for r in regions_to_query:
                regional_tasks.extend(
                    [
                        loop.run_in_executor(
                            executor, self._extract_subnetworks, r, gcp_session
                        ),
                        loop.run_in_executor(
                            executor,
                            self._extract_regional_backend_services,
                            r,
                            gcp_session,
                        ),
                        loop.run_in_executor(
                            executor, self._extract_forwarding_rules, r, gcp_session
                        ),
                    ]
                )

            all_tasks = global_tasks + regional_tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"GCP networking extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        logger.info(f"Extracted {len(artifacts)} Networking resources")
        return artifacts

    def _extract_networks(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract VPC networks (global)"""
        resources = []
        try:
            client = gcp_session.get_client("compute_networks")
            request = client.list(project=gcp_session.project_id)

            for network in request:
                network_dict = {
                    "resource_type": "gcp:networking:network",
                    "name": network.name,
                    "self_link": network.self_link,
                    "description": network.description,
                    "auto_create_subnetworks": network.auto_create_subnetworks,
                    "routing_config": (
                        {
                            "routing_mode": (
                                network.routing_config.routing_mode
                                if network.routing_config
                                else None
                            ),
                        }
                        if network.routing_config
                        else {}
                    ),
                    "subnetworks": [sub for sub in network.subnetworks],
                    "peerings": [
                        {
                            "name": peering.name,
                            "network": peering.network,
                            "state": peering.state,
                        }
                        for peering in network.peerings
                    ],
                }
                resources.append(network_dict)

        except Exception as e:
            logger.error(f"Error extracting networks: {e}")

        return resources

    def _extract_subnetworks(
        self, region: str, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract subnets for a specific region"""
        resources = []
        try:
            client = gcp_session.get_client("compute_subnetworks")
            request = client.list(project=gcp_session.project_id, region=region)

            for subnetwork in request:
                subnetwork_dict = {
                    "resource_type": "gcp:networking:subnetwork",
                    "name": subnetwork.name,
                    "self_link": subnetwork.self_link,
                    "region": subnetwork.region,
                    "network": subnetwork.network,
                    "ip_cidr_range": subnetwork.ip_cidr_range,
                    "description": subnetwork.description,
                    "private_ip_google_access": subnetwork.private_ip_google_access,
                    "secondary_ip_ranges": [
                        {
                            "range_name": range_.range_name,
                            "ip_cidr_range": range_.ip_cidr_range,
                        }
                        for range_ in subnetwork.secondary_ip_ranges
                    ],
                    "purpose": subnetwork.purpose,
                }
                resources.append(subnetwork_dict)

        except Exception as e:
            logger.error(f"Error extracting subnetworks for region {region}: {e}")

        return resources

    def _extract_firewalls(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract firewall rules (global)"""
        resources = []
        try:
            client = gcp_session.get_client("compute_firewalls")
            request = client.list(project=gcp_session.project_id)

            for firewall in request:
                firewall_dict = {
                    "resource_type": "gcp:networking:firewall",
                    "name": firewall.name,
                    "self_link": firewall.self_link,
                    "description": firewall.description,
                    "network": firewall.network,
                    "priority": firewall.priority,
                    "direction": firewall.direction,
                    "source_ranges": [range_ for range_ in firewall.source_ranges],
                    "destination_ranges": [
                        range_ for range_ in firewall.destination_ranges
                    ],
                    "source_tags": [tag for tag in firewall.source_tags],
                    "target_tags": [tag for tag in firewall.target_tags],
                    "source_service_accounts": [
                        sa for sa in firewall.source_service_accounts
                    ],
                    "target_service_accounts": [
                        sa for sa in firewall.target_service_accounts
                    ],
                    "allowed": [
                        {
                            "ip_protocol": getattr(rule, "ip_protocol", ""),
                            "ports": (
                                [port for port in getattr(rule, "ports", [])]
                                if hasattr(rule, "ports")
                                else []
                            ),
                        }
                        for rule in getattr(firewall, "allowed", [])
                    ],
                    "denied": [
                        {
                            "ip_protocol": getattr(rule, "ip_protocol", ""),
                            "ports": (
                                [port for port in getattr(rule, "ports", [])]
                                if hasattr(rule, "ports")
                                else []
                            ),
                        }
                        for rule in getattr(firewall, "denied", [])
                    ],
                    "disabled": firewall.disabled,
                }
                resources.append(firewall_dict)

        except Exception as e:
            logger.error(f"Error extracting firewalls: {e}")

        return resources

    def _extract_global_backend_services(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract global backend services"""
        resources = []
        try:
            client = gcp_session.get_client("compute_backend_services")
            request = client.list(project=gcp_session.project_id)

            for backend_service in request:
                if backend_service.region:  # Skip regional ones
                    continue

                backend_dict = {
                    "resource_type": "gcp:networking:backend-service",
                    "name": backend_service.name,
                    "self_link": backend_service.self_link,
                    "description": backend_service.description,
                    "protocol": backend_service.protocol,
                    "port": backend_service.port,
                    "port_name": backend_service.port_name,
                    "timeout_sec": backend_service.timeout_sec,
                    "backends": [
                        {
                            "group": backend.group,
                            "balancing_mode": backend.balancing_mode,
                            "max_rate": backend.max_rate,
                            "max_rate_per_instance": backend.max_rate_per_instance,
                            "max_connections": backend.max_connections,
                            "max_connections_per_instance": backend.max_connections_per_instance,
                        }
                        for backend in backend_service.backends
                    ],
                    "health_checks": [hc for hc in backend_service.health_checks],
                    "session_affinity": backend_service.session_affinity,
                    "affinity_cookie_ttl_sec": backend_service.affinity_cookie_ttl_sec,
                    "load_balancing_scheme": backend_service.load_balancing_scheme,
                }
                resources.append(backend_dict)

        except Exception as e:
            logger.error(f"Error extracting global backend services: {e}")

        return resources

    def _extract_regional_backend_services(
        self, region: str, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract regional backend services"""
        resources = []
        try:
            client = gcp_session.get_client("compute_backend_services")
            request = client.list(project=gcp_session.project_id)

            for backend_service in request:
                if not backend_service.region or region not in backend_service.region:
                    continue

                backend_dict = {
                    "resource_type": "gcp:networking:backend-service",
                    "name": backend_service.name,
                    "self_link": backend_service.self_link,
                    "region": backend_service.region,
                    "description": backend_service.description,
                    "protocol": backend_service.protocol,
                    "port": backend_service.port,
                    "port_name": backend_service.port_name,
                    "timeout_sec": backend_service.timeout_sec,
                    "backends": [
                        {
                            "group": backend.group,
                            "balancing_mode": backend.balancing_mode,
                            "max_rate": backend.max_rate,
                            "max_rate_per_instance": backend.max_rate_per_instance,
                            "max_connections": backend.max_connections,
                            "max_connections_per_instance": backend.max_connections_per_instance,
                        }
                        for backend in backend_service.backends
                    ],
                    "health_checks": [hc for hc in backend_service.health_checks],
                    "session_affinity": backend_service.session_affinity,
                    "affinity_cookie_ttl_sec": backend_service.affinity_cookie_ttl_sec,
                    "load_balancing_scheme": backend_service.load_balancing_scheme,
                }
                resources.append(backend_dict)

        except Exception as e:
            logger.error(
                f"Error extracting regional backend services for region {region}: {e}"
            )

        return resources

    def _extract_global_url_maps(self, gcp_session: GCPSession) -> List[Dict[str, Any]]:
        """Extract global URL maps"""
        resources = []
        try:
            client = gcp_session.get_client("compute_url_maps")
            request = client.list(project=gcp_session.project_id)

            for url_map in request:
                if url_map.region:  # Skip regional ones
                    continue

                url_map_dict = {
                    "resource_type": "gcp:networking:url-map",
                    "name": url_map.name,
                    "self_link": url_map.self_link,
                    "description": url_map.description,
                    "default_service": url_map.default_service,
                    "host_rules": [
                        {
                            "hosts": [host for host in rule.hosts],
                            "path_matcher": rule.path_matcher,
                        }
                        for rule in url_map.host_rules
                    ],
                    "path_matchers": [
                        {
                            "name": matcher.name,
                            "default_service": matcher.default_service,
                            "path_rules": [
                                {
                                    "paths": [path for path in rule.paths],
                                    "service": rule.service,
                                }
                                for rule in matcher.path_rules
                            ],
                        }
                        for matcher in url_map.path_matchers
                    ],
                }
                resources.append(url_map_dict)

        except Exception as e:
            logger.error(f"Error extracting global URL maps: {e}")

        return resources

    def _extract_global_target_proxies(
        self, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract global target proxies"""
        resources = []
        try:
            client = gcp_session.get_client("compute_target_proxies")
            request = client.list(project=gcp_session.project_id)

            for proxy in request:
                if proxy.region:  # Skip regional ones
                    continue

                proxy_dict = {
                    "resource_type": "gcp:networking:target-proxy",
                    "name": proxy.name,
                    "self_link": proxy.self_link,
                    "description": proxy.description,
                    "url_map": proxy.url_map,
                }
                resources.append(proxy_dict)

        except Exception as e:
            logger.error(f"Error extracting global target proxies: {e}")

        return resources

    def _extract_forwarding_rules(
        self, region: str, gcp_session: GCPSession
    ) -> List[Dict[str, Any]]:
        """Extract forwarding rules for a specific region"""
        resources = []
        try:
            client = gcp_session.get_client("compute_forwarding_rules")
            request = client.list(project=gcp_session.project_id, region=region)

            for rule in request:
                rule_dict = {
                    "resource_type": "gcp:networking:forwarding-rule",
                    "name": rule.name,
                    "self_link": rule.self_link,
                    "region": rule.region,
                    "description": rule.description,
                    "ip_address": rule.ip_address,
                    "ip_protocol": rule.ip_protocol,
                    "port_range": rule.port_range,
                    "target": rule.target,
                    "load_balancing_scheme": rule.load_balancing_scheme,
                    "network": rule.network,
                    "subnetwork": rule.subnetwork,
                }
                resources.append(rule_dict)

        except Exception as e:
            logger.error(f"Error extracting forwarding rules for region {region}: {e}")

        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw GCP Networking data into standardized metadata format.

        Args:
            raw_data: Raw resource dictionary from GCP API

        Returns:
            Standardized artifact dictionary
        """
        try:
            # Extract common fields
            resource_type_suffix = raw_data.get(
                "resource_type", "gcp:networking:network"
            )
            resource_id = raw_data.get("self_link", raw_data.get("name", "unknown"))
            region = raw_data.get("region", "global")

            # Get project ID from session
            gcp_session = cast(GCPSession, self.session)
            project_id = gcp_session.project_id

            # Build configuration based on resource type
            config = {}

            if "network" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "auto_create_subnetworks": raw_data.get(
                        "auto_create_subnetworks", False
                    ),
                    "routing_config": raw_data.get("routing_config", {}),
                    "subnetworks": raw_data.get("subnetworks", []),
                    "peerings": raw_data.get("peerings", []),
                }
            elif "subnetwork" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "network": raw_data.get("network", ""),
                    "ip_cidr_range": raw_data.get("ip_cidr_range", ""),
                    "private_ip_google_access": raw_data.get(
                        "private_ip_google_access", False
                    ),
                    "secondary_ip_ranges": raw_data.get("secondary_ip_ranges", []),
                    "purpose": raw_data.get("purpose", ""),
                }
            elif "firewall" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "network": raw_data.get("network", ""),
                    "priority": raw_data.get("priority", 1000),
                    "direction": raw_data.get("direction", ""),
                    "source_ranges": raw_data.get("source_ranges", []),
                    "destination_ranges": raw_data.get("destination_ranges", []),
                    "source_tags": raw_data.get("source_tags", []),
                    "target_tags": raw_data.get("target_tags", []),
                    "source_service_accounts": raw_data.get(
                        "source_service_accounts", []
                    ),
                    "target_service_accounts": raw_data.get(
                        "target_service_accounts", []
                    ),
                    "allowed": raw_data.get("allowed", []),
                    "denied": raw_data.get("denied", []),
                    "disabled": raw_data.get("disabled", False),
                }
            elif "backend-service" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "protocol": raw_data.get("protocol", ""),
                    "port": raw_data.get("port", ""),
                    "port_name": raw_data.get("port_name", ""),
                    "timeout_sec": raw_data.get("timeout_sec", ""),
                    "backends": raw_data.get("backends", []),
                    "health_checks": raw_data.get("health_checks", []),
                    "session_affinity": raw_data.get("session_affinity", ""),
                    "affinity_cookie_ttl_sec": raw_data.get(
                        "affinity_cookie_ttl_sec", ""
                    ),
                    "load_balancing_scheme": raw_data.get("load_balancing_scheme", ""),
                }
            elif "url-map" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "default_service": raw_data.get("default_service", ""),
                    "host_rules": raw_data.get("host_rules", []),
                    "path_matchers": raw_data.get("path_matchers", []),
                }
            elif "target-proxy" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "url_map": raw_data.get("url_map", ""),
                }
            elif "forwarding-rule" in resource_type_suffix:
                config = {
                    "name": raw_data.get("name", ""),
                    "description": raw_data.get("description", ""),
                    "ip_address": raw_data.get("ip_address", ""),
                    "ip_protocol": raw_data.get("ip_protocol", ""),
                    "port_range": raw_data.get("port_range", ""),
                    "target": raw_data.get("target", ""),
                    "load_balancing_scheme": raw_data.get("load_balancing_scheme", ""),
                    "network": raw_data.get("network", ""),
                    "subnetwork": raw_data.get("subnetwork", ""),
                }

            return {
                "cloud_provider": "gcp",
                "resource_type": resource_type_suffix,
                "metadata": self.create_metadata_object(
                    resource_id=resource_id,
                    service="networking",
                    region=region,
                    project_id=project_id,
                ),
                "configuration": config,
                "raw": raw_data,
            }

        except Exception as e:
            logger.error(f"Error transforming networking resource: {str(e)}")
            return {}
