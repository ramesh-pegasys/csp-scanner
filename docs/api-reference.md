---
layout: default
title: API Reference
nav_order: 8
---

# API Reference

This document provides comprehensive documentation for the Cloud Artifact Extractor's REST API endpoints.

## Base URL

```
http://localhost:8000
```


## JWT & Certificate Generation Utility

For local development and testing, use `generate_certs_and_jwt.py` to generate static JWT tokens and self-signed certificates.

See the project README and Getting Started guide for usage instructions.

All API endpoints except `/health` require a static JWT token for authentication.

To generate a token, use the provided utility script:

```bash
python generate_static_jwt.py
```

Set environment variables to customize:
- `JWT_SECRET_KEY` (default: 'your-secret-key')
- `JWT_ALGORITHM` (default: 'HS256')
- `JWT_EXPIRE_DAYS` (default: 365)

Include the token in your API requests:

```
Authorization: Bearer <your-token>
```

**Note:**
- No user management is performed in this app.
- All clients use the same static token for access.

---

**TODO:**
- Support for external JWT providers (e.g., Auth0, AWS Cognito, Google IAM) may be added in the future.

## Response Format

All API responses follow a consistent JSON structure:

```json
{
  "data": { ... },
  "message": "Optional message",
  "errors": []
}
```

## Endpoints

### Health Check

#### GET `/health`

Check the health status of the application.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

### Provider Management

#### GET `/extraction/providers`

List all enabled cloud providers.

**Response:**
```json
{
  "providers": ["aws", "azure", "gcp"],
  "total": 3
}
```

#### GET `/extraction/services`

List all available services across enabled providers.

**Query Parameters:**
- `provider` (optional): Filter by specific provider (`aws`, `azure`, `gcp`)

**Examples:**

```bash
# All services
GET /extraction/services

# AWS services only
GET /extraction/services?provider=aws

# Azure services only
GET /extraction/services?provider=azure
```

**Response:**
```json
{
  "services_by_provider": {
    "aws": [
      {
        "service": "ec2",
        "description": "Extracts EC2 instances and related resources",
        "resource_types": ["instance", "security-group"],
        "version": "1.0.0"
      }
    ],
    "azure": [
      {
        "service": "compute",
        "description": "Extracts Azure Virtual Machines and VM Scale Sets",
        "resource_types": ["virtual-machine", "vmss"],
        "version": "1.0.0"
      }
    ]
  },
  "total_services": 15
}
```

### Extraction Jobs

#### POST `/extraction/trigger`

Trigger a new extraction job.

**Request Body:**
```json
{
  "provider": "aws",           // Optional: "aws", "azure", "gcp", or null for all
  "services": ["ec2", "s3"],   // Optional: Array of service names, or null for all
  "regions": ["us-east-1"],    // Optional: Array of regions, or null for all
  "filters": {                 // Optional: Service-specific filters
    "instance_state": "running"
  },
  "batch_size": 100            // Optional: Default 100
}
```

**Examples:**

```bash
# Extract all resources from all enabled providers
curl -X POST http://localhost:8000/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{}'

# Extract specific AWS services
curl -X POST http://localhost:8000/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "services": ["ec2", "s3"],
    "regions": ["us-east-1", "us-west-2"]
  }'

# Extract Azure compute resources
curl -X POST http://localhost:8000/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "services": ["compute"],
    "regions": ["eastus"]
  }'

# Extract with custom batch size
curl -X POST http://localhost:8000/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "services": ["ec2"],
    "batch_size": 50
  }'
```

**Response:**
```json
{
  "job_id": "job_1234567890",
  "status": "started",
  "message": "Extraction job started successfully",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

#### GET `/extraction/jobs`

List recent extraction jobs.

**Query Parameters:**
- `limit` (optional): Maximum number of jobs to return (default: 10)
- `status` (optional): Filter by status (`running`, `completed`, `failed`)

**Examples:**

```bash
# Get recent jobs
GET /extraction/jobs

# Get last 5 jobs
GET /extraction/jobs?limit=5

# Get only running jobs
GET /extraction/jobs?status=running
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "job_1234567890",
      "status": "completed",
      "provider": "aws",
      "services": ["ec2", "s3"],
      "regions": ["us-east-1"],
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:32:15Z",
      "duration_seconds": 135,
      "resources_extracted": 245,
      "errors": []
    }
  ],
  "total": 1
}
```

#### GET `/extraction/jobs/{job_id}`

Get detailed information about a specific job.

**Path Parameters:**
- `job_id`: The job identifier

**Response:**
```json
{
  "job_id": "job_1234567890",
  "status": "completed",
  "provider": "aws",
  "services": ["ec2", "s3"],
  "regions": ["us-east-1"],
  "batch_size": 100,
  "filters": {},
  "progress": {
    "total_resources": 245,
    "processed_resources": 245,
    "failed_resources": 0,
    "current_service": null,
    "current_region": null
  },
  "timing": {
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:32:15Z",
    "duration_seconds": 135
  },
  "results": {
    "resources_extracted": 245,
    "services_processed": 2,
    "regions_processed": 1,
    "errors": []
  },
  "transport": {
    "type": "filesystem",
    "destination": "./file_collector",
    "files_created": 245
  }
}
```

### Schedule Management

#### POST `/schedules/`

Create a new extraction schedule.

**Request Body:**
```json
{
  "name": "daily-full-scan",
  "cron_expression": "0 2 * * *",  // Daily at 2 AM
  "provider": "aws",               // Optional
  "services": ["ec2", "s3"],       // Optional
  "regions": ["us-east-1"],        // Optional
  "batch_size": 200,
  "enabled": true
}
```

**Examples:**

```bash
# Daily full scan of all providers
curl -X POST http://localhost:8000/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-full-scan",
    "cron_expression": "0 2 * * *",
    "batch_size": 200
  }'

# Hourly AWS scan
curl -X POST http://localhost:8000/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hourly-aws-scan",
    "cron_expression": "0 * * * *",
    "provider": "aws",
    "services": ["ec2", "rds"]
  }'
```

**Response:**
```json
{
  "schedule_id": "sched_1234567890",
  "name": "daily-full-scan",
  "cron_expression": "0 2 * * *",
  "next_run": "2024-01-16T02:00:00Z",
  "status": "active"
}
```

#### GET `/schedules/`

List all extraction schedules.

**Response:**
```json
{
  "schedules": [
    {
      "schedule_id": "sched_1234567890",
      "name": "daily-full-scan",
      "cron_expression": "0 2 * * *",
      "provider": null,
      "services": null,
      "enabled": true,
      "last_run": "2024-01-15T02:00:00Z",
      "next_run": "2024-01-16T02:00:00Z",
      "status": "active"
    }
  ],
  "total": 1
}
```

#### GET `/schedules/{schedule_id}`

Get details of a specific schedule.

#### PUT `/schedules/{schedule_id}`

Update an existing schedule.

#### DELETE `/schedules/{schedule_id}`

Delete a schedule.

### Interactive API Documentation

The application provides interactive API documentation at:

**Swagger UI:** `http://localhost:8000/docs`
**ReDoc:** `http://localhost:8000/redoc`

These interfaces allow you to:
- View all available endpoints
- Test API calls directly in the browser
- See request/response schemas
- Download OpenAPI specification

## Error Handling

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (job/schedule doesn't exist)
- `422`: Validation Error (invalid request body)
- `500`: Internal Server Error

### Error Response Format

```json
{
  "detail": "Error message",
  "errors": [
    {
      "field": "services",
      "message": "Invalid service name: 'invalid-service'"
    }
  ]
}
```

### Common Errors

#### Invalid Provider
```json
{
  "detail": "Unsupported provider: 'invalid-provider'",
  "errors": []
}
```

#### Invalid Service
```json
{
  "detail": "Invalid services for aws: ['invalid-service']",
  "errors": []
}
```

#### Job Not Found
```json
{
  "detail": "Job not found: job_1234567890",
  "errors": []
}
```

#### Configuration Error
```json
{
  "detail": "No cloud providers enabled. Check ENABLED_PROVIDERS configuration.",
  "errors": []
}
```

## Rate Limiting

The API includes built-in rate limiting to prevent abuse:

- **Default**: 100 requests per minute per IP
- **Configurable**: Can be adjusted in configuration
- **Headers**: Rate limit information in response headers

## WebSocket Support

For real-time job monitoring, WebSocket connections are available:

**Endpoint:** `ws://localhost:8000/ws/jobs/{job_id}`

**Messages:**
```json
{
  "type": "progress",
  "data": {
    "job_id": "job_1234567890",
    "status": "running",
    "progress": {
      "processed_resources": 150,
      "total_resources": 245
    }
  }
}
```

## SDKs and Libraries

### Python Client

```python
import requests

class CSPScannerClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def trigger_extraction(self, provider=None, services=None, regions=None):
        payload = {}
        if provider:
            payload["provider"] = provider
        if services:
            payload["services"] = services
        if regions:
            payload["regions"] = regions
        
        response = requests.post(f"{self.base_url}/extraction/trigger", json=payload)
        return response.json()
    
    def get_job_status(self, job_id):
        response = requests.get(f"{self.base_url}/extraction/jobs/{job_id}")
        return response.json()

# Usage
client = CSPScannerClient()
result = client.trigger_extraction(services=["ec2", "s3"])
job_id = result["job_id"]
status = client.get_job_status(job_id)
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# List providers
curl http://localhost:8000/extraction/providers

# List services
curl http://localhost:8000/extraction/services

# Trigger extraction
curl -X POST http://localhost:8000/extraction/trigger \
  -H "Content-Type: application/json" \
  -d '{"services": ["ec2"]}'

# Check job status
curl http://localhost:8000/extraction/jobs/job_1234567890

# List schedules
curl http://localhost:8000/schedules/

# Create schedule
curl -X POST http://localhost:8000/schedules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily-scan",
    "cron_expression": "0 2 * * *",
    "services": ["ec2", "s3"]
  }'
```

## API Versioning

The API uses URL-based versioning:

- **Current Version**: v1 (`/api/v1/`)
- **Future Versions**: Will be added as `/api/v2/`, etc.

## Monitoring and Metrics

The API exposes Prometheus metrics at `/metrics` (if enabled):

- Request count and latency
- Job execution statistics
- Error rates
- Resource usage

## Production Considerations

### Security
- Add authentication/authorization
- Use HTTPS in production
- Implement rate limiting
- Validate input thoroughly

### Performance
- Use connection pooling
- Implement caching for metadata
- Consider API gateway
- Monitor response times

### Reliability
- Implement retry logic
- Add circuit breakers
- Use health checks
- Implement graceful shutdown

## Troubleshooting

### Common Issues

**Connection Refused**
- Ensure the application is running
- Check the correct port (default: 8000)
- Verify firewall settings

**Invalid JSON**
- Validate JSON syntax
- Check required fields
- Use tools like `jq` for validation

**Job Stuck in Running State**
- Check application logs
- Verify cloud provider credentials
- Look for network connectivity issues

**Empty Results**
- Verify cloud provider credentials
- Check resource permissions
- Ensure resources exist in specified regions

### Debug Mode

Enable debug logging for detailed API information:

```bash
export LOG_LEVEL="DEBUG"
uvicorn app.main:app --reload
```

### Logs

API logs include:
- Request/response details
- Error stack traces
- Performance metrics
- Cloud provider API calls

Check logs at:
- Console output (development)
- Log files (production)
- Cloud logging services