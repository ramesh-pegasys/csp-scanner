---
layout: default
title: GCP Setup
parent: Cloud Providers
nav_order: 3
---

# Google Cloud Platform (GCP)

## Authentication Methods

### 1. Service Account Key File (Recommended for Production)

**Create Service Account:**
```bash
# Create service account
gcloud iam service-accounts create csp-scanner \
    --description="Service account for CSP Scanner" \
    --display-name="CSP Scanner"
```

**Grant Permissions:**
```bash
# Compute Engine access
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.viewer"

# Cloud Storage access
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"
```

**Create and Download Key:**
```bash
gcloud iam service-accounts keys create csp-scanner-key.json \
    --iam-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com
```

**Configure Environment Variables:**
```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_CREDENTIALS_PATH="/path/to/csp-scanner-key.json"
export GCP_DEFAULT_REGION="us-central1"
```

### 2. Application Default Credentials (ADC)

For local development:

```bash
# Authenticate with user account
gcloud auth application-default login

# Set project
export GCP_PROJECT_ID="your-project-id"
```

When running on GCP resources (Compute Engine, Cloud Run, etc.), ADC automatically uses the instance's service account.

## Required Permissions

**Compute Engine:**
- `compute.instances.list`
- `compute.instances.get`
- `compute.instanceGroups.list`
- `compute.instanceGroups.get`
- `compute.instanceGroupManagers.list`
- `compute.instanceGroupManagers.get`
- `compute.zones.list`
- `compute.regions.list`

**Cloud Storage:**
- `storage.buckets.list`
- `storage.buckets.get`
- `storage.buckets.getIamPolicy` (optional)

**Resource Manager:**
- `resourcemanager.projects.get`

**Predefined Roles:**
- `roles/compute.viewer` (Compute Engine)
- `roles/storage.objectViewer` (Cloud Storage)
- `roles/viewer` (Resource Manager)

## Custom Role (Least Privilege)

Create a custom role for minimal permissions:

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

## Verification

Test GCP credentials:

```bash
# Using gcloud CLI
gcloud compute instances list --project=your-project-id
gcloud storage buckets list --project=your-project-id

# Test service account key
gcloud auth activate-service-account --key-file=/path/to/service-account-key.json
gcloud compute instances list --project=your-project-id
```

## Supported GCP Services

- **Compute Engine**: VM Instances, Managed Instance Groups
- **Cloud Storage**: Storage Buckets with full configuration
- **IAM**: Service Accounts, Roles, Policies
- **Kubernetes**: GKE Clusters, Node Pools
- **Networking**: VPC Networks, Subnets, Firewall Rules, Load Balancers

## Security Best Practices

1. **Use Service Accounts** with minimal permissions
2. **Rotate service account keys** regularly
3. **Store keys securely** (Secret Manager, etc.)
4. **Enable key rotation** policies
5. **Monitor with Cloud Audit Logs**

## Troubleshooting

### "Could not automatically determine credentials"
- Set `GCP_CREDENTIALS_PATH` to service account key file
- Or run `gcloud auth application-default login`
- Check file permissions on key file

### "Permission denied"
- Verify service account has required IAM roles
- Check project ID is correct
- Ensure APIs are enabled (Compute API, Storage API)

### "API not enabled"
- Enable required APIs: `gcloud services enable compute.googleapis.com storage.googleapis.com`
- Some APIs require billing to be enabled

## Production Deployment

- Use service account attached to Compute Engine/Cloud Run
- Store keys in Secret Manager
- Use Organization Policies for governance

## Cost Optimization

- Use GCP Free Tier credits
- Leverage Committed Use Discounts
- Monitor costs with Billing reports
