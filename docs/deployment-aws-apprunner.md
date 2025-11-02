---
layout: default
title: AWS App Runner Deployment
parent: Deployment
nav_order: 3
---

# AWS App Runner Deployment Guide

Deploy Cloud Artifact Extractor to AWS using App Runner - a fully managed container service with automatic scaling and monitoring.

## Quick Start

```bash
bash deploy/aws/apprunner-deploy.sh
```

Setup takes approximately **5 minutes**.

## What is AWS App Runner?

**Use Case:** Easiest managed container deployment with automatic scaling and monitoring.

- **Pros:**
  - Fully managed service (no infrastructure to manage)
  - Automatic scaling and load balancing
  - Built-in VPC support
  - Simple CI/CD integration with source repository
  - Low operational overhead
  - Pay-per-request pricing
  - Integrated with AWS CloudWatch and X-Ray
- **Cons:**
  - Less control over underlying infrastructure
  - Limited networking customization

## Prerequisites

- AWS CLI v2 installed and configured
- Docker installed
- Appropriate IAM permissions
- Container image built and ready

## Environment Configuration

The deployment requires these environment variables:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Service Configuration
ENABLED_PROVIDERS=["aws", "azure", "gcp"]
CONFIG_FILE=/app/config/production.yaml
HTTP_ENDPOINT_URL=https://your-scanner-endpoint.com
DEBUG=false

# For Azure Integration (if enabled)
AZURE_SUBSCRIPTION_ID=xxxxx
AZURE_TENANT_ID=xxxxx
AZURE_CLIENT_ID=xxxxx
AZURE_CLIENT_SECRET=xxxxx

# For GCP Integration (if enabled)
GCP_PROJECT_ID=xxxxx
GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-credentials.json

# JWT & Security
JWT_SECRET_KEY=your-secure-secret-key
```

## Architecture

```
┌─────────────────────────────────────────┐
│         App Runner Service              │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │  Container Instance (Auto-scaled) │  │
│  │                                   │  │
│  │  Cloud Artifact Extractor        │  │
│  │  (FastAPI Application)           │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         ↓
  CloudWatch Logs & Metrics
  X-Ray Tracing
  VPC Networking
```

## Deployment Steps

### 1. Build Container Image

```bash
docker build -t cloud-artifact-extractor:latest -f Dockerfile .
```

### 2. Run Deployment Script

```bash
bash deploy/aws/apprunner-deploy.sh
```

The script will:
- Create an ECR repository
- Push your container image
- Create an IAM role with necessary permissions
- Create the App Runner service
- Configure CloudWatch logging

### 3. Verify Deployment

```bash
# Get the service URL
aws apprunner describe-service \
  --service-arn "arn:aws:apprunner:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/cloud-artifact-extractor/apprunner-service" \
  --region ${AWS_REGION} \
  --query 'Service.ServiceUrl' \
  --output text

# Test the endpoint
curl https://<service-url>/api/v1/health/ready
```

## Monitoring & Logging

### CloudWatch Logs

```bash
# View logs
aws logs tail /aws/apprunner/cloud-artifact-extractor/apprunner-service/service-logs --follow

# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=apprunner-service \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### X-Ray Tracing

Enable X-Ray for distributed tracing:

```bash
aws apprunner update-service \
  --service-arn <service-arn> \
  --observability-configuration-arn arn:aws:apprunner:${AWS_REGION}::observability-configuration/XRayTracingEnabled
```

## Scaling Configuration

App Runner automatically scales based on request metrics:

- **Minimum instances:** 1
- **Maximum instances:** 25
- **Scaling metric:** CPU utilization and request count
- **Scale-up:** When average CPU > 70%
- **Scale-down:** When average CPU < 40%

Adjust in the deployment script if needed.

## Security Best Practices

1. **Use Managed Identity:** App Runner uses an IAM role automatically
2. **Private VPC:** Deploy within a VPC for private connectivity
3. **Secrets Management:** Use AWS Secrets Manager for sensitive data
4. **Encryption:** Enable encryption in transit (HTTPS) and at rest
5. **Network Security:** Use security groups to control traffic
6. **Audit Logging:** Enable CloudTrail for API audit logs
7. **Image Scanning:** Enable ECR image scanning for vulnerabilities

## Cost Optimization

- **Right-sizing:** Start with standard configuration and adjust based on metrics
- **Reserved Capacity:** Use App Runner reserved capacity for predictable workloads
- **CloudFront:** Add CloudFront for caching to reduce origin requests
- **Auto-scaling:** Leverage automatic scaling to avoid over-provisioning

## Troubleshooting

### Service fails to start

```bash
# Check the service status
aws apprunner describe-service \
  --service-arn <service-arn> \
  --region ${AWS_REGION}

# View logs for errors
aws logs tail /aws/apprunner/cloud-artifact-extractor/apprunner-service/service-logs --follow
```

**Common causes:**
- Container image not found in ECR
- Missing environment variables
- Port 8000 not exposed
- Insufficient IAM permissions
- Application startup errors

### High latency

```bash
# Check CPU and memory metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name CPUUtilization \
  --statistics Average \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)Z \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)Z \
  --period 60 \
  --dimensions Name=ServiceName,Value=apprunner-service
```

**Solutions:**
- Increase instance size (cpu/memory)
- Check cloud provider API rate limits
- Review application logs for bottlenecks

### Connection issues

```bash
# Verify service is running
aws apprunner describe-service \
  --service-arn <service-arn> \
  --query 'Service.Status' \
  --region ${AWS_REGION}

# Check security groups and network configuration
aws ec2 describe-security-groups --filters "Name=group-name,Values=cloud-artifact-extractor-sg"
```

## Post-Deployment Configuration

### 1. Set up CloudWatch Alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name cloud-artifact-extractor-cpu-high \
  --alarm-description "Alert when CPU is high" \
  --metric-name CPUUtilization \
  --namespace AWS/AppRunner \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 2. Configure Custom Domain

```bash
aws apprunner associate-custom-domain \
  --service-arn <service-arn> \
  --domain-name api.example.com \
  --enable-www-subdomain
```

### 3. Set up Auto-deployment from GitHub/GitLab

See the AWS console for connecting your repository for automatic deployments.

## Updating the Deployment

### Update Application Code

```bash
# Build new image
docker build -t cloud-artifact-extractor:latest -f Dockerfile .

# Re-run deployment script
bash deploy/aws/apprunner-deploy.sh
```

### Update Configuration

```bash
aws apprunner update-service \
  --service-arn <service-arn> \
  --source-configuration ImageRepository="{ImageIdentifier=<new-image-uri>,ImageRepositoryType=ECR,ImageConfiguration={Port=8000,RuntimeEnvironmentVariables={KEY=value}}}"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to App Runner

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to App Runner
        run: bash deploy/aws/apprunner-deploy.sh
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1
          AWS_ACCOUNT_ID: ${{ secrets.AWS_ACCOUNT_ID }}
```

## Comparison with Other AWS Options

| Feature | App Runner | ECS Fargate | Lambda | EC2 |
|---------|-----------|-----------|--------|-----|
| Setup Time | 5 min | 20 min | 15 min | 30 min |
| Scaling | Auto | Manual/Auto | Auto | Manual/Auto |
| Pricing | Request-based | CPU/Memory-based | Execution-based | Hourly |
| Container Support | Yes | Yes | Yes | Yes |
| Networking | VPC | VPC | Limited | Full |
| Best For | Web APIs | Production | Async tasks | Custom |

## Next Steps

1. ✅ Deploy using `apprunner-deploy.sh`
2. ⏳ Wait for service to be ready (2-5 minutes)
3. 📊 Set up monitoring and alarms
4. 🔐 Configure secrets in Secrets Manager
5. 🔄 Set up CI/CD for automated deployments
6. 📈 Monitor metrics and optimize as needed

## Additional Resources

- [AWS App Runner Documentation](https://docs.aws.amazon.com/apprunner/)
- [App Runner Pricing](https://aws.amazon.com/apprunner/pricing/)
- [App Runner Best Practices](https://docs.aws.amazon.com/apprunner/latest/dg/best-practices.html)
- [CloudWatch Metrics](https://docs.aws.amazon.com/apprunner/latest/dg/monitor-cloudwatch.html)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)