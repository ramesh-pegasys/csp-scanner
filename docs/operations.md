---
layout: default
title: Operations
nav_order: 6
---

# Operations Guide

Practical guidance for running the Cloud Artifact Extractor in day-to-day operations: common use cases, health checks, running in production, monitoring, scheduling, and maintenance.

## Common Use Cases

The Cloud Artifact Extractor is designed to support multiple operational scenarios:

### Security Scanning and Compliance

Extract cloud resources to analyze security configurations and policy compliance:

- **Security Posture Assessment**: Identify misconfigured resources (open security groups, public S3 buckets, etc.)
- **Policy Compliance Checking**: Verify resources meet organizational security policies
- **Regulatory Compliance**: Audit resources against standards like HIPAA, PCI-DSS, SOC 2
- **Vulnerability Detection**: Identify outdated software versions and unpatched resources

**Example Workflow:**
```bash
# Extract all resources
curl -X POST http://localhost:8000/extraction/extract

# Send artifacts to security scanner via HTTP transport
# Scanner analyzes artifacts for security issues
```

### Cloud Inventory Management

Maintain a comprehensive, up-to-date inventory of all cloud assets:

- **Asset Discovery**: Find all resources across multiple accounts and regions
- **Resource Tracking**: Monitor resource creation, modification, and deletion
- **Tag Management**: Ensure proper tagging across all resources
- **CMDB Integration**: Keep Configuration Management Database synchronized

**Example Workflow:**
```bash
# Schedule daily inventory refresh
curl -X POST http://localhost:8000/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-inventory",
    "cron_expression": "0 1 * * *",
    "batch_size": 500
  }'
```

### Cost Optimization Analysis

Extract resource data to identify cost-saving opportunities:

- **Idle Resource Detection**: Find underutilized VMs, load balancers, and storage
- **Right-Sizing Recommendations**: Analyze instance usage patterns
- **Reserved Instance Planning**: Identify candidates for RI purchases
- **Resource Cleanup**: Locate orphaned resources (unattached volumes, unused IPs)

**Example Workflow:**
```bash
# Extract compute and storage resources
curl -X POST "http://localhost:8000/extraction/extract?services=ec2,s3,compute,storage"

# Analyze extracted data for cost optimization
```

### Multi-Cloud Governance

Unified visibility and control across AWS, Azure, and GCP:

- **Standardization**: Ensure consistent configurations across clouds
- **Policy Enforcement**: Apply uniform policies to all providers
- **Shadow IT Detection**: Discover unauthorized cloud usage
- **Cross-Cloud Reporting**: Aggregate data from multiple providers

**Example Workflow:**
```yaml
# Configure multi-cloud extraction
enabled_providers:
  - aws
  - azure
  - gcp

# Extract from all providers
curl -X POST http://localhost:8000/extraction/extract
```

### Disaster Recovery Planning

Document and track infrastructure for recovery scenarios:

- **Infrastructure Documentation**: Maintain detailed records of all resources
- **Dependency Mapping**: Understand relationships between resources
- **Recovery Point Objectives**: Track configurations for point-in-time recovery
- **DR Testing**: Verify backup and recovery processes

## Health and Status

- Health endpoint: `GET /health`
- Recent jobs: `GET /extraction/jobs?limit=20`
- Job detail: `GET /extraction/jobs/{job_id}`

## Running in Production

- Use a process manager (systemd, supervisord, Docker, or Kubernetes)
- Configure `LOG_LEVEL=INFO` or `WARNING`
- Prefer HTTP transport to deliver artifacts to a central scanner

### Example: Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Scheduling Scans

Use the API to create schedules or an external scheduler (cron, Airflow, etc.).

### API-based schedule

```bash
curl -X POST http://localhost:8000/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-full-scan",
    "cron_expression": "0 2 * * *",
    "batch_size": 200
  }'
```

## Monitoring and Logs

- Log to stdout by default; ship with your log agent
- Optionally enable metrics if supported by your deployment

## Backup and Retention (Filesystem Transport)

- Rotate the `file_collector` directory with logrotate or a cron job
- Archive to object storage for long-term retention

## Common Operational Tasks

- Update configuration with minimal restarts: environment overrides are read on startup
- Validate credentials regularly using provider CLIs

## Troubleshooting

See the dedicated [Troubleshooting]({{ '/troubleshooting.html' | relative_url }}) page for common errors and fixes.
