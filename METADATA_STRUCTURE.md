# Cloud-Agnostic Metadata Structure

## Overview

This document describes the new cloud-agnostic metadata structure for resource artifacts in the CSP Scanner. The structure has been redesigned to support multiple cloud providers (AWS, Azure, GCP) while maintaining consistency and extensibility.

## New Structure

### Root Level Fields

```json
{
  "cloud_provider": "aws|azure|gcp",
  "resource_type": "<cloud_provider>:<service>:<type>",
  "metadata": { ... },
  "configuration": { ... },
  "raw": { ... }
}
```

### Metadata Object

The `metadata` object contains cloud-agnostic and cloud-specific identification and organizational fields:

```json
{
  "metadata": {
    "resource_id": "unique-identifier",
    
    // Cloud-specific fields (depending on cloud_provider)
    "service": "service-name",
    
    // AWS-specific
    "region": "us-east-1",
    "account_id": "123456789012",
    
    // Azure-specific
    "location": "eastus",
    "subscription_id": "subscription-uuid",
    "resource_group": "rg-name",
    
    // GCP-specific
    "region": "us-central1",
    "project_id": "project-id",
    
    // Extensible labels (combines tags and custom labels)
    "labels": {
      "Environment": "production",
      "Owner": "team-name",
      "CostCenter": "engineering",
      "custom-key": "custom-value"
    }
  }
}
```

## Field Descriptions

### cloud_provider (required)
- **Type**: String (Literal: "aws" | "azure" | "gcp")
- **Description**: Identifies the cloud provider for this resource
- **Example**: `"aws"`

### resource_type (required)
- **Type**: String
- **Format**: `<cloud_provider>:<service>:<resource_type>`
- **Description**: Fully qualified resource type with cloud provider prefix
- **Examples**: 
  - `"aws:ec2:instance"`
  - `"aws:s3:bucket"`
  - `"azure:compute:virtualmachine"`
  - `"gcp:compute:instance"`

### metadata (required)
A structured object containing resource identification and organizational metadata.

#### metadata.resource_id (required)
- **Type**: String
- **Description**: Unique identifier for the resource within its cloud provider
- **Examples**:
  - AWS: `"i-1234567890abcdef0"`, `"arn:aws:lambda:us-east-1:123456789012:function:my-function"`
  - Azure: `"/subscriptions/.../resourceGroups/.../providers/..."`
  - GCP: `"projects/my-project/zones/us-central1-a/instances/my-instance"`

#### metadata.service (optional)
- **Type**: String
- **Description**: Service name (e.g., "ec2", "s3", "lambda", "compute", "storage")
- **Example**: `"ec2"`

#### metadata.region (AWS/GCP, optional)
- **Type**: String
- **Description**: AWS region or GCP zone/region
- **Examples**: `"us-east-1"`, `"us-central1-a"`

#### metadata.account_id (AWS, optional)
- **Type**: String
- **Description**: AWS account ID (12-digit number)
- **Example**: `"123456789012"`

#### metadata.location (Azure, optional)
- **Type**: String
- **Description**: Azure location/region
- **Example**: `"eastus"`

#### metadata.subscription_id (Azure, optional)
- **Type**: String
- **Description**: Azure subscription ID (UUID)
- **Example**: `"12345678-1234-1234-1234-123456789012"`

#### metadata.resource_group (Azure, optional)
- **Type**: String
- **Description**: Azure resource group name
- **Example**: `"my-resource-group"`

#### metadata.project_id (GCP, optional)
- **Type**: String
- **Description**: GCP project ID
- **Example**: `"my-gcp-project"`

#### metadata.labels (required)
- **Type**: Object (Dictionary)
- **Description**: Extensible key-value pairs for resource labels/tags
- **Purpose**: 
  - Combines cloud provider native tags with custom labels
  - Provides a unified way to query and filter resources
  - Supports custom organizational metadata
- **Example**:
  ```json
  {
    "Environment": "production",
    "Application": "web-api",
    "Owner": "platform-team",
    "CostCenter": "engineering",
    "Compliance": "pci-dss",
    "custom-label": "custom-value"
  }
  ```

### configuration (required)
- **Type**: Object
- **Description**: Cloud-specific configuration details for the resource
- **Note**: Structure varies by resource type and cloud provider
- **Example**:
  ```json
  {
    "instance_type": "t3.medium",
    "state": "running",
    "vpc_id": "vpc-12345678",
    "security_groups": ["sg-12345678"]
  }
  ```

### raw (optional)
- **Type**: Object
- **Description**: Raw API response from the cloud provider
- **Purpose**: Provides complete resource details for comprehensive scanning

## Migration from Old Format

### Old Format
```json
{
  "resource_id": "i-1234567890abcdef0",
  "resource_type": "ec2:instance",
  "service": "ec2",
  "region": "us-east-1",
  "account_id": "123456789012",
  "configuration": {
    "instance_type": "t3.medium",
    "tags": {
      "Environment": "production"
    }
  },
  "raw": { ... }
}
```

### New Format
```json
{
  "cloud_provider": "aws",
  "resource_type": "aws:ec2:instance",
  "metadata": {
    "resource_id": "i-1234567890abcdef0",
    "service": "ec2",
    "region": "us-east-1",
    "account_id": "123456789012",
    "labels": {
      "Environment": "production"
    }
  },
  "configuration": {
    "instance_type": "t3.medium"
  },
  "raw": { ... }
}
```

## Benefits

1. **Cloud Agnostic**: Supports multiple cloud providers with a consistent structure
2. **Extensible**: Labels object allows custom metadata without schema changes
3. **Organized**: Clear separation between identification (metadata) and configuration
4. **Queryable**: Standardized labels enable cross-cloud resource queries
5. **Backward Compatible**: Migration script handles conversion from old format

## Code Usage

### In Extractors

```python
from app.extractors.base import BaseExtractor

class MyExtractor(BaseExtractor):
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        resource = raw_data["resource"]
        region = raw_data["region"]
        tags = {tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])}
        
        return {
            "cloud_provider": "aws",
            "resource_type": "aws:myservice:mytype",
            "metadata": self.create_metadata_object(
                resource_id=resource["Id"],
                service="myservice",
                region=region,
                account_id=resource.get("OwnerId"),
                tags=tags,
                labels={"CustomLabel": "value"}  # Optional custom labels
            ),
            "configuration": {
                # Resource-specific configuration
            },
            "raw": resource,
        }
```

### Validation

The base extractor validates the new structure:
- Requires: `cloud_provider`, `resource_type`, `metadata`, `configuration`
- Metadata must contain: `resource_id`
- Labels object is always present (empty dict if no labels)

## Examples by Cloud Provider

### AWS EC2 Instance
```json
{
  "cloud_provider": "aws",
  "resource_type": "aws:ec2:instance",
  "metadata": {
    "resource_id": "i-1234567890abcdef0",
    "service": "ec2",
    "region": "us-east-1",
    "account_id": "123456789012",
    "labels": {
      "Name": "web-server-01",
      "Environment": "production"
    }
  },
  "configuration": { ... },
  "raw": { ... }
}
```

### Azure Virtual Machine
```json
{
  "cloud_provider": "azure",
  "resource_type": "azure:compute:virtualmachine",
  "metadata": {
    "resource_id": "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm-name}",
    "service": "compute",
    "location": "eastus",
    "subscription_id": "12345678-1234-1234-1234-123456789012",
    "resource_group": "my-resource-group",
    "labels": {
      "Environment": "production"
    }
  },
  "configuration": { ... },
  "raw": { ... }
}
```

### GCP Compute Instance
```json
{
  "cloud_provider": "gcp",
  "resource_type": "gcp:compute:instance",
  "metadata": {
    "resource_id": "projects/my-project/zones/us-central1-a/instances/my-instance",
    "service": "compute",
    "region": "us-central1-a",
    "project_id": "my-project",
    "labels": {
      "environment": "production"
    }
  },
  "configuration": { ... },
  "raw": { ... }
}
```

## Migration Script

A migration script (`migrate_metadata.py`) is provided to convert existing JSON files from the old format to the new format. It:
- Processes all JSON files in `sample_extractions/` and `file_collector/`
- Automatically detects already-migrated files
- Extracts tags from configuration and moves them to `metadata.labels`
- Adds `cloud_provider` field and updates `resource_type` prefix
- Creates the new `metadata` object structure

Run the migration:
```bash
python3 migrate_metadata.py
```
