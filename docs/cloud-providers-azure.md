---
layout: default
title: Azure Setup
parent: Cloud Providers
nav_order: 2
---

# Microsoft Azure

## Authentication Methods

### 1. Service Principal (Recommended for Production)

**Create Service Principal:**
```bash
# Login to Azure
az login

# Create service principal with Reader role
az ad sp create-for-rbac --name "csp-scanner-sp" --role "Reader" --scopes /subscriptions/{subscription-id}
```

This outputs:
```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "csp-scanner-sp",
  "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

**Configure Environment Variables:**
```bash
export AZURE_SUBSCRIPTION_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export AZURE_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export AZURE_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # appId
export AZURE_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"      # password
export AZURE_DEFAULT_LOCATION="eastus"
```

### 2. DefaultAzureCredential (Development)

Uses automatic credential chain:

1. Environment variables (`AZURE_CLIENT_ID`, etc.)
2. Managed Identity (when running on Azure resources)
3. Azure CLI credentials (`az login`)
4. Visual Studio Code credentials
5. Azure PowerShell credentials

**Minimal Configuration:**
```bash
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
# Other credentials auto-detected
```

### 3. Azure CLI Authentication

```bash
# Login with Azure CLI
az login

# Set subscription
az account set --subscription "your-subscription-id"
```

## Required Permissions

The service principal or account needs **Reader** role at subscription level.

**Grant Reader Role:**
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

## Custom Role (Least Privilege)

For more restrictive access, create a custom role:

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

## Verification

Test Azure credentials:

```bash
# Using Azure CLI
az account show

# Test service principal
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID

az account show
```

## Supported Azure Services

- **Compute**: Virtual Machines, VM Scale Sets
- **Storage**: Storage Accounts with encryption and network rules
- **Network**: Network Security Groups, Virtual Networks, Load Balancers
- **Web**: App Service Plans, Web Apps, Function Apps
- **SQL**: SQL Servers, SQL Databases
- **Container Service**: AKS Clusters
- **Key Vault**: Key Vaults
- **Authorization**: Role Definitions, Role Assignments

## Security Best Practices

1. **Use Service Principals** for automation
2. **Rotate client secrets** regularly
3. **Apply least privilege** with custom roles
4. **Enable Azure AD MFA**
5. **Monitor with Azure Monitor** and Activity Logs

## Troubleshooting

### "Authentication failed"
- Verify `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`
- Check if service principal has correct permissions
- Test with `az login --service-principal`

### "Subscription not found"
- Verify `AZURE_SUBSCRIPTION_ID` is correct
- Ensure service principal has access to the subscription
- Check if subscription is active

### "Role assignment failed"
- Service principal needs Reader role or equivalent
- Check scope of role assignment (subscription vs resource group)

## Production Deployment

- Use Managed Identity on VMs/App Services
- Store credentials in Azure Key Vault
- Use Azure Policy for governance

## Cost Optimization

- Use Azure Free Account credits
- Leverage Azure Reservations for production
- Monitor costs with Cost Management
