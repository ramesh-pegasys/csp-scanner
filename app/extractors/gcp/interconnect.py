from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPInterconnectExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="interconnect",
            version="1.0.0",
            description="Extracts GCP Interconnect attachments and locations",
            resource_types=["gcp:interconnect:attachment", "gcp:interconnect:location"],
            cloud_provider="gcp",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Compute API is enabled (Interconnect uses Compute API)
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Interconnect operations")

            api_service = API_SERVICE_MAP["compute"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Compute API is not enabled for project {project_id}. Skipping Interconnect extraction."
                )
                return []

            from google.cloud import compute_v1

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Interconnect operations")

            # Get Interconnect Locations
            locations_client = compute_v1.InterconnectLocationsClient()
            for location in locations_client.list(project=project_id):
                raw_data = {
                    "name": location.name,
                    "id": location.id,
                    "type": "location",
                    "description": getattr(location, "description", ""),
                    "facility_provider": getattr(
                        location, "facility_provider_facility_id", ""
                    ),
                    "facility_address": getattr(location, "address", ""),
                    "availability_zone": getattr(location, "availability_zone", ""),
                }
                resources.append(self.transform(raw_data))

            # Get Interconnect Attachments
            attachments_client = compute_v1.InterconnectAttachmentsClient()
            request = compute_v1.AggregatedListInterconnectAttachmentsRequest(
                project=project_id
            )
            for scope, attachments_list in attachments_client.aggregated_list(
                request=request
            ):
                if not attachments_list.interconnect_attachments:
                    continue
                for attachment in attachments_list.interconnect_attachments:
                    raw_data = {
                        "name": attachment.name,
                        "id": attachment.id,
                        "type": "attachment",
                        "description": getattr(attachment, "description", ""),
                        "region": scope.split("/")[-1],
                        "interconnect": getattr(attachment, "interconnect", ""),
                        "router": getattr(attachment, "router", ""),
                        "attachment_type": getattr(attachment, "type", ""),
                        "state": getattr(attachment, "state", ""),
                        "bandwidth": getattr(attachment, "bandwidth", ""),
                    }
                    resources.append(self.transform(raw_data))

        except Exception as e:
            logger.error(f"Error extracting Interconnect resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Interconnect API response to standardized format"""
        resource_type_map = {
            "location": "gcp:interconnect:location",
            "attachment": "gcp:interconnect:attachment",
        }

        base = {
            "service": "interconnect",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"],
            "id": str(raw_data["id"]),
            "region": raw_data.get("region", "global"),
            "project_id": getattr(self.session, "project_id", "unknown"),
            "description": raw_data.get("description", ""),
        }

        if raw_data["type"] == "location":
            base.update(
                {
                    "facility_provider": raw_data["facility_provider"],
                    "facility_address": raw_data["facility_address"],
                    "availability_zone": raw_data["availability_zone"],
                }
            )
        else:  # attachment
            base.update(
                {
                    "interconnect": raw_data["interconnect"],
                    "router": raw_data["router"],
                    "type": raw_data["attachment_type"],
                    "state": raw_data["state"],
                    "bandwidth": raw_data["bandwidth"],
                }
            )

        return base
