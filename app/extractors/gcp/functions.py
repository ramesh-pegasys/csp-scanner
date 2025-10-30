from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPFunctionsExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="functions",
            version="1.0.0",
            description="Extracts GCP Cloud Functions",
            resource_types=["gcp:functions:function"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Cloud Functions API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError(
                    "Project ID is required for Cloud Functions operations"
                )

            api_service = API_SERVICE_MAP["functions"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Cloud Functions API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import functions_v2

            client = functions_v2.FunctionServiceClient()

            # List functions in all regions if no specific region is provided
            locations = [region] if region else ["-"]

            for location in locations:
                parent = f"projects/{project_id}/locations/{location}"
                for function in client.list_functions(parent=parent):
                    raw_data = {
                        "name": function.name,
                        "description": getattr(function, "description", ""),
                        "state": function.state.name if function.state else "UNKNOWN",
                        "runtime": getattr(function.build_config, "runtime", ""),
                        "entry_point": getattr(
                            function.build_config, "entry_point", ""
                        ),
                        "environment": getattr(
                            function.service_config, "environment", ""
                        ),
                        "max_instances": getattr(
                            function.service_config, "max_instance_count", 0
                        ),
                        "min_instances": getattr(
                            function.service_config, "min_instance_count", 0
                        ),
                        "available_memory": getattr(
                            function.service_config, "available_memory", ""
                        ),
                        "timeout": getattr(
                            function.service_config, "timeout_seconds", 0
                        ),
                        "vpc_connector": getattr(
                            function.service_config, "vpc_connector", ""
                        ),
                        "location": function.name.split("/")[3],
                    }
                    resources.append(self.transform(raw_data))

        except Exception as e:
            logger.error(f"Error extracting Cloud Functions: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud Functions API response to standardized format"""
        name = raw_data["name"].split("/")[-1]
        return {
            "service": "functions",
            "resource_type": "gcp:functions:function",
            "name": name,
            "id": raw_data["name"],
            "region": raw_data["location"],
            "project_id": getattr(self.session, "project_id", "unknown"),
            "description": raw_data["description"],
            "state": raw_data["state"],
            "runtime": raw_data["runtime"],
            "entry_point": raw_data["entry_point"],
            "environment": raw_data["environment"],
            "max_instances": raw_data["max_instances"],
            "min_instances": raw_data["min_instances"],
            "available_memory": raw_data["available_memory"],
            "timeout": raw_data["timeout"],
            "vpc_connector": raw_data["vpc_connector"],
        }
