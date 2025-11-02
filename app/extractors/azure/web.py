# app/extractors/azure/web.py
"""
Azure Web Apps extractor for App Services and Function Apps.
"""

from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.extractors.azure.utils import execute_azure_api_call
import logging

logger = logging.getLogger(__name__)


class AzureWebExtractor(BaseExtractor):
    """Extractor for Azure App Services and Function Apps"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="web",
            version="1.0.0",
            description="Extracts Azure App Services, Function Apps, and Web Apps",
            resource_types=["app-service", "function-app", "web-app"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure web resources"""
        locations = [region] if region else self.session.list_regions()
        artifacts = []

        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_location, loc, filters)
                for loc in locations
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Azure web extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        return artifacts

    def _extract_location(
        self, location: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract web resources from a specific location"""
        artifacts = []

        try:
            web_client = self.session.get_client("web")

            # Extract App Service Plans
            try:
                plans = self._extract_app_service_plans(web_client, location)
                artifacts.extend(plans)
            except Exception as e:
                logger.error(f"Failed to extract App Service Plans in {location}: {e}")

            # Extract Web Apps
            try:
                web_apps = self._extract_web_apps(web_client, location)
                artifacts.extend(web_apps)
            except Exception as e:
                logger.error(f"Failed to extract Web Apps in {location}: {e}")

            # Extract Function Apps
            try:
                function_apps = self._extract_function_apps(web_client, location)
                artifacts.extend(function_apps)
            except Exception as e:
                logger.error(f"Failed to extract Function Apps in {location}: {e}")

        except Exception as e:
            logger.error(f"Failed to get web client for {location}: {e}")

        return artifacts

    def _extract_app_service_plans(
        self, web_client: Any, location: str
    ) -> List[Dict[str, Any]]:
        """Extract App Service Plans"""
        artifacts: List[Dict[str, Any]] = []

        # List all app service plans with retry
        async def get_plans():
            return list(web_client.app_service_plans.list())

        try:
            plans = asyncio.run(
                execute_azure_api_call(get_plans, "get_app_service_plans")
            )
        except Exception as e:
            logger.error(f"Failed to list App Service Plans after retries: {e}")
            return artifacts

        for plan in plans:
            if plan.location != location:
                continue

            artifact = self.transform(
                {
                    "resource": plan,
                    "location": location,
                    "resource_type": "app-service-plan",
                }
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def _extract_web_apps(self, web_client: Any, location: str) -> List[Dict[str, Any]]:
        """Extract Web Apps"""
        artifacts: List[Dict[str, Any]] = []

        # List all web apps with retry
        async def get_web_apps():
            return list(web_client.web_apps.list())

        try:
            web_apps = asyncio.run(execute_azure_api_call(get_web_apps, "get_web_apps"))
        except Exception as e:
            logger.error(f"Failed to list Web Apps after retries: {e}")
            return artifacts

        for web_app in web_apps:
            if web_app.location != location:
                continue

            artifact = self.transform(
                {"resource": web_app, "location": location, "resource_type": "web-app"}
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def _extract_function_apps(
        self, web_client: Any, location: str
    ) -> List[Dict[str, Any]]:
        """Extract Function Apps"""
        artifacts: List[Dict[str, Any]] = []

        # List all web apps (includes function apps) with retry
        async def get_apps():
            return list(web_client.web_apps.list())

        try:
            function_apps = asyncio.run(
                execute_azure_api_call(get_apps, "get_function_apps")
            )
        except Exception as e:
            logger.error(f"Failed to list Function Apps after retries: {e}")
            return artifacts

        # Function Apps are also returned by web_apps.list() but have kind="functionapp"

        for app in function_apps:
            if app.location != location:
                continue

            # Check if it's a function app
            if hasattr(app, "kind") and app.kind and "functionapp" in app.kind.lower():
                artifact = self.transform(
                    {
                        "resource": app,
                        "location": location,
                        "resource_type": "function-app",
                    }
                )

                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure Web resource to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]
        resource_type = raw_data["resource_type"]

        resource_group = self._get_resource_group(resource.id)
        tags = resource.tags or {}

        if resource_type == "app-service-plan":
            config = {
                "provisioning_state": resource.provisioning_state,
                "status": resource.status,
            }

            # Add SKU
            if resource.sku:
                config["sku"] = {
                    "name": resource.sku.name,
                    "tier": resource.sku.tier,
                    "size": resource.sku.size,
                    "capacity": resource.sku.capacity,
                }

            # Add properties
            if hasattr(resource, "number_of_sites"):
                config["number_of_sites"] = resource.number_of_sites

            if hasattr(resource, "maximum_number_of_workers"):
                config["maximum_number_of_workers"] = resource.maximum_number_of_workers

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:web:app-service-plan",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="web",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        elif resource_type in ["web-app", "function-app"]:
            config = {
                "provisioning_state": resource.provisioning_state,
                "state": resource.state,
                "kind": resource.kind,
            }

            # Add site properties
            if hasattr(resource, "server_farm_id"):
                config["server_farm_id"] = resource.server_farm_id

            if hasattr(resource, "enabled"):
                config["enabled"] = resource.enabled

            if hasattr(resource, "https_only"):
                config["https_only"] = resource.https_only

            if hasattr(resource, "client_cert_enabled"):
                config["client_cert_enabled"] = resource.client_cert_enabled

            # Add site config if available
            if hasattr(resource, "site_config") and resource.site_config:
                site_config = {}
                if hasattr(resource.site_config, "linux_fx_version"):
                    site_config[
                        "linux_fx_version"
                    ] = resource.site_config.linux_fx_version
                if hasattr(resource.site_config, "windows_fx_version"):
                    site_config[
                        "windows_fx_version"
                    ] = resource.site_config.windows_fx_version
                if hasattr(resource.site_config, "net_framework_version"):
                    site_config[
                        "net_framework_version"
                    ] = resource.site_config.net_framework_version
                if hasattr(resource.site_config, "php_version"):
                    site_config["php_version"] = resource.site_config.php_version
                if hasattr(resource.site_config, "python_version"):
                    site_config["python_version"] = resource.site_config.python_version
                if hasattr(resource.site_config, "node_version"):
                    site_config["node_version"] = resource.site_config.node_version

                if site_config:
                    config["site_config"] = site_config

            resource_type_name = (
                "function-app" if resource_type == "function-app" else "web-app"
            )

            return {
                "cloud_provider": "azure",
                "resource_type": f"azure:web:{resource_type_name}",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="web",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        return {}

    def _get_resource_group(self, resource_id: str) -> str:
        """Extract resource group from Azure resource ID"""
        # Azure resource ID format: /subscriptions/{sub}/resourceGroups/{rg}/...
        parts = resource_id.split("/")
        try:
            rg_index = parts.index("resourceGroups")
            return parts[rg_index + 1]
        except (ValueError, IndexError):
            return ""

    def _get_subscription_id(self, resource_id: str) -> str:
        """Extract subscription ID from Azure resource ID"""
        parts = resource_id.split("/")
        try:
            sub_index = parts.index("subscriptions")
            return parts[sub_index + 1]
        except (ValueError, IndexError):
            return ""

    def _serialize_azure_resource(self, resource: Any) -> Dict[str, Any]:
        """Convert Azure SDK model to dictionary"""
        # Azure SDK models have as_dict() method
        if hasattr(resource, "as_dict"):
            return resource.as_dict()
        return {}
