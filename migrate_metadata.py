#!/usr/bin/env python3
"""
Script to migrate JSON files from old metadata format to new cloud-agnostic format.

Old format:
{
    "resource_id": "...",
    "resource_type": "service:type",
    "service": "...",
    "region": "...",
    "account_id": "...",
    "configuration": {...},
    "raw": {...}
}

New format:
{
    "cloud_provider": "aws",
    "resource_type": "aws:service:type",
    "metadata": {
        "resource_id": "...",
        "service": "...",
        "region": "...",
        "account_id": "...",
        "labels": {}
    },
    "configuration": {...},
    "raw": {...}
}
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


def migrate_artifact(old_artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate a single artifact from old to new format."""
    
    # Extract old metadata fields
    resource_id = old_artifact.get("resource_id")
    resource_type = old_artifact.get("resource_type", "")
    service = old_artifact.get("service")
    region = old_artifact.get("region")
    account_id = old_artifact.get("account_id")
    configuration = old_artifact.get("configuration", {})
    raw = old_artifact.get("raw", {})
    
    # Extract tags from configuration if present
    tags = configuration.get("tags", {})
    
    # Build new metadata object
    metadata: Dict[str, Any] = {
        "resource_id": resource_id,
    }
    
    if service:
        metadata["service"] = service
    if region:
        metadata["region"] = region
    if account_id:
        metadata["account_id"] = account_id
    
    # Merge tags into labels
    metadata["labels"] = tags if isinstance(tags, dict) else {}
    
    # Prefix resource_type with cloud provider
    if not resource_type.startswith("aws:"):
        new_resource_type = f"aws:{resource_type}"
    else:
        new_resource_type = resource_type
    
    # Remove tags from configuration since they're now in metadata.labels
    new_configuration = {k: v for k, v in configuration.items() if k != "tags"}
    
    # Build new artifact
    new_artifact = {
        "cloud_provider": "aws",
        "resource_type": new_resource_type,
        "metadata": metadata,
        "configuration": new_configuration,
        "raw": raw,
    }
    
    return new_artifact


def migrate_file(file_path: Path) -> bool:
    """Migrate a single JSON file."""
    try:
        print(f"Migrating {file_path.name}...")
        
        with open(file_path, 'r') as f:
            content = f.read().strip()
        
        # Parse JSON
        old_artifact = json.loads(content)
        
        # Check if already migrated
        if "cloud_provider" in old_artifact and "metadata" in old_artifact:
            print(f"  ✓ Already migrated, skipping")
            return True
        
        # Migrate
        new_artifact = migrate_artifact(old_artifact)
        
        # Write back
        with open(file_path, 'w') as f:
            json.dump(new_artifact, f, indent=2, default=str)
        
        print(f"  ✓ Migrated successfully")
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Main migration function."""
    # Get the script directory
    script_dir = Path(__file__).parent
    
    # Directories to migrate
    directories = [
        script_dir / "sample_extractions",
        script_dir / "file_collector",
    ]
    
    total_files = 0
    migrated_files = 0
    
    for directory in directories:
        if not directory.exists():
            print(f"Directory not found: {directory}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing directory: {directory.name}")
        print(f"{'='*60}\n")
        
        json_files = sorted(directory.glob("*.json"))
        
        for json_file in json_files:
            total_files += 1
            if migrate_file(json_file):
                migrated_files += 1
    
    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"Total files processed: {total_files}")
    print(f"Successfully migrated: {migrated_files}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
