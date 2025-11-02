---
layout: default
title: Configuration
nav_order: 3
---

# Configuration Guide

This guide covers all configuration options available in the Cloud Artifact Extractor, including environment variables, YAML files, and provider-specific settings.

## Configuration Hierarchy

The application loads configuration in this order (later sources override earlier ones):

1. **Default values** in the code
2. **YAML configuration files** (`config/*.yaml`)
3. **Environment variables** (highest priority)
4. **Runtime overrides** via API calls

## Configuration Files

### File Locations

Configuration files are stored in the `config/` directory:

```
config/
├── development.yaml    # Development environment settings
├── production.yaml     # Production environment settings
└── extractors.yaml     # Extractor-specific configuration
```

### Loading Configuration

#### Using Environment Variables

```bash
# Specify config file
export CONFIG_FILE=config/production.yaml

# Start application
uvicorn app.main:app --reload
```

#### Using Python

```python
from app.core.config import get_settings

settings = get_settings()
print(f"AWS Region: {settings.aws_default_region}")
```

## Core Configuration

### Multi-Cloud Provider Settings

```yaml
# config/production.yaml
enabled_providers:
  - aws
  - azure
  - gcp
```

**Environment Variables:**
```bash
export ENABLED_PROVIDERS='["aws", "azure", "gcp"]'
```

### Application Settings

```yaml
# config/production.yaml
app_name: "Cloud Artifact Extractor"
environment: "production"
debug: false
log_level: "INFO"
```

**Environment Variables:**
```bash
export APP_NAME="My CSP Scanner"
export ENVIRONMENT="production"
export DEBUG="false"
export LOG_LEVEL="INFO"
```

## Cloud Provider Configuration

### AWS Configuration


#### Basic AWS Settings (Multi-Account)

```yaml
# config/production.yaml
aws_accounts:
  - account_id: "123456789012"
    regions:
      - "us-west-2"
      - "us-east-1"
  - account_id: "987654321098"
    regions:
      - "eu-west-1"
aws_access_key_id: "your-access-key-id"  # Global or per-account
aws_secret_access_key: "your-secret-access-key"
aws_session_token: null  # Optional, for temporary credentials
```

**Environment Variables (legacy single-account config):**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_SESSION_TOKEN="temporary-token"  # Optional
```

#### AWS Profile Support

```yaml
# config/production.yaml
aws_profile: "production"  # Uses AWS credentials file profile
```

**Environment Variable:**
```bash
export AWS_PROFILE="production"
```

### Azure Configuration

#### Multi-Subscription & Multi-Location (Recommended)

```yaml
# config/production.yaml
azure_accounts:
  - subscription_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    locations:
      - "eastus"
      - "westeurope"
  - subscription_id: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
    locations:
      - "centralus"
      - "uksouth"
azure_tenant_id: "your-tenant-id"
azure_client_id: "your-client-id"
azure_client_secret: "your-client-secret"
```

**Environment Variables (legacy single-subscription):**
```bash
export AZURE_SUBSCRIPTION_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export AZURE_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export AZURE_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_DEFAULT_LOCATION="eastus"
```

Legacy config with a single subscription/location is still supported for backward compatibility.

### GCP Configuration


#### Basic GCP Settings (Multi-Project)

```yaml
# config/production.yaml
gcp_projects:
  - project_id: "pegasus-437722"
    regions:
      - "us-central1"
      - "us-east1"
  - project_id: "another-project"
    regions:
      - "us-west1"
      - "europe-west1"
gcp_credentials_path: "/path/to/service-account-key.json"  # Optional
```

**Environment Variables (legacy single-project config):**
```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_CREDENTIALS_PATH="/path/to/service-account-key.json"
export GCP_DEFAULT_REGION="us-central1"
```

## Transport Configuration

The transport layer determines how extracted artifacts are delivered.

### HTTP Transport

Sends artifacts to a remote HTTP endpoint (e.g., policy scanner).

```yaml
# config/production.yaml
transport_type: "http"
scanner_endpoint_url: "https://policy-scanner.example.com/api/scan"
transport_timeout_seconds: 30
transport_max_retries: 3
transport_retry_delay_seconds: 1
```

**Environment Variables:**
```bash
export TRANSPORT_TYPE="http"
export SCANNER_ENDPOINT_URL="https://policy-scanner.example.com/api/scan"
export TRANSPORT_TIMEOUT_SECONDS="30"
export TRANSPORT_MAX_RETRIES="3"
export TRANSPORT_RETRY_DELAY_SECONDS="1"
```

### Filesystem Transport

Writes artifacts to local JSON files.

```yaml
# config/production.yaml
transport_type: "filesystem"
filesystem_base_dir: "./file_collector"
filesystem_create_dir: true
filesystem_file_pattern: "{service}_{resource_type}_{resource_id}_{timestamp}_{uuid}.json"
```

**Environment Variables:**
```bash
export TRANSPORT_TYPE="filesystem"
export FILESYSTEM_BASE_DIR="./file_collector"
export FILESYSTEM_CREATE_DIR="true"
export FILESYSTEM_FILE_PATTERN="{service}_{resource_type}_{resource_id}_{timestamp}_{uuid}.json"
```

**File Pattern Variables:**
- `{service}`: Service name (e.g., "ec2", "s3")
- `{resource_type}`: Full resource type (e.g., "aws:ec2:instance")
- `{resource_id}`: Resource identifier
- `{timestamp}`: ISO timestamp
- `{uuid}`: Unique identifier

### Null Transport

Discards artifacts (useful for testing).

```yaml
# config/production.yaml
transport_type: "null"
```

**Environment Variable:**
```bash
export TRANSPORT_TYPE="null"
```

## Extractor Configuration

### Global Extractor Settings

```yaml
# config/extractors.yaml
global:
  max_concurrent_extractors: 5
  batch_size: 50
  batch_delay_seconds: 0.5
  enable_progress_tracking: true
  extraction_timeout_seconds: 300
```

### AWS Extractor Configuration

```yaml
# config/extractors.yaml
aws:
  ec2:
    max_workers: 10
    include_stopped: true
    include_terminated: false
    batch_size: 100

  s3:
    max_workers: 20
    include_bucket_policies: true
    include_bucket_acl: true
    check_public_access: true

  rds:
    max_workers: 5
    include_snapshots: false
    include_clusters: true

  lambda:
    max_workers: 15
    include_versions: false
    include_aliases: true

  iam:
    max_workers: 10
    include_policies: true
    include_roles: true
    include_users: true
    include_groups: true

  vpc:
    max_workers: 8
    include_subnets: true
    include_route_tables: true
    include_nat_gateways: true

  ecs:
    max_workers: 5
    include_services: true
    include_task_definitions: true

  eks:
    max_workers: 3
    include_nodegroups: true

  elb:
    max_workers: 5
    include_target_groups: true

  apprunner:
    max_workers: 5
    include_services: true

  cloudfront:
    max_workers: 10
    include_distributions: true

  apigateway:
    max_workers: 5
    include_rest_apis: true
    include_usage_plans: false

  kms:
    max_workers: 10
    include_keys: true
    include_grants: false
```

### Azure Extractor Configuration

```yaml
# config/extractors.yaml
azure:
  compute:
    max_workers: 10
    include_stopped: true
    include_vmss: true

  storage:
    max_workers: 20
    check_access_policies: true
    check_blob_encryption: true
    include_iam_policies: false

  network:
    max_workers: 10
    include_nsg_rules: true
    include_load_balancers: true

  web:
    max_workers: 15
    include_app_service_plans: true
    include_web_apps: true
    include_function_apps: true

  sql:
    max_workers: 10
    include_databases: true
    include_firewall_rules: true
    check_public_access: true

  containerservice:
    max_workers: 5
    include_node_pools: true
    include_network_config: true
    check_rbac_settings: true

  keyvault:
    max_workers: 10
    include_network_acls: true
    check_access_policies: true

  authorization:
    max_workers: 10
    include_custom_roles: true
    include_role_assignments: true
    analyze_scope_hierarchy: true
```

### GCP Extractor Configuration

```yaml
# config/extractors.yaml
gcp:
  compute:
    max_workers: 10
    include_stopped: true
    include_instance_groups: true

  storage:
    max_workers: 20
    include_iam_policies: false
    check_public_access: true
```

## Orchestrator Configuration

```yaml
# config/production.yaml
orchestrator:
  max_concurrent_jobs: 3
  job_timeout_seconds: 3600
  enable_job_persistence: true
  job_storage_path: "./jobs"
  enable_metrics: true
  metrics_port: 9090
```

## Scheduler Configuration

```yaml
# config/production.yaml
scheduler:
  enabled: true
  timezone: "UTC"
  job_defaults:
    coalesce: true
    max_instances: 1
    misfire_grace_time: 30
```

## Logging Configuration

```yaml
# config/production.yaml
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file:
    enabled: true
    path: "./logs/csp-scanner.log"
    max_bytes: 10485760  # 10MB
    backup_count: 5
  console:
    enabled: true
    level: "WARNING"
```

## Security Configuration

```yaml
# config/production.yaml
security:
  enable_ssl: true
  ssl_cert_path: "/path/to/cert.pem"
  ssl_key_path: "/path/to/key.pem"
  cors_origins: ["https://example.com"]
  api_key_required: false
  api_key_header: "X-API-Key"
  rate_limit_requests: 100
  rate_limit_window_seconds: 60
```

## Example Configuration Files

### Development Configuration

```yaml
# config/development.yaml
app_name: "Cloud Artifact Extractor"
environment: "development"
debug: true
log_level: "DEBUG"

enabled_providers:
  - aws

# AWS
aws_access_key_id: "your-dev-key"
aws_secret_access_key: "your-dev-secret"
aws_default_region: "us-east-1"

# Transport
transport_type: "filesystem"
filesystem_base_dir: "./file_collector"
filesystem_create_dir: true

# Extractors
extractors:
  global:
    max_concurrent_extractors: 2
    batch_size: 10
    batch_delay_seconds: 1.0

  aws:
    ec2:
      max_workers: 5
      include_stopped: true
    s3:
      max_workers: 10
      check_public_access: true
```

### Production Configuration

```yaml
# config/production.yaml
app_name: "Cloud Artifact Extractor"
environment: "production"
debug: false
log_level: "INFO"

enabled_providers:
  - aws
  - azure
  - gcp

# AWS
aws_access_key_id: "${AWS_ACCESS_KEY_ID}"
aws_secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
aws_default_region: "us-east-1"

# Azure
azure_subscription_id: "${AZURE_SUBSCRIPTION_ID}"
azure_tenant_id: "${AZURE_TENANT_ID}"
azure_client_id: "${AZURE_CLIENT_ID}"
azure_client_secret: "${AZURE_CLIENT_SECRET}"

# GCP
gcp_project_id: "${GCP_PROJECT_ID}"
gcp_credentials_path: "${GCP_CREDENTIALS_PATH}"

# Transport
transport_type: "http"
scanner_endpoint_url: "https://policy-scanner.example.com/api/scan"
transport_timeout_seconds: 60
transport_max_retries: 5

# Extractors
extractors:
  global:
    max_concurrent_extractors: 10
    batch_size: 200
    batch_delay_seconds: 0.1

  aws:
    ec2:
      max_workers: 20
    s3:
      max_workers: 50

  azure:
    compute:
      max_workers: 15
    storage:
      max_workers: 30

  gcp:
    compute:
      max_workers: 15
    storage:
      max_workers: 25

# Security
security:
  enable_ssl: true
  ssl_cert_path: "/etc/ssl/certs/csp-scanner.crt"
  ssl_key_path: "/etc/ssl/private/csp-scanner.key"
  cors_origins: ["https://trusted-domain.com"]

# Logging
logging:
  level: "INFO"
  file:
    enabled: true
    path: "/var/log/csp-scanner/app.log"
    max_bytes: 10485760
    backup_count: 10
```

## Environment Variable Overrides

You can override any configuration value using environment variables:

```bash
# Override transport settings
export TRANSPORT_TYPE="http"
export SCANNER_ENDPOINT_URL="https://new-scanner.example.com"

# Override extractor settings
export EXTRACTORS__AWS__EC2__MAX_WORKERS="15"
export EXTRACTORS__GLOBAL__BATCH_SIZE="100"

# Start application
uvicorn app.main:app --reload
```

**Naming Convention:**
- Nested YAML keys become double underscores
- Use uppercase for environment variables
- Arrays can be specified as JSON strings

## Validation

The application validates configuration on startup:

- **Required fields**: Checks for required cloud provider credentials
- **Format validation**: Validates URLs, UUIDs, and other formats
- **Dependency checks**: Ensures enabled providers have necessary credentials
- **Range validation**: Checks numeric values are within acceptable ranges

Invalid configuration will prevent startup with detailed error messages.

## Configuration Testing

### Validate Configuration

```bash
# Test configuration loading
python -c "from app.core.config import get_settings; print('✅ Config loaded successfully')"

# Check enabled providers
python -c "from app.core.config import get_settings; s = get_settings(); print(f'Providers: {s.enabled_providers}')"

# Validate cloud credentials
python -c "
from app.core.config import get_settings
from app.cloud.aws_session import AWSSession
import boto3

settings = get_settings()
if 'aws' in settings.enabled_providers:
    session = AWSSession(boto3.Session())
    print('✅ AWS credentials valid')
"
```

### Configuration Debugging

```bash
# Show all configuration values
python -c "
from app.core.config import get_settings
import json
settings = get_settings()
print(json.dumps(settings.dict(), indent=2, default=str))
"
```

## Best Practices

1. **Use environment variables** for sensitive data (credentials, secrets)
2. **Separate config files** for different environments (dev, staging, prod)
3. **Use consistent naming** across environments
4. **Document custom settings** in your deployment guides
5. **Version control** configuration templates (not secrets)
6. **Test configuration** changes in development first
7. **Monitor resource usage** and adjust worker counts accordingly
8. **Use appropriate timeouts** for your network conditions

## Troubleshooting

### Common Configuration Issues

**"Configuration file not found"**
- Ensure `CONFIG_FILE` points to an existing file
- Check file permissions

**"Invalid configuration format"**
- Validate YAML syntax
- Check for correct indentation
- Ensure required fields are present

**"Cloud provider credentials invalid"**
- Verify environment variables are set
- Check credential file paths exist
- Test credentials manually (e.g., `aws sts get-caller-identity`)

**"Transport configuration error"**
- Verify URLs are accessible
- Check file system permissions for filesystem transport
- Ensure HTTP endpoints accept POST requests

### Configuration Debugging

Enable debug logging to see configuration loading:

```bash
export LOG_LEVEL="DEBUG"
uvicorn app.main:app --reload
```

Look for log messages like:
```
DEBUG - Loading configuration from: config/development.yaml
DEBUG - Enabled providers: ['aws']
DEBUG - AWS session initialized successfully
```