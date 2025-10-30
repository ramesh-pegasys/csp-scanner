---
layout: default
title: Supported Resources
nav_order: 5
---

# Supported Resources

This document provides comprehensive information about all cloud resources supported by the CSP Scanner across AWS, Azure, and GCP.

## Overview

The scanner currently supports **3 cloud providers** with **50+ resource types**:

- **AWS**: 13 services, 20+ resource types
- **Azure**: 8 services, 20+ resource types
- **GCP**: 5 services, 10+ resource types

## Resource Type Naming Convention

All resources follow a consistent naming pattern:
```
{cloud_provider}:{service}:{resource_type}
```

Examples:
- `aws:ec2:instance`
- `azure:compute:virtual-machine`
- `gcp:compute:instance`

## Metadata Structure

All extracted resources include standardized metadata:

```json
{
  "cloud_provider": "aws|azure|gcp",
  "resource_type": "provider:service:type",
  "metadata": {
    "resource_id": "unique-resource-identifier",
    "service": "service-name",
    "region": "region-or-location",
    "account_id|subscription_id|project_id": "cloud-account-identifier",
    "labels": {
      "key": "value"
    }
  },
  "configuration": {
    // Resource-specific configuration
  },
  "raw": {
    // Full cloud provider API response
  }
}
```

## Amazon Web Services (AWS)

### Compute Services

#### EC2 Instances (`aws:ec2:instance`)
- **Description**: Virtual machines and their configurations
- **Extracted Data**:
  - Instance ID, type, state, and AMI
  - Network interfaces, security groups, and subnets
  - EBS volumes and their configurations
  - Tags, key pairs, and instance metadata
  - Launch time and availability zone
- **Configuration Options**:
  - `max_workers`: Parallel extraction workers
  - `include_stopped`: Include stopped instances
  - `include_terminated`: Include terminated instances

#### EC2 Security Groups (`aws:ec2:security-group`)
- **Description**: Security group rules and configurations
- **Extracted Data**:
  - Inbound and outbound rules
  - Referenced security groups and CIDR blocks
  - VPC association and description
  - Tags and metadata

### Storage Services

#### S3 Buckets (`aws:s3:bucket`)
- **Description**: S3 bucket configurations and policies
- **Extracted Data**:
  - Bucket policies and ACLs
  - Versioning, encryption, and logging settings
  - CORS configuration and lifecycle rules
  - Public access block settings
  - Replication and analytics configurations
- **Configuration Options**:
  - `include_bucket_policies`: Extract bucket policies
  - `include_bucket_acl`: Extract bucket ACLs
  - `check_public_access`: Check for public access

### Database Services

#### RDS Instances (`aws:rds:db-instance`)
- **Description**: Relational database instances
- **Extracted Data**:
  - Engine type, version, and instance class
  - Storage configuration and backup settings
  - Multi-AZ deployment and read replicas
  - Security groups and subnet groups
  - Parameter groups and option groups

#### RDS Clusters (`aws:rds:db-cluster`)
- **Description**: Aurora and other clustered databases
- **Extracted Data**:
  - Cluster configuration and member instances
  - Global database settings
  - Backup and maintenance windows

### Serverless Services

#### Lambda Functions (`aws:lambda:function`)
- **Description**: Serverless function configurations
- **Extracted Data**:
  - Runtime, handler, and memory settings
  - Environment variables and VPC configuration
  - IAM role and permissions
  - Event source mappings and aliases
- **Configuration Options**:
  - `include_versions`: Extract function versions
  - `include_aliases`: Extract function aliases

### Identity & Access Management

#### IAM Users (`aws:iam:user`)
- **Description**: IAM user accounts and configurations
- **Extracted Data**:
  - User policies and attached managed policies
  - Access keys and their status
  - MFA devices and password settings
  - Groups and inline policies

#### IAM Roles (`aws:iam:role`)
- **Description**: IAM roles and their trust relationships
- **Extracted Data**:
  - Assume role policies and permissions
  - Attached managed policies
  - Instance profiles and role usage

#### IAM Policies (`aws:iam:policy`)
- **Description**: IAM policies (managed and inline)
- **Extracted Data**:
  - Policy documents and versions
  - Attachment information
  - AWS managed vs customer managed

### Networking Services

#### VPCs (`aws:vpc:vpc`)
- **Description**: Virtual private clouds
- **Extracted Data**:
  - CIDR blocks and tenancy
  - DHCP options and DNS settings
  - Associated subnets and route tables

#### Subnets (`aws:vpc:subnet`)
- **Description**: VPC subnets
- **Extracted Data**:
  - CIDR block and availability zone
  - Route table and network ACL associations
  - Public/private subnet designation

#### Security Groups (`aws:vpc:security-group`)
- **Description**: VPC security groups
- **Extracted Data**:
  - Inbound and outbound rules
  - Referenced security groups

### Container Services

#### ECS Clusters (`aws:ecs:cluster`)
- **Description**: ECS container clusters
- **Extracted Data**:
  - Cluster configuration and capacity providers
  - Running tasks and services count
  - Networking and logging settings

#### ECS Services (`aws:ecs:service`)
- **Description**: ECS services
- **Extracted Data**:
  - Task definition and desired count
  - Load balancer configuration
  - Network configuration and security groups

#### EKS Clusters (`aws:eks:cluster`)
- **Description**: Elastic Kubernetes Service clusters
- **Extracted Data**:
  - Kubernetes version and platform version
  - VPC and subnet configuration
  - Security groups and IAM roles
  - Logging and monitoring settings

### Load Balancing

#### ELB Application Load Balancers (`aws:elb:application-load-balancer`)
- **Description**: ALB configurations
- **Extracted Data**:
  - Listeners and target groups
  - Security policies and SSL settings
  - Access logs and deletion protection

#### ELB Network Load Balancers (`aws:elb:network-load-balancer`)
- **Description**: NLB configurations
- **Extracted Data**:
  - Listeners and target groups
  - Cross-zone load balancing
  - Elastic IPs and subnet mappings

### Content Delivery

#### CloudFront Distributions (`aws:cloudfront:distribution`)
- **Description**: CDN distributions
- **Extracted Data**:
  - Origins and behaviors
  - SSL certificates and custom domains
  - Geographic restrictions and caching policies

### API Management

#### API Gateway REST APIs (`aws:apigateway:rest-api`)
- **Description**: API Gateway configurations
- **Extracted Data**:
  - API endpoints and methods
  - Authorizers and API keys
  - Stages and deployments
  - Usage plans and throttling

### Key Management

#### KMS Keys (`aws:kms:key`)
- **Description**: KMS encryption keys
- **Extracted Data**:
  - Key specifications and usage
  - Key policies and grants
  - Rotation settings and aliases

### App Runner

#### App Runner Services (`aws:apprunner:service`)
- **Description**: App Runner applications
- **Extracted Data**:
  - Source configuration and runtime
  - Network settings and custom domains
  - Health checks and scaling configuration

## Microsoft Azure

### Compute Services

#### Virtual Machines (`azure:compute:virtual-machine`)
- **Description**: Azure VMs and their configurations
- **Extracted Data**:
  - VM size and OS disk configuration
  - Network interfaces and security groups
  - Power state and provisioning status
  - Data disks and availability sets
  - Tags and metadata

#### VM Scale Sets (`azure:compute:vmss`)
- **Description**: Virtual machine scale sets
- **Extracted Data**:
  - SKU and capacity configuration
  - Upgrade policies and scaling settings
  - Network and load balancer configuration

### Storage Services

#### Storage Accounts (`azure:storage:account`)
- **Description**: Azure storage account configurations
- **Extracted Data**:
  - Account kind and SKU
  - Access tier and replication settings
  - Encryption configuration
  - Network rules and firewall settings
  - Blob service properties and CORS

### Networking Services

#### Network Security Groups (`azure:network:nsg`)
- **Description**: NSG rules and configurations
- **Extracted Data**:
  - Security rules (priorities, directions, actions)
  - Source/destination configurations
  - Associated subnets and NICs

#### Virtual Networks (`azure:network:vnet`)
- **Description**: Virtual network configurations
- **Extracted Data**:
  - Address spaces and subnets
  - DNS servers and DDoS protection
  - Peerings and service endpoints

#### Load Balancers (`azure:network:load-balancer`)
- **Description**: Azure load balancer configurations
- **Extracted Data**:
  - Frontend and backend configurations
  - Load balancing rules and probes
  - Inbound NAT rules

### Web Services

#### App Service Plans (`azure:web:app-service-plan`)
- **Description**: App service hosting plans
- **Extracted Data**:
  - SKU and capacity settings
  - Worker size and instance count
  - Geographic location and resource group

#### Web Apps (`azure:web:web-app`)
- **Description**: Azure web applications
- **Extracted Data**:
  - Runtime stack and configuration
  - App settings and connection strings
  - Custom domains and SSL certificates
  - Authentication and authorization

#### Function Apps (`azure:web:function-app`)
- **Description**: Azure Functions applications
- **Extracted Data**:
  - Runtime and version settings
  - Function configurations and bindings
  - App settings and environment variables

### Database Services

#### SQL Servers (`azure:sql:sql-server`)
- **Description**: Azure SQL server instances
- **Extracted Data**:
  - Server configuration and administrator
  - Firewall rules and virtual network rules
  - Security settings and audit policies

#### SQL Databases (`azure:sql:sql-database`)
- **Description**: Azure SQL databases
- **Extracted Data**:
  - Database configuration and SKU
  - Collation and compatibility level
  - Backup and geo-redundancy settings

### Container Services

#### AKS Clusters (`azure:containerservice:aks-cluster`)
- **Description**: Azure Kubernetes Service clusters
- **Extracted Data**:
  - Kubernetes version and node pools
  - Network configuration and add-ons
  - RBAC and security settings
  - Monitoring and logging configuration

### Security Services

#### Key Vaults (`azure:keyvault:key-vault`)
- **Description**: Azure Key Vault configurations
- **Extracted Data**:
  - Vault properties and access policies
  - Network ACLs and firewall rules
  - SKU and soft delete settings

### Identity & Access Management

#### Role Definitions (`azure:authorization:role-definition`)
- **Description**: Custom and built-in RBAC roles
- **Extracted Data**:
  - Role permissions and assignable scopes
  - Role type (built-in vs custom)

#### Role Assignments (`azure:authorization:role-assignment`)
- **Description**: RBAC role assignments
- **Extracted Data**:
  - Principal information and role definition
  - Assignment scope and conditions

## Google Cloud Platform (GCP)

### Compute Services

#### Compute Instances (`gcp:compute:instance`)
- **Description**: GCP VM instances
- **Extracted Data**:
  - Machine type and zone
  - Network interfaces and access configs
  - Disks (boot and additional)
  - Service accounts and scopes
  - Metadata and labels
  - Status and creation timestamp

#### Instance Groups (`gcp:compute:instance-group`)
- **Description**: Managed instance groups
- **Extracted Data**:
  - Instance template and target size
  - Auto-healing policies
  - Named ports and current actions

### Storage Services

#### Storage Buckets (`gcp:storage:bucket`)
- **Description**: Cloud Storage bucket configurations
- **Extracted Data**:
  - Location and storage class
  - Encryption settings (CMEK)
  - Lifecycle rules and retention policies
  - CORS configuration and website settings
  - IAM policies and public access prevention

### Identity & Access Management

#### Service Accounts (`gcp:iam:service-account`)
- **Description**: GCP service accounts
- **Extracted Data**:
  - Email and unique ID
  - Display name and description
  - OAuth2 client ID
  - Project membership

#### IAM Policies (`gcp:iam:iam-policy`)
- **Description**: Project-level IAM policies
- **Extracted Data**:
  - Bindings (role to members mapping)
  - Audit configs
  - Version and etag

#### Roles (`gcp:iam:role`)
- **Description**: Custom IAM roles
- **Extracted Data**:
  - Role name and title
  - Permissions list
  - Stage (ALPHA, BETA, GA, DISABLED)
  - Description

### Kubernetes Services

#### GKE Clusters (`gcp:kubernetes:cluster`)
- **Description**: Google Kubernetes Engine clusters
- **Extracted Data**:
  - Cluster configuration and status
  - Node pool configurations
  - Master and node versions
  - Network policy and add-ons
  - Authentication and authorization settings
  - Monitoring and logging configuration

#### Node Pools (`gcp:kubernetes:node-pool`)
- **Description**: GKE node pools
- **Extracted Data**:
  - Machine type and disk configuration
  - Auto-scaling settings
  - Management settings (auto-repair, auto-upgrade)
  - Network configuration
  - Node taints and labels

### Networking Services

#### VPC Networks (`gcp:networking:network`)
- **Description**: Virtual Private Cloud networks
- **Extracted Data**:
  - Network mode (auto, custom, legacy)
  - Routing configuration
  - Peerings
  - Subnetworks

#### Subnets (`gcp:networking:subnetwork`)
- **Description**: VPC subnetworks
- **Extracted Data**:
  - IP CIDR range
  - Region
  - Private Google access settings
  - Flow logs configuration

#### Firewall Rules (`gcp:networking:firewall`)
- **Description**: VPC firewall rules
- **Extracted Data**:
  - Priority and direction
  - Allowed/denied protocols and ports
  - Source/destination ranges
  - Target tags and service accounts

#### Load Balancers (`gcp:networking:backend-service`)
- **Description**: Load balancer configurations
- **Extracted Data**:
  - Backend services and health checks
  - URL maps and target proxies
  - Forwarding rules
  - Protocol and port settings

## Resource Coverage Summary

| Category | AWS | Azure | GCP | Total |
|----------|-----|-------|-----|-------|
| **Compute** | 2 (EC2, ECS) | 2 (VM, VMSS) | 2 (Compute, Instance Groups) | 6 |
| **Storage** | 1 (S3) | 1 (Storage) | 1 (Storage) | 3 |
| **Database** | 2 (RDS, Aurora) | 2 (SQL Server, DB) | 0 | 4 |
| **Networking** | 4 (VPC, ELB, CloudFront, API GW) | 3 (NSG, VNet, LB) | 4 (VPC, Firewall, LB, Subnets) | 11 |
| **Serverless** | 2 (Lambda, App Runner) | 2 (Web Apps, Functions) | 0 | 4 |
| **Identity** | 3 (IAM Users/Roles/Policies) | 2 (Role Defs/Assignments) | 3 (Service Accounts, Policies, Roles) | 8 |
| **Containers** | 2 (ECS, EKS) | 1 (AKS) | 1 (GKE) | 4 |
| **Security** | 1 (KMS) | 1 (Key Vault) | 0 | 2 |
| **Total Services** | 13 | 8 | 5 | 26 |
| **Total Resources** | 20+ | 20+ | 10+ | 50+ |

## Configuration Options

### Global Extractor Settings

```yaml
# config/extractors.yaml
global:
  max_concurrent_extractors: 5
  batch_size: 50
  batch_delay_seconds: 0.5
  enable_progress_tracking: true
  extraction_timeout_seconds: 300
```

### Provider-Specific Settings

Each provider has service-specific configuration options for controlling extraction behavior, parallelization, and filtering.

## Performance Considerations

### Parallel Extraction
- **AWS**: Uses boto3's built-in pagination and parallel processing
- **Azure**: ThreadPoolExecutor for concurrent API calls
- **GCP**: ThreadPoolExecutor with zone-level parallelization

### Rate Limiting
- **AWS**: Service-specific limits (EC2: 100 req/sec, S3: 5500 req/sec)
- **Azure**: Subscription-level limits (varies by service)
- **GCP**: Project-level quotas (Compute: 1000 req/min, Storage: 1000 req/sec)

### Memory Usage
- Large resource lists are processed in batches
- Raw API responses are included but can be filtered
- Configurable worker counts prevent resource exhaustion

## Filtering and Selection

### By Region
```json
{
  "services": ["ec2", "s3"],
  "regions": ["us-east-1", "us-west-2"]
}
```

### By Service
```json
{
  "services": ["compute", "storage"],
  "provider": "azure"
}
```

### By Resource Type
```json
{
  "services": ["ec2:instance", "s3:bucket"]
}
```

## Future Resource Support

### Planned Additions

#### AWS
- **Organizations**: Accounts and organizational units
- **Config**: Configuration items and rules
- **CloudTrail**: Audit trails and events
- **GuardDuty**: Security findings
- **SecurityHub**: Security findings aggregation

#### Azure
- **Resource Groups**: Resource organization
- **Policy**: Azure Policy definitions and assignments
- **Monitor**: Alerts and diagnostic settings
- **Security Center**: Security recommendations

#### GCP
- **Networking**: VPC networks, firewalls, load balancers
- **Kubernetes**: GKE clusters and workloads
- **Databases**: Cloud SQL, Cloud Spanner
- **Serverless**: Cloud Functions, Cloud Run
- **Security**: IAM, KMS, Security Command Center

## Custom Resource Types

The scanner is designed to be extensible. To add support for new resource types:

1. Create extractor class inheriting from `BaseExtractor`
2. Implement `get_metadata()`, `extract()`, and `transform()` methods
3. Register in the provider's registry
4. Add configuration options
5. Update documentation

See the [Development Guide](/csp-scanner/development.html) for detailed instructions.

## Data Quality and Validation

All extracted resources include:
- **Schema validation** against expected structure
- **Required field checking** (resource_id, cloud_provider, etc.)
- **Type validation** for configuration fields
- **Error handling** for malformed API responses
- **Logging** of extraction failures and warnings

## Compliance and Security Focus

Resources are extracted with security and compliance in mind:
- **Access controls** and permissions
- **Encryption settings** and key management
- **Network security** configurations
- **Public exposure** assessments
- **Compliance metadata** and tags

This enables downstream policy scanners to perform comprehensive security analysis across all supported cloud providers.