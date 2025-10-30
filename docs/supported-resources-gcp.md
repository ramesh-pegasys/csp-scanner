---
layout: default
title: GCP Supported Resources
parent: Supported Resources
nav_order: 3
has_children: false
---

# GCP Supported Resources

The following GCP resource extractors are supported:

- compute
- iam
- kubernetes
- networking
- storage

## Detailed Resource Information

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
