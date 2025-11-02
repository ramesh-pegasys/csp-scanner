# app/extractors/elb.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class ELBExtractor(BaseExtractor):
    """Extractor for AWS Elastic Load Balancing resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="elb",
            version="1.0.0",
            description="Extracts ELB load balancers (ALB, NLB, CLB)",
            resource_types=["load-balancer", "target-group"],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract ELB resources"""
        # Use us-east-1 as default region if none provided
        region = region or "us-east-1"

        artifacts = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor, self._extract_load_balancers, region, filters
                ),
                loop.run_in_executor(
                    executor, self._extract_target_groups, region, filters
                ),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"ELB extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_load_balancers(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract load balancers (ALB, NLB, CLB)"""
        artifacts = []
        client = self._get_client("elbv2", region=region)

        try:
            paginator = client.get_paginator("describe_load_balancers")
            for page in paginator.paginate():
                for lb in page["LoadBalancers"]:
                    try:
                        # Get additional load balancer details
                        lb_arn = lb["LoadBalancerArn"]

                        # Get listeners
                        listeners = []
                        try:
                            listeners_response = client.describe_listeners(
                                LoadBalancerArn=lb_arn
                            )
                            listeners = listeners_response["Listeners"]
                        except Exception as e:
                            logger.warning(
                                f"Failed to get listeners for LB {lb['LoadBalancerName']}: {e}"
                            )

                        # Get tags
                        tags = []
                        try:
                            tags_response = client.describe_tags(ResourceArns=[lb_arn])
                            if tags_response["TagDescriptions"]:
                                tags = tags_response["TagDescriptions"][0]["Tags"]
                        except Exception as e:
                            logger.warning(
                                f"Failed to get tags for LB {lb['LoadBalancerName']}: {e}"
                            )

                        lb_data = {**lb, "listeners": listeners, "tags": tags}

                        artifact = self.transform(
                            {
                                "resource": lb_data,
                                "resource_type": "load-balancer",
                                "region": region,
                            }
                        )

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract load balancer {lb.get('LoadBalancerName')}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list load balancers: {e}")

        return artifacts

    def _extract_target_groups(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract target groups"""
        artifacts = []
        client = self._get_client("elbv2", region=region)

        try:
            paginator = client.get_paginator("describe_target_groups")
            for page in paginator.paginate():
                for tg in page["TargetGroups"]:
                    try:
                        # Get target group details
                        tg_arn = tg["TargetGroupArn"]

                        # Get targets
                        targets = []
                        try:
                            targets_response = client.describe_target_health(
                                TargetGroupArn=tg_arn
                            )
                            targets = targets_response["TargetHealthDescriptions"]
                        except Exception as e:
                            logger.warning(
                                f"Failed to get targets for TG {tg['TargetGroupName']}: {e}"
                            )

                        # Get tags
                        tags = []
                        try:
                            tags_response = client.describe_tags(ResourceArns=[tg_arn])
                            if tags_response["TagDescriptions"]:
                                tags = tags_response["TagDescriptions"][0]["Tags"]
                        except Exception as e:
                            logger.warning(
                                f"Failed to get tags for TG {tg['TargetGroupName']}: {e}"
                            )

                        tg_data = {**tg, "targets": targets, "tags": tags}

                        artifact = self.transform(
                            {
                                "resource": tg_data,
                                "resource_type": "target-group",
                                "region": region,
                            }
                        )

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract target group {tg.get('TargetGroupName')}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list target groups: {e}")

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ELB resource to standardized format"""
        resource = raw_data["resource"]
        resource_type = raw_data["resource_type"]
        region = raw_data.get("region")

        if resource_type == "load-balancer":
            return {
                "resource_id": resource["LoadBalancerName"],
                "resource_type": f"elb:{resource['Type'].lower()}",
                "service": "elb",
                "region": region,
                "account_id": None,
                "configuration": {
                    "load_balancer_name": resource["LoadBalancerName"],
                    "load_balancer_arn": resource["LoadBalancerArn"],
                    "dns_name": resource.get("DNSName"),
                    "canonical_hosted_zone_id": resource.get("CanonicalHostedZoneId"),
                    "created_time": resource.get("CreatedTime"),
                    "load_balancer_addresses": resource.get(
                        "LoadBalancerAddresses", []
                    ),
                    "availability_zones": resource.get("AvailabilityZones", []),
                    "ip_address_type": resource.get("IpAddressType"),
                    "scheme": resource.get("Scheme"),
                    "state": resource.get("State", {}),
                    "type": resource.get("Type"),
                    "vpc_id": resource.get("VpcId"),
                    "security_groups": resource.get("SecurityGroups", []),
                    "listeners": resource.get("listeners", []),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        elif resource_type == "target-group":
            return {
                "resource_id": resource["TargetGroupName"],
                "resource_type": "elb:target-group",
                "service": "elb",
                "region": region,
                "account_id": None,
                "configuration": {
                    "target_group_name": resource["TargetGroupName"],
                    "target_group_arn": resource["TargetGroupArn"],
                    "protocol": resource.get("Protocol"),
                    "port": resource.get("Port"),
                    "vpc_id": resource.get("VpcId"),
                    "health_check": resource.get("HealthCheck", {}),
                    "target_type": resource.get("TargetType"),
                    "ip_address_type": resource.get("IpAddressType"),
                    "matcher": resource.get("Matcher", {}),
                    "targets": resource.get("targets", []),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        return {}
