---
layout: default
title: Troubleshooting
nav_order: 9
---

# Troubleshooting

This guide helps you diagnose and resolve common issues with the Cloud Artifact Extractor.

## Quick Diagnosis

### Check Application Health

```bash
# Check if the application is running
curl http://localhost:8000/health

# Check logs
docker logs cloud-artifact-extractor

# Check container status
docker ps | grep cloud-artifact-extractor
```

### Validate Configuration

```bash
# Test configuration loading
python -c "from app.core.config import load_config; print(load_config())"

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/production.yaml'))"
```

### Test Cloud Connectivity

```bash
# Test AWS connectivity
aws sts get-caller-identity

# Test Azure connectivity
az account show

# Test GCP connectivity
gcloud auth list
```

## Common Issues and Solutions

### 1. Authentication Errors

#### AWS Authentication Issues

**Error:** `Unable to locate credentials`

**Solutions:**
```bash
# Check AWS credentials
aws configure list

# Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Use instance profile (EC2)
# Ensure instance has IAM role attached
```

**Error:** `AccessDenied` or `UnauthorizedOperation`

**Solutions:**
- Verify IAM permissions in AWS console
- Check IAM policy attached to user/role
- Ensure correct region is specified
- Check if MFA is required

#### Azure Authentication Issues

**Error:** `Authentication failed`

**Solutions:**
```bash
# Login to Azure CLI
az login

# Set subscription
az account set --subscription "your-subscription-id"

# Check service principal permissions
az role assignment list --assignee "your-service-principal-id"
```

#### GCP Authentication Issues

**Error:** `Could not load the default credentials`

**Solutions:**
```bash
# Set service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Login with user account
gcloud auth application-default login

# Check project access
gcloud projects list
```

### 2. Configuration Issues

#### Invalid YAML Configuration

**Error:** `yaml.YAMLError: mapping values are not allowed here`

**Solutions:**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/production.yaml'))"

# Check indentation (use spaces, not tabs)
# Ensure proper quoting of string values
# Check for duplicate keys
```

#### Missing Configuration Files

**Error:** `FileNotFoundError: config/production.yaml`

**Solutions:**
```bash
# Create config directory
mkdir -p config

# Copy from template
cp config/development.yaml config/production.yaml

# Set correct permissions
chmod 600 config/production.yaml
```

### 3. Network and Connectivity Issues

#### Connection Timeouts

**Error:** `ConnectTimeout` or `ReadTimeout`

**Solutions:**
- Check network connectivity to cloud APIs
- Verify proxy settings if behind corporate proxy
- Increase timeout values in configuration
- Check firewall rules

#### DNS Resolution Issues

**Error:** `NameResolutionError`

**Solutions:**
```bash
# Test DNS resolution
nslookup sts.amazonaws.com
nslookup management.azure.com
nslookup www.googleapis.com

# Check /etc/resolv.conf
cat /etc/resolv.conf

# Use different DNS server
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
```

### 4. Resource Extraction Issues

#### Empty Results

**Problem:** No resources extracted despite having resources in cloud

**Debugging:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check extractor configuration
python -c "from app.core.config import load_config; print(load_config()['extractors'])"

# Test specific extractor
python -c "
from app.extractors.aws.ec2 import EC2Extractor
from app.core.sessions import AWSSession
session = AWSSession()
extractor = EC2Extractor(session)
resources = list(extractor.extract())
print(f'Found {len(resources)} resources')
"
```

**Common Causes:**
- Incorrect region configuration
- Resources in different regions than specified
- IAM permissions insufficient for listing resources
- Resources filtered out by configuration

#### Partial Results

**Problem:** Some resources missing from extraction

**Debugging:**
```bash
# Check for pagination issues
# Enable verbose logging to see API calls
export LOG_LEVEL=DEBUG

# Test pagination manually
python -c "
import boto3
client = boto3.client('ec2')
paginator = client.get_paginator('describe_instances')
for page in paginator.paginate():
    print(f'Page has {len(page[\"Reservations\"])} reservations')
"
```

### 5. Performance Issues

#### Slow Extractions

**Symptoms:** Extractions taking too long

**Solutions:**
```yaml
# Increase parallel processing
processing:
  max_workers: 8  # Increase from default 4
  batch_size: 50   # Decrease for more frequent processing

# Optimize API calls
extractors:
  aws:
    ec2:
      page_size: 50  # Smaller pages for better responsiveness
```

#### Memory Issues

**Error:** `MemoryError` or out of memory

**Solutions:**
```yaml
# Reduce batch sizes
processing:
  batch_size: 25

# Enable streaming for large datasets
transport:
  type: "filesystem"
  streaming: true
  compression: "gzip"
```

### 6. Docker and Containerization Issues

#### Container Won't Start

**Error:** Container exits immediately

**Solutions:**
```bash
# Check container logs
docker logs <container_id>

# Run interactively to debug
docker run -it --entrypoint /bin/bash cloud-artifact-extractor

# Check health endpoint
docker exec <container_id> curl http://localhost:8000/health
```

#### Port Binding Issues

**Error:** Port already in use

**Solutions:**
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <pid>

# Use different port
docker run -p 8001:8000 cloud-artifact-extractor
```

### 7. File System Issues

#### Permission Denied

**Error:** `PermissionError: [Errno 13] Permission denied`

**Solutions:**
```bash
# Check directory permissions
ls -la /output/dir

# Fix permissions
chmod 755 /output/dir
chown app:app /output/dir

# Run container as correct user
docker run --user $(id -u):$(id -g) cloud-artifact-extractor
```

#### Disk Space Issues

**Error:** `OSError: [Errno 28] No space left on device`

**Solutions:**
```bash
# Check disk usage
df -h

# Clean up old extractions
find /output/dir -name "*.json" -mtime +30 -delete

# Use compression
transport:
  compression: "gzip"
```

### 8. Database Issues (if using database transport)

#### Connection Refused

**Error:** `Connection refused` or `Can't connect to MySQL server`

**Solutions:**
```bash
# Check database service
docker ps | grep mysql

# Test connection
mysql -h localhost -u user -p

# Check connection string
# Verify host, port, credentials in config
```

#### Migration Issues

**Error:** `Migration failed` or `Table doesn't exist`

**Solutions:**
```bash
# Run migrations manually
alembic upgrade head

# Check migration status
alembic current

# Reset database (CAUTION: destroys data)
alembic downgrade base
alembic upgrade head
```

## Debugging Tools

### Enable Debug Logging

```python
# In configuration
app:
  log_level: "DEBUG"

# Or environment variable
export LOG_LEVEL=DEBUG
```

### Log Analysis

```bash
# Search for errors
grep "ERROR" logs/application.log

# Find specific resource type issues
grep "ec2" logs/application.log | grep "failed"

# Monitor extraction progress
tail -f logs/application.log | grep "extracted"
```

### Profiling Performance

```python
# Add profiling to main.py
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your extraction code here

profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumtime')
stats.print_stats(20)  # Top 20 time-consuming functions
```

### Network Debugging

```bash
# Trace network calls
tcpdump -i any port 443

# Test API endpoints
curl -v https://ec2.amazonaws.com/

# Check SSL certificates
openssl s_client -connect ec2.amazonaws.com:443
```

## Advanced Troubleshooting

### Threading and Concurrency Issues

**Problem:** Deadlocks or race conditions

**Debugging:**
```python
# Enable thread debugging
import threading
threading._VERBOSE = True

# Check for deadlocks
import faulthandler
faulthandler.enable()

# Monitor thread activity
python -c "
import threading
import time
while True:
    print(f'Active threads: {threading.active_count()}')
    for t in threading.enumerate():
        print(f'  {t.name}: {t.is_alive()}')
    time.sleep(5)
"
```

### Memory Leaks

**Problem:** Memory usage growing over time

**Debugging:**
```python
# Memory profiling
from memory_profiler import profile

@profile
def extract_resources():
    # Your extraction code
    pass

# Or use tracemalloc
import tracemalloc
tracemalloc.start()

# Your code here

current, peak = tracemalloc.get_traced_memory()
print(f'Current memory usage: {current / 1024 / 1024:.1f} MB')
print(f'Peak memory usage: {peak / 1024 / 1024:.1f} MB')
```

### API Rate Limiting

**Problem:** `ThrottlingException` or rate limit errors

**Solutions:**
```yaml
# Implement backoff and retry
processing:
  retry_attempts: 5
  retry_delay: 2.0
  exponential_backoff: true

# Reduce concurrency
processing:
  max_workers: 2

# Add delays between requests
processing:
  request_delay: 0.1  # seconds
```

## Getting Help

### Log Collection

When reporting issues, include:

```bash
# System information
uname -a
python --version
docker --version

# Application logs
tail -100 logs/application.log

# Configuration (redact sensitive data)
grep -v "password\|secret\|key" config/production.yaml

# Environment variables
env | grep -E "(AWS|AZURE|GOOGLE)" | head -10
```

### Support Channels

1. **GitHub Issues**: For bugs and feature requests
2. **Documentation**: Check this troubleshooting guide
3. **Community**: Search existing issues and discussions
4. **Logs**: Enable debug logging and provide relevant excerpts

### Emergency Contacts

For production issues:
- Check monitoring dashboards
- Review recent deployments
- Contact on-call engineer
- Escalate to infrastructure team if needed

## Prevention Best Practices

### Monitoring Setup

```yaml
# Enable metrics collection
monitoring:
  enabled: true
  metrics_port: 9090
  prometheus_endpoint: "/metrics"

# Set up alerts
alerts:
  - name: "extraction_failures"
    condition: "extraction_errors_total > 10"
    severity: "warning"
  
  - name: "high_memory_usage"
    condition: "memory_usage_percent > 90"
    severity: "critical"
```

### Regular Maintenance

```bash
# Update dependencies monthly
pip list --outdated
pip install --upgrade -r requirements.txt

# Rotate credentials quarterly
# Update SSL certificates
# Review and update IAM policies

# Backup configurations
cp config/production.yaml config/production.yaml.backup

# Clean up old logs and extractions
find logs/ -name "*.log" -mtime +30 -delete
find extractions/ -name "*.json" -mtime +90 -delete
```

### Testing Strategy

```bash
# Run tests before deployment
pytest tests/ -v

# Test in staging environment
# Validate with subset of production data
# Monitor performance metrics

# Integration tests
pytest tests/integration/ -v --tb=short
```

This comprehensive troubleshooting guide should help resolve most issues. If you encounter problems not covered here, please check the GitHub issues or create a new issue with detailed information.