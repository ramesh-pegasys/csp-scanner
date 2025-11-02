---
layout: default
title: GCP Cloud Run Deployment
parent: Deployment
nav_order: 5
---

# GCP Cloud Run Deployment Guide

Deploy Cloud Artifact Extractor to Google Cloud Platform using Cloud Run - a fully managed serverless container service.

## Quick Start

```bash
bash deploy/gcp/cloudrun-deploy.sh
```

Setup takes approximately **5 minutes**.

## What is Google Cloud Run?

**Use Case:** Serverless container deployment with automatic scaling and zero infrastructure management.

- **Pros:**
  - Fully managed, serverless
  - Pay-per-request pricing
  - Automatic scaling from 0 to N instances
  - Simple deployment
  - Built-in monitoring and logging
- **Cons:**
  - 60-minute execution timeout (for requests)
  - Request size limits
  - Less control over infrastructure

## Prerequisites

- Google Cloud SDK installed (`gcloud`)
- Docker installed
- Appropriate GCP permissions (Editor or Owner role)
- GCP project created and billing enabled

## Environment Configuration

The deployment requires these environment variables:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_SERVICE_ACCOUNT=cloud-artifact-extractor@your-project-id.iam.gserviceaccount.com

# Service Configuration
ENABLED_PROVIDERS=["aws", "azure", "gcp"]
CONFIG_FILE=/app/config/production.yaml
SCANNER_ENDPOINT_URL=https://your-scanner-endpoint.com
DEBUG=false

# Cloud Provider Credentials
GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-credentials.json

# AWS Integration (if scanning AWS)
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx

# Azure Integration (if scanning Azure)
AZURE_SUBSCRIPTION_ID=xxxxx
AZURE_TENANT_ID=xxxxx
AZURE_CLIENT_ID=xxxxx
AZURE_CLIENT_SECRET=xxxxx

# Security
JWT_SECRET_KEY=your-secure-secret-key
```

## Architecture

```
Load Balancer → Cloud Run Service → Cloud Tasks (for async)
              ↓
         Cloud Logging
         Cloud Trace
```

## Deployment Steps

### 1. Build Container Image

```bash
docker build -t cloud-artifact-extractor:latest -f Dockerfile .
```

### 2. Run Deployment Script

```bash
bash deploy/gcp/cloudrun-deploy.sh
```

The script will:
- Enable required APIs
- Create a service account
- Build and push container image to Artifact Registry
- Deploy to Cloud Run
- Configure IAM permissions

### 3. Verify Deployment

```bash
# Get the service URL
gcloud run services describe cloud-artifact-extractor \
  --region ${GCP_REGION} \
  --format 'value(status.url)'

# Test the endpoint
curl https://<service-url>/api/v1/health/ready
```

## Monitoring & Logging

### Cloud Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cloud-artifact-extractor" --limit 50

# Stream logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cloud-artifact-extractor"
```

### Cloud Monitoring

```bash
# View metrics
gcloud monitoring dashboards create --config-from-file=dashboard.json

# Set up alerts
gcloud alpha monitoring policies create --policy-from-file=alert-policy.json
```

### Cloud Trace

Enable distributed tracing:

```bash
# Enable Cloud Trace API
gcloud services enable cloudtrace.googleapis.com

# View traces in Cloud Console
open https://console.cloud.google.com/traces
```

## Scaling Configuration

Cloud Run automatically scales based on requests:

- **Minimum instances:** 0 (default)
- **Maximum instances:** 1000
- **Concurrency:** 80 requests per instance
- **CPU allocated:** 1 vCPU per instance
- **Memory:** 512 MiB per instance

Adjust with:

```bash
gcloud run services update cloud-artifact-extractor \
  --min-instances 1 \
  --max-instances 100 \
  --concurrency 50 \
  --cpu 2 \
  --memory 1Gi \
  --region ${GCP_REGION}
```

## Security Best Practices

1. **Use Service Accounts:** Create dedicated service accounts with minimal permissions
2. **VPC Access:** Connect to VPC for private resources
3. **Secret Manager:** Use Cloud Secret Manager for sensitive data
4. **IAM:** Implement principle of least privilege
5. **Binary Authorization:** Enable container image signing
6. **Audit Logs:** Enable Cloud Audit Logs
7. **Network Security:** Use VPC Service Controls

## Cost Optimization

- **Min instances = 0:** Avoid costs when service is idle
- **Right-sizing:** Monitor and adjust CPU/memory allocation
- **Request optimization:** Use Cloud CDN for static content
- **Cold starts:** Keep min instances > 0 for latency-sensitive apps

## Troubleshooting

### Service fails to start

```bash
# Check service status
gcloud run services describe cloud-artifact-extractor --region ${GCP_REGION}

# View logs for errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cloud-artifact-extractor" --limit 10
```

**Common causes:**
- Container image not found
- Missing environment variables
- Port 8000 not exposed
- Insufficient permissions
- Application startup errors

### High latency / cold starts

```bash
# Check cold start metrics
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.message: cold_start" --limit 20

# Increase min instances
gcloud run services update cloud-artifact-extractor --min-instances 1 --region ${GCP_REGION}
```

**Solutions:**
- Increase min instances to reduce cold starts
- Optimize container startup time
- Use Cloud Tasks for long-running operations

### Connection issues

```bash
# Check service URL
gcloud run services describe cloud-artifact-extractor \
  --region ${GCP_REGION} \
  --format 'value(status.traffic[0].url)'

# Test connectivity
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <service-url>/api/v1/health/ready
```

## Post-Deployment Configuration

### 1. Set up Custom Domain

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service cloud-artifact-extractor \
  --domain api.example.com \
  --region ${GCP_REGION}

# Configure DNS (add CNAME record pointing to ghs.googlehosted.com)
```

### 2. Configure VPC Access

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create cloud-artifact-extractor-connector \
  --region ${GCP_REGION} \
  --subnet subnet-name \
  --subnet-project ${GCP_PROJECT_ID}

# Attach to service
gcloud run services update cloud-artifact-extractor \
  --vpc-connector cloud-artifact-extractor-connector \
  --region ${GCP_REGION}
```

### 3. Set up Cloud Tasks for Async Operations

```bash
# Create queue
gcloud tasks queues create cloud-artifact-extractor-queue \
  --location ${GCP_REGION}

# Configure service account
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
  --member "serviceAccount:cloud-artifact-extractor@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role "roles/cloudtasks.enqueuer"
```

## Updating the Deployment

### Update Application Code

```bash
# Build new image
docker build -t cloud-artifact-extractor:latest -f Dockerfile .

# Deploy update
gcloud run deploy cloud-artifact-extractor \
  --image gcr.io/${GCP_PROJECT_ID}/cloud-artifact-extractor:latest \
  --region ${GCP_REGION} \
  --allow-unauthenticated
```

### Update Configuration

```bash
gcloud run services update cloud-artifact-extractor \
  --set-env-vars KEY1=value1,KEY2=value2 \
  --region ${GCP_REGION}
```

## CI/CD Integration

### Cloud Build Example

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/cloud-artifact-extractor:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/cloud-artifact-extractor:$COMMIT_SHA']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'cloud-artifact-extractor'
      - '--image'
      - 'gcr.io/$PROJECT_ID/cloud-artifact-extractor:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--allow-unauthenticated'
```

## Comparison with Other GCP Options

| Feature | Cloud Run | App Engine | GKE | Cloud Functions |
|---------|-----------|-----------|-----|-----------------|
| Setup Time | 5 min | 10 min | 30 min | 5 min |
| Scaling | Auto (0-N) | Auto | Manual/Auto | Auto |
| Pricing | Per-request | Per-instance | Per-node | Per-invocation |
| Container Support | Yes | Limited | Yes | No |
| Best For | Web APIs | Traditional apps | Enterprise | Event-driven |

## Next Steps

1. ✅ Deploy using `cloudrun-deploy.sh`
2. ⏳ Wait for service to be ready (1-2 minutes)
3. 📊 Set up monitoring and alerts
4. 🔐 Configure secrets in Secret Manager
5. 🔄 Set up CI/CD for automated deployments
6. 📈 Monitor metrics and optimize as needed

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/best-practices)
- [Cloud Logging](https://cloud.google.com/logging/docs)
- [GCP Security Best Practices](https://cloud.google.com/security/best-practices)