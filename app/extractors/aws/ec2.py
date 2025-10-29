# app/extractors/ec2.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class EC2Extractor(BaseExtractor):
    """Extractor for EC2 instances and related resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="ec2",
            version="1.0.0",
            description="Extracts EC2 instances, security groups, and network interfaces",
            resource_types=["instance", "security-group", "network-interface"],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract EC2 resources"""
        regions = [region] if region else self._get_all_regions()

        artifacts = []

        # Use ThreadPoolExecutor for I/O-bound boto3 calls
        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_region, reg, filters)
                for reg in regions
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and handle exceptions
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_region(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract EC2 resources from a specific region"""
        ec2_client = self._get_client("ec2", region)
        artifacts = []

        # Extract instances
        try:
            instances = self._extract_instances(ec2_client, region, filters)
            artifacts.extend(instances)
        except Exception as e:
            logger.error(f"Failed to extract instances in {region}: {e}")

        # Extract security groups
        try:
            security_groups = self._extract_security_groups(ec2_client, region, filters)
            artifacts.extend(security_groups)
        except Exception as e:
            logger.error(f"Failed to extract security groups in {region}: {e}")

        return artifacts

    def _extract_instances(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract EC2 instances"""
        artifacts = []

        paginator = client.get_paginator("describe_instances")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    artifact = self.transform(
                        {
                            "resource": instance,
                            "region": region,
                            "resource_type": "instance",
                        }
                    )
                    if self.validate(artifact):
                        artifacts.append(artifact)

        return artifacts

    def _extract_security_groups(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract security groups"""
        artifacts = []

        paginator = client.get_paginator("describe_security_groups")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for sg in page["SecurityGroups"]:
                artifact = self.transform(
                    {
                        "resource": sg,
                        "region": region,
                        "resource_type": "security-group",
                    }
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _get_all_regions(self) -> List[str]:
        """Get all enabled EC2 regions"""
        ec2_client = self._get_client("ec2")
        response = ec2_client.describe_regions(AllRegions=False)
        return [region["RegionName"] for region in response["Regions"]]

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform EC2 resource to standardized format"""
        resource = raw_data["resource"]
        region = raw_data["region"]
        resource_type = raw_data["resource_type"]

        if resource_type == "instance":
            tags = {tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])}
            
            return {
                "cloud_provider": "aws",
                "resource_type": "aws:ec2:instance",
                "metadata": self.create_metadata_object(
                    resource_id=resource["InstanceId"],
                    service="ec2",
                    region=region,
                    account_id=resource.get("OwnerId"),
                    tags=tags,
                ),
                "configuration": {
                    "instance_type": resource.get("InstanceType"),
                    "state": resource.get("State", {}).get("Name"),
                    "vpc_id": resource.get("VpcId"),
                    "subnet_id": resource.get("SubnetId"),
                    "security_groups": [
                        sg["GroupId"] for sg in resource.get("SecurityGroups", [])
                    ],
                    "iam_instance_profile": resource.get("IamInstanceProfile"),
                    "monitoring": resource.get("Monitoring", {}).get("State"),
                    "public_ip": resource.get("PublicIpAddress"),
                    "private_ip": resource.get("PrivateIpAddress"),
                },
                "raw": resource,  # Include full resource for comprehensive scanning
            }
        elif resource_type == "security-group":
            tags = {tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])}
            
            return {
                "cloud_provider": "aws",
                "resource_type": "aws:ec2:security-group",
                "metadata": self.create_metadata_object(
                    resource_id=resource["GroupId"],
                    service="ec2",
                    region=region,
                    account_id=resource.get("OwnerId"),
                    tags=tags,
                ),
                "configuration": {
                    "group_name": resource.get("GroupName"),
                    "description": resource.get("Description"),
                    "vpc_id": resource.get("VpcId"),
                    "ingress_rules": resource.get("IpPermissions", []),
                    "egress_rules": resource.get("IpPermissionsEgress", []),
                },
                "raw": resource,
            }

        return {}
