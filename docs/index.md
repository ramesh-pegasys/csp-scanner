---
layout: default
title: Home
nav_order: 1
---

<div class="hero">
  <div class="hero-title">Cloud Artifact Extractor</div>
  <div class="hero-subtitle">A modern FastAPI service for extracting and managing cloud service artifacts from AWS, Azure, and GCP.<br>Beautiful, secure, and multi-cloud ready.</div>
    <a href="{{ '/getting-started.html' | relative_url }}" class="btn">Get Started</a>
</div>

# Cloud Artifact Extractor

[![CI](https://github.com/ramesh-pegasys/csp-scanner/actions/workflows/ci.yml/badge.svg)](https://github.com/ramesh-pegasys/csp-scanner/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://pytest-cov.readthedocs.io/)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Flake8](https://img.shields.io/badge/flake8-checked-blue.svg)](https://flake8.pycqa.org/)
[![Black](https://img.shields.io/badge/black-formatted-black.svg)](https://github.com/psf/black)

A FastAPI-based service for extracting and managing cloud service artifacts from AWS, Azure, and GCP.

## 🚀 Quickstart


Get up and running in minutes:

- **[Installation & Setup]({{ '/getting-started.html' | relative_url }})** - Install dependencies and configure your environment
- **[Configuration Guide]({{ '/configuration.html' | relative_url }})** - Learn about configuration options and transport methods
- **[API Reference]({{ '/api-reference.html' | relative_url }})** - Explore available API endpoints

## ☁️ Cloud Providers

The CSP Scanner supports extracting resources from multiple cloud providers:

### Amazon Web Services (AWS)
- **Setup**: [AWS Guide]({{ '/cloud-providers-aws.html' | relative_url }})
- **Resources**: 13+ services including EC2, S3, RDS, Lambda, IAM, VPC
- **Authentication**: Access keys, IAM roles, environment variables

### Microsoft Azure
- **Setup**: [Azure Guide]({{ '/cloud-providers-azure.html' | relative_url }})
- **Resources**: 8+ services including Compute, Storage, Network, Web Apps, SQL
- **Authentication**: Service Principal, Managed Identity, Azure CLI

### Google Cloud Platform (GCP)
- **Setup**: [GCP Guide]({{ '/cloud-providers-gcp.html' | relative_url }})
- **Resources**: 2+ services including Compute Engine, Cloud Storage
- **Authentication**: Service Account keys, Application Default Credentials

## 📋 Supported Resources

View the complete list of [supported cloud resources]({{ '/supported-resources.html' | relative_url }}) across all providers.

## 🛠️ Development

- **[Contributing Guide]({{ '/development.html' | relative_url }})** - How to contribute to the project
- **[Architecture Overview]({{ '/development.html#project-architecture' | relative_url }})** - Understanding the codebase
- **[Testing]({{ '/development.html#testing' | relative_url }})** - Running tests and coverage

## 📖 Documentation Sections

### User Guides
- [Quickstart]({{ '/getting-started.html' | relative_url }}) - Installation and basic setup
- [Configuration]({{ '/configuration.html' | relative_url }}) - Detailed configuration options
- [Cloud Providers]({{ '/cloud-providers.html' | relative_url }}) - Provider-specific setup guides
- [Supported Resources]({{ '/supported-resources.html' | relative_url }}) - Complete resource coverage
- [API Reference]({{ '/api-reference.html' | relative_url }}) - REST API documentation

### Developer Resources
- [Development]({{ '/development.html' | relative_url }}) - Contributing and development setup
- [Metadata Structure]({{ '/metadata-structure.html' | relative_url }}) - Cloud-agnostic data format
- [Implementation Details]({{ '/implementation-details.html' | relative_url }}) - Architecture and design

## 🔧 Key Features

- **Multi-Cloud Support**: Scan AWS, Azure, and GCP simultaneously
- **Flexible Transport**: HTTP, filesystem, or null transport options
- **Async Processing**: High-performance concurrent extraction
- **Configurable Batching**: Control extraction batch sizes and delays
- **Scheduled Scanning**: Automated periodic resource scanning
- **Cloud-Agnostic Output**: Consistent artifact format across providers

## 🏗️ Architecture

The scanner follows a modular architecture designed for extensibility:

```mermaid
graph TB
    subgraph FastAPI["FastAPI Application"]
        API[REST API Endpoints]
    end
    
    subgraph CloudSession["CloudSession Abstraction Layer"]
        AWS[AWSSession<br/>boto3]
        Azure[AzureSession<br/>Azure SDK]
        GCP[GCPSession<br/>Google Cloud SDK]
    end
    
    subgraph Registry["ExtractorRegistry (Multi-Cloud)"]
        AWSE[AWS Extractors<br/>EC2, S3, RDS, etc.]
        AzureE[Azure Extractors<br/>Compute, Storage, etc.]
        GCPE[GCP Extractors<br/>Compute, Storage, etc.]
    end
    
    subgraph Orchestrator["ExtractionOrchestrator"]
        Orch[Cloud-Agnostic Orchestration]
    end
    
    subgraph Transport["Transport Layer"]
        HTTP[HTTP Transport]
        FS[Filesystem Transport]
        Null[Null Transport]
    end
    
    API --> CloudSession
    AWS --> AWSE
    Azure --> AzureE
    GCP --> GCPE
    AWSE --> Orch
    AzureE --> Orch
    GCPE --> Orch
    Orch --> Transport
    
    style FastAPI fill:#dbeafe,stroke:#1a4fa3,stroke-width:2px
    style CloudSession fill:#e0f2fe,stroke:#1a4fa3,stroke-width:2px
    style Registry fill:#dbeafe,stroke:#1a4fa3,stroke-width:2px
    style Orchestrator fill:#e0f2fe,stroke:#1a4fa3,stroke-width:2px
    style Transport fill:#dbeafe,stroke:#1a4fa3,stroke-width:2px
```

## 📊 Use Cases

- **Security Scanning**: Extract cloud resources for policy compliance checking
- **Inventory Management**: Maintain up-to-date catalog of cloud assets
- **Cost Optimization**: Analyze resource usage and identify optimization opportunities
- **Compliance Auditing**: Ensure resources meet organizational standards
- **Multi-Cloud Governance**: Unified view across AWS, Azure, and GCP

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide]({{ '/development.html' | relative_url }}) for details on:

- Setting up a development environment
- Running tests and code quality checks
- Adding new cloud providers or services
- Code style and documentation standards

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ramesh-pegasys/csp-scanner/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ramesh-pegasys/csp-scanner/discussions)
- **Documentation**: This site contains comprehensive guides and API references

---

**Last Updated**: October 31, 2025