# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional, List
from functools import lru_cache
import yaml  # type: ignore[import-untyped]
import os


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
    scanner_endpoint_url: str = "http://localhost:8000"
    scanner_api_key: Optional[str] = None
    transport_timeout_seconds: int = 30
    transport_max_retries: int = 3
    transport_type: str = "http"  # Options: http, filesystem, null
    filesystem_base_dir: str = "./file_collector"
    filesystem_create_dir: bool = True

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

    # Extractor Configuration
    extractor_config_path: str = "config/extractors.yaml"

    class Config:
        env_file = ".env"
        case_sensitive = False

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
        """Get transport configuration based on transport type"""
        if self.transport_type == "filesystem":
            return {
                "base_dir": self.filesystem_base_dir,
                "create_dir": self.filesystem_create_dir,
            }
        elif self.transport_type == "null":
            return {}
        else:  # Default to http
            return {
                "scanner_endpoint_url": self.scanner_endpoint_url,
                "api_key": self.scanner_api_key,
                "timeout_seconds": self.transport_timeout_seconds,
                "max_retries": self.transport_max_retries,
                "headers": {
                    "Content-Type": "application/json",
                    "User-Agent": f"{self.app_name}/1.0",
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
    2. .env file
    3. YAML config file if CONFIG_FILE env var is set
    """
    # Check if a config file is specified
    config_file = os.getenv("CONFIG_FILE")

    if config_file and os.path.exists(config_file):
        # Load settings from YAML file
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f) or {}

        # Create Settings with YAML data as defaults
        # Environment variables will still override these
        return Settings(**config_data)

    return Settings()
