# app/extractors/azure/sql.py
"""
Azure SQL Database extractor for SQL Servers and Databases.
"""

from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.extractors.azure.utils import execute_azure_api_call
import logging

logger = logging.getLogger(__name__)


class AzureSQLExtractor(BaseExtractor):
    """Extractor for Azure SQL Database resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="sql",
            version="1.0.0",
            description="Extracts Azure SQL Servers and Databases",
            resource_types=["sql-server", "sql-database"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure SQL resources"""
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
                logger.error(f"Azure SQL extraction error: {result}")
            elif isinstance(result, list):
                artifacts.extend(result)

        return artifacts

    def _extract_location(
        self, location: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract SQL resources from a specific location"""
        artifacts = []

        try:
            sql_client = self.session.get_client("sql")

            # Extract SQL Servers
            try:
                servers = self._extract_sql_servers(sql_client, location)
                artifacts.extend(servers)
            except Exception as e:
                logger.error(f"Failed to extract SQL Servers in {location}: {e}")

            # Extract SQL Databases (from all servers)
            try:
                databases = self._extract_sql_databases(sql_client)
                artifacts.extend(databases)
            except Exception as e:
                logger.error(f"Failed to extract SQL Databases: {e}")

        except Exception as e:
            logger.error(f"Failed to get SQL client for {location}: {e}")

        return artifacts

    def _extract_sql_servers(
        self, sql_client: Any, location: str
    ) -> List[Dict[str, Any]]:
        """Extract SQL Servers"""
        artifacts: List[Dict[str, Any]] = []

        # Get servers list with retry
        async def get_servers():
            return list(sql_client.servers.list())

        try:
            servers = asyncio.run(
                execute_azure_api_call(get_servers, "get_sql_servers")
            )
        except Exception as e:
            logger.error(f"Failed to list SQL servers in {location} after retries: {e}")
            return artifacts

        for server in servers:
            if server.location != location:
                continue

            artifact = self.transform(
                {
                    "resource": server,
                    "location": location,
                    "resource_type": "sql-server",
                }
            )

            if self.validate(artifact):
                artifacts.append(artifact)

        return artifacts

    def _extract_sql_databases(self, sql_client: Any) -> List[Dict[str, Any]]:
        """Extract SQL Databases from all servers"""
        artifacts: List[Dict[str, Any]] = []

        # Get servers list with retry
        async def get_servers():
            return list(sql_client.servers.list())

        try:
            servers = asyncio.run(
                execute_azure_api_call(get_servers, "get_sql_servers")
            )
        except Exception as e:
            logger.error(f"Failed to list SQL servers after retries: {e}")
            return artifacts

        for server in servers:
            resource_group = self._get_resource_group(server.id)
            server_name = server.name

            try:
                # Get databases for this server with retry
                async def get_databases():
                    return list(
                        sql_client.databases.list_by_server(
                            resource_group_name=resource_group, server_name=server_name
                        )
                    )

                databases = asyncio.run(
                    execute_azure_api_call(
                        get_databases, f"get_databases_for_server_{server_name}"
                    )
                )

                for database in databases:
                    # Skip system databases
                    if database.name in ["master", "model", "msdb", "tempdb"]:
                        continue

                    artifact = self.transform(
                        {
                            "resource": database,
                            "location": server.location,
                            "resource_type": "sql-database",
                            "server_name": server_name,
                            "server_id": server.id,
                        }
                    )

                    if self.validate(artifact):
                        artifacts.append(artifact)

            except Exception as e:
                logger.error(
                    f"Failed to extract databases for server {server_name}: {e}"
                )

        return artifacts

    def _get_firewall_rules_with_retry(
        self, sql_client: Any, resource_group: str, server_name: str
    ) -> List[Any]:
        """Get firewall rules for a server with retry logic for throttling."""

        async def get_firewall_rules():
            return list(
                sql_client.firewall_rules.list_by_server(
                    resource_group_name=resource_group, server_name=server_name
                )
            )

        try:
            return asyncio.run(
                execute_azure_api_call(
                    get_firewall_rules,
                    f"get_firewall_rules_{server_name}",
                    max_attempts=3,
                )
            )
        except Exception as e:
            logger.warning(
                f"Failed to get firewall rules for server {server_name} after retries: {e}"
            )
            return []

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure SQL resource to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]
        resource_type = raw_data["resource_type"]

        resource_group = self._get_resource_group(resource.id)
        tags = resource.tags or {}

        if resource_type == "sql-server":
            config = {
                "provisioning_state": resource.provisioning_state,
                "administrator_login": resource.administrator_login,
                "version": resource.version,
            }

            # Add security settings
            if hasattr(resource, "public_network_access"):
                config["public_network_access"] = resource.public_network_access

            if hasattr(resource, "minimal_tls_version"):
                config["minimal_tls_version"] = resource.minimal_tls_version

            # Add firewall rules summary
            try:
                sql_client = self.session.get_client("sql")
                firewall_rules = self._get_firewall_rules_with_retry(
                    sql_client, resource_group, resource.name
                )
                config["firewall_rules_count"] = len(firewall_rules)
                # Include basic firewall info
                config["firewall_rules"] = [
                    {
                        "name": rule.name,
                        "start_ip_address": rule.start_ip_address,
                        "end_ip_address": rule.end_ip_address,
                    }
                    for rule in firewall_rules[:10]  # Limit to first 10
                ]
            except Exception as e:
                logger.warning(
                    f"Failed to get firewall rules for server {resource.name}: {e}"
                )
                config["firewall_rules_count"] = 0

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:sql:sql-server",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="sql",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }

        elif resource_type == "sql-database":
            config = {
                "server_name": raw_data.get("server_name"),
                "collation": resource.collation,
                "max_size_bytes": resource.max_size_bytes,
                "status": resource.status,
                "database_id": resource.database_id,
            }

            # Add SKU information
            if hasattr(resource, "sku") and resource.sku:
                config["sku"] = {
                    "name": (
                        resource.sku.name if hasattr(resource.sku, "name") else None
                    ),
                    "tier": (
                        resource.sku.tier if hasattr(resource.sku, "tier") else None
                    ),
                    "capacity": (
                        resource.sku.capacity
                        if hasattr(resource.sku, "capacity")
                        else None
                    ),
                }

            # Add security settings
            if hasattr(resource, "default_secondary_location"):
                config[
                    "default_secondary_location"
                ] = resource.default_secondary_location

            if hasattr(resource, "zone_redundant"):
                config["zone_redundant"] = resource.zone_redundant

            return {
                "cloud_provider": "azure",
                "resource_type": "azure:sql:sql-database",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="sql",
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
