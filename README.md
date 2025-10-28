# Cloud Artifact Extractor

A FastAPI-based service for extracting and managing cloud service artifacts from AWS.

[![CI](https://github.com/username/repo/actions/workflows/ci.yml/badge.svg)](https://github.com/username/repo/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-pytest--cov-blue.svg)](https://pytest-cov.readthedocs.io/)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Flake8](https://img.shields.io/badge/flake8-checked-blue.svg)](https://flake8.pycqa.org/)
[![Black](https://img.shields.io/badge/black-formatted-black.svg)](https://github.com/psf/black)

## AWS Credentials Setup

The application requires AWS credentials to access and extract data from AWS services. Here are the different ways to provide AWS credentials:

### 1. Using Environment Variables

Set environment variables before running the application:

```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### 2. Using a .env File

Create a `.env` file in the project root directory:

```bash
# .env
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=us-east-1
```

### 3. Using AWS Credentials File

Create or update the AWS credentials file at `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = your-access-key-id
aws_secret_access_key = your-secret-access-key
region = us-east-1
```

### 4. Using AWS CLI Configuration

If you have the AWS CLI installed, configure credentials:

```bash
aws configure
```

This will prompt you to enter your AWS Access Key ID, Secret Access Key, default region, and output format.

### Creating AWS Credentials

#### Option A: IAM User (for development/testing)
1. Go to AWS IAM Console
2. Create a new IAM user
3. Attach appropriate policies (e.g., `ReadOnlyAccess` or specific service read permissions)
4. Generate access keys
5. Use the Access Key ID and Secret Access Key

#### Option B: IAM Role (recommended for production)
- Use IAM roles if running on EC2/ECS/EKS
- The application will automatically use the role's credentials

### Required Permissions

For the CSP scanner to work properly, your AWS credentials should have read-only access to these services:
- EC2, S3, RDS, Lambda, VPC, CloudFront, API Gateway, ELB, ECS, EKS, App Runner, KMS, IAM

Example IAM policy:
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

### Verification

After setting up credentials, verify they work by running:

```bash
python -c "import boto3; print(boto3.Session().get_credentials())"
```

Or start the application and check the logs for any authentication errors.

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