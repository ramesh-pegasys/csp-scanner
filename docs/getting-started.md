---
layout: default
title: Getting Started
nav_order: 2
---

# Getting Started

This guide will help you get the Cloud Artifact Extractor up and running quickly. Whether you're new to the project or setting up a new environment, follow these steps to get started.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10 or higher** installed on your system
- **Git** for cloning the repository
- **Cloud provider credentials** (AWS, Azure, or GCP) for the providers you want to scan

### Checking Python Version

```bash
python --version
# Should show Python 3.10 or higher
```

If you need to install Python, visit [python.org](https://python.org) for installation instructions.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ramesh-pegasys/csp-scanner.git
cd csp-scanner
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
# Check that key packages are installed
python -c "import fastapi, boto3, uvicorn; print('✅ Dependencies installed successfully')"
```

## Quick Configuration

### Option 1: Environment Variables (.env file)

Create a `.env` file in the project root directory:

```bash
# Enable providers you want to use
ENABLED_PROVIDERS=["aws"]  # or ["aws", "azure"], ["aws", "azure", "gcp"]

# AWS Configuration (if using AWS)
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=us-east-1

# Transport Configuration
TRANSPORT_TYPE=filesystem  # or 'http' for remote scanner
FILESYSTEM_BASE_DIR=./file_collector
```

### Option 2: YAML Configuration

Create `config/production.yaml`:

```yaml
enabled_providers:
  - aws

# AWS settings
aws_access_key_id: "your-access-key-id"
aws_secret_access_key: "your-secret-access-key"
aws_default_region: "us-east-1"

# Transport settings
transport_type: "filesystem"
filesystem_base_dir: "./file_collector"
```

## Cloud Provider Setup

### AWS Setup

#### Option A: Environment Variables

```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

#### Option B: AWS CLI

If you have AWS CLI installed:

```bash
aws configure
```

#### Option C: IAM Roles (for EC2/ECS/EKS)

If running on AWS infrastructure, use IAM roles - no explicit credentials needed.

### Azure Setup

#### Create Service Principal

```bash
# Login to Azure
az login

# Create service principal with Reader role
az ad sp create-for-rbac --name "csp-scanner-sp" --role "Reader" --scopes /subscriptions/{subscription-id}
```

#### Configure Environment Variables

```bash
export ENABLED_PROVIDERS='["azure"]'
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"          # appId from above
export AZURE_CLIENT_SECRET="your-client-secret"  # password from above
```

### GCP Setup

#### Create Service Account

```bash
# Create service account
gcloud iam service-accounts create csp-scanner \
    --description="Service account for CSP Scanner"

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.viewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

# Create and download key
gcloud iam service-accounts keys create csp-scanner-key.json \
    --iam-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com
```

#### Configure Environment Variables

```bash
export ENABLED_PROVIDERS='["gcp"]'
export GCP_PROJECT_ID="your-project-id"
export GCP_CREDENTIALS_PATH="/path/to/csp-scanner-key.json"
```

## Running the Application

### Development Mode

```bash
# Using default configuration
uvicorn app.main:app --reload

# Using specific config file
CONFIG_FILE=config/production.yaml uvicorn app.main:app --reload

# Using environment variables
ENABLED_PROVIDERS='["aws"]' AWS_DEFAULT_REGION=us-east-1 uvicorn app.main:app --reload
```

### Production Mode

```bash
# With host binding
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Using production config
CONFIG_FILE=config/production.yaml uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Testing the Setup

### 1. Check Application Health

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### 2. List Enabled Providers

```bash
curl http://localhost:8000/extraction/providers
# Expected: {"providers": ["aws"], "total": 1}
```

### 3. List Available Services

```bash
curl http://localhost:8000/extraction/services
# Shows all available services for enabled providers
```

### 4. Test Extraction

```bash
# Extract from all enabled providers
curl -X POST http://localhost:8000/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{}'

# Extract specific services
curl -X POST http://localhost:8000/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "services": ["ec2", "s3"],
    "regions": ["us-east-1"]
  }'
```

### 5. Check Job Status

```bash
# Get job status (replace {job_id} with actual ID from trigger response)
curl http://localhost:8000/extraction/jobs/{job_id}
```

## Project Structure

After setup, your project should look like this:

```
csp-scanner/
├── app/                    # Main application code
│   ├── api/               # FastAPI routes
│   ├── cloud/             # Cloud provider sessions
│   ├── core/              # Configuration and settings
│   ├── extractors/        # Cloud service extractors
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic
│   ├── transport/         # Data transport mechanisms
│   └── main.py           # Application entry point
├── config/                # Configuration files
│   ├── development.yaml
│   ├── production.yaml
│   └── extractors.yaml
├── tests/                 # Test suite
├── file_collector/        # Extracted artifacts (if using filesystem transport)
├── requirements.txt       # Python dependencies
├── pytest.ini           # Test configuration
├── .env                 # Environment variables (create this)
└── README.md
```

## Common Issues & Solutions

### "No cloud providers enabled"
- **Cause**: `ENABLED_PROVIDERS` not set or empty
- **Solution**: Set `ENABLED_PROVIDERS=["aws"]` or your preferred providers

### AWS Authentication Errors
- **Cause**: Invalid or missing AWS credentials
- **Solution**: Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, verify with `aws sts get-caller-identity`

### Azure Authentication Errors
- **Cause**: Invalid service principal credentials
- **Solution**: Verify `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`

### GCP Authentication Errors
- **Cause**: Invalid service account key or project ID
- **Solution**: Check `GCP_CREDENTIALS_PATH` points to valid key file, verify `GCP_PROJECT_ID`

### Import Errors
- **Cause**: Missing dependencies
- **Solution**: Run `pip install -r requirements.txt`

### Port Already in Use
- **Cause**: Another application using port 8000
- **Solution**: Use different port: `uvicorn app.main:app --port 8001`

## Next Steps

1. **Configure Transport**: Set up HTTP transport to send artifacts to your policy scanner
2. **Schedule Extractions**: Set up automated periodic scanning
3. **Monitor Logs**: Check application logs for extraction progress and errors
4. **Customize Configuration**: Adjust batch sizes, worker counts, and other settings
5. **Add More Providers**: Enable Azure and/or GCP if needed

## Getting Help

- **API Documentation**: Visit `http://localhost:8000/docs` for interactive API docs
- **Logs**: Check console output for detailed error messages
- **Configuration**: See [Configuration Guide](configuration.md) for advanced options
- **Troubleshooting**: See provider-specific setup guides for detailed troubleshooting

## Development Setup

If you plan to contribute to the project:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Code quality checks
black app tests
flake8 app tests
mypy app
```

See the [Development Guide](development.md) for detailed contribution instructions.