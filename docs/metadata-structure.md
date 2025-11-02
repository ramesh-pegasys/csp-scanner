---
layout: default
title: Metadata Structure
nav_order: 6
---

# Metadata Structure

This document describes the cloud-agnostic metadata structure used by the Cloud Artifact Extractor for consistent resource representation across AWS, Azure, and GCP.

## Overview

All extracted cloud resources follow a standardized metadata structure that enables:

- **Cross-cloud consistency**: Same fields and format across providers
- **Unified querying**: Search and filter resources regardless of provider
- **Extensibility**: Add custom metadata without breaking compatibility
- **Compliance**: Standardized fields for security and compliance tools

## Core Structure

Every extracted resource includes these top-level fields:

```json
{
  "cloud_provider": "aws|azure|gcp",
  "resource_type": "provider:service:resource-type",
  "metadata": {
    // Standardized identification and organizational fields
  },
  "configuration": {
    // Provider-specific configuration details
  },
  "raw": {
    // Complete API response from cloud provider
  }
}
```

## Metadata Object

The `metadata` object contains cloud-agnostic fields for resource identification and organization:

```json
{
  "metadata": {
    "resource_id": "string",           // Required: Unique identifier
    "service": "string",               // Optional: Service name
    "region": "string",                // Optional: Region/location
    "account_id": "string",            // AWS: Account ID
    "subscription_id": "string",       // Azure: Subscription ID
    "project_id": "string",            // GCP: Project ID
    "resource_group": "string",        // Azure: Resource group
    "labels": {                        // Required: Key-value pairs
      "Environment": "production",
      "Owner": "team-name",
      "custom-tag": "value"
    }
  }
}
```

### Field Descriptions

#### resource_id (required)
- **Type**: `string`
- **Description**: Unique identifier for the resource within its cloud provider
- **Examples**:
  - AWS: `"i-1234567890abcdef0"`, `"arn:aws:s3:::my-bucket"`
  - Azure: `"/subscriptions/.../resourceGroups/.../providers/.../instances/my-vm"`
  - GCP: `"projects/my-project/zones/us-central1-a/instances/my-instance"`

#### service (optional)
- **Type**: `string`
- **Description**: Cloud service name (e.g., "ec2", "compute", "storage")
- **Purpose**: Enables service-level filtering and grouping

#### region (optional)
- **Type**: `string`
- **Description**: Geographic region or location
- **Examples**: `"us-east-1"`, `"eastus"`, `"us-central1"`

#### Cloud-Specific Identifiers

**AWS:**
- `account_id`: 12-digit AWS account number

**Azure:**
- `subscription_id`: UUID of the Azure subscription
- `resource_group`: Resource group name

**GCP:**
- `project_id`: GCP project identifier

#### labels (required)
- **Type**: `object` (dictionary)
- **Description**: Extensible key-value pairs for resource tagging and organization
- **Purpose**:
  - Combines cloud provider native tags with custom labels
  - Enables cross-cloud resource querying
  - Supports organizational metadata
- **Always present**: Empty object `{}` if no labels exist

**Common Label Keys:**
```json
{
  "Environment": "production|staging|development",
  "Owner": "team-name|user-email",
  "Project": "project-name",
  "CostCenter": "department-code",
  "Compliance": "pci-dss|hipaa|sox",
  "Backup": "daily|weekly|none",
  "Security": "public|private|restricted"
}
```

## Configuration Object

The `configuration` object contains provider-specific resource details:

- **Structure**: Varies by resource type and cloud provider
- **Purpose**: Complete resource configuration for analysis
- **Validation**: Must be a valid JSON object

**Examples:**

**AWS EC2 Instance:**
```json
{
  "configuration": {
    "instance_type": "t3.medium",
    "state": "running",
    "vpc_id": "vpc-12345678",
    "subnet_id": "subnet-12345678",
    "security_groups": ["sg-12345678"],
    "key_name": "my-key-pair",
    "monitoring": {"state": "enabled"},
    "ebs_optimized": true
  }
}
```

**Azure Virtual Machine:**
```json
{
  "configuration": {
    "vm_size": "Standard_DS1_v2",
    "os_type": "Linux",
    "provisioning_state": "Succeeded",
    "power_state": "running",
    "network_interfaces": ["/subscriptions/.../networkInterfaces/my-nic"],
    "os_disk": {
      "name": "my-os-disk",
      "disk_size_gb": 30,
      "caching": "ReadWrite"
    }
  }
}
```

**GCP Storage Bucket:**
```json
{
  "configuration": {
    "location": "US",
    "storage_class": "STANDARD",
    "versioning_enabled": false,
    "encryption": {
      "default_kms_key_name": null
    },
    "lifecycle_rules": [],
    "public_access_prevention": "inherited"
  }
}
```

## Raw Object

The `raw` object contains the complete API response from the cloud provider:

- **Purpose**: Provides full resource details for comprehensive analysis
- **Structure**: Native cloud provider API format
- **Optional**: May be omitted in some transport configurations to reduce size

## Resource Type Naming Convention

Resource types follow a hierarchical naming pattern:

```
{cloud_provider}:{service}:{resource_type}
```

**Examples:**
- `aws:ec2:instance` - AWS EC2 instance
- `aws:s3:bucket` - AWS S3 bucket
- `azure:compute:virtual-machine` - Azure VM
- `azure:storage:account` - Azure storage account
- `gcp:compute:instance` - GCP compute instance
- `gcp:storage:bucket` - GCP storage bucket

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
      "Environment": "production",
      "Owner": "platform-team"
    }
  },
  "configuration": {
    "instance_type": "t3.medium",
    "state": "running",
    "vpc_id": "vpc-12345678",
    "security_groups": ["sg-12345678"]
  },
  "raw": {
    // Complete EC2 describe_instances response
  }
}
```

### Azure Virtual Machine

```json
{
  "cloud_provider": "azure",
  "resource_type": "azure:compute:virtual-machine",
  "metadata": {
    "resource_id": "/subscriptions/xxx/resourceGroups/my-rg/providers/Microsoft.Compute/virtualMachines/my-vm",
    "service": "compute",
    "location": "eastus",
    "subscription_id": "xxx-xxx-xxx",
    "resource_group": "my-rg",
    "labels": {
      "environment": "production",
      "owner": "platform-team"
    }
  },
  "configuration": {
    "vm_size": "Standard_DS1_v2",
    "os_type": "Linux",
    "provisioning_state": "Succeeded"
  },
  "raw": {
    // Complete Azure VM resource object
  }
}
```

### GCP Storage Bucket

```json
{
  "cloud_provider": "gcp",
  "resource_type": "gcp:storage:bucket",
  "metadata": {
    "resource_id": "projects/my-project/buckets/my-bucket",
    "service": "storage",
    "region": "us-central1",
    "project_id": "my-project",
    "labels": {
      "env": "production",
      "team": "platform"
    }
  },
  "configuration": {
    "location": "US",
    "storage_class": "STANDARD",
    "versioning_enabled": false
  },
  "raw": {
    // Complete GCP bucket resource object
  }
}
```

## Migration and Compatibility

### From Legacy Format

The scanner includes migration utilities to convert from older formats:

**Legacy AWS Format:**
```json
{
  "resource_id": "i-123",
  "resource_type": "ec2:instance",
  "service": "ec2",
  "region": "us-east-1",
  "configuration": { ... },
  "raw": { ... }
}
```

**New Standardized Format:**
```json
{
  "cloud_provider": "aws",
  "resource_type": "aws:ec2:instance",
  "metadata": {
    "resource_id": "i-123",
    "service": "ec2",
    "region": "us-east-1",
    "labels": {}
  },
  "configuration": { ... },
  "raw": { ... }
}
```

### Migration Script

Run the migration script to convert existing artifacts:

```bash
python migrate_metadata.py
```

This script:
- Processes all JSON files in `file_collector/` and `sample_extractions/`
- Adds missing fields (`cloud_provider`, `metadata` object)
- Converts legacy tags to `metadata.labels`
- Updates `resource_type` to include provider prefix

## Validation

All extracted resources are validated against the schema:

### Required Fields
- `cloud_provider`: Must be "aws", "azure", or "gcp"
- `resource_type`: Must match `{provider}:{service}:{type}` pattern
- `metadata`: Must be present
- `metadata.resource_id`: Must be non-empty string
- `metadata.labels`: Must be object (can be empty)

### Optional Fields
- `metadata.service`: Service name string
- `metadata.region`: Region/location string
- `configuration`: Provider-specific object
- `raw`: Original API response object

## Benefits

### For Security Tools
- **Consistent querying**: Same field names across clouds
- **Unified policies**: Write once, apply to all providers
- **Standardized reporting**: Common format for dashboards

### For Developers
- **Predictable structure**: Always know where to find data
- **Extensible design**: Add custom fields without breaking changes
- **Type safety**: Clear schema for validation

### For Operations
- **Cross-cloud visibility**: Single view of multi-cloud resources
- **Unified monitoring**: Same metrics and alerts
- **Simplified automation**: Consistent API for all providers

## Implementation Details

### Base Extractor Methods

All extractors use these methods to create standardized output:

```python
def create_metadata_object(
    self,
    resource_id: str,
    service: Optional[str] = None,
    region: Optional[str] = None,
    account_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    project_id: Optional[str] = None,
    resource_group: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create standardized metadata object"""
    metadata = {
        "resource_id": resource_id,
        "labels": labels or {}
    }
    
    if service:
        metadata["service"] = service
    if region:
        metadata["region"] = region
    
    # Add cloud-specific identifiers
    if account_id:
        metadata["account_id"] = account_id
    if subscription_id:
        metadata["subscription_id"] = subscription_id
    if project_id:
        metadata["project_id"] = project_id
    if resource_group:
        metadata["resource_group"] = resource_group
    
    # Merge tags into labels
    if tags:
        metadata["labels"].update(tags)
    
    return metadata
```

### Transform Method Pattern

```python
def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw cloud data to standardized format"""
    resource = raw_data["resource"]
    
    return {
        "cloud_provider": self.cloud_provider,
        "resource_type": f"{self.cloud_provider}:{self.metadata.service_name}:{resource_type}",
        "metadata": self.create_metadata_object(
            resource_id=extract_resource_id(resource),
            service=self.metadata.service_name,
            region=extract_region(resource),
            # ... other fields
            tags=extract_tags(resource)
        ),
        "configuration": extract_configuration(resource),
        "raw": resource
    }
```

## Future Extensions

### Additional Metadata Fields

Planned additions to the metadata object:

```json
{
  "metadata": {
    "resource_id": "string",
    "service": "string",
    "region": "string",
    // Existing fields...
    
    // Future additions
    "created_at": "2024-01-15T10:30:00Z",     // ISO timestamp
    "updated_at": "2024-01-15T10:30:00Z",     // ISO timestamp
    "compliance": ["pci-dss", "hipaa"],       // Compliance frameworks
    "cost_center": "engineering",              // Cost allocation
    "lifecycle": "active|deprecated|archived" // Resource lifecycle
  }
}
```

### Custom Labels

Organizations can define custom label schemas:

```json
{
  "metadata": {
    "labels": {
      // Standard labels
      "Environment": "production",
      "Owner": "platform-team",
      
      // Custom organizational labels
      "BusinessUnit": "engineering",
      "DataClassification": "confidential",
      "RetentionPeriod": "7-years",
      "BackupSchedule": "daily"
    }
  }
}
```

This metadata structure provides a solid foundation for cloud-agnostic resource management and security analysis.