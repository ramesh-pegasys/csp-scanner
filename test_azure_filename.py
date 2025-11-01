#!/usr/bin/env python3
"""
Test script to verify Azure artifact filename generation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.transport.filesystem import FilesystemTransport


def test_azure_filename_generation():
    """Test filename generation for Azure artifacts."""

    # Create a mock filesystem transport
    transport = FilesystemTransport({"base_dir": "/tmp/test"})

    # Sample Azure storage account artifact
    azure_artifact = {
        "cloud_provider": "azure",
        "resource_type": "azure:storage:account",
        "metadata": {
            "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/my-rg/providers/Microsoft.Storage/storageAccounts/mystorageaccount",
            "service": "storage",
            "location": "eastus",
            "subscription_id": "12345678-1234-1234-1234-123456789012",
            "resource_group": "my-rg",
            "labels": {},
        },
        "configuration": {"kind": "StorageV2", "provisioning_state": "Succeeded"},
        "raw": {},
    }

    # Generate filename
    filename = transport._generate_filename(azure_artifact)
    print(f"Generated filename: {filename}")

    # Check that it contains the correct components
    assert "storage" in filename, "Service should be 'storage'"
    assert "azure_storage_account" in filename, "Resource type should be normalized"
    assert (
        "mystorageaccount" in filename
    ), "Resource name should be extracted from resource_id"
    assert (
        not "unknown" in filename.split("_")[:3]
    ), "Should not have unknown in service/resource_type/resource_name"

    print("✅ Azure filename generation test passed!")


if __name__ == "__main__":
    test_azure_filename_generation()
