# app/cloud/aws_session.py
"""
AWS session wrapper implementing CloudSession protocol.
"""

import boto3  # type: ignore[import-untyped]
from typing import Any, Optional, List
from app.cloud.base import CloudProvider
import logging

logger = logging.getLogger(__name__)


class AWSSession:
    """Wrapper around boto3.Session implementing CloudSession protocol"""

    def __init__(self, boto_session: boto3.Session):
        """
        Initialize AWS session wrapper.

        Args:
            boto_session: Configured boto3.Session instance
        """
        self._session = boto_session
        self._regions_cache: Optional[List[str]] = None

    @property
    def provider(self) -> CloudProvider:
        """Return AWS as the cloud provider"""
        return CloudProvider.AWS

    def get_client(self, service: str, region: Optional[str] = None) -> Any:
        """
        Get a boto3 client for a specific AWS service.

        Args:
            service: AWS service name (e.g., 'ec2', 's3', 'lambda')
            region: AWS region name (optional)

        Returns:
            boto3 service client
        """
        kwargs = {}
        if region is not None:
            kwargs["region_name"] = region
        return self._session.client(service, **kwargs)  # type: ignore[call-overload]

    def list_regions(self) -> List[str]:
        """
        List all available AWS regions.

        Returns:
            List of AWS region names
        """
        if self._regions_cache is not None:
            return self._regions_cache

        try:
            ec2_client = self._session.client("ec2")
            response = ec2_client.describe_regions(AllRegions=False)
            self._regions_cache = [
                region["RegionName"] for region in response["Regions"]
            ]
            return self._regions_cache
        except Exception as e:
            logger.error(f"Failed to list AWS regions: {e}")
            # Return a default set of regions
            return [
                "us-east-1",
                "us-east-2",
                "us-west-1",
                "us-west-2",
                "eu-west-1",
                "eu-central-1",
                "ap-southeast-1",
                "ap-northeast-1",
            ]

    @property
    def boto_session(self) -> boto3.Session:
        """Get the underlying boto3.Session (for backward compatibility)"""
        return self._session
