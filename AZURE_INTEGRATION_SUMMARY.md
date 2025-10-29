# Azure Integration Summary

## Quick Overview

This document provides a high-level summary of the plan to add Azure resource scanning capabilities to the CSP Scanner.

## Key Decision: Azure SDK for Python (NOT Bicep)

**❌ Bicep** - Infrastructure as Code language for *deploying* resources
**✅ Azure SDK for Python** - Runtime library for *reading* existing resources (like boto3 for AWS)

## Core Packages Needed

```bash
pip install azure-identity azure-mgmt-compute azure-mgmt-network \
    azure-mgmt-storage azure-mgmt-web azure-mgmt-sql
```

## Architecture Approach

### 1. Cloud Session Abstraction
Create a provider-agnostic session interface:
```
CloudSession (Protocol)
├── AWSSession (wraps boto3.Session)
└── AzureSession (wraps Azure credentials + management clients)
```

### 2. Multi-Provider Registry
```
ExtractorRegistry
├── AWS Extractors (EC2, S3, RDS, etc.)
└── Azure Extractors (Compute, Storage, Network, etc.)
```

### 3. Unified Configuration
```yaml
enabled_providers: ["aws", "azure"]

aws:
  access_key_id: xxx
  region: us-east-1

azure:
  subscription_id: xxx
  tenant_id: xxx
  client_id: xxx
```

## Implementation Phases

| Phase | Component | Status |
|-------|-----------|--------|
| 1 | Cloud session abstraction layer | Planned |
| 2 | Multi-cloud configuration | Planned |
| 3 | Enhanced extractor registry | Planned |
| 4 | Azure extractors (Compute, Storage) | Planned |
| 5 | Remaining Azure extractors | Planned |
| 6 | API updates for multi-cloud | Planned |

## Azure Resource Mappings

### Priority Resources (MVP)
- Virtual Machines → `azure:compute:virtual-machine`
- Storage Accounts → `azure:storage:account`
- Network Security Groups → `azure:network:nsg`
- App Services → `azure:web:app-service`
- SQL Databases → `azure:sql:database`

### Extended Resources
- AKS Clusters → `azure:containerservice:aks`
- Key Vaults → `azure:keyvault:vault`
- Function Apps → `azure:web:function-app`
- Load Balancers → `azure:network:load-balancer`
- Application Gateways → `azure:network:application-gateway`

## Backward Compatibility

✅ Existing AWS-only deployments continue to work unchanged
✅ Azure is opt-in via configuration
✅ Same API endpoints support both providers
✅ Transport and orchestration layers are already cloud-agnostic

## Example Usage

### Extract from AWS only (current behavior)
```bash
POST /api/v1/extract
{
  "provider": "aws",
  "services": ["ec2", "s3"]
}
```

### Extract from Azure only
```bash
POST /api/v1/extract
{
  "provider": "azure",
  "services": ["compute", "storage"]
}
```

### Extract from both providers
```bash
POST /api/v1/extract
{
  "services": null  # all services from all enabled providers
}
```

## Benefits

1. **Reuses Existing Architecture** - Same patterns for AWS and Azure
2. **Cloud-Agnostic Core** - Orchestrator and transport layers work for any provider
3. **Parallel Processing** - Azure extractors use same async/threading patterns
4. **Unified Output** - Same artifact format for all cloud providers
5. **Flexible Deployment** - Run AWS-only, Azure-only, or multi-cloud

## Next Steps

1. Review the detailed plan in `AZURE_INTEGRATION_PLAN.md`
2. Set up Azure test subscription and credentials
3. Implement Phase 1 (abstraction layer)
4. Create first Azure extractor (Virtual Machines)
5. Test end-to-end with both providers

## Questions?

- See detailed implementation in `AZURE_INTEGRATION_PLAN.md`
- Azure SDK documentation: https://docs.microsoft.com/en-us/azure/developer/python/
- Azure authentication: https://docs.microsoft.com/en-us/python/api/azure-identity/
