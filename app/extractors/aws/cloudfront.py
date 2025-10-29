# app/extractors/cloudfront.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class CloudFrontExtractor(BaseExtractor):
    """Extractor for AWS CloudFront distributions and related resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="cloudfront",
            version="1.0.0",
            description="Extracts CloudFront distributions, origins, and cache behaviors",
            resource_types=["distribution", "origin-access-identity"],
            supports_regions=False,  # CloudFront is global
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract CloudFront resources"""
        artifacts = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_distributions, filters),
                loop.run_in_executor(
                    executor, self._extract_origin_access_identities, filters
                ),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"CloudFront extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_distributions(
        self, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract CloudFront distributions"""
        artifacts = []
        client = self._get_client("cloudfront")  # CloudFront is global

        try:
            paginator = client.get_paginator("list_distributions")
            for page in paginator.paginate():
                items = page.get("DistributionList", {}).get("Items", [])
                for distribution_summary in items:
                    try:
                        # Get detailed distribution information
                        distribution_id = distribution_summary["Id"]
                        response = client.get_distribution(Id=distribution_id)

                        distribution = response["Distribution"]
                        config = distribution["DistributionConfig"]

                        # Get tags
                        tags = []
                        try:
                            tags_response = client.list_tags_for_resource(
                                Resource=f"arn:aws:cloudfront::{self._get_account_id()}:distribution/{distribution_id}"
                            )
                            tags = tags_response["Tags"]["Items"]
                        except Exception as e:
                            logger.warning(
                                f"Failed to get tags for distribution {distribution_id}: {e}"
                            )

                        dist_data = {
                            "distribution": distribution,
                            "config": config,
                            "tags": tags,
                        }

                        artifact = self.transform(
                            {"resource": dist_data, "resource_type": "distribution"}
                        )

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract CloudFront distribution {distribution_summary.get('Id')}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list CloudFront distributions: {e}")

        return artifacts

    def _extract_origin_access_identities(
        self, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract CloudFront origin access identities"""
        artifacts = []
        client = self._get_client("cloudfront")

        try:
            paginator = client.get_paginator(
                "list_cloud_front_origin_access_identities"
            )
            for page in paginator.paginate():
                items = page.get("CloudFrontOriginAccessIdentityList", {}).get(
                    "Items", []
                )
                for oai_summary in items:
                    try:
                        # Get detailed OAI information
                        oai_id = oai_summary["Id"]
                        response = client.get_cloud_front_origin_access_identity(
                            Id=oai_id
                        )

                        oai = response["CloudFrontOriginAccessIdentity"]
                        config = oai["CloudFrontOriginAccessIdentityConfig"]

                        artifact = self.transform(
                            {
                                "resource": {"oai": oai, "config": config},
                                "resource_type": "origin-access-identity",
                            }
                        )

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract OAI {oai_summary.get('Id')}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list CloudFront origin access identities: {e}")

        return artifacts

    def _get_account_id(self) -> str:
        """Get AWS account ID from STS"""
        try:
            sts_client = self._get_client("sts")
            return sts_client.get_caller_identity()["Account"]
        except Exception:
            return "unknown"

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CloudFront resource to standardized format"""
        resource = raw_data["resource"]
        resource_type = raw_data["resource_type"]

        if resource_type == "distribution":
            config = resource["config"]
            distribution = resource["distribution"]

            return {
                "resource_id": config["CallerReference"],
                "resource_type": "cloudfront:distribution",
                "service": "cloudfront",
                "region": None,  # CloudFront is global
                "account_id": None,
                "configuration": {
                    "id": distribution["Id"],
                    "arn": distribution["ARN"],
                    "status": distribution["Status"],
                    "domain_name": config.get("Aliases", {}).get("Items", []),
                    "origins": config.get("Origins", {}),
                    "default_cache_behavior": config.get("DefaultCacheBehavior", {}),
                    "cache_behaviors": config.get("CacheBehaviors", {}),
                    "custom_error_responses": config.get("CustomErrorResponses", {}),
                    "comment": config.get("Comment"),
                    "enabled": config.get("Enabled"),
                    "price_class": config.get("PriceClass"),
                    "http_version": config.get("HttpVersion"),
                    "is_ipv6_enabled": config.get("IsIPV6Enabled"),
                    "web_acl_id": config.get("WebACLId"),
                    "restrictions": config.get("Restrictions", {}),
                    "viewer_certificate": config.get("ViewerCertificate", {}),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        elif resource_type == "origin-access-identity":
            config = resource["config"]
            oai = resource["oai"]

            return {
                "resource_id": config["CallerReference"],
                "resource_type": "cloudfront:origin-access-identity",
                "service": "cloudfront",
                "region": None,  # CloudFront is global
                "account_id": None,
                "configuration": {
                    "id": oai["Id"],
                    "s3_canonical_user_id": oai["S3CanonicalUserId"],
                    "comment": config.get("Comment"),
                    "caller_reference": config["CallerReference"],
                },
                "raw": resource,
            }

        return {}
