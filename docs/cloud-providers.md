---
layout: default
title: Cloud Providers
nav_order: 4
has_children: true
---

# Cloud Provider Setup

This guide provides detailed setup instructions for each supported cloud provider. For provider-specific information, see:

- [AWS Setup]({{ '/cloud-providers-aws.html' | relative_url }})
- [Azure Setup]({{ '/cloud-providers-azure.html' | relative_url }})
- [GCP Setup]({{ '/cloud-providers-gcp.html' | relative_url }})

For detailed configuration options, see the [Configuration Guide]({{ '/configuration.html' | relative_url }}).

## Multi-Cloud Configuration

You can enable one or more cloud providers in your configuration:

```yaml
# config/production.yaml
enabled_providers:
  - aws
  - azure
  - gcp
```

```bash
# Environment variable
export ENABLED_PROVIDERS='["aws", "azure", "gcp"]'
```

## Multi-Cloud Setup Examples

### AWS + Azure + GCP

```bash
# Enable all providers
export ENABLED_PROVIDERS='["aws", "azure", "gcp"]'

# AWS credentials
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export AWS_DEFAULT_REGION="us-east-1"

# Azure credentials
export AZURE_SUBSCRIPTION_ID="your-sub-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# GCP credentials
export GCP_PROJECT_ID="your-project-id"
export GCP_CREDENTIALS_PATH="/path/to/service-account-key.json"
```

### AWS Only

```bash
export ENABLED_PROVIDERS='["aws"]'
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export AWS_DEFAULT_REGION="us-east-1"
```

### Azure + GCP

```bash
export ENABLED_PROVIDERS='["azure", "gcp"]'

# Azure
export AZURE_SUBSCRIPTION_ID="your-sub-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# GCP
export GCP_PROJECT_ID="your-project-id"
export GCP_CREDENTIALS_PATH="/path/to/service-account-key.json"
```

## Security Best Practices Summary

### AWS
1. **Use IAM Roles** instead of access keys when possible
2. **Rotate access keys** regularly
3. **Apply least privilege** principle
4. **Use MFA** for IAM users
5. **Monitor with CloudTrail** for audit logs

### Azure
1. **Use Service Principals** for automation
2. **Rotate client secrets** regularly
3. **Apply least privilege** with custom roles
4. **Enable Azure AD MFA**
5. **Monitor with Azure Monitor** and Activity Logs

### GCP
1. **Use Service Accounts** with minimal permissions
2. **Rotate service account keys** regularly
3. **Store keys securely** (Secret Manager, etc.)
4. **Enable key rotation** policies
5. **Monitor with Cloud Audit Logs**

## Production Deployment

### AWS
- Use IAM roles on EC2/ECS/EKS
- Store credentials in AWS Secrets Manager or Parameter Store
- Use AWS Config for compliance monitoring

### Azure
- Use Managed Identity on VMs/App Services
- Store credentials in Azure Key Vault
- Use Azure Policy for governance

### GCP
- Use service account attached to Compute Engine/Cloud Run
- Store keys in Secret Manager
- Use Organization Policies for governance

## Cost Optimization

### AWS
- Use Spot Instances for testing
- Leverage AWS Free Tier for development
- Monitor costs with Cost Explorer

### Azure
- Use Azure Free Account credits
- Leverage Azure Reservations for production
- Monitor costs with Cost Management

### GCP
- Use GCP Free Tier credits
- Leverage Committed Use Discounts
- Monitor costs with Billing reports

## Next Steps

1. **Choose your cloud providers** and gather credentials
2. **Test authentication** using the verification commands in the provider-specific guides
3. **Configure the scanner** using environment variables or YAML files
