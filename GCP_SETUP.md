# GCP Setup Guide

This guide explains how to set up and configure the CSP Scanner for Google Cloud Platform (GCP) resource extraction.

## Prerequisites

- GCP project with resources to scan
- Python 3.10 or higher
- GCP credentials (service account or application default credentials)

## Authentication Methods

The GCP scanner supports two authentication methods:

### 1. Service Account Key File (Recommended for Automation)

1. Create a service account in your GCP project:
   ```bash
   gcloud iam service-accounts create csp-scanner \
       --description="Service account for CSP Scanner" \
       --display-name="CSP Scanner"
   ```

2. Grant necessary permissions to the service account:
   ```bash
   # Grant read-only access to compute resources
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/compute.viewer"
   
   # Grant read-only access to storage resources
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/storage.objectViewer"
   ```

3. Create and download a key file:
   ```bash
   gcloud iam service-accounts keys create csp-scanner-key.json \
       --iam-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com
   ```

4. Set environment variables:
   ```bash
   export GCP_PROJECT_ID="your-project-id"
   export GCP_CREDENTIALS_PATH="/path/to/csp-scanner-key.json"
   ```

### 2. Application Default Credentials (ADC)

For local development or when running on GCP resources:

```bash
# Authenticate with your user account
gcloud auth application-default login

# Set project ID
export GCP_PROJECT_ID="your-project-id"
```

When running on GCP resources (e.g., Compute Engine, Cloud Run), ADC automatically uses the instance's service account.

## Configuration

### Method 1: Environment Variables

Create a `.env` file in the project root:

```env
# Enable GCP provider
ENABLED_PROVIDERS=["aws", "azure", "gcp"]

# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_CREDENTIALS_PATH=/path/to/service-account-key.json  # Optional, uses ADC if not provided
GCP_DEFAULT_REGION=us-central1
```

### Method 2: YAML Configuration

Create or update a configuration file (e.g., `config/development.yaml`):

```yaml
# Multi-Cloud Configuration
enabled_providers:
  - aws
  - azure
  - gcp

# GCP Configuration
gcp_project_id: "your-project-id"
gcp_credentials_path: "/path/to/service-account-key.json"  # Optional
gcp_default_region: "us-central1"
```

Load it with:
```bash
export CONFIG_FILE=config/development.yaml
```

## Required IAM Permissions

The service account or user needs the following minimum permissions:

### Compute Engine
- `compute.instances.list`
- `compute.instances.get`
- `compute.instanceGroups.list`
- `compute.instanceGroups.get`
- `compute.instanceGroupManagers.list`
- `compute.instanceGroupManagers.get`
- `compute.zones.list`
- `compute.regions.list`

**Predefined Role:** `roles/compute.viewer`

### Cloud Storage
- `storage.buckets.list`
- `storage.buckets.get`
- `storage.buckets.getIamPolicy` (optional, for IAM policy extraction)

**Predefined Role:** `roles/storage.objectViewer` or `roles/storage.admin` for IAM policies

### Resource Manager
- `resourcemanager.projects.get`

**Predefined Role:** `roles/viewer`

### Recommended: Custom Role

For least privilege access, create a custom role:

```bash
gcloud iam roles create cspScanner \
    --project=PROJECT_ID \
    --title="CSP Scanner" \
    --description="Custom role for CSP Scanner with minimum required permissions" \
    --permissions=compute.instances.list,compute.instances.get,compute.instanceGroups.list,compute.instanceGroups.get,compute.instanceGroupManagers.list,compute.instanceGroupManagers.get,compute.zones.list,compute.regions.list,storage.buckets.list,storage.buckets.get,resourcemanager.projects.get \
    --stage=GA

# Assign the custom role
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
    --role="projects/PROJECT_ID/roles/cspScanner"
```

## Installation

1. Install GCP dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Verify GCP packages are installed:
   ```bash
   pip list | grep google-cloud
   ```

## Testing the Setup

1. Test authentication:
   ```bash
   # If using service account key
   gcloud auth activate-service-account --key-file=/path/to/service-account-key.json
   
   # Verify access
   gcloud compute instances list --project=your-project-id
   gcloud storage buckets list --project=your-project-id
   ```

2. Test the scanner:
   ```bash
   # Start the application
   uvicorn app.main:app --reload
   
   # Test the /providers endpoint
   curl http://localhost:8000/extraction/providers
   # Should return: {"providers": ["aws", "azure", "gcp"]}
   
   # List GCP services
   curl http://localhost:8000/extraction/services?provider=gcp
   # Should return: ["gcp:compute", "gcp:storage"]
   ```

3. Trigger extraction:
   ```bash
   curl -X POST http://localhost:8000/extraction/trigger \
       -H "Content-Type: application/json" \
       -d '{
         "services": ["compute", "storage"],
         "provider": "gcp",
         "region": "us-central1"
       }'
   ```

## Extractor Configuration

Configure GCP extractors in `config/extractors.yaml`:

```yaml
gcp:
  compute:
    max_workers: 10                    # Parallel extraction workers
    include_stopped: true              # Include stopped instances
    include_instance_groups: true      # Include managed instance groups
  
  storage:
    max_workers: 20                    # Parallel extraction workers
    include_iam_policies: false        # Fetch IAM policies (requires additional permissions)
    check_public_access: true          # Check public access settings
```

## Multi-Region Extraction

By default, the scanner extracts resources from all regions. To limit to specific regions:

```bash
# Extract from specific region
curl -X POST http://localhost:8000/extraction/trigger \
    -H "Content-Type: application/json" \
    -d '{
      "services": ["compute"],
      "provider": "gcp",
      "region": "us-central1"
    }'
```

Available regions:
- `us-central1`, `us-east1`, `us-west1`, `us-west2`
- `europe-west1`, `europe-west2`, `europe-north1`
- `asia-east1`, `asia-southeast1`, `asia-northeast1`
- And more...

## Troubleshooting

### Authentication Errors

**Error:** `DefaultCredentialsError: Could not automatically determine credentials`

**Solution:** 
1. Set `GCP_CREDENTIALS_PATH` to point to your service account key
2. Or run `gcloud auth application-default login`

### Permission Denied

**Error:** `403 Forbidden` or `Permission denied`

**Solution:**
1. Verify service account has required permissions:
   ```bash
   gcloud projects get-iam-policy PROJECT_ID \
       --flatten="bindings[].members" \
       --format="table(bindings.role)" \
       --filter="bindings.members:serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com"
   ```

2. Add missing permissions or roles

### Project ID Not Set

**Error:** `Project ID not set`

**Solution:**
Set the `GCP_PROJECT_ID` environment variable or configuration value.

### API Not Enabled

**Error:** `API [compute.googleapis.com] not enabled`

**Solution:**
Enable required APIs:
```bash
gcloud services enable compute.googleapis.com storage.googleapis.com
```

### Quota Exceeded

**Error:** `Quota exceeded`

**Solution:**
1. Request quota increase in GCP Console
2. Reduce `max_workers` in extractor configuration
3. Extract fewer resources per request

## Security Best Practices

1. **Use Service Accounts:** Don't use personal credentials for automation
2. **Rotate Keys:** Regularly rotate service account keys
3. **Least Privilege:** Grant only necessary permissions
4. **Secure Storage:** Store key files securely, never commit to version control
5. **Audit Logs:** Enable Cloud Audit Logs to track scanner activity
6. **Key Management:** Use Secret Manager for storing credentials in production

## Running in Production

### On Compute Engine

1. Create instance with service account:
   ```bash
   gcloud compute instances create csp-scanner \
       --service-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com \
       --scopes=cloud-platform
   ```

2. No need to set `GCP_CREDENTIALS_PATH` - uses instance metadata

### On Cloud Run

1. Deploy with service account:
   ```bash
   gcloud run deploy csp-scanner \
       --image=gcr.io/PROJECT_ID/csp-scanner \
       --service-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com
   ```

2. Set environment variable:
   ```bash
   gcloud run services update csp-scanner \
       --set-env-vars="GCP_PROJECT_ID=your-project-id"
   ```

### On Kubernetes (GKE)

1. Create Kubernetes service account with Workload Identity:
   ```bash
   kubectl create serviceaccount csp-scanner
   
   gcloud iam service-accounts add-iam-policy-binding \
       csp-scanner@PROJECT_ID.iam.gserviceaccount.com \
       --role roles/iam.workloadIdentityUser \
       --member "serviceAccount:PROJECT_ID.svc.id.goog[default/csp-scanner]"
   
   kubectl annotate serviceaccount csp-scanner \
       iam.gke.io/gcp-service-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com
   ```

2. Deploy with the service account

## Next Steps

- [GCP Resources Documentation](./GCP_RESOURCES.md) - Supported GCP resources
- [API Documentation](./API_DOCUMENTATION.md) - API endpoints
- [CONTRIBUTING](./CONTRIBUTING.md) - Add more GCP extractors
