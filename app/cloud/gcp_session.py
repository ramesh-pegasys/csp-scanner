# app/cloud/gcp_session.py
"""
GCP session wrapper implementing CloudSession protocol.
"""

from typing import Any, Optional, Dict, List
from app.cloud.base import CloudProvider
import logging

logger = logging.getLogger(__name__)


class GCPSession:
    """GCP session wrapper implementing CloudSession protocol"""

    def __init__(
        self,
        project_id: str,
        credentials_path: Optional[str] = None,
        credentials: Optional[Any] = None,
    ):
        """
        Initialize GCP session wrapper.

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON key file
            credentials: Google credentials object (if None, will use credentials_path or application default)
        """
        self.project_id = project_id
        self.credentials_path = credentials_path
        self._clients: Dict[str, Any] = {}
        self._regions_cache: Optional[List[str]] = None

        # Initialize credentials
        if credentials:
            self.credentials = credentials
        elif credentials_path:
            # Load from service account JSON file
            try:
                from google.oauth2 import service_account  # type: ignore[import-untyped]

                self.credentials = (
                    service_account.Credentials.from_service_account_file(
                        credentials_path
                    )
                )
                logger.info("Initialized GCP session with service account file")
            except ImportError:
                logger.error(
                    "google-auth not installed. Please install: pip install google-auth"
                )
                raise
            except Exception as e:
                logger.error(
                    f"Failed to load GCP credentials from {credentials_path}: {e}"
                )
                raise
        else:
            # Use application default credentials (environment variable, gcloud, etc.)
            try:
                from google.auth import default  # type: ignore[import-untyped]

                self.credentials, _ = default()
                logger.info(
                    "Initialized GCP session with application default credentials"
                )
            except ImportError:
                logger.error(
                    "google-auth not installed. Please install: pip install google-auth"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to get default GCP credentials: {e}")
                raise

    @property
    def provider(self) -> CloudProvider:
        """Return GCP as the cloud provider"""
        return CloudProvider.GCP

    def get_client(self, service: str, region: Optional[str] = None) -> Any:
        """
        Get GCP client for a service.

        Args:
            service: Service name (e.g., 'compute', 'storage', 'container')
            region: GCP region/zone (optional, not all services need it)

        Returns:
            GCP service client instance

        Service mapping:
            - 'compute' -> Compute Engine client
            - 'storage' -> Cloud Storage client
            - 'container' -> GKE client
            - 'asset' -> Cloud Asset Inventory client (for unified resource discovery)
            - 'functions' -> Cloud Functions client
            - 'iam' -> IAM client
            - 'compute_firewalls' -> Compute Engine firewalls
            - 'compute_networks' -> Compute Engine networks
            - 'compute_subnetworks' -> Compute Engine subnetworks
            - 'compute_backend_services' -> Load balancer backend services
            - 'compute_url_maps' -> Load balancer URL maps
            - 'compute_target_proxies' -> Load balancer target proxies
            - 'compute_forwarding_rules' -> Load balancer forwarding rules
        """
        cache_key = f"{service}:{region}" if region else service

        if cache_key not in self._clients:
            self._clients[cache_key] = self._create_client(service, region)

        return self._clients[cache_key]

    def _create_client(self, service: str, region: Optional[str] = None) -> Any:
        """Create appropriate GCP client"""
        try:
            if service == "compute":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.InstancesClient(credentials=self.credentials)

            elif service == "compute_zones":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.ZonesClient(credentials=self.credentials)

            elif service == "compute_regions":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.RegionsClient(credentials=self.credentials)

            elif service == "compute_firewalls":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.FirewallsClient(credentials=self.credentials)

            elif service == "compute_networks":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.NetworksClient(credentials=self.credentials)

            elif service == "compute_subnetworks":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.SubnetworksClient(credentials=self.credentials)

            elif service == "compute_backend_services":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.BackendServicesClient(credentials=self.credentials)

            elif service == "compute_url_maps":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.UrlMapsClient(credentials=self.credentials)

            elif service == "compute_target_proxies":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.TargetHttpProxiesClient(credentials=self.credentials)

            elif service == "compute_forwarding_rules":
                from google.cloud import compute_v1  # type: ignore[import-untyped]

                return compute_v1.ForwardingRulesClient(credentials=self.credentials)

            elif service == "storage":
                from google.cloud import storage  # type: ignore[import-untyped]

                return storage.Client(
                    project=self.project_id, credentials=self.credentials
                )

            elif service == "container":
                from google.cloud import container_v1  # type: ignore[import-untyped]

                return container_v1.ClusterManagerClient(credentials=self.credentials)

            elif service == "asset":
                from google.cloud import asset_v1  # type: ignore[import-untyped]

                return asset_v1.AssetServiceClient(credentials=self.credentials)

            elif service == "functions":
                from google.cloud import functions_v1  # type: ignore[import-untyped]

                return functions_v1.CloudFunctionsServiceClient(
                    credentials=self.credentials
                )

            elif service == "iam":
                from google.cloud import iam_v1  # type: ignore[import-untyped]

                return iam_v1.IAMClient(credentials=self.credentials)

            elif service == "resource_manager":
                from google.cloud import resourcemanager_v3  # type: ignore[import-untyped]

                return resourcemanager_v3.ProjectsClient(credentials=self.credentials)

            else:
                raise ValueError(f"Unknown GCP service: {service}")

        except ImportError as e:
            logger.error(f"Failed to import GCP client library for {service}: {e}")
            logger.error(f"Please install: pip install google-cloud-{service}")
            raise

    def list_regions(self) -> List[str]:
        """
        List available GCP regions.

        Returns:
            List of GCP region names
        """
        if self._regions_cache is not None:
            return self._regions_cache

        try:
            from google.cloud import compute_v1  # type: ignore[import-untyped]

            regions_client = compute_v1.RegionsClient(credentials=self.credentials)
            request = compute_v1.ListRegionsRequest(project=self.project_id)

            regions = []
            for region in regions_client.list(request=request):
                regions.append(region.name)

            self._regions_cache = regions
            return self._regions_cache

        except Exception as e:
            logger.error(f"Failed to list GCP regions: {e}")
            # Return a default set of regions
            return [
                "us-central1",
                "us-east1",
                "us-west1",
                "europe-west1",
                "europe-west2",
                "asia-east1",
                "asia-southeast1",
            ]

    def list_zones(self, region: Optional[str] = None) -> List[str]:
        """
        List available GCP zones.

        Args:
            region: Filter zones by region (optional)

        Returns:
            List of GCP zone names
        """
        try:
            from google.cloud import compute_v1  # type: ignore[import-untyped]

            zones_client = compute_v1.ZonesClient(credentials=self.credentials)
            request = compute_v1.ListZonesRequest(project=self.project_id)

            zones = []
            for zone in zones_client.list(request=request):
                if region and not zone.name.startswith(region):
                    continue
                zones.append(zone.name)

            return zones

        except Exception as e:
            logger.error(f"Failed to list GCP zones: {e}")
            # Return a default set of zones
            default_zones = [
                "us-central1-a",
                "us-central1-b",
                "us-central1-c",
                "us-east1-b",
                "us-east1-c",
                "us-east1-d",
                "us-west1-a",
                "us-west1-b",
                "us-west1-c",
                "europe-west1-b",
                "europe-west1-c",
                "europe-west1-d",
                "asia-east1-a",
                "asia-east1-b",
                "asia-east1-c",
            ]

            if region:
                return [z for z in default_zones if z.startswith(region)]
            return default_zones

    def search_resources(
        self, asset_types: Optional[List[str]] = None, scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for GCP resources using Cloud Asset Inventory.

        Args:
            asset_types: List of asset types to search for (e.g., ['sqladmin.googleapis.com/Instance'])
            scope: Scope for the search (project, folder, or organization). Defaults to current project.

        Returns:
            List of resource dictionaries with metadata
        """
        try:
            from google.cloud import asset_v1  # type: ignore[import-untyped]

            asset_client = self.get_client("asset")

            if scope is None:
                scope = f"projects/{self.project_id}"

            request = asset_v1.SearchAllResourcesRequest(
                scope=scope,
                asset_types=asset_types,
            )

            resources = []
            for resource in asset_client.search_all_resources(request=request):
                resources.append(
                    {
                        "name": resource.name,
                        "asset_type": resource.asset_type,
                        "location": resource.location,
                        "project": resource.project,
                        "display_name": resource.display_name,
                        "description": resource.description,
                        "labels": dict(resource.labels) if resource.labels else {},
                        "create_time": resource.create_time,
                        "update_time": resource.update_time,
                    }
                )

            return resources

        except Exception as e:
            logger.error(f"Failed to search GCP resources: {e}")
            return []
