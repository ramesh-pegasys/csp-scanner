# GCP Deployment Guide

This directory contains deployment configurations for Cloud Artifact Extractor on Google Cloud Platform using different deployment strategies.

## Deployment Options

### 1. Cloud Run (Recommended for Simplicity)
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

**Quick Start:**
```bash
bash deploy/gcp/cloudrun-deploy.sh
```

See `cloudrun-deploy.sh` for details.

---

### 2. App Engine (Traditional)
**Use Case:** Standard web application deployment with built-in scaling and monitoring.

- **Pros:**
  - Automatic scaling
  - Built-in load balancing
  - Health checks and monitoring
  - Multiple languages supported
- **Cons:**
  - Less container-native
  - More expensive than Cloud Run
  - Less flexible deployment

**Quick Start:**
```bash
bash deploy/gcp/appengine-deploy.sh
```

See `app.yaml` for configuration.

---

### 3. Google Kubernetes Engine (GKE - Production Grade)
**Use Case:** Enterprise-grade orchestration with advanced networking and security.

- **Pros:**
  - Full Kubernetes power
  - Advanced networking and security
  - Multi-region deployment
  - Workload Identity integration
  - Cost optimization with Autopilot
- **Cons:**
  - Higher complexity
  - More operational overhead
  - Requires Kubernetes expertise
  - Higher minimum cost

**Quick Start:**
```bash
bash deploy/gcp/gke-deploy.sh
```

See `gke-deploy.sh` and Kubernetes manifests.

---

### 5. Compute Engine (IaaS with Auto Scaling)
**Use Case:** Full control with custom infrastructure and on-demand scaling.

- **Pros:**
  - Full VM control
  - Custom configurations
  - Detailed monitoring
  - Cost optimization options
- **Cons:**
  - Infrastructure management required
  - More operational overhead
  - No automatic container management

**Quick Start:**
```bash
bash deploy/gcp/compute-engine-deploy.sh
```

See `compute-engine-deploy.sh` for details.

---

## Prerequisites

- Google Cloud SDK installed (`gcloud`)
- Docker installed (for container deployments)
- Kubernetes CLI (`kubectl`) for GKE deployments
- Appropriate GCP permissions (Editor or Owner role)
- GCP project created and billing enabled

## Environment Configuration

All deployments require these environment variables:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_SERVICE_ACCOUNT=cloud-artifact-extractor@your-project-id.iam.gserviceaccount.com

# Service Configuration
ENABLED_PROVIDERS=["aws", "azure", "gcp"]
CONFIG_FILE=/app/config/production.yaml
HTTP_ENDPOINT_URL=https://your-scanner-endpoint.com
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

## Quick Comparison

| Feature | Cloud Run | App Engine | GKE | Compute |
|---------|-----------|-----------|-----|---------|
| Setup Time | 5 min | 10 min | 30 min | 20 min |
| Scaling | Auto (0-N) | Auto | Manual/Auto | Manual/Auto |
| Pricing | Per-request | Per-instance | Per-node | Per-minute |
| Best For | Web APIs | Traditional apps | Enterprise | Custom |
| Complexity | Very Low | Low | High | Medium |

## Deployment Architecture

### Cloud Run
```
Load Balancer → Cloud Run Service → Cloud Tasks (for async)
              ↓
         Cloud Logging
         Cloud Trace
```

### GKE
```
Cloud Load Balancer → GKE Cluster → Pods
                   ↓
              Workload Identity
              Cloud SQL Proxy
              Cloud Logging
```

## Monitoring & Logging

All deployments integrate with:
- **Cloud Logging:** Application and system logs
- **Cloud Monitoring:** Metrics and dashboards
- **Cloud Trace:** Distributed tracing
- **Cloud Profiler:** Performance profiling
- **Error Reporting:** Error tracking

## Security Best Practices

1. Use Service Accounts with minimal permissions
2. Enable Workload Identity (GKE)
3. Use Secret Manager for sensitive data
4. Implement Binary Authorization (GKE)
5. Enable VPC Service Controls for network isolation
6. Use Cloud Armor for DDoS protection
7. Enable Cloud Audit Logs for compliance
8. Encrypt data in transit with TLS/SSL

## Cost Optimization

1. **Cloud Run:** Use minInstances=0 for cost savings
2. **Functions:** Use Pub/Sub triggers for efficiency
3. **GKE:** Use Autopilot for cost optimization
4. **Compute Engine:** Use preemptible instances for non-critical workloads

## Auto Scaling Configuration

### Cloud Run
```yaml
min_instances: 0
max_instances: 1000
cpu_throttling: true
memory: 2Gi
```

### GKE
```yaml
autoscaling:
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
```

## Troubleshooting

### Common Issues

**Container fails to start:**
- Check logs: `gcloud run services describe <service> --region <region>`
- Verify image in Container Registry
- Check environment variables
- Verify permissions on service account

**High latency:**
- Check Cloud Trace for bottlenecks
- Review Cloud Monitoring metrics
- Monitor CPU and memory usage
- Check network throughput

**Scaling not working:**
- Verify metrics are being exported
- Check Cloud Monitoring dashboards
- Ensure sufficient quota in region

## Next Steps

1. Choose your deployment method above
2. Review the corresponding deployment script
3. Update configuration values for your GCP project
4. Run the deployment script
5. Monitor through GCP Console
6. Set up monitoring and alerts

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Google Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Google App Engine Documentation](https://cloud.google.com/appengine/docs)
- [Google Kubernetes Engine Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Google Compute Engine Documentation](https://cloud.google.com/compute/docs)
- [GCP Security Best Practices](https://cloud.google.com/security/best-practices)
