# GCP Supported Resources

This document lists the Google Cloud Platform (GCP) resources supported by the CSP Scanner, their extraction capabilities, and configuration options.

## Overview

The scanner currently supports **2 GCP services** with **3 resource types**:

- **Compute Engine** (compute)
- **Cloud Storage** (storage)

## Compute Engine (`gcp:compute`)

Extracts VM instances and managed instance groups from Google Compute Engine.

### Resource Types

#### 1. VM Instances (`gcp:compute:instance`)

**What is extracted:**
- Instance ID, name, and self-link
- Zone and derived region
- Machine type (e.g., `n1-standard-4`)
- Instance status (RUNNING, STOPPED, TERMINATED)
- Creation timestamp
- Network interfaces with internal and external IPs
- Attached disks (boot and data disks)
- Service accounts with OAuth2 scopes
- Custom metadata key-value pairs
- Network tags
- Labels

**Configuration:**
```yaml
gcp:
  compute:
    max_workers: 10              # Number of parallel workers
    include_stopped: true        # Include stopped instances
    include_instance_groups: true # Include managed instance groups
```

**Extracted Data Structure:**
```json
{
  "cloud_provider": "gcp",
  "resource_type": "gcp:compute:instance",
  "metadata": {
    "resource_id": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a/instances/my-instance",
    "service": "compute",
    "region": "us-central1",
    "project_id": "my-project",
    "labels": {}
  },
  "configuration": {
    "zone": "us-central1-a",
    "status": "RUNNING",
    "machine_type": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a/machineTypes/n1-standard-4",
    "creation_timestamp": "2024-01-15T10:30:00.000-07:00",
    "network_interfaces": [
      {
        "network": "https://www.googleapis.com/compute/v1/projects/my-project/global/networks/default",
        "subnetwork": "https://www.googleapis.com/compute/v1/projects/my-project/regions/us-central1/subnetworks/default",
        "network_ip": "10.128.0.2",
        "access_configs": [
          {
            "name": "External NAT",
            "nat_ip": "34.123.45.67",
            "type": "ONE_TO_ONE_NAT"
          }
        ]
      }
    ],
    "disks": [
      {
        "device_name": "persistent-disk-0",
        "source": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a/disks/my-instance",
        "boot": true,
        "auto_delete": true,
        "mode": "READ_WRITE"
      }
    ],
    "service_accounts": [
      {
        "email": "123456789-compute@developer.gserviceaccount.com",
        "scopes": [
          "https://www.googleapis.com/auth/cloud-platform"
        ]
      }
    ],
    "metadata": {},
    "tags": []
  }
}
```

#### 2. Managed Instance Groups (`gcp:compute:instance-group`)

**What is extracted:**
- Instance group ID, name, and self-link
- Zone
- Instance template reference
- Base instance name pattern
- Target size (desired number of instances)
- Current actions (creating, deleting, etc.)
- Named ports configuration
- Auto-healing policies

**Extracted Data Structure:**
```json
{
  "cloud_provider": "gcp",
  "resource_type": "gcp:compute:instance-group",
  "metadata": {
    "resource_id": "https://www.googleapis.com/compute/v1/projects/my-project/zones/us-central1-a/instanceGroupManagers/my-mig",
    "service": "compute",
    "region": "us-central1",
    "project_id": "my-project"
  },
  "configuration": {
    "zone": "us-central1-a",
    "instance_template": "https://www.googleapis.com/compute/v1/projects/my-project/global/instanceTemplates/my-template",
    "target_size": 3,
    "current_actions": {
      "creating": 0,
      "deleting": 0,
      "recreating": 0
    },
    "named_ports": [
      {
        "name": "http",
        "port": 80
      }
    ],
    "auto_healing_policies": []
  }
}
```

### API Permissions Required

- `compute.instances.list`
- `compute.instances.get`
- `compute.instanceGroups.list`
- `compute.instanceGroups.get`
- `compute.instanceGroupManagers.list`
- `compute.instanceGroupManagers.get`
- `compute.zones.list`
- `compute.regions.list`

**Predefined Role:** `roles/compute.viewer`

---

## Cloud Storage (`gcp:storage`)

Extracts Cloud Storage buckets and their configurations.

### Resource Types

#### Storage Buckets (`gcp:storage:bucket`)

**What is extracted:**
- Bucket name, ID, and self-link
- Location and location type (region/multi-region)
- Storage class (STANDARD, NEARLINE, COLDLINE, ARCHIVE)
- Creation and update timestamps
- Versioning status
- Labels
- Encryption configuration (CMEK)
- Lifecycle rules
- CORS configuration
- IAM policy bindings (optional)
- Logging configuration
- Website configuration
- Public access prevention settings
- Uniform bucket-level access

**Configuration:**
```yaml
gcp:
  storage:
    max_workers: 20                # Number of parallel workers
    include_iam_policies: false    # Fetch IAM policies (requires additional permissions)
    check_public_access: true      # Check public access settings
```

**Extracted Data Structure:**
```json
{
  "cloud_provider": "gcp",
  "resource_type": "gcp:storage:bucket",
  "metadata": {
    "resource_id": "https://www.googleapis.com/storage/v1/b/my-bucket",
    "service": "storage",
    "region": "US",
    "project_id": "my-project",
    "labels": {
      "env": "production"
    }
  },
  "configuration": {
    "location": "US",
    "location_type": "multi-region",
    "storage_class": "STANDARD",
    "versioning_enabled": false,
    "time_created": "2024-01-15 10:30:00+00:00",
    "updated": "2024-01-20 15:45:00+00:00",
    "encryption": {
      "default_kms_key_name": "projects/my-project/locations/us/keyRings/my-keyring/cryptoKeys/my-key"
    },
    "lifecycle_rules": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 365,
          "matches_storage_class": ["NEARLINE", "COLDLINE"]
        }
      }
    ],
    "cors": [
      {
        "origin": ["https://example.com"],
        "method": ["GET", "POST"],
        "response_header": ["Content-Type"],
        "max_age_seconds": 3600
      }
    ],
    "public_access_prevention": {
      "is_enforced": true,
      "uniform_bucket_level_access": {
        "enabled": true
      }
    }
  }
}
```

**Optional: IAM Policy Extraction**

When `include_iam_policies: true`, also extracts:
```json
{
  "configuration": {
    "iam_policy": {
      "bindings": [
        {
          "role": "roles/storage.objectViewer",
          "members": [
            "user:alice@example.com",
            "serviceAccount:service@project.iam.gserviceaccount.com"
          ]
        }
      ]
    }
  }
}
```

### API Permissions Required

**Basic:**
- `storage.buckets.list`
- `storage.buckets.get`

**For IAM Policies:**
- `storage.buckets.getIamPolicy`

**Predefined Roles:**
- Basic: `roles/storage.objectViewer`
- With IAM: `roles/storage.admin`

---

## Regional Support

### Compute Engine
Supports all GCP regions and zones. By default, extracts from all zones. Use the `region` parameter to filter:

```bash
curl -X POST http://localhost:8000/extraction/trigger \
    -H "Content-Type: application/json" \
    -d '{
      "services": ["compute"],
      "provider": "gcp",
      "region": "us-central1"
    }'
```

### Cloud Storage
Buckets are global resources but have a location attribute. Filter by location:

```bash
curl -X POST http://localhost:8000/extraction/trigger \
    -H "Content-Type: application/json" \
    -d '{
      "services": ["storage"],
      "provider": "gcp",
      "region": "US"  # or "us-central1", "europe-west1", etc.
    }'
```

## Performance Considerations

### Parallel Extraction
- **Compute:** Extracts zones in parallel using thread pool
- **Storage:** Single-threaded bucket listing (GCP limitation)

### Rate Limits
GCP API quotas vary by API:
- **Compute:** 2,000 read requests per 100 seconds
- **Storage:** 5,000 read operations per second per project

Adjust `max_workers` if hitting rate limits.

### Large Environments
For projects with many resources:
1. Use regional filtering
2. Reduce `max_workers`
3. Implement batch extraction with delays

## Filtering

Currently supported filters:

### By Region
```json
{
  "services": ["compute"],
  "provider": "gcp",
  "region": "us-central1"
}
```

### By Multiple Services
```json
{
  "services": ["compute", "storage"],
  "provider": "gcp"
}
```

## Future Resource Support

Planned additions (not yet implemented):

### Networking
- VPC Networks
- Firewall Rules
- Cloud Load Balancers
- Cloud NAT
- VPN Gateways

### Container Services
- GKE Clusters
- GKE Node Pools

### Database Services
- Cloud SQL Instances
- Cloud Spanner Instances

### Serverless
- Cloud Functions
- Cloud Run Services

### Security & IAM
- IAM Policies
- Service Accounts
- Cloud KMS Keys

### Other Services
- Cloud DNS Zones
- Cloud Pub/Sub Topics
- BigQuery Datasets

## Adding New Extractors

To add support for a new GCP resource type:

1. Create extractor class in `app/extractors/gcp/`:
   ```python
   class GCPNewServiceExtractor(BaseExtractor):
       def get_metadata(self) -> ExtractorMetadata:
           return ExtractorMetadata(
               service_name="newservice",
               version="1.0.0",
               description="Extracts GCP NewService resources",
               resource_types=["resource"],
               cloud_provider="gcp",
           )
       
       async def extract(self, region, filters):
           # Implementation
           pass
       
       def transform(self, raw_data):
           # Transform to standard format
           pass
   ```

2. Register in `app/services/registry.py`:
   ```python
   from app.extractors.gcp.newservice import GCPNewServiceExtractor
   # Add to _register_gcp_extractors()
   ```

3. Add configuration in `config/extractors.yaml`:
   ```yaml
   gcp:
     newservice:
       max_workers: 10
       # Service-specific options
   ```

4. Update GCP session in `app/cloud/gcp_session.py` if needed:
   ```python
   elif service == "newservice":
       from google.cloud import newservice_v1
       return newservice_v1.NewServiceClient(credentials=self.credentials)
   ```

## Troubleshooting

### No Resources Found
- Verify resources exist in the specified region
- Check service account permissions
- Enable Cloud Asset API for better visibility

### Extraction Timeout
- Reduce `max_workers`
- Extract fewer zones at once
- Use regional filtering

### Memory Issues
- Process regions/zones separately
- Reduce batch size
- Increase worker memory allocation

## Related Documentation

- [GCP Setup Guide](./GCP_SETUP.md) - Authentication and configuration
- [API Documentation](./API_DOCUMENTATION.md) - API usage
- [Contributing Guide](./CONTRIBUTING.md) - Adding extractors
