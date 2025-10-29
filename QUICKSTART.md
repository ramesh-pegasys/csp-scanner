# Quick Start Guide - Multi-Cloud CSP Scanner

## Installation

```bash
# Clone and navigate to project
cd /path/to/csp-scanner

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### Option 1: Environment Variables (.env file)

```bash
# Enable both providers
ENABLED_PROVIDERS=["aws", "azure"]

# AWS Credentials
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1

# Azure Credentials
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-client-secret
AZURE_DEFAULT_LOCATION=eastus

# Transport Configuration
TRANSPORT_TYPE=filesystem  # or 'http' for remote scanner
FILESYSTEM_BASE_DIR=./file_collector
```

### Option 2: YAML Configuration

Create `config/production.yaml`:

```yaml
enabled_providers:
  - aws
  - azure

# AWS
aws_access_key_id: "your-key"
aws_secret_access_key: "your-secret"
aws_default_region: "us-east-1"

# Azure
azure_subscription_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
azure_tenant_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
azure_client_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
azure_client_secret: "your-secret"
azure_default_location: "eastus"

# Transport
transport_type: "filesystem"
filesystem_base_dir: "./file_collector"
```

## Running the Application

### Using Environment Variables

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using YAML Config

```bash
export CONFIG_FILE=config/production.yaml
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Usage

### Check Enabled Providers

```bash
curl http://localhost:8000/providers
```

Response:
```json
{
  "providers": ["aws", "azure"],
  "total": 2
}
```

### List Available Services

```bash
# All services
curl http://localhost:8000/services

# AWS services only
curl http://localhost:8000/services?provider=aws

# Azure services only
curl http://localhost:8000/services?provider=azure
```

### Trigger Extraction

#### Extract All Resources from All Providers

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Extract from AWS Only

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws"
  }'
```

#### Extract from Azure Only

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure"
  }'
```

#### Extract Specific Services

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "services": ["compute", "storage"],
    "regions": ["eastus", "westus2"],
    "batch_size": 100
  }'
```

### Check Job Status

```bash
# Get job status
curl http://localhost:8000/jobs/{job_id}

# List recent jobs
curl http://localhost:8000/jobs?limit=10
```

## Project Structure

```
app/
├── cloud/                  # Cloud session abstraction
│   ├── base.py            # CloudProvider enum, CloudSession protocol
│   ├── aws_session.py     # AWS session wrapper
│   └── azure_session.py   # Azure session wrapper
├── extractors/
│   ├── base.py           # BaseExtractor class
│   ├── aws/              # AWS extractors
│   │   ├── ec2.py
│   │   ├── s3.py
│   │   ├── rds.py
│   │   ├── lambda_extractor.py
│   │   ├── iam.py
│   │   ├── vpc.py
│   │   ├── ecs.py
│   │   ├── eks.py
│   │   ├── elb.py
│   │   ├── apprunner.py
│   │   ├── cloudfront.py
│   │   ├── apigateway.py
│   │   └── kms.py
│   └── azure/            # Azure extractors
│       ├── compute.py
│       ├── storage.py
│       └── network.py
├── services/
│   ├── registry.py       # Multi-cloud extractor registry
│   └── orchestrator.py   # Extraction orchestrator
├── api/
│   └── routes/
│       └── extraction.py # API endpoints
├── core/
│   └── config.py         # Multi-cloud configuration
└── main.py              # Application entry point
```

## Supported Resources

### AWS
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

### Azure
- **Compute**: Virtual Machines, VM Scale Sets
- **Storage**: Storage Accounts with encryption and network rules
- **Network**: Network Security Groups, Virtual Networks, Load Balancers

## Common Scenarios

### AWS Only Deployment

```bash
# .env
ENABLED_PROVIDERS=["aws"]
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

### Azure Only Deployment

```bash
# .env
ENABLED_PROVIDERS=["azure"]
AZURE_SUBSCRIPTION_ID=your-sub-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-secret
```

### Multi-Cloud Deployment

```bash
# .env
ENABLED_PROVIDERS=["aws", "azure"]
# Include both AWS and Azure credentials
```

## Troubleshooting

### Check Application Logs

```bash
# Look for initialization messages
INFO - Starting Cloud Artifact Extractor
INFO - Initializing AWS session...
INFO - AWS session initialized
INFO - Initializing Azure session...
INFO - Azure session initialized
INFO - Registered extractor: aws:ec2
INFO - Registered extractor: azure:compute
```

### Verify Credentials

#### AWS
```bash
# Test AWS credentials
aws sts get-caller-identity
```

#### Azure
```bash
# Test Azure credentials
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID

az account show
```

### Common Issues

**Issue**: "No cloud providers enabled!"
- **Solution**: Check `ENABLED_PROVIDERS` setting includes at least one provider

**Issue**: AWS extraction fails
- **Solution**: Verify AWS credentials and permissions (ReadOnlyAccess or equivalent)

**Issue**: Azure extraction fails
- **Solution**: Verify Azure credentials and subscription ID, ensure Reader role is assigned

**Issue**: Import errors for Azure SDK
- **Solution**: Run `pip install -r requirements.txt` to install all dependencies

## Next Steps

1. **Setup Credentials**: Configure AWS and/or Azure credentials
2. **Test Connection**: Run the application and check `/providers` endpoint
3. **Run Extraction**: Trigger your first extraction job
4. **Review Output**: Check `file_collector/` directory or remote scanner
5. **Customize**: Modify `config/extractors.yaml` for your needs

## Documentation

- [AZURE_SETUP.md](./AZURE_SETUP.md) - Azure setup guide
- [AZURE_RESOURCES.md](./AZURE_RESOURCES.md) - Supported Azure resources
- [AZURE_INTEGRATION_PLAN.md](./AZURE_INTEGRATION_PLAN.md) - Architecture details
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Implementation overview
- [README.md](./README.md) - General project documentation

## Development

### Adding New AWS Extractor

1. Create `app/extractors/aws/myservice.py`
2. Inherit from `BaseExtractor`
3. Implement `get_metadata()`, `extract()`, `transform()`
4. Register in `app/services/registry.py`
5. Add config to `config/extractors.yaml`

### Adding New Azure Extractor

1. Create `app/extractors/azure/myservice.py`
2. Inherit from `BaseExtractor`
3. Set `cloud_provider="azure"` in metadata
4. Implement required methods
5. Register in `app/services/registry.py`
6. Add config to `config/extractors.yaml`

## Support

For issues or questions:
- Check logs for error messages
- Review documentation files
- Verify credentials and permissions
- Check network connectivity to cloud APIs
