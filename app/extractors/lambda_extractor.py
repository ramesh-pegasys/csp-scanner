# app/extractors/lambda_extractor.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class LambdaExtractor(BaseExtractor):
    """Extractor for Lambda functions and related resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="lambda",
            version="1.0.0",
            description="Extracts Lambda functions, layers, and event source mappings",
            resource_types=["function", "layer", "event-source-mapping"],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Lambda resources"""
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
        """Extract Lambda resources from a specific region"""
        lambda_client = self.session.client("lambda", region_name=region)
        artifacts = []

        # Extract functions
        try:
            functions = self._extract_functions(lambda_client, region, filters)
            artifacts.extend(functions)
        except Exception as e:
            logger.error(f"Failed to extract functions in {region}: {e}")

        # Extract layers
        try:
            layers = self._extract_layers(lambda_client, region, filters)
            artifacts.extend(layers)
        except Exception as e:
            logger.error(f"Failed to extract layers in {region}: {e}")

        # Extract event source mappings
        try:
            event_mappings = self._extract_event_source_mappings(
                lambda_client, region, filters
            )
            artifacts.extend(event_mappings)
        except Exception as e:
            logger.error(f"Failed to extract event source mappings in {region}: {e}")

        return artifacts

    def _extract_functions(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract Lambda functions"""
        artifacts = []

        paginator = client.get_paginator("list_functions")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for func in page["Functions"]:
                artifact = self.transform(
                    {"resource": func, "region": region, "resource_type": "function"}
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_layers(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract Lambda layers"""
        artifacts = []

        paginator = client.get_paginator("list_layers")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for layer in page["Layers"]:
                artifact = self.transform(
                    {"resource": layer, "region": region, "resource_type": "layer"}
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_event_source_mappings(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract Lambda event source mappings"""
        artifacts = []

        paginator = client.get_paginator("list_event_source_mappings")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for mapping in page["EventSourceMappings"]:
                artifact = self.transform(
                    {
                        "resource": mapping,
                        "region": region,
                        "resource_type": "event-source-mapping",
                    }
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
        """Transform Lambda resource to standardized format"""
        resource = raw_data["resource"]
        region = raw_data["region"]
        resource_type = raw_data["resource_type"]

        if resource_type == "function":
            tags = raw_data.get("tags", {})
            account_id = resource["FunctionArn"].split(":")[4]
            
            return {
                "cloud_provider": "aws",
                "resource_type": "aws:lambda:function",
                "metadata": self.create_metadata_object(
                    resource_id=resource["FunctionArn"],
                    service="lambda",
                    region=region,
                    account_id=account_id,
                    tags=tags,
                ),
                "configuration": {
                    "function_name": resource["FunctionName"],
                    "runtime": resource.get("Runtime"),
                    "role": resource.get("Role"),
                    "handler": resource.get("Handler"),
                    "code_size": resource.get("CodeSize"),
                    "timeout": resource.get("Timeout"),
                    "memory_size": resource.get("MemorySize"),
                    "environment": resource.get("Environment", {}),
                    "vpc_config": resource.get("VpcConfig"),
                    "last_modified": resource.get("LastModified"),
                    "version": resource.get("Version"),
                    "architectures": resource.get("Architectures", []),
                    "package_type": resource.get("PackageType"),
                    "ephemeral_storage": resource.get("EphemeralStorage", {}),
                },
                "raw": resource,  # Include full resource for comprehensive scanning
            }
        elif resource_type == "layer":
            account_id = resource["LayerArn"].split(":")[4]
            
            return {
                "cloud_provider": "aws",
                "resource_type": "aws:lambda:layer",
                "metadata": self.create_metadata_object(
                    resource_id=resource["LayerArn"],
                    service="lambda",
                    region=region,
                    account_id=account_id,
                ),
                "configuration": {
                    "layer_name": resource["LayerName"],
                    "version": resource.get("Version"),
                    "description": resource.get("Description"),
                    "created_date": resource.get("CreatedDate"),
                    "compatible_runtimes": resource.get("CompatibleRuntimes", []),
                    "license_info": resource.get("LicenseInfo"),
                },
                "raw": resource,
            }
        elif resource_type == "event-source-mapping":
            account_id = (
                resource.get("FunctionArn", "").split(":")[4]
                if resource.get("FunctionArn")
                else None
            )
            
            return {
                "cloud_provider": "aws",
                "resource_type": "aws:lambda:event-source-mapping",
                "metadata": self.create_metadata_object(
                    resource_id=resource["UUID"],
                    service="lambda",
                    region=region,
                    account_id=account_id,
                ),
                "configuration": {
                    "function_arn": resource.get("FunctionArn"),
                    "event_source_arn": resource.get("EventSourceArn"),
                    "state": resource.get("State"),
                    "state_reason": resource.get("StateReason"),
                    "state_reason_code": resource.get("StateReasonCode"),
                    "last_modified": resource.get("LastModified"),
                    "last_processing_result": resource.get("LastProcessingResult"),
                    "batch_size": resource.get("BatchSize"),
                    "maximum_batching_window_in_seconds": resource.get(
                        "MaximumBatchingWindowInSeconds"
                    ),
                    "parallelization_factor": resource.get("ParallelizationFactor"),
                    "starting_position": resource.get("StartingPosition"),
                    "starting_position_timestamp": resource.get(
                        "StartingPositionTimestamp"
                    ),
                },
                "raw": resource,
            }

        return {}
