# app/extractors/apigateway.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class APIGatewayExtractor(BaseExtractor):
    """Extractor for AWS API Gateway resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="apigateway",
            version="1.0.0",
            description="Extracts API Gateway REST APIs, resources, methods, and deployments",
            resource_types=["rest-api", "resource", "method", "deployment", "stage"],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract API Gateway resources"""
        # Use us-east-1 as default region if none provided
        region = region or "us-east-1"

        artifacts = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_rest_apis, region, filters)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"API Gateway extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_rest_apis(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract REST APIs and their components"""
        artifacts = []
        client = self._get_client("apigateway", region=region)

        try:
            paginator = client.get_paginator("get_rest_apis")
            for page in paginator.paginate():
                for api in page["items"]:
                    try:
                        api_id = api["id"]

                        # Extract the REST API itself
                        api_artifact = self.transform(
                            {
                                "resource": api,
                                "resource_type": "rest-api",
                                "region": region,
                            }
                        )
                        if self.validate(api_artifact):
                            artifacts.append(api_artifact)

                        # Extract resources for this API
                        resources_artifacts = self._extract_resources(
                            client, api_id, region
                        )
                        artifacts.extend(resources_artifacts)

                        # Extract deployments and stages for this API
                        deployments_artifacts = self._extract_deployments(
                            client, api_id, region
                        )
                        artifacts.extend(deployments_artifacts)

                    except Exception as e:
                        logger.error(f"Failed to extract REST API {api.get('id')}: {e}")

        except Exception as e:
            logger.error(f"Failed to list REST APIs: {e}")

        return artifacts

    def _extract_resources(
        self, client, api_id: str, region: str
    ) -> List[Dict[str, Any]]:
        """Extract resources for a REST API"""
        artifacts = []

        try:
            paginator = client.get_paginator("get_resources")
            for page in paginator.paginate(restApiId=api_id):
                for resource in page["items"]:
                    try:
                        # Extract the resource
                        resource_artifact = self.transform(
                            {
                                "resource": resource,
                                "resource_type": "resource",
                                "region": region,
                                "api_id": api_id,
                            }
                        )
                        if self.validate(resource_artifact):
                            artifacts.append(resource_artifact)

                        # Extract methods for this resource
                        if resource.get("resourceMethods"):
                            for method_name, method_config in resource[
                                "resourceMethods"
                            ].items():
                                method_artifact = self.transform(
                                    {
                                        "resource": {
                                            "method": method_name,
                                            "config": method_config,
                                            "resource_id": resource["id"],
                                        },
                                        "resource_type": "method",
                                        "region": region,
                                        "api_id": api_id,
                                    }
                                )
                                if self.validate(method_artifact):
                                    artifacts.append(method_artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract resource {resource.get('id')} for API {api_id}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list resources for API {api_id}: {e}")

        return artifacts

    def _extract_deployments(
        self, client, api_id: str, region: str
    ) -> List[Dict[str, Any]]:
        """Extract deployments and stages for a REST API"""
        artifacts = []

        try:
            paginator = client.get_paginator("get_deployments")
            for page in paginator.paginate(restApiId=api_id):
                for deployment in page["items"]:
                    try:
                        deployment_id = deployment["id"]

                        # Extract deployment
                        deployment_artifact = self.transform(
                            {
                                "resource": deployment,
                                "resource_type": "deployment",
                                "region": region,
                                "api_id": api_id,
                            }
                        )
                        if self.validate(deployment_artifact):
                            artifacts.append(deployment_artifact)

                        # Get stages for this deployment
                        stages_response = client.get_stages(
                            restApiId=api_id, deploymentId=deployment_id
                        )
                        for stage in stages_response["item"]:
                            stage_artifact = self.transform(
                                {
                                    "resource": stage,
                                    "resource_type": "stage",
                                    "region": region,
                                    "api_id": api_id,
                                    "deployment_id": deployment_id,
                                }
                            )
                            if self.validate(stage_artifact):
                                artifacts.append(stage_artifact)

                    except Exception as e:
                        logger.error(
                            f"Failed to extract deployment {deployment.get('id')} for API {api_id}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to list deployments for API {api_id}: {e}")

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform API Gateway resource to standardized format"""
        resource = raw_data["resource"]
        resource_type = raw_data["resource_type"]
        region = raw_data.get("region")

        if resource_type == "rest-api":
            return {
                "resource_id": resource["id"],
                "resource_type": "apigateway:rest-api",
                "service": "apigateway",
                "region": region,
                "account_id": None,
                "configuration": {
                    "id": resource["id"],
                    "name": resource.get("name"),
                    "description": resource.get("description"),
                    "created_date": resource.get("createdDate"),
                    "api_key_source_type": resource.get("apiKeySourceType"),
                    "endpoint_configuration": resource.get("endpointConfiguration", {}),
                    "policy": resource.get("policy"),
                    "version": resource.get("version"),
                    "warnings": resource.get("warnings", []),
                    "disable_execute_api_endpoint": resource.get(
                        "disableExecuteApiEndpoint"
                    ),
                },
                "raw": resource,
            }

        elif resource_type == "resource":
            return {
                "resource_id": f"{raw_data.get('api_id', 'unknown')}/{resource['id']}",
                "resource_type": "apigateway:resource",
                "service": "apigateway",
                "region": region,
                "account_id": None,
                "configuration": {
                    "id": resource["id"],
                    "parent_id": resource.get("parentId"),
                    "path_part": resource.get("pathPart"),
                    "path": resource.get("path"),
                    "resource_methods": resource.get("resourceMethods", {}),
                },
                "raw": resource,
            }

        elif resource_type == "method":
            return {
                "resource_id": f"{raw_data.get('api_id', 'unknown')}/{resource['resource_id']}/{resource['method']}",
                "resource_type": "apigateway:method",
                "service": "apigateway",
                "region": region,
                "account_id": None,
                "configuration": {
                    "method": resource["method"],
                    "resource_id": resource["resource_id"],
                    "http_method": resource["config"].get("httpMethod"),
                    "authorization_type": resource["config"].get("authorizationType"),
                    "api_key_required": resource["config"].get("apiKeyRequired"),
                    "request_models": resource["config"].get("requestModels", {}),
                    "request_parameters": resource["config"].get(
                        "requestParameters", {}
                    ),
                    "method_responses": resource["config"].get("methodResponses", {}),
                    "method_integration": resource["config"].get(
                        "methodIntegration", {}
                    ),
                },
                "raw": resource,
            }

        elif resource_type == "deployment":
            return {
                "resource_id": f"{raw_data.get('api_id', 'unknown')}/{resource['id']}",
                "resource_type": "apigateway:deployment",
                "service": "apigateway",
                "region": region,
                "account_id": None,
                "configuration": {
                    "id": resource["id"],
                    "description": resource.get("description"),
                    "created_date": resource.get("createdDate"),
                    "api_summary": resource.get("apiSummary", {}),
                },
                "raw": resource,
            }

        elif resource_type == "stage":
            return {
                "resource_id": (
                    f"{raw_data.get('api_id', 'unknown')}/"
                    f"{raw_data.get('deployment_id', 'unknown')}/"
                    f"{resource['stageName']}"
                ),
                "resource_type": "apigateway:stage",
                "service": "apigateway",
                "region": region,
                "account_id": None,
                "configuration": {
                    "stage_name": resource["stageName"],
                    "deployment_id": resource.get("deploymentId"),
                    "description": resource.get("description"),
                    "created_date": resource.get("createdDate"),
                    "last_updated_date": resource.get("lastUpdatedDate"),
                    "method_settings": resource.get("methodSettings", {}),
                    "variables": resource.get("variables", {}),
                    "documentation_version": resource.get("documentationVersion"),
                    "access_log_settings": resource.get("accessLogSettings", {}),
                    "canary_settings": resource.get("canarySettings", {}),
                    "tracing_enabled": resource.get("tracingEnabled"),
                    "web_acl_arn": resource.get("webAclArn"),
                    "tags": resource.get("tags", {}),
                },
                "raw": resource,
            }

        return {}
