#!/usr/bin/env python3
"""
Example: Dynamic Provider Management via Config API

This script demonstrates how to enable/disable cloud providers
dynamically using the configuration API.
"""

import requests
import json
import time
from typing import List, Dict, Any


class CSPScannerClient:
    """Client for CSP Scanner API"""

    def __init__(self, base_url: str = "https://localhost:8443", token: str = ""):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        # Disable SSL verification for self-signed certs
        self.verify_ssl = False

    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        response = requests.get(
            f"{self.base_url}/api/v1/config/",
            headers=self.headers,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    def update_config(
        self, config: Dict[str, Any], description: str = ""
    ) -> Dict[str, Any]:
        """Update configuration (full replace)"""
        payload = {"config": config, "description": description}
        response = requests.put(
            f"{self.base_url}/api/v1/config/",
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    def patch_config(
        self, config: Dict[str, Any], description: str = ""
    ) -> Dict[str, Any]:
        """Update configuration (partial merge)"""
        payload = {"config": config, "description": description}
        response = requests.patch(
            f"{self.base_url}/api/v1/config/",
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()

    def get_providers(self) -> List[str]:
        """Get list of enabled providers"""
        response = requests.get(
            f"{self.base_url}/extraction/providers",
            headers=self.headers,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()["providers"]

    def get_services(self, provider: str | None = None) -> Dict[str, Any]:
        """Get list of available services"""
        url = f"{self.base_url}/extraction/services"
        if provider:
            url += f"?provider={provider}"

        response = requests.get(url, headers=self.headers, verify=self.verify_ssl)
        response.raise_for_status()
        return response.json()


def example_enable_aws(client: CSPScannerClient):
    """Example: Enable AWS provider"""
    print("\n=== Example 1: Enable AWS Provider ===")

    config = {
        "enabled_providers": ["aws"],
        "aws_access_key_id": "YOUR_ACCESS_KEY",
        "aws_secret_access_key": "YOUR_SECRET_KEY",
        "aws_accounts": [
            {"account_id": "123456789012", "regions": ["us-east-1", "us-west-2"]}
        ],
    }

    result = client.patch_config(config, "Enable AWS provider")
    print(f"✓ Configuration updated: version {result['version']}")
    print(f"  Message: {result['message']}")

    # Wait a moment for registration
    time.sleep(1)

    # Verify providers
    providers = client.get_providers()
    print(f"✓ Active providers: {providers}")

    # Check AWS services
    services = client.get_services(provider="aws")
    aws_services = services["services_by_provider"].get("aws", [])
    print(f"✓ AWS services available: {len(aws_services)}")
    for service in aws_services[:3]:
        print(f"  - {service['service']}: {service['description']}")


def example_enable_multiple_providers(client: CSPScannerClient):
    """Example: Enable multiple providers"""
    print("\n=== Example 2: Enable Multiple Providers ===")

    config = {
        "enabled_providers": ["aws", "azure", "gcp"],
        # AWS credentials
        "aws_access_key_id": "YOUR_AWS_KEY",
        "aws_secret_access_key": "YOUR_AWS_SECRET",
        "aws_accounts": [{"account_id": "123456789012", "regions": ["us-east-1"]}],
        # Azure credentials
        "azure_tenant_id": "YOUR_TENANT_ID",
        "azure_client_id": "YOUR_CLIENT_ID",
        "azure_client_secret": "YOUR_CLIENT_SECRET",
        "azure_accounts": [{"subscription_id": "YOUR_SUB_ID", "locations": ["eastus"]}],
        # GCP credentials
        "gcp_credentials_path": "/path/to/credentials.json",
        "gcp_projects": [{"project_id": "your-project", "regions": ["us-central1"]}],
    }

    result = client.patch_config(config, "Enable all providers")
    print(f"✓ Configuration updated: version {result['version']}")

    # Wait for registration
    time.sleep(2)

    # Verify all providers
    providers = client.get_providers()
    print(f"✓ Active providers: {providers}")

    # Show service counts per provider
    for provider in providers:
        services = client.get_services(provider=provider)
        count = services["total_services"]
        print(f"  - {provider}: {count} services")


def example_disable_provider(client: CSPScannerClient):
    """Example: Disable a provider"""
    print("\n=== Example 3: Disable a Provider ===")

    # Get current providers
    current_providers = client.get_providers()
    print(f"Current providers: {current_providers}")

    if "azure" in current_providers:
        # Remove Azure from the list
        new_providers = [p for p in current_providers if p != "azure"]

        config = {"enabled_providers": new_providers}

        result = client.patch_config(config, "Disable Azure provider")
        print(f"✓ Configuration updated: version {result['version']}")

        # Wait for unregistration
        time.sleep(1)

        # Verify provider removed
        providers = client.get_providers()
        print(f"✓ Active providers after disable: {providers}")
        print(f"✓ Azure removed: {'azure' not in providers}")
    else:
        print("Azure is not enabled, skipping disable example")


def example_switch_providers(client: CSPScannerClient):
    """Example: Switch from one provider to another"""
    print("\n=== Example 4: Switch Providers ===")

    # Switch from AWS to Azure
    config = {
        "enabled_providers": ["azure"],
        "azure_tenant_id": "YOUR_TENANT_ID",
        "azure_client_id": "YOUR_CLIENT_ID",
        "azure_client_secret": "YOUR_CLIENT_SECRET",
        "azure_accounts": [{"subscription_id": "YOUR_SUB_ID", "locations": ["eastus"]}],
    }

    result = client.patch_config(config, "Switch to Azure only")
    print(f"✓ Configuration updated: version {result['version']}")

    # Wait for registration/unregistration
    time.sleep(2)

    # Verify only Azure is active
    providers = client.get_providers()
    print(f"✓ Active providers: {providers}")
    print(f"✓ Only Azure: {providers == ['azure']}")


def example_incremental_changes(client: CSPScannerClient):
    """Example: Incrementally add/remove providers"""
    print("\n=== Example 5: Incremental Provider Changes ===")

    # Start with AWS only
    print("Step 1: Enable AWS only")
    config = {"enabled_providers": ["aws"]}
    client.patch_config(config, "Start with AWS")
    time.sleep(1)
    print(f"  Providers: {client.get_providers()}")

    # Add Azure
    print("Step 2: Add Azure")
    config = {"enabled_providers": ["aws", "azure"]}
    client.patch_config(config, "Add Azure")
    time.sleep(1)
    print(f"  Providers: {client.get_providers()}")

    # Add GCP
    print("Step 3: Add GCP")
    config = {"enabled_providers": ["aws", "azure", "gcp"]}
    client.patch_config(config, "Add GCP")
    time.sleep(1)
    print(f"  Providers: {client.get_providers()}")

    # Remove AWS
    print("Step 4: Remove AWS")
    config = {"enabled_providers": ["azure", "gcp"]}
    client.patch_config(config, "Remove AWS")
    time.sleep(1)
    print(f"  Providers: {client.get_providers()}")


def main():
    """Run examples"""
    # Initialize client
    # Note: You need to obtain a JWT token first
    token = "YOUR_JWT_TOKEN_HERE"
    client = CSPScannerClient(token=token)

    print("Dynamic Provider Management Examples")
    print("=" * 50)

    try:
        # Show current state
        print("\n=== Current State ===")
        current_config = client.get_current_config()
        providers = current_config["config"].get("enabled_providers", [])
        print(f"Enabled providers: {providers}")

        # Run examples (uncomment the ones you want to try)

        # example_enable_aws(client)
        # example_enable_multiple_providers(client)
        # example_disable_provider(client)
        # example_switch_providers(client)
        # example_incremental_changes(client)

        print("\n" + "=" * 50)
        print("✓ Examples completed successfully")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  Response: {e.response.text}")


if __name__ == "__main__":
    # Suppress SSL warnings for self-signed certs
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main()
