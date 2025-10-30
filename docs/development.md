---
layout: default
title: Development
nav_order: 10
---

# Development Guide

This guide covers development setup, contribution guidelines, architecture overview, and testing for the Cloud Artifact Extractor.

## Development Setup

### Prerequisites

- **Python 3.10 or higher**
- **Git** for version control
- **Cloud provider credentials** (AWS, Azure, or GCP) for testing
- **Virtual environment** tool (venv, conda, etc.)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ramesh-pegasys/csp-scanner.git
   cd csp-scanner
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development tools
   ```

4. **Set up pre-commit hooks** (optional)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Configuration for Development

Create a `.env` file for local development:

```bash
# Enable providers for testing
ENABLED_PROVIDERS=["aws"]

# AWS credentials (replace with your test credentials)
AWS_ACCESS_KEY_ID=your-test-key
AWS_SECRET_ACCESS_KEY=your-test-secret
AWS_DEFAULT_REGION=us-east-1

# Development settings
DEBUG=true
LOG_LEVEL=DEBUG

# Filesystem transport for easy testing
TRANSPORT_TYPE=filesystem
FILESYSTEM_BASE_DIR=./file_collector
```

### Verify Setup

```bash
# Check Python version
python --version

# Test import
python -c "import fastapi, boto3; print('✅ Dependencies OK')"

# Run basic health check
python -c "from app.core.config import get_settings; print('✅ Config loads')"

# Start development server
uvicorn app.main:app --reload
```

## Project Architecture

### Core Components

```
app/
├── api/              # FastAPI routes and endpoints
│   ├── routes/       # API route handlers
│   └── dependencies.py
├── cloud/            # Cloud provider abstractions
│   ├── aws_session.py    # AWS session wrapper
│   ├── azure_session.py  # Azure session wrapper
│   └── gcp_session.py    # GCP session wrapper
├── core/             # Configuration and utilities
│   ├── config.py     # Settings management
│   └── exceptions.py # Custom exceptions
├── extractors/       # Cloud service extractors
│   ├── base.py       # Base extractor class
│   ├── aws/          # AWS extractors
│   ├── azure/        # Azure extractors
│   └── gcp/          # GCP extractors
├── models/           # Pydantic data models
├── services/         # Business logic
│   ├── registry.py   # Extractor registry
│   └── orchestrator.py # Extraction orchestration
├── transport/        # Data transport mechanisms
│   ├── http.py       # HTTP transport
│   ├── filesystem.py # Filesystem transport
│   └── null.py       # Null transport
└── utils/            # Shared utilities
```

### Architecture Patterns

#### 1. Cloud Provider Abstraction

The `CloudSession` protocol provides a unified interface for all cloud providers:

```python
class CloudSession(Protocol):
    @property
    def provider(self) -> CloudProvider: ...
    def get_client(self, service: str, region: Optional[str] = None) -> Any: ...
    def list_regions(self) -> list[str]: ...
```

Each provider implements this protocol:
- **AWS**: Wraps `boto3.Session`
- **Azure**: Uses Azure SDK credentials
- **GCP**: Uses Google Auth credentials

#### 2. Extractor Pattern

All extractors inherit from `BaseExtractor`:

```python
class BaseExtractor(ABC):
    def __init__(self, session: CloudSession, config: Dict[str, Any]):
        self.session = session
        self.config = config
    
    @abstractmethod
    def get_metadata(self) -> ExtractorMetadata: ...
    
    @abstractmethod
    async def extract(self, region: Optional[str] = None, filters: Optional[Dict] = None) -> List[Dict]: ...
    
    @abstractmethod
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]: ...
```

#### 3. Multi-Cloud Registry

The `ExtractorRegistry` manages extractors across providers:

```python
class ExtractorRegistry:
    def __init__(self, sessions: Dict[CloudProvider, CloudSession], config: Settings):
        self.sessions = sessions
        self.extractors = {}
        self._register_extractors()
```

#### 4. Transport Abstraction

Multiple transport mechanisms for delivering artifacts:

```python
class Transport(ABC):
    @abstractmethod
    async def send(self, artifacts: List[Dict[str, Any]]) -> None: ...
```

### Data Flow

```
API Request → Orchestrator → Registry → Extractors → Transport → Destination
     ↓             ↓           ↓         ↓           ↓           ↓
  Trigger      Coordinate  Get Extractor  Extract    Transform  Send
  Job          Execution   by Service     Resources  to Standard Deliver
                                                        Format   Artifacts
```

## Development Workflow

### 1. Choose a Task

- **Bug fixes**: Look at GitHub issues
- **New features**: Check project roadmap
- **Documentation**: Update guides and API docs
- **Testing**: Add test coverage

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

Follow the established patterns:
- Add tests for new functionality
- Update documentation
- Follow code style guidelines
- Keep commits focused and atomic

### 4. Run Quality Checks

```bash
# Code formatting
black app tests

# Linting
flake8 app tests

# Type checking
mypy app

# Tests
pytest --cov=app --cov-report=term-missing
```

### 5. Test Your Changes

```bash
# Unit tests
pytest tests/test_your_feature.py

# Integration tests
pytest tests/integration/

# Manual testing
uvicorn app.main:app --reload
curl http://localhost:8000/health
```

### 6. Update Documentation

- Update API docs if endpoints changed
- Add examples for new features
- Update configuration documentation

### 7. Commit and Push

```bash
git add .
git commit -m "feat: add new feature description"
git push origin your-branch
```

### 8. Create Pull Request

- Use descriptive title and description
- Reference related issues
- Request review from maintainers

## Testing

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests
│   ├── test_extractors/
│   ├── test_transport/
│   └── test_services/
├── integration/          # Integration tests
│   ├── test_aws_extraction.py
│   ├── test_azure_extraction.py
│   └── test_gcp_extraction.py
└── e2e/                  # End-to-end tests
    └── test_full_workflow.py
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Specific test file
pytest tests/unit/test_extractors/test_ec2.py

# Tests matching pattern
pytest -k "test_extraction"

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Writing Tests

#### Unit Tests

```python
import pytest
from app.extractors.aws.ec2 import EC2Extractor

class TestEC2Extractor:
    def test_get_metadata(self):
        extractor = EC2Extractor(mock_session, {})
        metadata = extractor.get_metadata()
        assert metadata.service_name == "ec2"
        assert "instance" in metadata.resource_types

    def test_transform_instance(self):
        extractor = EC2Extractor(mock_session, {})
        raw_data = {"instance": mock_ec2_instance}
        result = extractor.transform(raw_data)
        
        assert result["cloud_provider"] == "aws"
        assert result["resource_type"] == "aws:ec2:instance"
        assert "metadata" in result
        assert "configuration" in result
```

#### Integration Tests

```python
import pytest
from app.services.orchestrator import ExtractionOrchestrator

@pytest.mark.asyncio
async def test_aws_ec2_extraction():
    # Requires real AWS credentials
    orchestrator = create_test_orchestrator()
    
    job_id = await orchestrator.run_extraction(
        services=["ec2"],
        regions=["us-east-1"]
    )
    
    # Wait for completion
    status = await orchestrator.get_job_status(job_id)
    assert status["status"] == "completed"
    assert status["resources_extracted"] > 0
```

#### Mocking Cloud APIs

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_aws_session():
    session = Mock()
    client = Mock()
    session.get_client.return_value = client
    session.provider = "aws"
    return session

def test_extractor_with_mock(mock_aws_session):
    with patch('boto3.client') as mock_client:
        mock_client.return_value.describe_instances.return_value = {
            'Reservations': [{'Instances': [mock_instance_data]}]
        }
        
        extractor = EC2Extractor(mock_aws_session, {})
        results = asyncio.run(extractor.extract())
        
        assert len(results) == 1
        assert results[0]["resource_type"] == "aws:ec2:instance"
```

### Test Coverage Goals

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: Cover all extractors with real APIs (optional)
- **E2E Tests**: Full workflow testing

### CI/CD Testing

GitHub Actions runs:
- Code quality checks (black, flake8, mypy)
- Unit tests with coverage
- Integration tests (with credentials)
- Security scanning

## Code Quality

### Code Style

- **Black**: Automatic code formatting
- **Flake8**: Linting and style checking
- **MyPy**: Static type checking
- **Pre-commit hooks**: Automated quality checks

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions
- `chore`: Maintenance

Examples:
```
feat(aws): add support for EC2 instance extraction
fix(azure): handle authentication errors gracefully
docs(api): update endpoint documentation
test(extractors): add unit tests for S3 extractor
```

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code style checks pass
- [ ] Type hints added
- [ ] No new linting errors
- [ ] Backward compatibility maintained
- [ ] Security considerations addressed

## Adding New Features

### New Cloud Provider

1. **Create session wrapper**
   ```python
   # app/cloud/newcloud_session.py
   class NewCloudSession:
       def __init__(self, credentials):
           self.credentials = credentials
       
       @property
       def provider(self):
           return CloudProvider.NEWCLOUD
       
       def get_client(self, service: str, region=None):
           # Return appropriate client
           pass
       
       def list_regions(self):
           # Return available regions
           pass
   ```

2. **Add to configuration**
   ```python
   # app/core/config.py
   newcloud_project_id: Optional[str] = None
   # ... other settings
   ```

3. **Create extractors**
   ```python
   # app/extractors/newcloud/service.py
   class NewCloudServiceExtractor(BaseExtractor):
       def get_metadata(self):
           return ExtractorMetadata(
               service_name="service",
               cloud_provider="newcloud",
               # ...
           )
   ```

4. **Update registry**
   ```python
   # app/services/registry.py
   def _register_newcloud_extractors(self, session):
       # Register extractors
       pass
   ```

### New Service Extractor

1. **Create extractor class**
   ```python
   class NewServiceExtractor(BaseExtractor):
       def get_metadata(self):
           return ExtractorMetadata(
               service_name="newservice",
               resource_types=["resource"],
               cloud_provider="aws",  # or azure, gcp
           )
       
       async def extract(self, region=None, filters=None):
           client = self.session.get_client("newservice", region)
           # Extract logic
           pass
       
       def transform(self, raw_data):
           return {
               "cloud_provider": "aws",
               "resource_type": "aws:newservice:resource",
               "metadata": self.create_metadata_object(...),
               "configuration": {...},
               "raw": raw_data,
           }
   ```

2. **Register in registry**
   ```python
   # app/services/registry.py
   from app.extractors.aws.newservice import NewServiceExtractor
   
   def _register_aws_extractors(self, session):
       extractors = [NewServiceExtractor, ...]
       for extractor_class in extractors:
           # registration logic
   ```

3. **Add configuration**
   ```yaml
   # config/extractors.yaml
   aws:
     newservice:
       max_workers: 10
       # service-specific options
   ```

4. **Add tests**
   ```python
   # tests/unit/test_extractors/test_newservice.py
   class TestNewServiceExtractor:
       # test methods
   ```

### New Transport Method

1. **Create transport class**
   ```python
   # app/transport/newtransport.py
   class NewTransport(Transport):
       def __init__(self, config):
           self.config = config
       
       async def send(self, artifacts):
           # Send logic
           pass
   ```

2. **Add to factory**
   ```python
   # app/transport/factory.py
   def create(transport_type: str, config: Dict) -> Transport:
       if transport_type == "newtransport":
           return NewTransport(config)
       # ...
   ```

3. **Add configuration**
   ```yaml
   # config/production.yaml
   transport_type: "newtransport"
   newtransport_option: "value"
   ```

## Debugging

### Logging

Enable debug logging:

```bash
export LOG_LEVEL="DEBUG"
uvicorn app.main:app --reload
```

### Common Debug Scenarios

#### Authentication Issues
```python
# Test credentials manually
import boto3
client = boto3.client('sts')
print(client.get_caller_identity())
```

#### API Call Debugging
```python
# Add logging to see API calls
import logging
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
```

#### Performance Issues
```python
# Profile code execution
import cProfile
cProfile.run('main_function()')
```

### Development Tools

#### VS Code Extensions
- Python
- Pylance
- Black Formatter
- Flake8
- MyPy Type Checker

#### Useful Commands
```bash
# Check imports
python -c "import app.main; print('Imports OK')"

# Validate configuration
python -c "from app.core.config import get_settings; get_settings()"

# Test specific extractor
python -c "
from app.extractors.aws.ec2 import EC2Extractor
from app.cloud.aws_session import AWSSession
import boto3
session = AWSSession(boto3.Session())
extractor = EC2Extractor(session, {})
print('Extractor created successfully')
"
```

## Contributing Guidelines

### Issue Reporting

- Use GitHub issues for bugs and feature requests
- Include reproduction steps
- Add environment details (Python version, OS, cloud provider)
- Attach relevant logs

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Add** tests
5. **Update** documentation
6. **Run** quality checks
7. **Submit** pull request

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help newcomers learn
- Focus on solutions, not problems

## Release Process

### Versioning

Follow semantic versioning (MAJOR.MINOR.PATCH)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped
- [ ] Release notes written
- [ ] CI/CD passes
- [ ] Tag created
- [ ] Release published

### Deployment

```bash
# Create release
git tag v1.2.3
git push origin v1.2.3

# GitHub Actions will:
# - Build Docker image
# - Run tests
# - Create release
# - Deploy to staging/production
```

## Getting Help

### Resources

- **Documentation**: This guide and API docs
- **Issues**: GitHub issues for bugs
- **Discussions**: GitHub discussions for questions
- **Slack/Teams**: Team communication channels

### Common Questions

**Q: How do I add a new AWS service?**
A: Follow the "New Service Extractor" section above.

**Q: Why are my tests failing?**
A: Check that you have test credentials configured and the service is accessible.

**Q: How do I debug API issues?**
A: Enable debug logging and check cloud provider documentation.

**Q: What's the difference between unit and integration tests?**
A: Unit tests test individual components with mocks; integration tests test with real APIs.

## Future Development

### Roadmap

- **Q2 2024**: Additional GCP services
- **Q3 2024**: Enhanced filtering and querying
- **Q4 2024**: Multi-cloud compliance reporting
- **2025**: Advanced analytics and insights

### Contributing Areas

- **New extractors**: Add support for more cloud services
- **Performance**: Optimize extraction speed and memory usage
- **Security**: Enhance credential handling and access controls
- **Monitoring**: Add metrics and observability
- **Documentation**: Improve guides and examples

---

Thank you for contributing to the Cloud Artifact Extractor! Your contributions help make cloud security scanning better for everyone.