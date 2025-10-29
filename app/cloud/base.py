# app/cloud/base.py
"""
Base classes and protocols for cloud session abstraction.
"""

from typing import Protocol, Any, Optional, List
from enum import Enum


class CloudProvider(str, Enum):
    """Supported cloud providers"""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class CloudSession(Protocol):
    """Protocol for cloud provider sessions"""

    @property
    def provider(self) -> CloudProvider:
        """Return the cloud provider type"""
        ...

    def get_client(self, service: str, region: Optional[str] = None) -> Any:
        """
        Get a client for a specific service.

        Args:
            service: Service name (e.g., 'ec2', 'compute', 's3', 'storage')
            region: Region/location for the client (optional)

        Returns:
            Service client instance
        """
        ...

    def list_regions(self) -> List[str]:
        """
        List available regions/locations for this cloud provider.

        Returns:
            List of region/location names
        """
        ...
