# Azure Container Apps Deployment Guide

Deploy Cloud Artifact Extractor to Azure using Container Apps - a fully managed serverless container service with automatic scaling.

## Quick Start

```bash
bash deploy/azure/container-apps-deploy.sh
```

Setup takes approximately **10 minutes**.

## What is Azure Container Apps?

**Use Case:** Modern, serverless container deployment with automatic scaling and monitoring.

- **Pros:**
  - Fully managed service (no infrastructure to manage)
  - Automatic scaling based on metrics
  - Built-in networking and service discovery
  - Easy CI/CD integration
  - DAPR support for distributed applications
  - Pay-per-compute resources
  - Integrated with Azure Monitor
- **Cons:**
  - Relatively newer service (less mature than AKS)
  - Some advanced features still in preview

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Docker installed
- Appropriate Azure permissions (Contributor role on subscription)

## Environment Configuration

The deployment requires these environment variables:

```bash
# Azure Configuration
AZURE_SUBSCRIPTION_ID=xxxxxx
AZURE_RESOURCE_GROUP=cloud-artifact-extractor-rg
AZURE_LOCATION=eastus
AZURE_CONTAINER_REGISTRY_NAME=yourregistryname

# Service Configuration
ENABLED_PROVIDERS=["aws", "azure", "gcp"]
CONFIG_FILE=/app/config/production.yaml
HTTP_ENDPOINT_URL=https://your-scanner-endpoint.com
DEBUG=false

# Azure Integration (if scanning Azure)
AZURE_TENANT_ID=xxxxx
AZURE_CLIENT_ID=xxxxx
AZURE_CLIENT_SECRET=xxxxx

# AWS Integration (if scanning AWS)
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx

# GCP Integration (if scanning GCP)
GCP_PROJECT_ID=xxxxx
GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-credentials.json

# Security
JWT_SECRET_KEY=your-secure-secret-key
```

## Architecture

```
┌─────────────────────────────────────────┐
│    Azure Container Apps Environment     │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │ Container App (Auto-scaled)       │  │
│  │                                   │  │
│  │ Cloud Artifact Extractor         │  │
│  │ (FastAPI Application)            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         ↓
  Azure Monitor & Logging
  Application Insights
  Virtual Network
```

## Deployment Steps

### 1. Build Container Image

```bash
docker build -t cloud-artifact-extractor:latest -f Dockerfile .
```

### 2. Run Deployment Script

```bash
bash deploy/azure/container-apps-deploy.sh
```

The script will:
- Create an Azure resource group
- Create an Azure Container Registry
- Build and push your container image
- Create a Log Analytics workspace
- Create Container App environment
- Deploy the Container App service
- Configure auto-scaling

### 3. Verify Deployment

```bash
# Get the application URL
az containerapp show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --query 'properties.configuration.ingress.fqdn' \
  --output tsv

# Test the endpoint
curl https://<fqdn>/api/v1/health/ready
```

## Monitoring & Logging

### Azure Monitor Logs

```bash
# View logs
az containerapp logs show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --follow

# View metrics
az monitor metrics list \
  --resource /subscriptions/<id>/resourceGroups/<rg>/providers/Microsoft.App/containerApps/cloud-artifact-extractor \
  --metric CPUUtilization MemoryPercentage
```

### Application Insights

Enable Application Insights for detailed APM and diagnostics:

```bash
# Create Application Insights resource
az monitor app-insights component create \
  --app cloud-artifact-extractor \
  --location eastus \
  --resource-group cloud-artifact-extractor-rg \
  --application-type web
```

## Scaling Configuration

Container Apps automatically scales based on metrics:

- **Minimum replicas:** 2
- **Maximum replicas:** 10
- **CPU target:** 70%
- **Memory target:** 80%

Adjust in the deployment script if needed.

## Security Best Practices

1. **Use Managed Identity:** Enable system-assigned managed identity
2. **Private Registry:** Use private Azure Container Registry
3. **Secrets Management:** Use Azure Key Vault for sensitive data
4. **Network Security:** Deploy within a virtual network
5. **Encryption:** Enable encryption in transit (HTTPS) and at rest
6. **Audit Logging:** Enable Azure Audit Logs
7. **Image Scanning:** Enable image vulnerability scanning
8. **Network Access:** Use Network Security Groups (NSG)

## Cost Optimization

- **Right-sizing:** Start with standard configuration and adjust
- **Consumption plan:** Use consumption-based pricing for variable workloads
- **Reserved Capacity:** Reserve capacity for predictable workloads
- **Auto-scaling:** Leverage automatic scaling to avoid over-provisioning

## Troubleshooting

### Service fails to start

```bash
# Check the app status
az containerapp show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --query 'properties.provisioningState'

# View logs for errors
az containerapp logs show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg
```

**Common causes:**
- Container image not found in registry
- Missing environment variables
- Port 8000 not exposed
- Insufficient permissions
- Application startup errors

### High latency

```bash
# Check CPU and memory metrics
az monitor metrics list \
  --resource /subscriptions/<id>/resourceGroups/<rg>/providers/Microsoft.App/containerApps/cloud-artifact-extractor \
  --metric CPUUtilization MemoryPercentage \
  --start-time 2024-01-01T00:00:00Z
```

**Solutions:**
- Increase resource allocation (CPU/memory)
- Review application logs
- Check network throughput

### Connection issues

```bash
# Verify app is running
az containerapp show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --query 'properties.runningStatus'

# Check ingress configuration
az containerapp ingress show \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg
```

## Post-Deployment Configuration

### 1. Set up Azure Alerts

```bash
az monitor metrics alert create \
  --name cloud-artifact-extractor-cpu-high \
  --resource-group cloud-artifact-extractor-rg \
  --scopes /subscriptions/<id>/resourceGroups/<rg>/providers/Microsoft.App/containerApps/cloud-artifact-extractor \
  --condition "avg CPUUtilization > 80" \
  --window-size 5m \
  --evaluation-frequency 1m
```

### 2. Configure Custom Domain

```bash
az containerapp hostname add \
  --hostname api.example.com \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg
```

### 3. Set up Continuous Deployment

Connect your GitHub/GitLab repository for automatic deployments through Azure Portal.

## Updating the Deployment

### Update Application Code

```bash
# Build new image
docker build -t cloud-artifact-extractor:latest -f Dockerfile .

# Re-run deployment script
bash deploy/azure/container-apps-deploy.sh
```

### Update Configuration

```bash
az containerapp update \
  --name cloud-artifact-extractor \
  --resource-group cloud-artifact-extractor-rg \
  --set-env-vars KEY=value
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Container Apps
        run: bash deploy/azure/container-apps-deploy.sh
        env:
          AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          AZURE_RESOURCE_GROUP: cloud-artifact-extractor-rg
          AZURE_LOCATION: eastus
```

## Next Steps

1. ✅ Deploy using `container-apps-deploy.sh`
2. ⏳ Wait for service to be ready (10-15 minutes)
3. 📊 Set up monitoring and alerts
4. 🔐 Configure secrets in Key Vault
5. 🔄 Set up CI/CD for automated deployments
6. 📈 Monitor metrics and optimize as needed

## Additional Resources

- [Azure Container Apps Documentation](https://docs.microsoft.com/en-us/azure/container-apps/)
- [Container Apps Pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)
- [Container Apps Best Practices](https://learn.microsoft.com/en-us/azure/container-apps/best-practices)
- [Azure Monitor Documentation](https://docs.microsoft.com/en-us/azure/azure-monitor/)
- [Azure Security Best Practices](https://docs.microsoft.com/en-us/azure/security/)

## Quick Comparison

| Feature | Container Apps | App Service | AKS |
|---------|-----------------|-------------|-----|
| Setup Time | 10 min | 10 min | 30 min |
| Scaling | Auto | Manual/Auto | Auto/Manual |
| Pricing | Resource-based | App Service plan | Per-node |
| Best For | Production APIs | Traditional apps | Enterprise |
| Complexity | Low | Low | High |

## Networking Configuration

### For Container Apps
- Use Azure Virtual Network (vnet) for private deployments
- Use Network Security Groups for firewall rules
- Use Azure Firewall for centralized security

### For AKS
- Use Azure CNI or kubenet for networking
- Implement network policies
- Use Azure Service Mesh (ASM) for advanced traffic management
- Use Azure Private Link for private cluster access

## Monitoring & Logging

All deployments integrate with:
- **Azure Monitor:** Metrics and logs
- **Application Insights:** APM and diagnostics
- **Log Analytics:** Centralized log analysis
- **Azure Alerts:** Alert on conditions

## Security Best Practices

1. Use Azure Container Registry with private endpoints
2. Enable Managed Identity for authentication
3. Use Azure Key Vault for secrets
4. Implement network policies (AKS)
5. Enable Azure Policy for compliance
6. Use Azure DDoS Protection for public endpoints
7. Enable Azure Defender for container images
8. Use pod security policies (AKS)

## Cost Optimization

1. **Container Apps:** Use consumption plan for variable workloads
2. **App Service:** Use reserved instances for predictable load
3. **AKS:** Use Azure Spot Instances for cost reduction

## Auto Scaling Configuration

### Container Apps
```yaml
scaling:
  minReplicas: 2
  maxReplicas: 10
  rules:
    - name: cpu-scaling
      azureQueue:
        auth: connection
        queueLength: 5
```

### AKS
```yaml
autoscaling:
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Functions
- Automatic based on queue length or timer triggers
- Configure premium plan for dedicated resources

## Troubleshooting

### Common Issues

**Container fails to start:**
- Check logs: `az container logs --resource-group <rg> --name <name>`
- Verify image in registry
- Check environment variables
- Verify networking access

**High latency:**
- Check container metrics in Azure Portal
- Review Application Insights traces
- Check network throughput
- Monitor CPU and memory usage

**Scaling not working:**
- Verify scaling rules are configured
- Check metrics availability
- Ensure sufficient capacity in region

## Next Steps

1. Choose your deployment method above
2. Review the corresponding deployment script
3. Update configuration values for your Azure subscription
4. Run the deployment script
5. Monitor through Azure Portal or CLI
6. Set up monitoring and alerts

## Additional Resources

- [Azure Container Instances](https://docs.microsoft.com/en-us/azure/container-instances/)
- [Azure Container Apps](https://docs.microsoft.com/en-us/azure/container-apps/)
- [Azure App Service](https://docs.microsoft.com/en-us/azure/app-service/)
- [Azure Kubernetes Service](https://docs.microsoft.com/en-us/azure/aks/)
- [Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/)
- [Azure Security Best Practices](https://docs.microsoft.com/en-us/azure/security/)
