---
layout: default
title: Deployment Quick Reference
parent: Deployment
nav_order: 2
---

# Deployment Quick Reference

Quick command reference for deploying Cloud Artifact Extractor to different platforms.

**Last Updated:** November 1, 2025

## One-Command Deployments

### Prerequisites (All Platforms)
```bash
# Build Docker image
docker build -t cloud-artifact-extractor:latest -f Dockerfile .

# Verify image
docker images | grep cloud-artifact-extractor
```

### AWS App Runner
```bash
# Deploy
bash deploy/aws/apprunner-deploy.sh

# Get service URL
aws apprunner describe-service \
  --service-arn "arn:aws:apprunner:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/cloud-artifact-extractor/apprunner-service" \
  --region ${AWS_REGION} \
  --query 'Service.ServiceUrl' \
  --output text

# Test endpoint
curl https://<service-url>/api/v1/health/ready
```

### Azure Container Apps
```bash
# Deploy
bash deploy/azure/container-apps-deploy.sh

# Get application URL
az containerapp show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --query 'properties.configuration.ingress.fqdn' \
  --output tsv

# Test endpoint
curl https://<fqdn>/api/v1/health/ready
```

### Google Cloud Run
```bash
# Deploy
bash deploy/gcp/cloudrun-deploy.sh

# Get service URL
gcloud run services describe cloud-artifact-extractor \
  --format 'value(status.url)'

# Test endpoint
curl https://<url>/api/v1/health/ready
```

### Kubernetes (AWS EKS)
```bash
# Create cluster
bash deploy/kubernetes/aws-eks-deploy.sh

# Deploy application
kubectl apply -f deploy/kubernetes/manifests/

# Get ingress URL
kubectl get ingress -n cloud-artifact-extractor

# Test endpoint
curl https://<ingress-url>/api/v1/health/ready
```

### Kubernetes (Azure AKS)
```bash
# Create cluster
bash deploy/kubernetes/azure-aks-deploy.sh

# Deploy application
kubectl apply -f deploy/kubernetes/manifests/

# Get ingress URL
kubectl get ingress -n cloud-artifact-extractor

# Test endpoint
curl https://<ingress-url>/api/v1/health/ready
```

### Kubernetes (Google GKE)
```bash
# Create cluster
bash deploy/kubernetes/gcp-gke-deploy.sh

# Deploy application
kubectl apply -f deploy/kubernetes/manifests/

# Get ingress URL
kubectl get ingress -n cloud-artifact-extractor

# Test endpoint
curl https://<ingress-url>/api/v1/health/ready
```

---

## Verification Commands

### AWS App Runner
```bash
# Check service status
aws apprunner describe-service --service-arn <service-arn>

# View recent logs
aws logs tail /aws/apprunner/cloud-artifact-extractor/apprunner-service/service-logs --follow

# Get metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=apprunner-service \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Azure Container Apps
```bash
# Check app status
az containerapp show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg

# View logs
az containerapp logs show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --follow

# Get metrics
az monitor metrics list \
  --resource /subscriptions/<id>/resourceGroups/<rg>/providers/Microsoft.App/containerApps/cloud-artifact-extractor \
  --metric CPUUtilization MemoryPercentage
```

### Google Cloud Run
```bash
# Check service details
gcloud run services describe cloud-artifact-extractor

# View recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Get metrics
gcloud monitoring time-series list \
  --filter 'metric.type=run.googleapis.com/request_count'
```

### Kubernetes
```bash
# Check deployment status
kubectl get deployment -n cloud-artifact-extractor

# View pods
kubectl get pods -n cloud-artifact-extractor

# Check pod logs
kubectl logs -n cloud-artifact-extractor -l app=cloud-artifact-extractor -f

# Check resource usage
kubectl top nodes
kubectl top pods -n cloud-artifact-extractor

# Check HPA status
kubectl get hpa -n cloud-artifact-extractor
```

---

## Common Operations

### Scaling

#### AWS App Runner
Auto-scaling enabled by default (no manual configuration needed).

#### Azure Container Apps
```bash
az containerapp update \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --min-replicas 2 \
  --max-replicas 10
```

#### Google Cloud Run
```bash
gcloud run services update cloud-artifact-extractor \
  --min-instances 1 \
  --max-instances 100
```

#### Kubernetes
```bash
kubectl autoscale deployment cloud-artifact-extractor \
  -n cloud-artifact-extractor \
  --min=2 --max=10 --cpu-percent=70
```

### Updating Configuration

#### AWS App Runner
Edit environment variables in AWS Console or update and redeploy.

#### Azure Container Apps
```bash
az containerapp update \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --set-env-vars KEY=value
```

#### Google Cloud Run
```bash
gcloud run services update cloud-artifact-extractor \
  --update-env-vars KEY=value
```

#### Kubernetes
```bash
kubectl set env deployment/cloud-artifact-extractor \
  KEY=value \
  -n cloud-artifact-extractor
```

### Rolling Updates

#### AWS App Runner
Redeploy with new image:
```bash
docker build -t cloud-artifact-extractor:latest .
bash deploy/aws/apprunner-deploy.sh
```

#### Azure Container Apps
```bash
docker build -t cloud-artifact-extractor:latest .
bash deploy/azure/container-apps-deploy.sh
```

#### Google Cloud Run
```bash
docker build -t cloud-artifact-extractor:latest .
bash deploy/gcp/cloudrun-deploy.sh
```

#### Kubernetes
```bash
kubectl set image deployment/cloud-artifact-extractor \
  cloud-artifact-extractor=<registry>/cloud-artifact-extractor:v2 \
  -n cloud-artifact-extractor

# Monitor rollout
kubectl rollout status deployment/cloud-artifact-extractor -n cloud-artifact-extractor
```

### Rolling Back

#### AWS App Runner
Redeploy with previous image.

#### Azure Container Apps
```bash
az containerapp revision list \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg

az containerapp revision set-active \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --revision <revision-name>
```

#### Google Cloud Run
```bash
gcloud run deploy cloud-artifact-extractor --image <previous-image-uri>
```

#### Kubernetes
```bash
kubectl rollout history deployment/cloud-artifact-extractor -n cloud-artifact-extractor
kubectl rollout undo deployment/cloud-artifact-extractor -n cloud-artifact-extractor
```

### Deleting Deployment

#### AWS App Runner
```bash
aws apprunner delete-service \
  --service-arn <your-service-arn>
```

#### Azure Container Apps
```bash
az containerapp delete \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg

# Optional: Delete resource group
az group delete --name cloud-artifact-extractor-rg
```

#### Google Cloud Run
```bash
gcloud run services delete cloud-artifact-extractor
```

#### Kubernetes
```bash
kubectl delete -f deploy/kubernetes/manifests/
kubectl delete namespace cloud-artifact-extractor
```

---

## API Endpoints

### Health Checks
```bash
# Readiness check
curl -X GET https://<endpoint>/api/v1/health/ready

# Liveness check
curl -X GET https://<endpoint>/api/v1/health/alive
```

### Extraction Endpoints
```bash
# Trigger extraction
curl -X POST https://<endpoint>/api/v1/extraction/trigger \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'

# Check job status
curl -X GET https://<endpoint>/api/v1/extraction/jobs/<job_id> \
  -H "Authorization: Bearer <token>"

# List services
curl -X GET https://<endpoint>/api/v1/extraction/services \
  -H "Authorization: Bearer <token>"
```

### Schedule Endpoints
```bash
# Create schedule
curl -X POST https://<endpoint>/api/v1/schedules/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-scan",
    "cron_expression": "0 2 * * *",
    "services": ["ec2", "s3"]
  }'

# List schedules
curl -X GET https://<endpoint>/api/v1/schedules/ \
  -H "Authorization: Bearer <token>"
```

---

## Troubleshooting Checklist

- [ ] Docker image built successfully
- [ ] Cloud CLI tool configured and authenticated
- [ ] Required environment variables set
- [ ] Cloud credentials have necessary permissions
- [ ] Container logs checked for startup errors
- [ ] Health endpoint responding correctly
- [ ] Metrics appearing in cloud provider console
- [ ] Auto-scaling configured (if needed)
- [ ] Firewall/security groups allow ingress traffic

---

## Environment Variable Configuration

All deployments require:

```bash
# Required
ENABLED_PROVIDERS='["aws","azure","gcp"]'
CONFIG_FILE=/app/config/production.yaml
DEBUG=false

# Cloud-specific (if scanning that cloud)
AWS_REGION=us-east-1
AZURE_SUBSCRIPTION_ID=xxxxx
GCP_PROJECT_ID=xxxxx

# Security
JWT_SECRET_KEY=your-secret-key
```

For complete environment variable reference, see individual deployment guides.

---

## Useful Links

- [Full Deployment Guide](./deployment.md)
- [AWS Deployment Guide](../deploy/aws/README.md)
- [Azure Deployment Guide](../deploy/azure/README.md)
- [GCP Deployment Guide](../deploy/gcp/README.md)
- [Kubernetes Deployment Guide](../deploy/kubernetes/README.md)
