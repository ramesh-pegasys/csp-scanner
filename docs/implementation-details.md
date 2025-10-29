---
layout: default
title: Implementation Details
nav_order: 7
---

# Implementation Details

This document provides technical details about the Cloud Artifact Extractor's architecture, design patterns, and implementation specifics.

## Architecture Overview

The Cloud Artifact Extractor follows a modular, cloud-agnostic architecture designed for scalability, maintainability, and extensibility.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud APIs    │    │   Extractors    │    │   Transports    │
│                 │    │                 │    │                 │
│ • AWS SDK       │    │ • AWS Extractors│    │ • HTTP API      │
│ • Azure SDK     │    │ • Azure Extractors│  │ • Filesystem    │
│ • GCP SDK       │    │ • GCP Extractors│    │ • Null Transport│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Core Engine   │
                    │                 │
                    │ • Session Mgmt  │
                    │ • Orchestration │
                    │ • Error Handling│
                    └─────────────────┘
```

## Core Components

### 1. Cloud Sessions

Cloud sessions provide authenticated, provider-specific connections:

```python
# app/core/sessions.py
class CloudSession(ABC):
    """Abstract base class for cloud provider sessions"""
    
    @abstractmethod
    def get_client(self, service_name: str) -> Any:
        """Get authenticated client for specific service"""
        pass
    
    @abstractmethod
    def get_credentials(self) -> Dict[str, str]:
        """Get session credentials for serialization"""
        pass
```

**AWS Session Implementation:**
```python
class AWSSession(CloudSession):
    def __init__(self, region: str, profile: Optional[str] = None):
        self.session = boto3.Session(
            region_name=region,
            profile_name=profile
        )
    
    def get_client(self, service_name: str):
        return self.session.client(service_name)
```

**Azure Session Implementation:**
```python
class AzureSession(CloudSession):
    def __init__(self, subscription_id: str, credential):
        self.subscription_id = subscription_id
        self.credential = credential
        self.clients = {}
    
    def get_client(self, service_name: str):
        if service_name not in self.clients:
            client_class = getattr(azure.mgmt, service_name)
            self.clients[service_name] = client_class(
                self.credential, self.subscription_id
            )
        return self.clients[service_name]
```

### 2. Extractor Pattern

All resource extractors follow a consistent interface:

```python
# app/extractors/base.py
class BaseExtractor(ABC):
    """Base class for all cloud resource extractors"""
    
    def __init__(self, session: CloudSession, config: ExtractorConfig):
        self.session = session
        self.config = config
        self.metadata = ExtractorMetadata(
            service_name=self.get_service_name(),
            resource_types=self.get_resource_types()
        )
    
    @abstractmethod
    def extract(self) -> Iterator[Dict[str, Any]]:
        """Extract resources from cloud provider"""
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Return service name (e.g., 'ec2', 'compute')"""
        pass
    
    @abstractmethod
    def get_resource_types(self) -> List[str]:
        """Return list of resource types this extractor handles"""
        pass
```

**Example EC2 Extractor:**
```python
class EC2Extractor(BaseExtractor):
    def get_service_name(self) -> str:
        return "ec2"
    
    def get_resource_types(self) -> List[str]:
        return ["instance", "security-group", "vpc", "subnet"]
    
    def extract(self) -> Iterator[Dict[str, Any]]:
        client = self.session.get_client("ec2")
        
        # Extract instances
        instances = client.describe_instances()
        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:
                yield self.transform_instance(instance)
        
        # Extract security groups
        sgs = client.describe_security_groups()
        for sg in sgs["SecurityGroups"]:
            yield self.transform_security_group(sg)
```

### 3. Transport Layer

Transports handle output delivery:

```python
# app/transport/base.py
class BaseTransport(ABC):
    """Base class for output transports"""
    
    @abstractmethod
    def send(self, data: Dict[str, Any]) -> None:
        """Send extracted data to destination"""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered data"""
        pass
```

**Filesystem Transport:**
```python
class FilesystemTransport(BaseTransport):
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def send(self, data: Dict[str, Any]) -> None:
        resource_type = data["resource_type"].replace(":", "_")
        resource_id = data["metadata"]["resource_id"]
        
        filename = f"{resource_type}_{resource_id}_{timestamp()}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
```

## Design Patterns

### Factory Pattern for Sessions

```python
class SessionFactory:
    @staticmethod
    def create_session(provider: str, config: Dict[str, Any]) -> CloudSession:
        if provider == "aws":
            return AWSSession(**config)
        elif provider == "azure":
            return AzureSession(**config)
        elif provider == "gcp":
            return GCPSession(**config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
```

### Strategy Pattern for Extractors

```python
class ExtractorStrategy:
    def __init__(self, session: CloudSession):
        self.session = session
        self.extractors = {
            "aws:ec2": EC2Extractor,
            "aws:s3": S3Extractor,
            "azure:compute": AzureComputeExtractor,
            "gcp:compute": GCPComputeExtractor,
        }
    
    def get_extractor(self, resource_type: str) -> BaseExtractor:
        provider, service, resource = resource_type.split(":")
        extractor_class = self.extractors.get(resource_type)
        if not extractor_class:
            raise ValueError(f"No extractor for {resource_type}")
        return extractor_class(self.session)
```

### Observer Pattern for Progress Tracking

```python
class ExtractionProgress:
    def __init__(self):
        self.observers = []
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def notify_progress(self, resource_type: str, count: int):
        for observer in self.observers:
            observer.on_progress_update(resource_type, count)
```

## Configuration Management

### Extractor Configuration

```yaml
# config/extractors.yaml
extractors:
  aws:
    ec2:
      enabled: true
      regions: ["us-east-1", "us-west-2"]
      filters:
        instance-state-name: ["running", "stopped"]
    s3:
      enabled: true
      regions: ["us-east-1"]
      include_buckets: ["prod-*", "staging-*"]
  
  azure:
    compute:
      enabled: true
      subscriptions: ["sub-1", "sub-2"]
      resource_groups: ["rg-prod-*"]
    storage:
      enabled: true
      include_accounts: ["prod*", "staging*"]
  
  gcp:
    compute:
      enabled: true
      projects: ["my-prod-project"]
      zones: ["us-central1-*"]
    storage:
      enabled: true
      include_buckets: ["prod-*"]
```

### Application Configuration

```yaml
# config/production.yaml
app:
  name: "Cloud Artifact Extractor"
  version: "1.0.0"
  log_level: "INFO"

cloud_providers:
  aws:
    enabled: true
    regions: ["us-east-1", "us-west-2", "eu-west-1"]
    profiles: ["default", "prod"]
  
  azure:
    enabled: true
    subscriptions: ["xxx-xxx-xxx"]
    tenant_id: "xxx-xxx-xxx"
  
  gcp:
    enabled: true
    projects: ["my-project-123"]
    service_account_key: "/path/to/key.json"

transport:
  type: "filesystem"
  output_dir: "/var/data/extractions"
  compression: "gzip"

processing:
  max_workers: 4
  batch_size: 100
  retry_attempts: 3
  retry_delay: 1.0
```

## Error Handling and Resilience

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException()
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
```

### Retry with Exponential Backoff

```python
def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
):
    attempt = 0
    while attempt < max_attempts:
        try:
            return func()
        except Exception as e:
            attempt += 1
            if attempt == max_attempts:
                raise e
            
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            time.sleep(delay)
```

## Performance Optimizations

### Parallel Processing

```python
async def extract_resources_parallel(
    extractors: List[BaseExtractor],
    max_workers: int = 4
) -> AsyncIterator[Dict[str, Any]]:
    """Extract resources using parallel processing"""
    
    semaphore = asyncio.Semaphore(max_workers)
    
    async def extract_with_semaphore(extractor: BaseExtractor):
        async with semaphore:
            async for resource in extractor.extract_async():
                yield resource
    
    tasks = [
        extract_with_semaphore(extractor)
        for extractor in extractors
    ]
    
    for task in asyncio.as_completed(tasks):
        async for resource in task:
            yield resource
```

### Batching and Pagination

```python
def paginate_api_call(
    client_method: Callable,
    page_size: int = 100,
    **kwargs
) -> Iterator[Dict[str, Any]]:
    """Handle pagination for API calls"""
    
    paginator = client_method.paginate(
        PaginationConfig={
            'PageSize': page_size,
            'StartingToken': None
        },
        **kwargs
    )
    
    for page in paginator:
        yield from page.get('Items', [])
```

### Memory Management

```python
class StreamingJSONWriter:
    """Write large JSON files without loading everything into memory"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.first_item = True
    
    def __enter__(self):
        self.file = open(self.filepath, 'w')
        self.file.write('[\n')
        return self
    
    def write_item(self, item: Dict[str, Any]):
        if not self.first_item:
            self.file.write(',\n')
        json.dump(item, self.file, indent=2, default=str)
        self.first_item = False
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.write('\n]')
        self.file.close()
```

## Testing Strategy

### Unit Tests

```python
# tests/test_extractors.py
class TestEC2Extractor:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        client = MagicMock()
        session.get_client.return_value = client
        return session, client
    
    def test_extract_instances(self, mock_session):
        session, client = mock_session
        
        # Mock API response
        client.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "InstanceId": "i-123",
                    "InstanceType": "t3.medium",
                    "State": {"Name": "running"}
                }]
            }]
        }
        
        extractor = EC2Extractor(session)
        resources = list(extractor.extract())
        
        assert len(resources) == 1
        assert resources[0]["resource_type"] == "aws:ec2:instance"
        assert resources[0]["metadata"]["resource_id"] == "i-123"
```

### Integration Tests

```python
# tests/integration/test_aws_extraction.py
class TestAWSIntegration:
    @pytest.fixture(scope="class")
    def aws_session(self):
        # Use test AWS account/credentials
        return AWSSession(region="us-east-1", profile="test")
    
    def test_ec2_extraction_real_api(self, aws_session):
        extractor = EC2Extractor(aws_session)
        resources = list(extractor.extract())
        
        # Verify structure
        for resource in resources:
            assert "cloud_provider" in resource
            assert "resource_type" in resource
            assert "metadata" in resource
            assert "resource_id" in resource["metadata"]
```

### Mock Data Strategy

```python
# tests/fixtures/mock_responses.py
MOCK_EC2_INSTANCES = {
    "Reservations": [{
        "Instances": [{
            "InstanceId": "i-mock123",
            "InstanceType": "t3.medium",
            "State": {"Name": "running"},
            "Tags": [
                {"Key": "Name", "Value": "test-instance"},
                {"Key": "Environment", "Value": "test"}
            ]
        }]
    }]
}

MOCK_S3_BUCKETS = {
    "Buckets": [{
        "Name": "test-bucket",
        "CreationDate": "2024-01-01T00:00:00Z"
    }]
}
```

## Deployment and Containerization

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app.main; print('OK')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloud-artifact-extractor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cloud-artifact-extractor
  template:
    metadata:
      labels:
        app: cloud-artifact-extractor
    spec:
      containers:
      - name: extractor
        image: myregistry/cloud-artifact-extractor:latest
        ports:
        - containerPort: 8000
        env:
        - name: CONFIG_FILE
          value: "/config/production.yaml"
        volumeMounts:
        - name: config-volume
          mountPath: /config
        - name: output-volume
          mountPath: /output
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: config-volume
        configMap:
          name: extractor-config
      - name: output-volume
        persistentVolumeClaim:
          claimName: extractor-output-pvc
```

## Monitoring and Observability

### Metrics Collection

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

extraction_duration = Histogram(
    'extraction_duration_seconds',
    'Time spent extracting resources',
    ['provider', 'service', 'resource_type']
)

extraction_count = Counter(
    'extraction_count_total',
    'Number of resources extracted',
    ['provider', 'service', 'resource_type']
)

extraction_errors = Counter(
    'extraction_errors_total',
    'Number of extraction errors',
    ['provider', 'service', 'resource_type', 'error_type']
)

active_extractors = Gauge(
    'active_extractors',
    'Number of currently active extractors'
)
```

### Logging Configuration

```python
# app/core/logging.py
import structlog

def configure_logging(level: str = "INFO"):
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if sys.stderr.isatty():
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### Health Checks

```python
# app/api/health.py
from fastapi import APIRouter, HTTPException
from app.core.sessions import SessionFactory

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "checks": {}
    }
    
    # Check cloud provider connectivity
    providers = ["aws", "azure", "gcp"]
    for provider in providers:
        try:
            session = SessionFactory.create_session(provider, {})
            # Test basic connectivity
            health_status["checks"][f"{provider}_connectivity"] = "ok"
        except Exception as e:
            health_status["checks"][f"{provider}_connectivity"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"
    
    # Check database/file system
    try:
        # Test output directory access
        health_status["checks"]["filesystem"] = "ok"
    except Exception as e:
        health_status["checks"]["filesystem"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status
```

## Security Considerations

### Credential Management

```python
# app/core/credentials.py
class CredentialManager:
    def __init__(self):
        self.vault_client = hvac.Client()
    
    def get_credentials(self, provider: str, environment: str) -> Dict[str, str]:
        """Retrieve credentials from HashiCorp Vault"""
        path = f"secret/cloud-extractor/{environment}/{provider}"
        secret = self.vault_client.secrets.kv.v1.read_secret_version(path=path)
        
        return secret["data"]["data"]
    
    def rotate_credentials(self, provider: str, environment: str):
        """Rotate credentials and update Vault"""
        new_credentials = self.generate_credentials(provider)
        
        # Update cloud provider
        self.update_cloud_credentials(provider, new_credentials)
        
        # Update Vault
        path = f"secret/cloud-extractor/{environment}/{provider}"
        self.vault_client.secrets.kv.v1.create_or_update_secret(
            path=path,
            secret=dict(data=new_credentials)
        )
```

### Data Encryption

```python
# app/core/encryption.py
from cryptography.fernet import Fernet

class DataEncryptor:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt sensitive data before storage"""
        json_data = json.dumps(data, default=str)
        return self.fernet.encrypt(json_data.encode())
    
    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt stored data"""
        decrypted = self.fernet.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
```

### Access Control

```python
# app/core/auth.py
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

class JWTAuthenticator:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.security = HTTPBearer()
    
    async def authenticate(
        self, credentials: HTTPAuthorizationCredentials
    ) -> Dict[str, Any]:
        """Authenticate JWT token"""
        try:
            payload = jwt.decode(
                credentials.credentials,
                self.secret_key,
                algorithms=["HS256"]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
    
    def authorize(self, user: Dict[str, Any], required_role: str) -> bool:
        """Check if user has required role"""
        user_roles = user.get("roles", [])
        return required_role in user_roles
```

This implementation provides a robust, scalable foundation for cloud artifact extraction with comprehensive error handling, security, and observability features.