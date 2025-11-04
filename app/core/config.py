# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict, Any, Optional, List
from functools import lru_cache
import yaml  # type: ignore[import-untyped]
import os
from app.models.database import get_db_manager


class Settings(BaseSettings):
    # Application
    app_name: str = "Cloud Artifact Extractor"
    environment: str = "development"
    debug: bool = False

    # Multi-Cloud Configuration
    enabled_providers: List[str] = ["aws"]  # Options: ["aws", "azure", "gcp"]

    # AWS Configuration (multi-account)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_accounts: Optional[List[Dict[str, Any]]] = None
    # Legacy single-account fields
    aws_account_id: Optional[str] = None
    aws_default_region: str = "us-east-1"

    @property
    def aws_accounts_list(self) -> List[Dict[str, Any]]:
        """
        Returns a list of AWS accounts and regions from config.
        Example: [{"account_id": ..., "regions": [...]}, ...]
        """
        if self.aws_accounts:
            return self.aws_accounts
        # Fallback for legacy config
        account_id = getattr(self, "aws_account_id", None)
        region = getattr(self, "aws_default_region", None)
        if (account_id and region) or (region and region != "us-east-1"):
            return [{"account_id": account_id or "default", "regions": [region]}]
        return []

    # Azure Configuration (multi-subscription)
    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_accounts: Optional[List[Dict[str, Any]]] = None
    # Legacy single-subscription field
    azure_default_location: str = "eastus"

    @property
    def azure_accounts_list(self) -> List[Dict[str, Any]]:
        """
        Returns a list of Azure subscriptions and locations from config.
        Example: [{"subscription_id": ..., "locations": [...]}, ...]
        """
        if self.azure_accounts:
            return self.azure_accounts
        # Fallback for legacy config
        subscription_id = getattr(self, "azure_subscription_id", None)
        location = getattr(self, "azure_default_location", None)
        if (subscription_id and location) or (location and location != "eastus"):
            return [
                {
                    "subscription_id": subscription_id or "default",
                    "locations": [location],
                }
            ]
        return []

    # GCP Configuration (multi-project)
    gcp_projects: Optional[List[Dict[str, Any]]] = None
    gcp_credentials_path: Optional[str] = None
    # Legacy single-project fields
    gcp_project_id: Optional[str] = None
    gcp_default_region: str = "us-central1"

    @property
    def gcp_projects_list(self) -> List[Dict[str, Any]]:
        """
        Returns a list of GCP projects and regions from config.
        Example: [{"project_id": ..., "regions": [...]}, ...]
        """
        if self.gcp_projects:
            return self.gcp_projects
        # Fallback for legacy config
        project_id = getattr(self, "gcp_project_id", None)
        region = getattr(self, "gcp_default_region", None)
        if (project_id and region) or (region and region != "us-central1"):
            return [{"project_id": project_id or "default", "regions": [region]}]
        return []

    # Transport Configuration
    transport: Optional[dict] = None
    http_endpoint_url: str = "http://localhost:8000"
    scanner_api_key: Optional[str] = None
    transport_timeout_seconds: int = 30
    transport_max_retries: int = 3
    transport_type: str = "http"  # Options: http, filesystem, null
    filesystem_base_dir: str = "./file_collector"
    filesystem_create_dir: bool = True
    allow_insecure_ssl: bool = False  # Allow insecure HTTPS connections (not recommended for production)

    # Orchestration Configuration
    max_concurrent_extractors: int = 10
    batch_size: int = 100
    batch_delay_seconds: float = 0.1

    # Security Configuration
    api_key_enabled: bool = False
    api_key: Optional[str] = None

    # Rate Limiting
    rate_limiting_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 3600

    # Database Configuration
    database_host: str = Field(default="localhost")
    database_port: int = Field(default=5432)
    database_name: str = Field(default="csp_scanner")
    database_user: Optional[str] = Field(default=None)
    database_password: Optional[str] = Field(default=None)
    database_enabled: bool = Field(default=False)

    @property
    def database_url(self) -> str:
        """Construct database URL from individual components."""
        if self.database_user and self.database_password:
            return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"
        else:
            return f"postgresql://{self.database_host}:{self.database_port}/{self.database_name}"

    # Extractor Configuration
    extractor_config_path: str = "config/extractors.yaml"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        env_prefix="CSP_SCANNER_",
        # If you previously used 'schema_extra', replace with 'json_schema_extra' for Pydantic v2
        # json_schema_extra={}
    )

    @property
    def is_aws_enabled(self) -> bool:
        """Check if AWS provider is enabled"""
        return "aws" in self.enabled_providers

    @property
    def is_azure_enabled(self) -> bool:
        """Check if Azure provider is enabled"""
        return "azure" in self.enabled_providers

    @property
    def is_gcp_enabled(self) -> bool:
        """Check if GCP provider is enabled"""
        return "gcp" in self.enabled_providers

    @property
    def transport_config(self) -> Dict[str, Any]:
        """Get transport configuration based on transport node"""
        if hasattr(self, "transport") and isinstance(self.transport, dict):
            config = self.transport.copy()
            config["type"] = self.transport.get("type")
            return config
        # Legacy fallback
        if hasattr(self, "transport_type") and self.transport_type == "filesystem":
            return {
                "type": "filesystem",
                "base_dir": self.filesystem_base_dir,
                "create_dir": self.filesystem_create_dir,
            }
        elif hasattr(self, "transport_type") and self.transport_type == "null":
            return {"type": "null"}
        else:
            return {
                "type": "http",
                "http_endpoint_url": getattr(self, "http_endpoint_url", None),
                "api_key": getattr(self, "scanner_api_key", None),
                "timeout_seconds": getattr(self, "transport_timeout_seconds", 30),
                "max_retries": getattr(self, "transport_max_retries", 3),
                "allow_insecure_ssl": getattr(self, "allow_insecure_ssl", False),
                "headers": {
                    "Content-Type": "application/json",
                    "User-Agent": f"{getattr(self, 'app_name', 'App')}/1.0",
                },
            }

    @property
    def orchestrator_config(self) -> Dict[str, Any]:
        return {
            "max_workers": self.max_concurrent_extractors,
            "batch_delay_seconds": self.batch_delay_seconds,
        }

    @property
    def extractors(self) -> Dict[str, Any]:
        """Load extractor-specific configuration"""
        if os.path.exists(self.extractor_config_path):
            with open(self.extractor_config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.

    Loads settings from:
    1. Environment variables (highest priority)
    2. Database (if enabled)
    3. YAML config file if CONFIG_FILE env var is set
    4. .env file (lowest priority, handled by pydantic-settings)
    """
    config_data = {}

    # Load from database if enabled
    db_config = _load_config_from_database()
    if db_config:
        config_data.update(db_config)

    # Check if a config file is specified
    config_file = os.getenv("CONFIG_FILE")

    if config_file and os.path.exists(config_file):
        # Load settings from YAML file
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f) or {}
        # File config has lower priority than DB, so update (don't overwrite DB values)
        for key, value in file_config.items():
            if key not in config_data:
                config_data[key] = value

    # Create Settings with merged config data as defaults
    # Environment variables will still override these
    return Settings(**config_data)


def _load_config_from_database() -> Dict[str, Any]:
    """Load configuration from database."""
    try:
        # Create a temporary settings instance to check DB config
        temp_settings = Settings()
        if not temp_settings.database_enabled:
            return {}

        db_manager = get_db_manager()
        # Get all config entries from database
        all_config = db_manager.get_all_config()
        return all_config
    except Exception as e:
        # If database loading fails, log and continue without DB config
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load config from database: {e}")
        return {}
