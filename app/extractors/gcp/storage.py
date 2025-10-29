# app/extractors/gcp/storage.py
"""
GCP Cloud Storage extractor.
Extracts Cloud Storage buckets and their configurations.
"""

from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.cloud.gcp_session import GCPSession
import logging

logger = logging.getLogger(__name__)


class GCPStorageExtractor(BaseExtractor):
    """
    Extractor for GCP Cloud Storage resources.
    
    Extracts:
    - Storage Buckets
    - Bucket IAM policies
    - Lifecycle configurations
    """

    def get_metadata(self) -> ExtractorMetadata:
        """
        Get metadata about the GCP Storage extractor.
        
        Returns:
            ExtractorMetadata object
        """
        return ExtractorMetadata(
            service_name="storage",
            version="1.0.0",
            description="Extracts GCP Cloud Storage buckets and configurations",
            resource_types=["bucket"],
            cloud_provider="gcp",
            supports_regions=False,  # Buckets are global but have location
            requires_pagination=False,
        )

    async def extract(
        self,
        region: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract GCP Cloud Storage buckets.
        
        Args:
            region: Optional location to filter buckets
            filters: Optional filters to apply
            
        Returns:
            List of raw bucket dictionaries
        """
        # Cast session to GCPSession for type checking
        gcp_session = cast(GCPSession, self.session)
        
        logger.info(f"Extracting GCP Cloud Storage buckets for project {gcp_session.project_id}")
        
        try:
            # Extract buckets (runs in thread pool since GCP client is sync)
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                buckets = await loop.run_in_executor(
                    executor,
                    self._extract_buckets,
                    gcp_session,
                    region
                )
            
            logger.info(f"Extracted {len(buckets)} Cloud Storage buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Error extracting GCP Cloud Storage buckets: {str(e)}")
            raise

    def _extract_buckets(
        self,
        gcp_session: GCPSession,
        location_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract Cloud Storage buckets.
        
        Args:
            gcp_session: GCP session object
            location_filter: Optional location to filter buckets
            
        Returns:
            List of bucket dictionaries
        """
        storage_client = gcp_session.get_client("storage")
        
        try:
            # List all buckets in the project
            buckets_list = storage_client.list_buckets(project=gcp_session.project_id)
            
            buckets = []
            for bucket in buckets_list:
                # Apply location filter if specified
                if location_filter and bucket.location.lower() != location_filter.lower():
                    continue
                
                bucket_dict = {
                    "name": bucket.name,
                    "id": bucket.id,
                    "self_link": bucket.self_link if hasattr(bucket, 'self_link') else f"https://www.googleapis.com/storage/v1/b/{bucket.name}",
                    "location": bucket.location,
                    "location_type": bucket.location_type,
                    "storage_class": bucket.storage_class,
                    "time_created": str(bucket.time_created) if bucket.time_created else None,
                    "updated": str(bucket.updated) if bucket.updated else None,
                    "versioning_enabled": bucket.versioning_enabled if hasattr(bucket, 'versioning_enabled') else False,
                    "labels": dict(bucket.labels) if bucket.labels else {},
                    "resource_type": "gcp:storage:bucket",
                }
                
                # Extract encryption configuration
                if bucket.default_kms_key_name:
                    bucket_dict["encryption"] = {
                        "default_kms_key_name": bucket.default_kms_key_name,
                    }
                
                # Extract lifecycle rules if configured
                if bucket.lifecycle_rules:
                    lifecycle_rules = []
                    for rule in bucket.lifecycle_rules:
                        rule_dict = {
                            "action": {"type": rule.get("action", {}).get("type", "")},
                            "condition": {}
                        }
                        
                        # Extract rule conditions
                        condition = rule.get("condition", {})
                        if "age" in condition:
                            rule_dict["condition"]["age"] = condition["age"]
                        if "created_before" in condition:
                            rule_dict["condition"]["created_before"] = str(condition["created_before"])
                        if "matches_storage_class" in condition:
                            rule_dict["condition"]["matches_storage_class"] = condition["matches_storage_class"]
                        if "num_newer_versions" in condition:
                            rule_dict["condition"]["num_newer_versions"] = condition["num_newer_versions"]
                        
                        lifecycle_rules.append(rule_dict)
                    
                    bucket_dict["lifecycle_rules"] = lifecycle_rules
                
                # Extract CORS configuration
                if bucket.cors:
                    cors_rules = []
                    for cors in bucket.cors:
                        cors_rules.append({
                            "origin": cors.get("origin", []),
                            "method": cors.get("method", []),
                            "response_header": cors.get("responseHeader", []),
                            "max_age_seconds": cors.get("maxAgeSeconds"),
                        })
                    bucket_dict["cors"] = cors_rules
                
                # Extract IAM configuration if enabled
                if self.config.get("include_iam_policies", False):
                    try:
                        policy = bucket.get_iam_policy()
                        if policy:
                            bindings = []
                            for binding in policy.bindings:
                                bindings.append({
                                    "role": binding["role"],
                                    "members": list(binding.get("members", [])),
                                })
                            bucket_dict["iam_policy"] = {"bindings": bindings}
                    except Exception as e:
                        logger.warning(f"Could not fetch IAM policy for bucket {bucket.name}: {str(e)}")
                
                # Extract logging configuration
                if bucket.logging:
                    bucket_dict["logging"] = {
                        "log_bucket": bucket.logging.get("logBucket", ""),
                        "log_object_prefix": bucket.logging.get("logObjectPrefix", ""),
                    }
                
                # Extract website configuration
                if bucket.website:
                    bucket_dict["website"] = {
                        "main_page_suffix": bucket.website.get("mainPageSuffix", ""),
                        "not_found_page": bucket.website.get("notFoundPage", ""),
                    }
                
                # Extract public access prevention
                if hasattr(bucket, 'iam_configuration'):
                    iam_config = bucket.iam_configuration
                    bucket_dict["public_access_prevention"] = {
                        "is_enforced": iam_config.public_access_prevention == "enforced" if hasattr(iam_config, 'public_access_prevention') else False,
                        "uniform_bucket_level_access": {
                            "enabled": iam_config.uniform_bucket_level_access_enabled if hasattr(iam_config, 'uniform_bucket_level_access_enabled') else False,
                        },
                    }
                
                buckets.append(bucket_dict)
            
            logger.debug(f"Extracted {len(buckets)} buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Error listing Cloud Storage buckets: {str(e)}")
            return []

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw GCP Cloud Storage data into standardized format.
        
        Args:
            raw_data: Raw bucket dictionary from GCP API
            
        Returns:
            Standardized artifact dictionary
        """
        try:
            # Extract common fields
            resource_id = raw_data.get("self_link", raw_data.get("name", "unknown"))
            bucket_name = raw_data.get("name", "unknown")
            location = raw_data.get("location", "unknown")
            
            # Get project ID from session
            gcp_session = cast(GCPSession, self.session)
            project_id = gcp_session.project_id
            
            # Get labels
            labels = raw_data.get("labels", {})
            
            # Build configuration
            config = {
                "location": location,
                "location_type": raw_data.get("location_type", ""),
                "storage_class": raw_data.get("storage_class", ""),
                "versioning_enabled": raw_data.get("versioning_enabled", False),
                "time_created": raw_data.get("time_created"),
                "updated": raw_data.get("updated"),
            }
            
            # Add optional configurations
            if "encryption" in raw_data:
                config["encryption"] = raw_data["encryption"]
            
            if "lifecycle_rules" in raw_data:
                config["lifecycle_rules"] = raw_data["lifecycle_rules"]
            
            if "cors" in raw_data:
                config["cors"] = raw_data["cors"]
            
            if "iam_policy" in raw_data:
                config["iam_policy"] = raw_data["iam_policy"]
            
            if "logging" in raw_data:
                config["logging"] = raw_data["logging"]
            
            if "website" in raw_data:
                config["website"] = raw_data["website"]
            
            if "public_access_prevention" in raw_data:
                config["public_access_prevention"] = raw_data["public_access_prevention"]
            
            return {
                "cloud_provider": "gcp",
                "resource_type": "gcp:storage:bucket",
                "metadata": self.create_metadata_object(
                    resource_id=resource_id,
                    service="storage",
                    region=location,  # For buckets, location is the region
                    project_id=project_id,
                    labels=labels,
                ),
                "configuration": config,
                "raw": raw_data,
            }
            
        except Exception as e:
            logger.error(f"Error transforming bucket: {str(e)}")
            return {}
