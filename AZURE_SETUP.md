# Azure Setup Guide

This guide explains how to set up Azure support for the CSP Scanner.

## Prerequisites

1. **Azure Subscription**: You need an active Azure subscription
2. **Azure CLI** (optional but recommended): Install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

## Authentication Methods

### Method 1: Service Principal (Recommended for Production)

#### Create a Service Principal

```bash
# Login to Azure
az login

# Create a service principal with Reader role
az ad sp create-for-rbac --name "csp-scanner-sp" --role "Reader" --scopes /subscriptions/{subscription-id}
```

This will output:
```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "csp-scanner-sp",
  "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

#### Configure Environment Variables

Create or update your `.env` file:

```bash
# Enable Azure provider
ENABLED_PROVIDERS=["aws", "azure"]

# Azure Configuration
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  # appId from above
AZURE_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxx       # password from above
AZURE_DEFAULT_LOCATION=eastus
```

### Method 2: DefaultAzureCredential (Development)

If you don't provide explicit credentials, the scanner will use `DefaultAzureCredential` which tries:

1. Environment variables
2. Managed Identity (if running on Azure VM/App Service)
3. Azure CLI credentials
4. Visual Studio Code credentials
5. Azure PowerShell credentials

#### Using Azure CLI Credentials

```bash
# Login with Azure CLI
az login

# Set subscription (if you have multiple)
az account set --subscription "your-subscription-id"
```

Then configure only these environment variables:

```bash
ENABLED_PROVIDERS=["aws", "azure"]
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## Required Permissions

The service principal or account needs **Reader** role at the subscription level or specific resource groups.

### Minimum Required Permissions

```json
{
  "Name": "CSP Scanner Reader",
  "Description": "Read access for cloud security scanning",
  "Actions": [
    "Microsoft.Compute/virtualMachines/read",
    "Microsoft.Compute/virtualMachineScaleSets/read",
    "Microsoft.Storage/storageAccounts/read",
    "Microsoft.Storage/storageAccounts/blobServices/read",
    "Microsoft.Network/networkSecurityGroups/read",
    "Microsoft.Network/virtualNetworks/read",
    "Microsoft.Network/loadBalancers/read",
    "Microsoft.Web/sites/read",
    "Microsoft.Sql/servers/read",
    "Microsoft.Sql/servers/databases/read",
    "Microsoft.ContainerService/managedClusters/read",
    "Microsoft.KeyVault/vaults/read"
  ],
  "NotActions": [],
  "DataActions": [],
  "NotDataActions": []
}
```

### Grant Reader Role (Recommended)

```bash
# For entire subscription
az role assignment create \
  --assignee {client-id} \
  --role "Reader" \
  --scope "/subscriptions/{subscription-id}"

# For specific resource group
az role assignment create \
  --assignee {client-id} \
  --role "Reader" \
  --scope "/subscriptions/{subscription-id}/resourceGroups/{resource-group-name}"
```

## Configuration Examples

### AWS + Azure Multi-Cloud

```bash
# .env
ENABLED_PROVIDERS=["aws", "azure"]

# AWS
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1

# Azure
AZURE_SUBSCRIPTION_ID=your-sub-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_DEFAULT_LOCATION=eastus
```

### Azure Only

```bash
# .env
ENABLED_PROVIDERS=["azure"]

AZURE_SUBSCRIPTION_ID=your-sub-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### Using YAML Configuration

Create `config/production.yaml`:

```yaml
enabled_providers:
  - azure

azure_subscription_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
azure_tenant_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
azure_client_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
azure_client_secret: "xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
azure_default_location: "eastus"

transport_type: "http"
scanner_endpoint_url: "https://your-scanner.example.com"
```

Then run:

```bash
export CONFIG_FILE=config/production.yaml
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Verify Azure Connection

After starting the application, verify Azure is enabled:

```bash
# Check enabled providers
curl http://localhost:8000/providers

# Expected response:
{
  "providers": ["azure"],
  "total": 1
}

# List Azure services
curl http://localhost:8000/services?provider=azure

# Expected response:
{
  "services_by_provider": {
    "azure": [
      {
        "service": "compute",
        "description": "Extracts Azure Virtual Machines and VM Scale Sets",
        "resource_types": ["virtual-machine", "vmss"],
        "version": "1.0.0"
      },
      ...
    ]
  },
  "total_services": 3
}
```

## Troubleshooting

### Issue: "azure-identity not installed"

```bash
pip install -r requirements.txt
```

### Issue: Authentication Failed

```bash
# Test Azure CLI login
az account show

# Verify service principal
az login --service-principal \
  -u {client-id} \
  -p {client-secret} \
  --tenant {tenant-id}

# List resources to verify permissions
az resource list --subscription {subscription-id}
```

### Issue: No Azure Extractors Available

Check logs for:
```
INFO - Initializing Azure session...
INFO - Azure session initialized
INFO - Registered extractor: azure:compute
INFO - Registered extractor: azure:storage
INFO - Registered extractor: azure:network
```

If missing, verify:
1. `ENABLED_PROVIDERS` includes "azure"
2. Azure credentials are correctly configured
3. Azure SDK packages are installed

## Security Best Practices

1. **Use Service Principal**: Don't use personal accounts for production
2. **Least Privilege**: Grant only Reader role, not Contributor
3. **Rotate Secrets**: Regularly rotate client secrets
4. **Audit Logs**: Enable Azure Activity Logs to monitor access
5. **Secure Storage**: Store credentials in Azure Key Vault or similar
6. **Network Security**: Restrict network access if running in Azure

## Next Steps

- See [AZURE_RESOURCES.md](./AZURE_RESOURCES.md) for supported resource types
- See [AZURE_INTEGRATION_PLAN.md](./AZURE_INTEGRATION_PLAN.md) for architecture details
- Configure extractor settings in `config/extractors.yaml`
