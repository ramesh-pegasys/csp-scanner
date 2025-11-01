# Cloud Artifact Extractor

Copyright © 2025 Aegis and Pegasys.ai (www.pegasys.ai) - Licensed under MIT License

A FastAPI-based service for extracting and managing cloud service artifacts from AWS, Azure, and GCP.

[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)
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

The application supports multiple transport methods for sending extracted artifacts:

#### 1. HTTP Transport (Default)
Sends artifacts to a remote HTTP endpoint (e.g., policy scanner):

```yaml
# config/development.yaml
transport_type: "http"
scanner_endpoint_url: "http://localhost:8001/api/scan"
transport_timeout_seconds: 30
transport_max_retries: 3
```

#### 2. Filesystem Transport
Writes artifacts to local JSON files:

```yaml
# config/development.yaml
transport_type: "filesystem"
filesystem_base_dir: "./file_collector"
filesystem_create_dir: true
```

Each artifact is saved as a separate JSON file with a unique filename in the format:
`{service}_{resource_type}_{resource_id}_{timestamp}_{uuid}.json`

#### 3. Null Transport
Discards artifacts (useful for testing):

```yaml
# config/development.yaml
transport_type: "null"
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
scanner_endpoint_url: "https://policy-scanner.example.com/api/scan"
transport_timeout_seconds: 60
transport_max_retries: 5

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