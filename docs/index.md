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
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)(https://pytest-cov.readthedocs.io/)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Flake8](https://img.shields.io/badge/flake8-checked-blue.svg)](https://flake8.pycqa.org/)
[![Black](https://img.shields.io/badge/black-formatted-black.svg)](https://github.com/psf/black)

A FastAPI-based service for extracting and managing cloud service artifacts across AWS, Azure, and Google Cloud Platform. Built for security scanning, inventory management, and multi-cloud governance.

## 🚀 Quick Links

<div class="card-grid">
  <div class="card">
    <h3>📘 Getting Started</h3>
    <p>Install and configure the scanner in minutes</p>
    <a href="{{ '/getting-started.html' | relative_url }}">Get Started →</a>
  </div>
  
  <div class="card">
    <h3>☁️ Cloud Providers</h3>
    <p>Setup guides for AWS, Azure, and GCP</p>
    <a href="{{ '/cloud-providers.html' | relative_url }}">View Providers →</a>
  </div>
  
  <div class="card">
    <h3>⚙️ Configuration</h3>
    <p>Configure transport, batching, and scheduling</p>
    <a href="{{ '/configuration.html' | relative_url }}">Configure →</a>
  </div>
  
  <div class="card">
    <h3>📚 API Reference</h3>
    <p>Explore REST API endpoints and examples</p>
    <a href="{{ '/api-reference.html' | relative_url }}">View API →</a>
  </div>
</div>

## 🔧 Key Features

- **Multi-Cloud Support** - Scan AWS, Azure, and GCP with a unified interface
- **Flexible Transport** - Send artifacts via HTTP, filesystem, or null transport
- **Async Processing** - High-performance concurrent extraction
- **Scheduled Scanning** - Automated periodic resource scanning with cron expressions
- **Cloud-Agnostic Output** - Consistent metadata format across all providers
- **Extensible Architecture** - Easy to add new providers and resource types

## ☁️ Supported Cloud Providers

| Provider | Services | Authentication Methods |
|----------|----------|------------------------|
| **AWS** | 13+ services (EC2, S3, RDS, Lambda, IAM, VPC, etc.) | Access Keys, IAM Roles, Environment Variables |
| **Azure** | 8+ services (Compute, Storage, Network, Web Apps, SQL, etc.) | Service Principal, Managed Identity, Azure CLI |
| **GCP** | 2+ services (Compute Engine, Cloud Storage) | Service Account Keys, Application Default Credentials |

[View all supported resources →]({{ '/supported-resources.html' | relative_url }})

## � Documentation

### For Users
- **[Getting Started]({{ '/getting-started.html' | relative_url }})** - Quick installation and setup guide
- **[Configuration]({{ '/configuration.html' | relative_url }})** - Environment variables, YAML files, and settings
- **[Cloud Providers]({{ '/cloud-providers.html' | relative_url }})** - Provider-specific setup and authentication
- **[API Reference]({{ '/api-reference.html' | relative_url }})** - Complete REST API documentation
- **[Operations]({{ '/operations.html' | relative_url }})** - Running extractions and managing schedules
- **[Troubleshooting]({{ '/troubleshooting.html' | relative_url }})** - Common issues and solutions

### For Developers
- **[Development Guide]({{ '/development.html' | relative_url }})** - Contributing and development setup
- **[Implementation Details]({{ '/implementation-details.html' | relative_url }})** - Architecture and design patterns
- **[Metadata Structure]({{ '/metadata-structure.html' | relative_url }})** - Cloud-agnostic data format specification

## 📊 Common Use Cases

- **Security Scanning** - Extract cloud resources for policy compliance and security analysis
- **Inventory Management** - Maintain an up-to-date catalog of all cloud assets
- **Cost Optimization** - Analyze resource usage patterns and identify cost savings
- **Compliance Auditing** - Verify resources meet organizational and regulatory standards
- **Multi-Cloud Governance** - Unified visibility and control across multiple cloud providers

## 🤝 Contributing

We welcome contributions! See our [Development Guide]({{ '/development.html' | relative_url }}) for:

- Setting up a development environment
- Running tests and code quality checks
- Adding new cloud providers or services
- Code style and documentation standards

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/ramesh-pegasys/csp-scanner/blob/main/LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ramesh-pegasys/csp-scanner/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ramesh-pegasys/csp-scanner/discussions)

---

**Last Updated**: November 01, 2025