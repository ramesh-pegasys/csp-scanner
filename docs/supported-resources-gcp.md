---
layout: default
title: GCP Supported Resources
parent: Supported Resources
nav_order: 3
has_children: false
---

# GCP Supported Resources

The following GCP resource extractors are supported:

- armor
- bigquery
- bigtable
- billing
- cloudbuild
- cloudrun
- compute
- dataflow
- dataproc
- dns
- filestore
- firestore
- functions
- iam
- iap
- interconnect
- kubernetes
- loadbalancer
- logging
- memorystore
- monitoring
- networking
- pubsub
- resource_manager
- scheduler
- spanner
- storage
- tasks

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

## Big Data & Analytics Services

### BigQuery (`gcp:bigquery:dataset`, `gcp:bigquery:table`)
- **Description**: BigQuery datasets and tables
- **Extracted Data**:
  - Dataset metadata and access controls
  - Table schemas and partitioning
  - Dataset locations and encryption settings

### Bigtable (`gcp:bigtable:instance`, `gcp:bigtable:cluster`, `gcp:bigtable:table`)
- **Description**: Cloud Bigtable instances, clusters, and tables
- **Extracted Data**:
  - Instance configurations and clusters
  - Table schemas and column families
  - Storage types and replication settings

### Dataproc (`gcp:dataproc:cluster`, `gcp:dataproc:job`, `gcp:dataproc:workflowtemplate`)
- **Description**: Dataproc clusters, jobs, and workflow templates
- **Extracted Data**:
  - Cluster configurations and node pools
  - Job definitions and execution history
  - Workflow templates and dependencies

### Dataflow (`gcp:dataflow:job`)
- **Description**: Dataflow streaming and batch jobs
- **Extracted Data**:
  - Job configurations and pipeline definitions
  - Execution environments and worker pools
  - Job states and performance metrics

### Spanner (`gcp:spanner:instance`, `gcp:spanner:database`)
- **Description**: Spanner instances and databases
- **Extracted Data**:
  - Instance configurations and node counts
  - Database schemas and DDL statements
  - Backup schedules and retention policies

## Storage & Database Services

### Firestore (`gcp:firestore:database`, `gcp:firestore:collection`)
- **Description**: Firestore databases and collections
- **Extracted Data**:
  - Database configurations and locations
  - Collection structures and indexes
  - Security rules and IAM policies

### Memorystore (`gcp:memorystore:instance`, `gcp:memorystore:backup`)
- **Description**: Memorystore Redis instances and backups
- **Extracted Data**:
  - Instance configurations and tiers
  - Network settings and maintenance windows
  - Backup schedules and retention

### Filestore (`gcp:filestore:instance`, `gcp:filestore:backup`)
- **Description**: Filestore NFS instances and backups
- **Extracted Data**:
  - Instance configurations and capacity
  - Network settings and access controls
  - Backup configurations and schedules

## Messaging & Integration Services

### Pub/Sub (`gcp:pubsub:topic`, `gcp:pubsub:subscription`)
- **Description**: Pub/Sub topics and subscriptions
- **Extracted Data**:
  - Topic configurations and schemas
  - Subscription settings and filters
  - Message retention and dead letter topics

### Cloud Tasks (`gcp:tasks:queue`, `gcp:tasks:task`)
- **Description**: Cloud Tasks queues and tasks
- **Extracted Data**:
  - Queue configurations and routing
  - Task definitions and schedules
  - Retry policies and rate limits

### Cloud Scheduler (`gcp:scheduler:job`)
- **Description**: Cloud Scheduler jobs
- **Extracted Data**:
  - Job schedules and targets
  - Authentication and retry settings
  - Execution history and status

## Compute & Serverless Services

### Cloud Run (`gcp:run:service`)
- **Description**: Cloud Run services
- **Extracted Data**:
  - Service configurations and revisions
  - Traffic splits and scaling settings
  - Environment variables and secrets

### Cloud Functions (`gcp:functions:function`)
- **Description**: Cloud Functions
- **Extracted Data**:
  - Function configurations and triggers
  - Runtime environments and dependencies
  - Execution settings and timeouts

### Cloud Build (`gcp:cloudbuild:build`, `gcp:cloudbuild:trigger`)
- **Description**: Cloud Build configurations and triggers
- **Extracted Data**:
  - Build configurations and steps
  - Trigger definitions and repositories
  - Build history and artifacts

## Security & Identity Services

### Cloud Armor (`gcp:armor:securitypolicy`, `gcp:armor:securityrule`)
- **Description**: Cloud Armor security policies and rules
- **Extracted Data**:
  - Security policy configurations
  - Rule definitions and priorities
  - Adaptive protection settings

### Identity-Aware Proxy (`gcp:iap:web`, `gcp:iap:appengine`, `gcp:iap:compute`)
- **Description**: IAP configurations for web, App Engine, and Compute Engine
- **Extracted Data**:
  - IAP settings and OAuth configurations
  - Access policies and user groups
  - Resource-level access controls

## Networking & Connectivity Services

### Cloud DNS (`gcp:dns:managedzone`, `gcp:dns:recordset`)
- **Description**: Cloud DNS managed zones and record sets
- **Extracted Data**:
  - Zone configurations and name servers
  - DNS records and TTL settings
  - Private zone configurations

### Cloud Interconnect (`gcp:interconnect:attachment`, `gcp:interconnect:location`)
- **Description**: Interconnect attachments and locations
- **Extracted Data**:
  - Attachment configurations and bandwidth
  - Interconnect locations and availability
  - VLAN configurations and routing

### Load Balancer (`gcp:loadbalancer:urlmap`, `gcp:loadbalancer:forwardingrule`, `gcp:loadbalancer:targetproxy`, `gcp:loadbalancer:backendservice`)
- **Description**: Load balancer components
- **Extracted Data**:
  - URL maps and routing rules
  - Forwarding rules and IP addresses
  - Target proxies and SSL certificates
  - Backend services and health checks

## Management & Monitoring Services

### Cloud Logging (`gcp:logging:sink`, `gcp:logging:metric`, `gcp:logging:exclusion`)
- **Description**: Cloud Logging sinks, metrics, and exclusions
- **Extracted Data**:
  - Log sink destinations and filters
  - Custom metrics and aggregations
  - Log exclusions and retention

### Cloud Monitoring (`gcp:monitoring:alertpolicy`, `gcp:monitoring:notificationchannel`, `gcp:monitoring:uptimecheckconfig`)
- **Description**: Cloud Monitoring alert policies, notification channels, and uptime checks
- **Extracted Data**:
  - Alert policy conditions and thresholds
  - Notification channel configurations
  - Uptime check targets and settings

## Resource Management Services

### Resource Manager (`gcp:resourcemanager:project`, `gcp:resourcemanager:folder`, `gcp:resourcemanager:organization`, `gcp:resourcemanager:project-iam-policy`, `gcp:resourcemanager:folder-iam-policy`, `gcp:resourcemanager:org-iam-policy`)
- **Description**: GCP resource hierarchy and IAM policies
- **Extracted Data**:
  - Project, folder, and organization metadata
  - IAM policies at all levels
  - Resource labels and tags

### Cloud Billing (`gcp:billing:account`, `gcp:billing:budget`, `gcp:billing:project`)
- **Description**: Cloud Billing accounts, budgets, and project billing configurations
- **Extracted Data**:
  - Billing account information
  - Budget definitions and thresholds
  - Project billing settings
