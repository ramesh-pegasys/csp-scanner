# app/extractors/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Literal, Union, TYPE_CHECKING
from dataclasses import dataclass
import boto3  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from app.cloud.base import CloudSession

# Cloud provider type (kept for backward compatibility)
CloudProvider = Literal["aws", "azure", "gcp"]


@dataclass
class ExtractorMetadata:
    """Metadata about the extractor"""

    service_name: str
    version: str
    description: str
    resource_types: List[str]
    cloud_provider: CloudProvider = "aws"
    supports_regions: bool = True
    requires_pagination: bool = True


class BaseExtractor(ABC):
    """Base class for all cloud resource extractors"""

    def __init__(
        self, session: Union[boto3.Session, "CloudSession"], config: Dict[str, Any]
    ):
        # Support both old boto3.Session and new CloudSession for backward compatibility
        self.session: "CloudSession"
        if isinstance(session, boto3.Session):
            # Wrap boto3 session for backward compatibility
            from app.cloud.aws_session import AWSSession

            self.session = AWSSession(session)
        else:
            self.session = session

        self.config = config
        self.metadata = self.get_metadata()
        self.cloud_provider: CloudProvider = getattr(
            self.metadata, "cloud_provider", "aws"
        )

    def _get_client(self, service: str, region: Optional[str] = None) -> Any:
        """
        Get a cloud service client (backward compatible helper).

        This method provides backward compatibility for extractors that were
        written before the CloudSession abstraction.

        Args:
            service: Service name (e.g., 'ec2', 's3', 'compute')
            region: Region/location name (optional)

        Returns:
            Service client instance
        """
        return self.session.get_client(service, region)

    @abstractmethod
    def get_metadata(self) -> ExtractorMetadata:
        """Return metadata about this extractor"""
        pass

    @abstractmethod
    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract resources from AWS

        Args:
            region: AWS region (None for global services)
            filters: Optional filters to apply

        Returns:
            List of resource configurations as dictionaries
        """
        pass

    @abstractmethod
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw AWS API response to standardized format

        Args:
            raw_data: Raw response from AWS API

        Returns:
            Standardized artifact dictionary
        """
        pass

    def validate(self, artifact: Dict[str, Any]) -> bool:
        """
        Validate artifact before sending to scanner

        Args:
            artifact: Transformed artifact

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "cloud_provider",
            "resource_type",
            "metadata",
            "configuration",
        ]
        if not all(field in artifact for field in required_fields):
            return False

        # Validate metadata structure
        metadata = artifact.get("metadata", {})
        required_metadata_fields = ["resource_id"]
        return all(field in metadata for field in required_metadata_fields)

    def create_metadata_object(
        self,
        resource_id: str,
        service: Optional[str] = None,
        region: Optional[str] = None,
        account_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        project_id: Optional[str] = None,
        resource_group: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a cloud-agnostic metadata object

        Args:
            resource_id: Unique identifier for the resource
            service: Service name (e.g., 'ec2', 'compute', etc.)
            region: AWS region, Azure location, or GCP zone/region
            account_id: AWS account ID
            subscription_id: Azure subscription ID
            project_id: GCP project ID
            resource_group: Azure resource group
            labels: Extensible key-value pairs for labels
            tags: Resource tags (will be merged into labels)

        Returns:
            Metadata dictionary
        """
        metadata: Dict[str, Any] = {
            "resource_id": resource_id,
        }

        # Add cloud-specific fields
        if self.cloud_provider == "aws":
            if service:
                metadata["service"] = service
            if region:
                metadata["region"] = region
            if account_id:
                metadata["account_id"] = account_id
        elif self.cloud_provider == "azure":
            if service:
                metadata["service"] = service
            if region:
                metadata["location"] = region
            if subscription_id:
                metadata["subscription_id"] = subscription_id
            if resource_group:
                metadata["resource_group"] = resource_group
        elif self.cloud_provider == "gcp":
            if service:
                metadata["service"] = service
            if region:
                metadata["region"] = region
            if project_id:
                metadata["project_id"] = project_id

        # Merge tags and labels
        merged_labels = {}
        if tags:
            merged_labels.update(tags)
        if labels:
            merged_labels.update(labels)

        if merged_labels:
            metadata["labels"] = merged_labels
        else:
            metadata["labels"] = {}

        return metadata
