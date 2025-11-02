from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPDNSExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="dns",
            version="1.0.0",
            description="Extracts GCP Cloud DNS zones and records",
            resource_types=["gcp:dns:managedzone", "gcp:dns:recordset"],
            cloud_provider="gcp",
            supports_regions=False,  # DNS is a global service
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if DNS API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Cloud DNS operations")

            api_service = API_SERVICE_MAP["dns"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP DNS API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from googleapiclient.discovery import build

            credentials = getattr(self.session, "credentials", None)
            service = build("dns", "v1", credentials=credentials, cache_discovery=False)

            # List DNS managed zones
            try:
                request = service.managedZones().list(project=project_id)
                response = request.execute()

                for zone in response.get("managedZones", []):
                    zone_data = {
                        "name": zone.get("name"),
                        "type": "managedzone",
                        "dns_name": zone.get("dnsName"),
                        "description": zone.get("description", ""),
                        "name_servers": zone.get("nameServers", []),
                        "visibility": zone.get("visibility", "public"),
                        "dnssec_config": zone.get("dnssecConfig"),
                        "labels": zone.get("labels", {}),
                    }
                    resources.append(self.transform(zone_data))

                    # List record sets in each zone
                    try:
                        rrsets_request = service.resourceRecordSets().list(
                            project=project_id, managedZone=zone.get("name")
                        )
                        rrsets_response = rrsets_request.execute()

                        for record_set in rrsets_response.get("rrsets", []):
                            record_data = {
                                "name": record_set.get("name"),
                                "type": "recordset",
                                "zone_name": zone.get("name"),
                                "record_type": record_set.get("type"),
                                "ttl": record_set.get("ttl"),
                                "rrdatas": record_set.get("rrdatas", []),
                            }
                            resources.append(self.transform(record_data))
                    except Exception as e:
                        logger.warning(
                            f"Error listing record sets for zone {zone.get('name')}: {e}"
                        )

            except Exception as e:
                logger.warning(f"Error listing DNS zones: {e}")

        except Exception as e:
            logger.error(f"Error extracting Cloud DNS resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Cloud DNS API response to standardized format"""
        resource_type_map = {
            "managedzone": "gcp:dns:managedzone",
            "recordset": "gcp:dns:recordset",
        }

        base = {
            "service": "dns",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"],
            "id": raw_data["name"],
            "region": "global",  # DNS is a global service
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "managedzone":
            base.update(
                {
                    "dns_name": raw_data["dns_name"],
                    "description": raw_data["description"],
                    "name_servers": raw_data["name_servers"],
                    "visibility": raw_data["visibility"],
                    "dnssec_config": raw_data["dnssec_config"],
                    "labels": raw_data["labels"],
                }
            )
        else:  # recordset
            base.update(
                {
                    "zone_name": raw_data["zone_name"],
                    "record_type": raw_data["record_type"],
                    "ttl": raw_data["ttl"],
                    "rrdatas": raw_data["rrdatas"],
                }
            )

        return base
