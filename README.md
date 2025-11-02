# Cloud Artifact Extractor

Copyright © 2025 Aegis and Pegasys.ai (www.pegasys.ai) - Licensed under MIT License

A FastAPI-based service for extracting and managing cloud service artifacts from AWS, Azure, and GCP.

[![CI](https://github.com/ramesh-pegasys/csp-scanner/actions/workflows/ci.yml/badge.svg)](https://github.com/ramesh-pegasys/csp-scanner/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Flake8](https://img.shields.io/badge/flake8-checked-blue.svg)](https://flake8.pycqa.org/)
[![Black](https://img.shields.io/badge/black-formatted-black.svg)](https://github.com/psf/black)

## Multi-Cloud Support

The CSP Scanner supports extracting resources from **AWS**, **Azure**, and **GCP**. Enable the providers you need:

```bash
# Environment variable
export ENABLED_PROVIDERS='["aws", "azure", "gcp"]'

# Or in YAML config
enabled_providers:
  - aws
  - azure
  - gcp
```

For detailed setup instructions see the consolidated provider guide in the docs: [Cloud Providers Guide](./docs/cloud-providers.md)

- **AWS Setup**: [Amazon Web Services (AWS)](./docs/cloud-providers.md#amazon-web-services-aws)
- **Azure Setup**: [Microsoft Azure](./docs/cloud-providers.md#microsoft-azure)
- **GCP Setup**: [Google Cloud Platform (GCP)](./docs/cloud-providers.md#google-cloud-platform-gcp)

## Deployment

The Cloud Artifact Extractor can be deployed to multiple cloud platforms and Kubernetes clusters. Choose your deployment method based on your infrastructure and operational preferences.

### Quick Deployment Summary

| Cloud Provider | Method | Setup Time | Command | Guide |
|---|---|---|---|---|
| **AWS** | App Runner | 5 min | `bash deploy/aws/apprunner-deploy.sh` | [AWS Guide](./deploy/aws/README.md) |
| **Azure** | Container Apps | 10 min | `bash deploy/azure/container-apps-deploy.sh` | [Azure Guide](./deploy/azure/README.md) |
| **GCP** | Cloud Run | 5 min | `bash deploy/gcp/cloudrun-deploy.sh` | [GCP Guide](./deploy/gcp/README.md) |
| **Kubernetes** | EKS/AKS/GKE | 30 min | See guide for cloud-specific setup | [K8s Guide](./deploy/kubernetes/README.md) |

### Deployment Methods

#### AWS Deployment
- **Recommended: AWS App Runner** - Fully managed container service with automatic scaling
  - Zero infrastructure management
  - Automatic scaling and load balancing
  - Integrated CloudWatch monitoring
  - Pay-per-request pricing

#### Azure Deployment
- **Recommended: Azure Container Apps** - Serverless container service with automatic scaling
  - Fully managed, no infrastructure needed
  - Automatic scaling based on metrics
  - DAPR support for distributed applications
  - Integrated Azure Monitor

#### GCP Deployment
- **Recommended: Google Cloud Run** - Serverless container service with automatic scaling
  - Pay-per-request pricing
  - Automatic scaling from 0 to N instances
  - Fully managed serverless
  - Simple one-command deployment

#### Kubernetes Deployment
- **Multi-Cloud Support:** Deploy to AWS EKS, Azure AKS, or GCP GKE
  - Advanced networking and security
  - Multi-region deployment capabilities
  - Workload Identity integration
  - Enterprise-grade orchestration

### Deployment Prerequisites

**General:**
- Docker installed
- Container image built: `docker build -t cloud-artifact-extractor:latest -f Dockerfile .`

**Cloud Provider Requirements:**
- **AWS**: AWS CLI v2 configured with appropriate IAM permissions
- **Azure**: Azure CLI installed and authenticated (`az login`)
- **GCP**: Google Cloud SDK (`gcloud`) with appropriate project permissions
- **Kubernetes**: `kubectl` configured for your cluster

### Getting Started

1. **Choose your deployment platform** from the table above
2. **Review the deployment guide** for your chosen platform
3. **Prepare your environment** with cloud provider CLI tools
4. **Run the deployment script** from the appropriate `deploy/` subdirectory
5. **Verify the deployment** by testing the service endpoint

For detailed instructions, environment configuration, monitoring setup, and troubleshooting, see the deployment guides in the `deploy/` directory.



## JWT & Certificate Generation Utility

Use `utils/generate_certs_and_jwt.py` to generate static JWT tokens and self-signed certificates for local HTTPS testing.

Run interactively:

```bash
python utils/generate_certs_and_jwt.py
```
and follow the prompts.

Or use CLI options:

```bash
# Generate only JWT token
python utils/generate_certs_and_jwt.py --jwt

# Generate only self-signed certs
python utils/generate_certs_and_jwt.py --certs

# Generate both JWT and certs
python utils/generate_certs_and_jwt.py --jwt --certs

# Specify certs directory and base name
python utils/generate_certs_and_jwt.py --certs --certs-dir ./certs --certs-name server
```

For HTTPS local testing, run Uvicorn with the generated certs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

The `certs/` directory is included in the repo but all contents are ignored via `.gitignore` to prevent accidental check-in of sensitive files.

## Pre-commit Checks

Run the pre-commit check script before pushing changes:

```bash
python utils/precommit_checks.py
```

Or both at once:

```bash
python generate_certs_and_jwt.py --jwt --certs
```

## API Authentication (JWT)

This app uses static JWT tokens for API authentication. To generate a token, use the provided utility script:

```bash
python generate_static_jwt.py
```

Set environment variables to customize:
- `JWT_SECRET_KEY` (default: 'your-secret-key')
- `JWT_ALGORITHM` (default: 'HS256')
- `JWT_EXPIRE_DAYS` (default: 365)

Use the generated token in your API requests:

```
Authorization: Bearer <your-token>
```

**Note:**
- No user management is performed in this app.
- All clients use the same static token for access.

---

**TODO:**
- Implement support for external JWT providers (e.g., Auth0, AWS Cognito, Google IAM) for more advanced authentication options in the future.

## Cloud Provider Credentials Setup

The application requires credentials to access and extract data from your cloud providers. Below is a quick reference for each provider - for comprehensive setup instructions, see the [Cloud Providers Guide](./docs/cloud-providers.md).

### AWS Credentials Setup

**Quick Setup with Environment Variables:**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

**Alternative Methods:**
- AWS credentials file (`~/.aws/credentials`)
- AWS CLI configuration (`aws configure`)
- IAM roles (recommended for production on EC2/ECS/EKS)
- `.env` file in project root

**Verification:**
```bash
python -c "import boto3; print(boto3.Session().get_credentials())"
```

**Required Permissions:** Read-only access to EC2, S3, RDS, Lambda, VPC, CloudFront, API Gateway, ELB, ECS, EKS, App Runner, KMS, IAM

See [AWS Setup Guide](./docs/cloud-providers.md#amazon-web-services-aws) for IAM policies and detailed instructions.

### Azure Credentials Setup

**Quick Setup with Environment Variables:**
```bash
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_DEFAULT_LOCATION="eastus"
```

**Alternative Methods:**
- Azure CLI authentication (`az login`)
- DefaultAzureCredential (automatic credential chain)
- Managed Identity (recommended for production on Azure VMs/App Services)
- `.env` file in project root

**Create Service Principal:**
```bash
az ad sp create-for-rbac --name "csp-scanner-sp" --role "Reader" --scopes /subscriptions/{subscription-id}
```

**Verification:**
```bash
az account show
```

**Required Permissions:** Reader role at subscription level or custom role with read access to VMs, Storage, Network, Web, SQL, AKS, Key Vault

See [Azure Setup Guide](./docs/cloud-providers.md#microsoft-azure) for service principal creation and detailed instructions.

### GCP Credentials Setup

**Quick Setup with Environment Variables:**
```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_CREDENTIALS_PATH="/path/to/service-account-key.json"
export GCP_DEFAULT_REGION="us-central1"
```

**Alternative Methods:**
- Application Default Credentials (`gcloud auth application-default login`)
- Service account attached to Compute Engine/Cloud Run (recommended for production)
- `.env` file in project root

**Create Service Account:**
```bash
gcloud iam service-accounts create csp-scanner \
    --description="Service account for CSP Scanner" \
    --display-name="CSP Scanner"

gcloud iam service-accounts keys create csp-scanner-key.json \
    --iam-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com
```

**Verification:**
```bash
gcloud compute instances list --project=your-project-id
```

**Required Permissions:** Viewer roles for Compute Engine, Cloud Storage, and Resource Manager

See [GCP Setup Guide](./docs/cloud-providers.md#google-cloud-platform-gcp) for IAM roles and detailed instructions.

## Configuration

The application uses configuration files in the `config/` directory to control its behavior. You can customize settings for different environments.

### Configuration Files

- **`config/development.yaml`** - Development environment settings
- **`config/production.yaml`** - Production environment settings
- **`config/extractors.yaml`** - Extractor-specific configuration

### Transport Configuration


The application supports multiple transport methods for sending extracted artifacts using a unified `transport:` node in the config YAML:

#### 1. HTTP Transport (New Structure)
Sends artifacts to a remote HTTP endpoint (e.g., policy scanner):

```yaml
# config/development-aws.yaml
transport:
  type: "http"
  http_endpoint_url: "http://localhost:8001/api/scan"
  api_key: "your-api-key-here"
  timeout_seconds: 30
  max_retries: 3
  headers:
    Content-Type: "application/json"
    User-Agent: "CloudArtifactExtractor/1.0"
```

#### 2. Filesystem Transport (New Structure)
Writes artifacts to local JSON files:

```yaml
# config/development-aws.yaml
transport:
  type: "filesystem"
  base_dir: "./file_collector"
  create_dir: true
```

Each artifact is saved as a separate JSON file with a unique filename in the format:
`{service}_{resource_type}_{resource_id}_{timestamp}_{uuid}.json`

#### 3. Null Transport (New Structure)
Discards artifacts (useful for testing):

```yaml
# config/development-aws.yaml
transport:
  type: "null"
```

### Loading Configuration

By default, the application loads settings from:
1. Environment variables (highest priority)
2. `.env` file in the project root
3. Configuration YAML files in `config/`

To override specific settings, use environment variables:

```bash
# Override transport type
export TRANSPORT_TYPE=filesystem
export FILESYSTEM_BASE_DIR=/tmp/artifacts

# Start the application
uvicorn app.main:app --reload
```

### Example Configuration Files

**Development with Filesystem Transport:**
```yaml
# config/development.yaml
app_name: "Cloud Artifact Extractor"
environment: "development"
debug: true

aws_default_region: "us-east-1"

transport_type: "filesystem"
filesystem_base_dir: "./file_collector"
filesystem_create_dir: true

max_concurrent_extractors: 5
batch_size: 50
batch_delay_seconds: 0.5
```

**Production with HTTP Transport:**
```yaml
# config/production.yaml
app_name: "Cloud Artifact Extractor"
environment: "production"
debug: false

aws_default_region: "us-east-1"

transport_type: "http"
http_endpoint_url: "https://policy-scanner.example.com/api/scan"
transport_timeout_seconds: 30
transport_max_retries: 3

max_concurrent_extractors: 20
batch_size: 200
batch_delay_seconds: 0.1
```

## Usage Examples

### Start the Application

#### Using Default Configuration (Development)
```bash
uvicorn app.main:app --reload
```

#### Using a Specific Configuration File
```bash
# Use development config
CONFIG_FILE=config/development.yaml uvicorn app.main:app --reload

# Use production config
CONFIG_FILE=config/production.yaml uvicorn app.main:app --host 0.0.0.0 --port 8000

# Use custom config
CONFIG_FILE=/path/to/custom-config.yaml uvicorn app.main:app --reload
```

#### Using Environment Variables to Override Settings
```bash
# Override transport type and other settings
export TRANSPORT_TYPE=filesystem
export FILESYSTEM_BASE_DIR=/var/artifacts
export AWS_DEFAULT_REGION=us-west-2

uvicorn app.main:app --reload
```

#### Using Both Config File and Environment Variables
Environment variables always take precedence over config file settings:

```bash
# Load base settings from config, override specific values
CONFIG_FILE=config/production.yaml \
TRANSPORT_TYPE=filesystem \
FILESYSTEM_BASE_DIR=/tmp/artifacts \
uvicorn app.main:app --reload
```

### API Endpoints

#### Trigger Ad-hoc Extraction (All Services, All Regions)
```bash
curl -X POST http://localhost:8000/api/v1/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Trigger Extraction for Specific Services
```bash
curl -X POST http://localhost:8000/api/v1/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "services": ["ec2", "s3", "iam"],
    "regions": ["us-east-1", "us-west-2"],
    "batch_size": 100
  }'
```

#### Check Job Status
```bash
curl http://localhost:8000/api/v1/extraction/jobs/{job_id}
```

#### Create a Schedule (Daily at 2 AM)
```bash
curl -X POST http://localhost:8000/api/v1/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-scan",
    "cron_expression": "0 2 * * *",
    "services": ["ec2", "s3", "rds", "iam"],
    "batch_size": 200
  }'
```

#### List All Schedules
```bash
curl http://localhost:8000/api/v1/schedules/
```

#### List Available Services
```bash
curl http://localhost:8000/api/v1/extraction/services
```