# app/extractors/vpc.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class VPCExtractor(BaseExtractor):
    """Extractor for VPC resources and related networking components"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="vpc",
            version="1.0.0",
            description="Extracts VPCs, subnets, internet gateways, NAT gateways, route tables, and network ACLs",
            resource_types=[
                "vpc",
                "subnet",
                "internet-gateway",
                "nat-gateway",
                "route-table",
                "network-acl",
            ],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract VPC resources"""
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
        """Extract VPC resources from a specific region"""
        ec2_client = self.session.client("ec2", region_name=region)
        artifacts = []

        # Extract VPCs
        try:
            vpcs = self._extract_vpcs(ec2_client, region, filters)
            artifacts.extend(vpcs)
        except Exception as e:
            logger.error(f"Failed to extract VPCs in {region}: {e}")

        # Extract subnets
        try:
            subnets = self._extract_subnets(ec2_client, region, filters)
            artifacts.extend(subnets)
        except Exception as e:
            logger.error(f"Failed to extract subnets in {region}: {e}")

        # Extract internet gateways
        try:
            igws = self._extract_internet_gateways(ec2_client, region, filters)
            artifacts.extend(igws)
        except Exception as e:
            logger.error(f"Failed to extract internet gateways in {region}: {e}")

        # Extract NAT gateways
        try:
            nat_gateways = self._extract_nat_gateways(ec2_client, region, filters)
            artifacts.extend(nat_gateways)
        except Exception as e:
            logger.error(f"Failed to extract NAT gateways in {region}: {e}")

        # Extract route tables
        try:
            route_tables = self._extract_route_tables(ec2_client, region, filters)
            artifacts.extend(route_tables)
        except Exception as e:
            logger.error(f"Failed to extract route tables in {region}: {e}")

        # Extract network ACLs
        try:
            network_acls = self._extract_network_acls(ec2_client, region, filters)
            artifacts.extend(network_acls)
        except Exception as e:
            logger.error(f"Failed to extract network ACLs in {region}: {e}")

        return artifacts

    def _extract_vpcs(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract VPCs"""
        artifacts = []

        paginator = client.get_paginator("describe_vpcs")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for vpc in page["Vpcs"]:
                artifact = self.transform(
                    {"resource": vpc, "region": region, "resource_type": "vpc"}
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_subnets(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract subnets"""
        artifacts = []

        paginator = client.get_paginator("describe_subnets")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for subnet in page["Subnets"]:
                artifact = self.transform(
                    {"resource": subnet, "region": region, "resource_type": "subnet"}
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_internet_gateways(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract internet gateways"""
        artifacts = []

        paginator = client.get_paginator("describe_internet_gateways")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for igw in page["InternetGateways"]:
                artifact = self.transform(
                    {
                        "resource": igw,
                        "region": region,
                        "resource_type": "internet-gateway",
                    }
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_nat_gateways(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract NAT gateways"""
        artifacts = []

        paginator = client.get_paginator("describe_nat_gateways")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for nat_gw in page["NatGateways"]:
                artifact = self.transform(
                    {
                        "resource": nat_gw,
                        "region": region,
                        "resource_type": "nat-gateway",
                    }
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_route_tables(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract route tables"""
        artifacts = []

        paginator = client.get_paginator("describe_route_tables")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for rt in page["RouteTables"]:
                artifact = self.transform(
                    {"resource": rt, "region": region, "resource_type": "route-table"}
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_network_acls(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract network ACLs"""
        artifacts = []

        paginator = client.get_paginator("describe_network_acls")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for nacl in page["NetworkAcls"]:
                artifact = self.transform(
                    {"resource": nacl, "region": region, "resource_type": "network-acl"}
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _get_all_regions(self) -> List[str]:
        """Get all enabled regions (using EC2 as reference)"""
        ec2_client = self.session.client("ec2")
        response = ec2_client.describe_regions(AllRegions=False)
        return [region["RegionName"] for region in response["Regions"]]

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform VPC resource to standardized format"""
        resource = raw_data["resource"]
        region = raw_data["region"]
        resource_type = raw_data["resource_type"]

        if resource_type == "vpc":
            return {
                "resource_id": resource["VpcId"],
                "resource_type": "vpc:vpc",
                "service": "vpc",
                "region": region,
                "account_id": None,  # VPC doesn't include account ID
                "configuration": {
                    "vpc_id": resource["VpcId"],
                    "state": resource.get("State"),
                    "cidr_block": resource.get("CidrBlock"),
                    "dhcp_options_id": resource.get("DhcpOptionsId"),
                    "instance_tenancy": resource.get("InstanceTenancy"),
                    "is_default": resource.get("IsDefault"),
                    "cidr_block_association_set": resource.get(
                        "CidrBlockAssociationSet", []
                    ),
                    "tags": {
                        tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])
                    },
                },
                "raw": resource,  # Include full resource for comprehensive scanning
            }
        elif resource_type == "subnet":
            return {
                "resource_id": resource["SubnetId"],
                "resource_type": "vpc:subnet",
                "service": "vpc",
                "region": region,
                "account_id": None,
                "configuration": {
                    "subnet_id": resource["SubnetId"],
                    "vpc_id": resource.get("VpcId"),
                    "state": resource.get("State"),
                    "cidr_block": resource.get("CidrBlock"),
                    "ipv6_cidr_block_association_set": resource.get(
                        "Ipv6CidrBlockAssociationSet", []
                    ),
                    "availability_zone": resource.get("AvailabilityZone"),
                    "availability_zone_id": resource.get("AvailabilityZoneId"),
                    "available_ip_address_count": resource.get(
                        "AvailableIpAddressCount"
                    ),
                    "default_for_az": resource.get("DefaultForAz"),
                    "map_public_ip_on_launch": resource.get("MapPublicIpOnLaunch"),
                    "assign_ipv6_address_on_creation": resource.get(
                        "AssignIpv6AddressOnCreation"
                    ),
                    "tags": {
                        tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])
                    },
                },
                "raw": resource,
            }
        elif resource_type == "internet-gateway":
            return {
                "resource_id": resource["InternetGatewayId"],
                "resource_type": "vpc:internet-gateway",
                "service": "vpc",
                "region": region,
                "account_id": None,
                "configuration": {
                    "internet_gateway_id": resource["InternetGatewayId"],
                    "attachments": resource.get("Attachments", []),
                    "tags": {
                        tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])
                    },
                },
                "raw": resource,
            }
        elif resource_type == "nat-gateway":
            return {
                "resource_id": resource["NatGatewayId"],
                "resource_type": "vpc:nat-gateway",
                "service": "vpc",
                "region": region,
                "account_id": None,
                "configuration": {
                    "nat_gateway_id": resource["NatGatewayId"],
                    "subnet_id": resource.get("SubnetId"),
                    "nat_gateway_addresses": resource.get("NatGatewayAddresses", []),
                    "state": resource.get("State"),
                    "create_time": resource.get("CreateTime"),
                    "delete_time": resource.get("DeleteTime"),
                    "failure_code": resource.get("FailureCode"),
                    "failure_message": resource.get("FailureMessage"),
                    "tags": {
                        tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])
                    },
                },
                "raw": resource,
            }
        elif resource_type == "route-table":
            return {
                "resource_id": resource["RouteTableId"],
                "resource_type": "vpc:route-table",
                "service": "vpc",
                "region": region,
                "account_id": None,
                "configuration": {
                    "route_table_id": resource["RouteTableId"],
                    "vpc_id": resource.get("VpcId"),
                    "routes": resource.get("Routes", []),
                    "associations": resource.get("Associations", []),
                    "propagating_vgws": resource.get("PropagatingVgws", []),
                    "tags": {
                        tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])
                    },
                },
                "raw": resource,
            }
        elif resource_type == "network-acl":
            return {
                "resource_id": resource["NetworkAclId"],
                "resource_type": "vpc:network-acl",
                "service": "vpc",
                "region": region,
                "account_id": None,
                "configuration": {
                    "network_acl_id": resource["NetworkAclId"],
                    "vpc_id": resource.get("VpcId"),
                    "is_default": resource.get("IsDefault"),
                    "entries": resource.get("Entries", []),
                    "associations": resource.get("Associations", []),
                    "tags": {
                        tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])
                    },
                },
                "raw": resource,
            }

        return {}
