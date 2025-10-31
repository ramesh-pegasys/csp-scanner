# Contributing to Cloud Artifact Extractor

Thank you for your interest in contributing to the Cloud Artifact Extractor! This document provides guidelines and instructions for contributors.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Known Issues & Areas for Improvement](#known-issues--areas-for-improvement)

## Development Setup

### Prerequisites

- Python 3.12 or higher
- AWS credentials with read access to cloud services (see README.md for details)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd csp-scanner
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up AWS credentials** (see README.md for detailed instructions)

5. **Verify setup**
   ```bash
   python -c "import boto3; print('AWS setup successful')"
   uvicorn app.main:app --reload
   ```

## Project Architecture

The project follows a modular architecture designed for maintainability and scalability:

```
app/
├── api/              # FastAPI routes and endpoints
│   ├── routes/       # API route handlers
│   └── dependencies.py
├── core/             # Core configuration and utilities
├── extractors/       # AWS service-specific extractors
├── models/           # Pydantic models for data structures
├── services/         # Business logic and orchestration
├── transport/        # Data transport mechanisms
└── utils/            # Shared utility functions
```

### Architecture Guidelines

#### Adding New Features

1. **New AWS Service Support**
   - Create extractor in `app/extractors/`
   - Follow the base extractor pattern (inherit from `BaseExtractor`)
   - Add service to registry in `app/services/registry.py`
   - Update configuration in `config/extractors.yaml`

2. **New API Endpoints**
   - Add routes in appropriate file under `app/api/routes/`
   - Include proper error handling and validation
   - Add OpenAPI documentation

3. **New Transport Methods**
   - Implement transport class in `app/transport/`
   - Register in `TransportFactory`
   - Add configuration support

4. **New Models**
   - Define Pydantic models in `app/models/`
   - Ensure proper validation and documentation

#### Code Organization Principles

- **Single Responsibility**: Each module/class has one clear purpose
- **Dependency Injection**: Use constructor injection for dependencies
- **Configuration-Driven**: Make behavior configurable through settings
- **Error Handling**: Use custom exceptions from `app.core.exceptions`
- **Logging**: Use structured logging with appropriate levels

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes following the architecture guidelines**

3. **Write tests** for new functionality

4. **Run tests and ensure coverage >90%**
   ```bash
   python -m pytest --cov=app --cov-report=term-missing
   ```

5. **Run code quality checks**
   ```bash
   black app tests
   flake8 app tests
   mypy app
   ```

6. **Update documentation** if needed

## Testing

### Test Structure

Tests are organized to mirror the application structure:

```
tests/
├── conftest.py           # Shared test fixtures
├── test_*.py            # Unit and integration tests
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_extractors.py

# Run tests matching pattern
python -m pytest -k "test_extraction"
```

### Coverage Requirements

- **Minimum Coverage**: 90% overall (current: 91.87%)
- **Coverage Report**: Must include line-by-line missing coverage
- **Exclusions**: Only `file_collector/` and `sample_extractions/` are excluded

**Note**: Some Pydantic deprecation warnings may appear in test output. These are from the current codebase and should be addressed in future updates to maintain compatibility with Pydantic V3.

### Writing Tests

1. **Use descriptive test names** that explain what is being tested
2. **Test both success and failure scenarios**
3. **Use fixtures** for common setup (defined in `conftest.py`)
4. **Mock external dependencies** (AWS services, HTTP calls)
5. **Test async code** properly with `pytest-asyncio`

Example test structure:
```python
import pytest
from app.services.orchestrator import ExtractionOrchestrator

class TestExtractionOrchestrator:
    def test_successful_extraction(self, orchestrator_fixture):
        # Test successful extraction flow

    def test_extraction_with_errors(self, orchestrator_fixture):
        # Test error handling

    @pytest.mark.asyncio
    async def test_concurrent_extractions(self, orchestrator_fixture):
        # Test concurrent processing
```

## Code Style

### Python Style

- **Black**: Code formatting (line length: 88 characters)
- **Flake8**: Linting and style checking
- **MyPy**: Static type checking

### Commit Messages

Follow conventional commit format:
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
- `test`: Test additions/modifications
- `chore`: Maintenance tasks

### Documentation

- **Docstrings**: Use Google-style docstrings for all public functions/classes
- **Type Hints**: Include type annotations for function parameters and return values
- **Comments**: Explain complex logic, not obvious code

## Pull Request Process

### Before Submitting

1. **Run pre-commit checks**
   ```bash
   python precommit_checks.py
   ```
   This will run all code quality checks, tests, and update coverage badges and documentation dates.

2. **Ensure all tests pass**
3. **Verify test coverage >90%**
4. **Update documentation**
5. **Test manually** if applicable

### PR Template

When creating a pull request, include:

- **Description**: What changes were made and why
- **Testing**: How the changes were tested
- **Coverage**: Current test coverage percentage
- **Breaking Changes**: Any breaking changes (if applicable)

### Review Process

1. **Automated Checks**: CI will run tests and quality checks
2. **Code Review**: At least one maintainer review required
3. **Coverage Check**: Must maintain >90% coverage
4. **Merge**: Squash merge with descriptive commit message

### Post-Merge

- **Deploy**: Changes are automatically deployed to staging
- **Monitor**: Check application logs and metrics
- **Rollback**: Be prepared to rollback if issues arise

## Known Issues & Areas for Improvement

### High Priority
- **Type Safety**: Fix mypy errors in `app/main.py` (variable redefinition issue)
- **Code Quality**: Address flake8 violations (unused imports, line length)
- **Pydantic Migration**: Update to Pydantic V2 patterns (remove deprecated `Config` classes)

### Medium Priority  
- **Test Coverage**: Improve coverage for extractors with low coverage (<90%)
- **Error Handling**: Add proper error handling for AWS API failures
- **Documentation**: Add docstrings to all public functions and classes

### Future Enhancements
- **Performance**: Optimize concurrent extraction processing
- **Monitoring**: Add metrics and health checks
- **Configuration**: Support for more cloud providers beyond AWS

## Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions
- **Documentation**: Check README.md and inline documentation

Thank you for contributing to the Cloud Artifact Extractor! 🚀