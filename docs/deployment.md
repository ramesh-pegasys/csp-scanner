# Deployment Guide

This guide covers deploying the Cloud Artifact Extractor to multiple cloud platforms and Kubernetes clusters.

**Document Version:** November 2025  
**Last Updated:** November 1, 2025

## Table of Contents

1. [Overview](#overview)
2. [Supported Platforms](#supported-platforms)
3. [Deployment Methods](#deployment-methods)
4. [Prerequisites](#prerequisites)
5. [Platform-Specific Guides](#platform-specific-guides)
6. [Common Tasks](#common-tasks)
7. [Monitoring and Operations](#monitoring-and-operations)

---

## Overview

The Cloud Artifact Extractor is a containerized FastAPI application that can be deployed to various cloud platforms. Each platform offers different trade-offs between ease of use, cost, and operational complexity.

### Supported Platforms

- **AWS** - Amazon Web Services App Runner
- **Azure** - Microsoft Azure Container Apps
- **GCP** - Google Cloud Platform Cloud Run
- **Kubernetes** - Multi-cloud (EKS, AKS, GKE)

### Deployment Architecture

All deployments follow the same core components:

```
┌──────────────────────┐
│   User/Client        │
└──────────┬───────────┘
           │ HTTP/HTTPS
           ▼
┌──────────────────────────────────────┐
│   Ingress / Load Balancer            │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│   Cloud Artifact Extractor           │
│   (FastAPI Application)              │
│   ├─ Cloud Extraction APIs           │
│   ├─ Artifact Collection             │
│   ├─ Job Management                  │
│   └─ Scheduling Service              │
└──────────┬───────────────────────────┘
           │
           ├─► CloudWatch/Azure Monitor/Cloud Logging
           ├─► Configuration (ConfigMap/Secrets)
           └─► Credentials (Service Accounts/IAM)
```

---

## Supported Platforms

### 1. AWS App Runner

**Best For:** Quick serverless deployment with minimal infrastructure management

**Key Features:**
- Fully managed container service
- Automatic scaling and load balancing
- Built-in CloudWatch integration
- VPC support
- Pay-per-request pricing

**Setup Time:** ~5 minutes

**Command:**
```bash
bash deploy/aws/apprunner-deploy.sh
```

**Learn More:** [AWS App Runner Deployment Guide](../deploy/aws/README.md)

---

### 2. Azure Container Apps

**Best For:** Modern serverless deployment with DAPR support

**Key Features:**
- Fully managed service
- Automatic scaling based on metrics
- DAPR support for distributed apps
- Virtual Network integration
- Azure Monitor integration

**Setup Time:** ~10 minutes

**Command:**
```bash
bash deploy/azure/container-apps-deploy.sh
```

**Learn More:** [Azure Container Apps Deployment Guide](../deploy/azure/README.md)

---

### 3. Google Cloud Run

**Best For:** Simple serverless deployment with minimal configuration

**Key Features:**
- Pay-per-request pricing
- Automatic scaling from 0 to N
- Fully managed serverless
- Container-native
- Cloud Logging integration

**Setup Time:** ~5 minutes

**Command:**
```bash
bash deploy/gcp/cloudrun-deploy.sh
```

**Learn More:** [GCP Cloud Run Deployment Guide](../deploy/gcp/README.md)

---

### 4. Kubernetes (EKS, AKS, GKE)

**Best For:** Enterprise deployments requiring advanced control

**Key Features:**
- Multi-cloud support
- Advanced networking and security
- Workload Identity integration
- Auto-scaling with HPA
- Network policies and RBAC

**Setup Time:** ~30 minutes

**Commands:**
```bash
# AWS EKS
bash deploy/kubernetes/aws-eks-deploy.sh

# Azure AKS
bash deploy/kubernetes/azure-aks-deploy.sh

# GCP GKE
bash deploy/kubernetes/gcp-gke-deploy.sh
```

**Learn More:** [Kubernetes Deployment Guide](../deploy/kubernetes/README.md)

---

## Deployment Methods

### Quick Comparison

| Aspect | App Runner | Container Apps | Cloud Run | Kubernetes |
|--------|-----------|-----------------|-----------|-----------|
| **Setup Time** | 5 min | 10 min | 5 min | 30 min |
| **Infrastructure** | Fully Managed | Fully Managed | Fully Managed | Self-Managed |
| **Scaling** | Automatic | Automatic | Automatic | Auto/Manual |
| **Pricing Model** | Per-request | Per-compute | Per-request | Per-node |
| **Complexity** | Very Low | Low | Very Low | High |
| **Cost for Dev** | Low | Low | Low | Medium-High |
| **Control Level** | Limited | Medium | Limited | Full |
| **Multi-region** | Via ALB | Via traffic manager | Native | Native |

### Choosing a Platform

**For Fastest Deployment:**
- → Cloud Run (5 min) or App Runner (5 min)

**For Cost-Conscious Deployments:**
- → Cloud Run (true pay-per-request)
- → App Runner (minimal baseline cost)

**For Enterprise Deployments:**
- → Kubernetes (any cloud)
- → Azure Container Apps (DAPR support)

**For Existing AWS Infrastructure:**
- → App Runner (easy integration with existing services)

**For Existing Azure Infrastructure:**
- → Container Apps (DAPR, native Azure Monitor)

**For Existing GCP Infrastructure:**
- → Cloud Run (native GCP service)

---

## Prerequisites

### For All Deployments

1. **Docker installed** on your local machine
2. **Container image built:**
   ```bash
   docker build -t cloud-artifact-extractor:latest -f Dockerfile .
   ```
3. **Cloud credentials configured** for your target platform

### Platform-Specific Prerequisites

#### AWS App Runner
- AWS CLI v2 installed
- AWS credentials configured (`aws configure`)
- IAM permissions for App Runner, ECR, and CloudWatch

#### Azure Container Apps
- Azure CLI installed
- Azure credentials (`az login`)
- Contributor role on target subscription

#### Google Cloud Run
- Google Cloud SDK (`gcloud`) installed
- GCP project created with billing enabled
- Appropriate project permissions

#### Kubernetes
- `kubectl` installed and configured
- Cloud CLI tools for your provider (aws, az, gcloud)
- Cluster admin permissions

---

## Platform-Specific Guides

Each deployment method has its own comprehensive guide:

### AWS App Runner
**Location:** `deploy/aws/README.md`

**Quick Start:**
```bash
bash deploy/aws/apprunner-deploy.sh
```

**Topics Covered:**
- Prerequisites and setup
- Environment configuration
- Deployment steps
- Monitoring with CloudWatch
- Scaling configuration
- Cost optimization
- Troubleshooting

### Azure Container Apps
**Location:** `deploy/azure/README.md`

**Quick Start:**
```bash
bash deploy/azure/container-apps-deploy.sh
```

**Topics Covered:**
- Prerequisites and setup
- Environment configuration
- Deployment steps
- Monitoring with Azure Monitor
- Auto-scaling setup
- Security best practices
- Troubleshooting

### Google Cloud Run
**Location:** `deploy/gcp/README.md`

**Quick Start:**
```bash
bash deploy/gcp/cloudrun-deploy.sh
```

**Topics Covered:**
- Cloud Run overview
- Prerequisites and setup
- Environment configuration
- Deployment steps
- Monitoring with Cloud Logging
- Scaling and performance
- Cost optimization
- Troubleshooting

### Kubernetes (EKS/AKS/GKE)
**Location:** `deploy/kubernetes/README.md`

**Quick Start:**
```bash
# Create cluster and deploy
bash deploy/kubernetes/aws-eks-deploy.sh
kubectl apply -f deploy/kubernetes/manifests/
```

**Topics Covered:**
- Architecture overview
- Cluster setup for each cloud provider
- Kubernetes manifests explained
- ConfigMap and Secrets setup
- RBAC configuration
- Network policies
- Monitoring and logging
- Scaling with HPA
- Upgrading and maintenance

---

## Common Tasks

### 1. Deploying the Application

**Step 1: Build the Docker image**
```bash
docker build -t cloud-artifact-extractor:latest -f Dockerfile .
```

**Step 2: Run the appropriate deployment script**

For your chosen platform:
- AWS: `bash deploy/aws/apprunner-deploy.sh`
- Azure: `bash deploy/azure/container-apps-deploy.sh`
- GCP: `bash deploy/gcp/cloudrun-deploy.sh`
- Kubernetes: See platform-specific guide

### 2. Verifying Deployment

After deployment, verify the service is running:

**AWS App Runner:**
```bash
aws apprunner describe-service --service-arn <your-service-arn>
```

**Azure Container Apps:**
```bash
az containerapp show --name cloud-artifact-extractor --resource-group <your-rg>
```

**Google Cloud Run:**
```bash
gcloud run services describe cloud-artifact-extractor
```

**Kubernetes:**
```bash
kubectl get deployment -n cloud-artifact-extractor
kubectl get pods -n cloud-artifact-extractor
```

### 3. Viewing Logs

**AWS App Runner:**
```bash
aws logs tail /aws/apprunner/cloud-artifact-extractor/apprunner-service/service-logs --follow
```

**Azure Container Apps:**
```bash
az containerapp logs show --name cloud-artifact-extractor --resource-group <your-rg> --follow
```

**Google Cloud Run:**
```bash
gcloud run services describe cloud-artifact-extractor
# View in Cloud Logging console or:
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cloud-artifact-extractor"
```

**Kubernetes:**
```bash
kubectl logs -n cloud-artifact-extractor -l app=cloud-artifact-extractor -f
```

### 4. Scaling the Application

**AWS App Runner:**
Automatic scaling is enabled by default. No manual configuration needed.

**Azure Container Apps:**
```bash
az containerapp update \
  --name cloud-artifact-extractor \
  --resource-group <your-rg> \
  --min-replicas 2 \
  --max-replicas 10
```

**Google Cloud Run:**
```bash
gcloud run services update cloud-artifact-extractor \
  --min-instances 1 \
  --max-instances 100
```

**Kubernetes:**
```bash
kubectl autoscale deployment cloud-artifact-extractor \
  -n cloud-artifact-extractor \
  --min=2 --max=10 --cpu-percent=70
```

### 5. Updating the Application

**AWS App Runner:**
```bash
# Rebuild and push image
docker build -t cloud-artifact-extractor:latest .
bash deploy/aws/apprunner-deploy.sh  # Re-run to update
```

**Azure Container Apps:**
```bash
# Rebuild and push
docker build -t cloud-artifact-extractor:latest .
bash deploy/azure/container-apps-deploy.sh  # Re-run to update
```

**Google Cloud Run:**
```bash
# Rebuild and deploy
docker build -t cloud-artifact-extractor:latest .
bash deploy/gcp/cloudrun-deploy.sh
```

**Kubernetes:**
```bash
kubectl set image deployment/cloud-artifact-extractor \
  cloud-artifact-extractor=<registry>/cloud-artifact-extractor:new-tag \
  -n cloud-artifact-extractor
```

### 6. Configuring Environment Variables

**AWS App Runner:**
```bash
aws apprunner update-service \
  --service-arn <your-service-arn> \
  --source-configuration InstanceConfiguration={Cpu=1,Memory=2048,Port=8000}
```

**Azure Container Apps:**
```bash
az containerapp update \
  --name cloud-artifact-extractor \
  --resource-group <your-rg> \
  --set-env-vars KEY=value
```

**Google Cloud Run:**
```bash
gcloud run services update cloud-artifact-extractor \
  --update-env-vars KEY=value
```

**Kubernetes:**
Edit `manifests/configmap.yaml` and apply:
```bash
kubectl apply -f deploy/kubernetes/manifests/configmap.yaml
```

### 7. Rolling Back a Deployment

**AWS App Runner:**
Revert the image or redeploy previous version:
```bash
bash deploy/aws/apprunner-deploy.sh  # With previous image
```

**Azure Container Apps:**
```bash
az containerapp revision list --name cloud-artifact-extractor --resource-group <your-rg>
az containerapp revision set-active --name cloud-artifact-extractor --resource-group <your-rg> --revision <revision-name>
```

**Google Cloud Run:**
```bash
gcloud run deploy cloud-artifact-extractor --image <previous-image-uri>
```

**Kubernetes:**
```bash
kubectl rollout history deployment/cloud-artifact-extractor -n cloud-artifact-extractor
kubectl rollout undo deployment/cloud-artifact-extractor -n cloud-artifact-extractor
```

---

## Monitoring and Operations

### Health Checks

All deployments support the following health endpoints:

```bash
# Readiness check
curl https://<your-endpoint>/api/v1/health/ready

# Liveness check
curl https://<your-endpoint>/api/v1/health/alive
```

### Metrics to Monitor

1. **Application Metrics:**
   - Request latency (p50, p95, p99)
   - Error rate (4xx, 5xx)
   - Throughput (requests/sec)

2. **Infrastructure Metrics:**
   - CPU utilization
   - Memory utilization
   - Disk I/O

3. **Business Metrics:**
   - Extraction job success rate
   - Total artifacts extracted
   - Processing time per cloud provider

### Setting Up Alerts

#### AWS CloudWatch
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name cloud-artifact-extractor-high-errors \
  --alarm-description "Alert on high error rate" \
  --metric-name ErrorCount \
  --namespace AWS/AppRunner \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

#### Azure Monitor
```bash
az monitor metrics alert create \
  --name high-cpu-alert \
  --resource-group <your-rg> \
  --scopes /subscriptions/<id>/resourceGroups/<rg>/providers/Microsoft.App/containerApps/cloud-artifact-extractor \
  --condition "avg CPUUtilization > 80" \
  --window-size 5m \
  --evaluation-frequency 1m
```

#### Google Cloud
Use Cloud Monitoring console or:
```bash
gcloud alpha monitoring policies create \
  --notification-channels=<channel-id> \
  --display-name="High Error Rate"
```

### Security Best Practices for Deployments

1. **Use Managed Identities/Service Accounts:**
   - AWS: IAM roles for App Runner
   - Azure: Managed Identities
   - GCP: Workload Identity

2. **Secure Secrets Management:**
   - Use cloud provider secret managers
   - Never hardcode credentials
   - Rotate secrets regularly

3. **Network Security:**
   - Use private endpoints where available
   - Implement network policies (Kubernetes)
   - Enable VPC/VNET for container deployments

4. **Image Security:**
   - Scan container images for vulnerabilities
   - Use private registries
   - Sign images (optional but recommended)

5. **Access Control:**
   - Principle of least privilege
   - Enable RBAC (Kubernetes)
   - Audit access logs

### Cost Optimization Tips

1. **Right-Size Resources:**
   - Start with minimum specs
   - Monitor and adjust based on metrics
   - Use performance testing

2. **Leverage Auto-Scaling:**
   - Set appropriate min/max replicas
   - Configure scaling thresholds
   - Use schedule-based scaling if applicable

3. **Use Spot/Preemptible Instances:**
   - Kubernetes: Use Spot instances for non-critical workloads
   - AWS: Consider Spot instances
   - GCP: Use preemptible VMs

4. **Monitor Costs:**
   - Set up cost alerts
   - Review monthly spending
   - Optimize data transfer costs

---

## Troubleshooting

### Common Deployment Issues

**Container fails to start:**
1. Check logs for startup errors
2. Verify environment variables
3. Ensure all required credentials are set
4. Check port configuration (default: 8000)

**High latency or timeouts:**
1. Check CPU and memory metrics
2. Review application logs
3. Increase resource allocation
4. Check network connectivity

**Scaling not working:**
1. Verify metrics are being collected
2. Check scaling rules are configured
3. Ensure minimum resources available
4. Review platform-specific scaling documentation

**Out of memory errors:**
1. Increase memory allocation
2. Check for memory leaks in application
3. Review memory metrics
4. Consider caching optimization

### Getting Help

- Review platform-specific guides in `deploy/` directory
- Check application logs for detailed error messages
- Consult cloud provider documentation
- Review troubleshooting sections in deployment guides

---

## Next Steps

1. **Choose your deployment platform** based on requirements
2. **Read the corresponding deployment guide** for detailed instructions
3. **Prepare your environment** with necessary tools and credentials
4. **Deploy the application** using the provided script
5. **Verify deployment** by testing endpoints
6. **Set up monitoring** for production deployments
7. **Configure auto-scaling** for your workload
8. **Implement security best practices** from the guide

For more information, see the deployment guides in the `deploy/` directory.
