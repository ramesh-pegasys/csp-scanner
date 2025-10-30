---
layout: default
title: Cloud Providers
nav_order: 4
---

# Cloud Provider Setup

This guide provides detailed setup instructions for each supported cloud provider: AWS, Azure, and GCP.

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

## Amazon Web Services (AWS)

### Authentication Methods

#### 1. IAM User Credentials (Development/Testing)

**Create IAM User:**
1. Go to AWS IAM Console
2. Create a new IAM user
3. Attach appropriate policies (e.g., `ReadOnlyAccess` or specific service read permissions)
4. Generate access keys

**Configure Credentials:**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

#### 2. AWS CLI Configuration

If you have AWS CLI installed:

```bash
aws configure
```

This creates credentials in `~/.aws/credentials` and region in `~/.aws/config`.

#### 3. IAM Roles (Recommended for Production)

When running on EC2/ECS/EKS, use IAM roles attached to the instance/service.

**No explicit credentials needed** - the application automatically uses the instance role.

#### 4. Environment Variables

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="secret..."
export AWS_DEFAULT_REGION="us-east-1"
export AWS_SESSION_TOKEN="token..."  # For temporary credentials
```

#### 5. AWS Profile

```bash
export AWS_PROFILE="production"
```

Uses the specified profile from `~/.aws/credentials`.

### Required Permissions

For comprehensive scanning, your credentials should have read-only access to these services:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:Describe*",
                "s3:List*",
                "s3:Get*",
                "rds:Describe*",
                "lambda:List*",
                "lambda:Get*",
                "vpc:Describe*",
                "cloudfront:List*",
                "apigateway:GET",
                "elasticloadbalancing:Describe*",
                "ecs:Describe*",
                "ecs:List*",
                "eks:Describe*",
                "eks:List*",
                "apprunner:Describe*",
                "apprunner:List*",
                "kms:Describe*",
                "kms:List*",
                "iam:List*",
                "iam:Get*"
            ],
            "Resource": "*"
        }
    ]
}
```

**Predefined Policy:** `ReadOnlyAccess`

### Verification

Test your AWS credentials:

```bash
# Using AWS CLI
aws sts get-caller-identity

# Using Python
python -c "import boto3; print(boto3.Session().get_credentials())"
```

### Supported AWS Services

- **EC2**: Instances, Security Groups, Network Interfaces
- **S3**: Buckets with policies and configurations
- **RDS**: Database instances and clusters
- **Lambda**: Functions with configurations
- **IAM**: Users, Roles, Policies
- **VPC**: VPCs, Subnets, Route Tables, NAT Gateways
- **ECS**: Clusters, Services, Task Definitions
- **EKS**: Kubernetes clusters
- **ELB**: Application and Network Load Balancers
- **AppRunner**: Services
- **CloudFront**: Distributions
- **API Gateway**: REST APIs
- **KMS**: Keys and key policies

## Microsoft Azure

### Authentication Methods

#### 1. Service Principal (Recommended for Production)

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

#### 2. DefaultAzureCredential (Development)

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

#### 3. Azure CLI Authentication

```bash
# Login with Azure CLI
az login

# Set subscription
az account set --subscription "your-subscription-id"
```

### Required Permissions

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

### Custom Role (Least Privilege)

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

### Verification

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

### Supported Azure Services

- **Compute**: Virtual Machines, VM Scale Sets
- **Storage**: Storage Accounts with encryption and network rules
- **Network**: Network Security Groups, Virtual Networks, Load Balancers
- **Web**: App Service Plans, Web Apps, Function Apps
- **SQL**: SQL Servers, SQL Databases
- **Container Service**: AKS Clusters
- **Key Vault**: Key Vaults
- **Authorization**: Role Definitions, Role Assignments

## Google Cloud Platform (GCP)

### Authentication Methods

#### 1. Service Account Key File (Recommended for Production)

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

#### 2. Application Default Credentials (ADC)

For local development:

```bash
# Authenticate with user account
gcloud auth application-default login

# Set project
export GCP_PROJECT_ID="your-project-id"
```

When running on GCP resources (Compute Engine, Cloud Run, etc.), ADC automatically uses the instance's service account.

### Required Permissions

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

### Custom Role (Least Privilege)

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

### Verification

Test GCP credentials:

```bash
# Using gcloud CLI
gcloud compute instances list --project=your-project-id
gcloud storage buckets list --project=your-project-id

# Test service account key
gcloud auth activate-service-account --key-file=/path/to/service-account-key.json
gcloud compute instances list --project=your-project-id
```

### Supported GCP Services

- **Compute Engine**: VM Instances, Managed Instance Groups
- **Cloud Storage**: Storage Buckets with full configuration

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

## Security Best Practices

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

## Troubleshooting

### AWS Issues

**"Unable to locate credentials"**
- Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set
- Verify credentials are not expired
- Test with `aws sts get-caller-identity`

**"Access denied"**
- Verify IAM permissions include required actions
- Check if MFA is required for the operation
- Ensure you're using the correct AWS account/region

**"Region not supported"**
- Some services have limited regional availability
- Check AWS service availability by region

### Azure Issues

**"Authentication failed"**
- Verify `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`
- Check if service principal has correct permissions
- Test with `az login --service-principal`

**"Subscription not found"**
- Verify `AZURE_SUBSCRIPTION_ID` is correct
- Ensure service principal has access to the subscription
- Check if subscription is active

**"Role assignment failed"**
- Service principal needs Reader role or equivalent
- Check scope of role assignment (subscription vs resource group)

### GCP Issues

**"Could not automatically determine credentials"**
- Set `GCP_CREDENTIALS_PATH` to service account key file
- Or run `gcloud auth application-default login`
- Check file permissions on key file

**"Permission denied"**
- Verify service account has required IAM roles
- Check project ID is correct
- Ensure APIs are enabled (Compute API, Storage API)

**"API not enabled"**
- Enable required APIs: `gcloud services enable compute.googleapis.com storage.googleapis.com`
- Some APIs require billing to be enabled

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
2. **Test authentication** using the verification commands above
3. **Configure the scanner** using environment variables or YAML files
4. **Run a test extraction** to verify everything works
5. **Set up automated scanning** with schedules
6. **Configure transport** to send artifacts to your policy scanner

For detailed configuration options, see the [Configuration Guide](/csp-scanner/configuration.html).