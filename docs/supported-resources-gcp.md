---
layout: default
title: GCP Supported Resources
parent: Supported Resources
nav_order: 3
has_children: false
---

# GCP Supported Resources

This document provides a comprehensive reference for all Google Cloud Platform (GCP) resources supported by the Cloud Artifact Extractor.

**Total Services**: 29 extractors covering 100+ resource types

## Service Extractors

### Quick Service List

<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; font-family: monospace;">
  <a href="#cloud-armor-armor">armor</a>
  <a href="#bigquery-bigquery">bigquery</a>
  <a href="#cloud-bigtable-bigtable">bigtable</a>
  <a href="#cloud-billing-billing">billing</a>
  <a href="#cloud-build-cloudbuild">cloudbuild</a>
  <a href="#cloud-run-cloudrun">cloudrun</a>
  <a href="#compute-engine-compute">compute</a>
  <a href="#dataflow-dataflow">dataflow</a>
  <a href="#dataproc-dataproc">dataproc</a>
  <a href="#cloud-dns-dns">dns</a>
  <a href="#filestore-filestore">filestore</a>
  <a href="#cloud-firestore-firestore">firestore</a>
  <a href="#cloud-functions-functions">functions</a>
  <a href="#identity-and-access-management-iam">iam</a>
  <a href="#identity-aware-proxy-iap">iap</a>
  <a href="#cloud-interconnect-interconnect">interconnect</a>
  <a href="#google-kubernetes-engine-kubernetes">kubernetes</a>
  <a href="#load-balancer-loadbalancer">loadbalancer</a>
  <a href="#cloud-logging-logging">logging</a>
  <a href="#memorystore-memorystore">memorystore</a>
  <a href="#cloud-monitoring-monitoring">monitoring</a>
  <a href="#vpc-networking-networking">networking</a>
  <a href="#cloud-pubsub-pubsub">pubsub</a>
  <a href="#resource-manager-resource_manager">resource_manager</a>
  <a href="#cloud-scheduler-scheduler">scheduler</a>
  <a href="#cloud-spanner-spanner">spanner</a>
  <a href="#cloud-storage-storage">storage</a>
  <a href="#cloud-tasks-tasks">tasks</a>
</div>

---

## Compute & Serverless Services

### Compute Engine (`compute`)
{: #compute-engine-compute}

Extracts Google Compute Engine virtual machine instances and related compute resources.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:compute:instance` | VM instances | Machine type, zone, network, disks, metadata |
| `gcp:compute:instance-group` | Managed instance groups | Template, target size, auto-healing policies |
| `gcp:compute:instance-template` | Instance templates | Configuration specifications for VM creation |
| `gcp:compute:disk` | Persistent disks | Size, type, encryption, attached instances |
| `gcp:compute:image` | Custom machine images | Source, family, licenses, encryption |
| `gcp:compute:snapshot` | Disk snapshots | Source disk, creation time, storage location |

**Common Use Cases:**
- Inventory all VM instances across projects and regions
- Track machine types and resource utilization
- Audit disk encryption and backup configurations
- Monitor instance template compliance

**Example Extraction:**
```bash
curl -X POST "http://localhost:8000/extraction/extract?services=compute&provider=gcp"
```

---

### Google Kubernetes Engine (`kubernetes`)
{: #google-kubernetes-engine-kubernetes}

Extracts GKE cluster configurations and node pool settings.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:kubernetes:cluster` | GKE clusters | Version, network, authentication, add-ons |
| `gcp:kubernetes:node-pool` | Node pools | Machine type, auto-scaling, management settings |

**Extracted Configuration:**
- Cluster configuration and status
- Master and node Kubernetes versions
- Network policy and security settings
- Monitoring and logging configuration
- Workload identity and authentication
- Auto-scaling and auto-repair settings

**Common Use Cases:**
- Audit GKE cluster security configurations
- Track Kubernetes version compliance
- Monitor node pool auto-scaling settings
- Verify workload identity enablement

---

### Cloud Run (`cloudrun`)
{: #cloud-run-cloudrun}

Extracts serverless Cloud Run service configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:run:service` | Cloud Run services | Configuration, revisions, traffic splits |
| `gcp:run:revision` | Service revisions | Container image, resources, scaling |

**Extracted Configuration:**
- Service configurations and revisions
- Traffic splitting and rollout strategies
- Environment variables and secrets references
- Resource limits (CPU, memory)
- Concurrency and scaling settings
- IAM policies and invoker permissions

**Common Use Cases:**
- Audit Cloud Run security settings
- Track container image versions
- Monitor resource allocation
- Verify IAM invoker policies

---

### Cloud Functions (`functions`)
{: #cloud-functions-functions}

Extracts Cloud Functions configurations and triggers.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:functions:function` | Cloud Functions (Gen 1 & 2) | Runtime, trigger type, environment, timeout |

**Extracted Configuration:**
- Function runtime environment (Node.js, Python, Go, etc.)
- Trigger configurations (HTTP, Pub/Sub, Storage, etc.)
- Environment variables and secrets
- Execution settings (memory, timeout, concurrency)
- VPC connector and network settings
- Service account and IAM permissions

**Common Use Cases:**
- Inventory all deployed functions
- Audit function security configurations
- Track runtime versions for updates
- Monitor timeout and memory settings

---

### Cloud Build (`cloudbuild`)
{: #cloud-build-cloudbuild}

Extracts CI/CD build configurations and triggers.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:cloudbuild:build` | Build executions | Steps, status, artifacts, logs |
| `gcp:cloudbuild:trigger` | Build triggers | Repository, branch, build config |

**Extracted Configuration:**
- Build configurations and steps
- Trigger definitions (GitHub, Cloud Source Repositories)
- Substitution variables and secrets
- Build history and artifacts
- Service account permissions
- Build timeouts and machine types

**Common Use Cases:**
- Audit build pipeline security
- Track build trigger configurations
- Monitor build success rates
- Verify artifact storage settings

---

## Storage & Database Services

### Cloud Storage (`storage`)
{: #cloud-storage-storage}

Extracts Cloud Storage bucket configurations and access controls.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:storage:bucket` | Storage buckets | Location, storage class, encryption, lifecycle, IAM |

**Extracted Configuration:**
- Bucket location and storage class
- Encryption settings (CMEK, default encryption)
- Lifecycle management rules
- Retention policies and legal holds
- CORS and website configurations
- IAM policies and ACLs
- Public access prevention settings
- Uniform bucket-level access

**Common Use Cases:**
- Identify publicly accessible buckets
- Audit encryption configurations
- Verify lifecycle and retention policies
- Monitor bucket access controls

**Security Checks:**
- ✅ Uniform bucket-level access enabled
- ✅ Public access prevention enforced
- ✅ Customer-managed encryption keys (CMEK)
- ✅ Lifecycle rules for cost optimization

---

### Cloud Spanner (`spanner`)
{: #cloud-spanner-spanner}

Extracts Cloud Spanner instance and database configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:spanner:instance` | Spanner instances | Node count, configuration, location |
| `gcp:spanner:database` | Spanner databases | Schema, DDL, encryption, backups |

**Extracted Configuration:**
- Instance configurations (regional, multi-regional)
- Node count and processing units
- Database schemas and DDL statements
- Backup schedules and retention policies
- Encryption settings (CMEK)
- IAM policies

---

### Cloud Firestore (`firestore`)
{: #cloud-firestore-firestore}

Extracts Firestore database and collection configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:firestore:database` | Firestore databases | Mode (Native, Datastore), location, settings |
| `gcp:firestore:collection` | Document collections | Indexes, structure |

**Extracted Configuration:**
- Database configurations and locations
- Collection structures and composite indexes
- Security rules
- IAM policies
- App Engine integration settings

---

### Cloud Bigtable (`bigtable`)
{: #cloud-bigtable-bigtable}

Extracts Bigtable instance, cluster, and table configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:bigtable:instance` | Bigtable instances | Type, clusters, app profiles |
| `gcp:bigtable:cluster` | Bigtable clusters | Zone, nodes, storage type |
| `gcp:bigtable:table` | Bigtable tables | Column families, replication |

**Extracted Configuration:**
- Instance types (production, development)
- Cluster configurations and node counts
- Storage types (SSD, HDD)
- Replication settings
- App profiles and routing policies
- Table schemas and column families

---

### Memorystore (`memorystore`)
{: #memorystore-memorystore}

Extracts Redis and Memcached instance configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:memorystore:instance` | Redis/Memcached instances | Tier, capacity, network, auth |
| `gcp:memorystore:backup` | Redis backups | Schedule, retention |

**Extracted Configuration:**
- Instance tiers (Basic, Standard)
- Memory size and capacity
- Network settings and authorized networks
- Authentication settings (AUTH string)
- Maintenance windows
- Backup configurations (Standard tier)

---

### Filestore (`filestore`)
{: #filestore-filestore}

Extracts managed NFS file system configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:filestore:instance` | Filestore instances | Tier, capacity, network, shares |
| `gcp:filestore:backup` | Filestore backups | Source, schedule, retention |

**Extracted Configuration:**
- Instance tiers (Basic, Enterprise)
- Capacity and performance characteristics
- Network configurations and access controls
- File share configurations
- Backup schedules and retention policies

---

## Networking Services

### VPC Networking (`networking`)
{: #vpc-networking-networking}

Extracts Virtual Private Cloud network configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:networking:network` | VPC networks | Mode (auto, custom), routing, peering |
| `gcp:networking:subnetwork` | Subnets | CIDR range, region, private access, flow logs |
| `gcp:networking:firewall` | Firewall rules | Priority, direction, protocols, ranges, targets |
| `gcp:networking:route` | Routes | Destination range, next hop, priority |
| `gcp:networking:router` | Cloud Routers | BGP configuration, interfaces |
| `gcp:networking:vpc-peering` | VPC peering | Peer network, routes exchange |

**Extracted Configuration:**
- Network mode (auto-created subnets vs custom)
- Routing configuration and policies
- VPC peering connections
- Private Google Access settings
- Flow logs configurations
- Firewall rule priorities and targets

**Common Use Cases:**
- Audit firewall rules for overly permissive access
- Verify private Google Access enablement
- Track VPC peering relationships
- Monitor flow logs configuration

**Security Checks:**
- ✅ Firewall rules follow least privilege
- ✅ Default deny-all rules in place
- ✅ Flow logs enabled for audit trails
- ✅ Private Google Access configured

---

### Load Balancer (`loadbalancer`)
{: #load-balancer-loadbalancer}

Extracts load balancer configurations and components.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:loadbalancer:urlmap` | URL maps | Routing rules, path matchers |
| `gcp:loadbalancer:forwardingrule` | Forwarding rules | IP address, port, target |
| `gcp:loadbalancer:targetproxy` | Target proxies | SSL certificates, URL map |
| `gcp:loadbalancer:backendservice` | Backend services | Backends, health checks, protocol |
| `gcp:loadbalancer:healthcheck` | Health checks | Check type, interval, timeout |

**Extracted Configuration:**
- URL maps and routing rules
- Forwarding rules and IP addresses
- SSL certificate configurations
- Backend service configurations
- Health check settings
- Session affinity and connection draining

---

### Cloud DNS (`dns`)
{: #cloud-dns-dns}

Extracts Cloud DNS managed zone and record set configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:dns:managedzone` | DNS managed zones | DNS name, visibility, DNSSEC |
| `gcp:dns:recordset` | DNS record sets | Type, TTL, values |

**Extracted Configuration:**
- Managed zone configurations
- DNS name and name servers
- DNSSEC configurations
- DNS record sets (A, AAAA, CNAME, MX, TXT, etc.)
- Private zone settings
- Routing policies (geo, weighted, failover)

---

### Cloud Interconnect (`interconnect`)
{: #cloud-interconnect-interconnect}

Extracts hybrid connectivity configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:interconnect:attachment` | VLAN attachments | Interconnect, VLAN, router |
| `gcp:interconnect:location` | Interconnect locations | Available facilities |

**Extracted Configuration:**
- VLAN attachment configurations
- Interconnect locations and availability
- Bandwidth allocations
- Cloud Router associations
- BGP session configurations

---

## Big Data & Analytics Services

### BigQuery (`bigquery`)
{: #bigquery-bigquery}

Extracts data warehouse datasets and tables.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:bigquery:dataset` | BigQuery datasets | Location, access controls, encryption |
| `gcp:bigquery:table` | BigQuery tables | Schema, partitioning, clustering, encryption |

**Extracted Configuration:**
- Dataset metadata and locations
- Dataset access controls and IAM
- Table schemas and descriptions
- Partitioning and clustering configurations
- Encryption settings (CMEK)
- Table expiration settings
- Authorized views and routines

**Common Use Cases:**
- Audit dataset access controls
- Verify encryption configurations
- Track table partitioning strategies
- Monitor dataset locations for compliance

---

### Dataproc (`dataproc`)
{: #dataproc-dataproc}

Extracts Hadoop/Spark cluster configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:dataproc:cluster` | Dataproc clusters | Configuration, nodes, software |
| `gcp:dataproc:job` | Dataproc jobs | Type, status, configuration |
| `gcp:dataproc:workflowtemplate` | Workflow templates | Jobs, DAG, parameters |

**Extracted Configuration:**
- Cluster configurations (master, worker, preemptible nodes)
- Software configurations (Hadoop, Spark versions)
- Job definitions and execution history
- Workflow templates and dependencies
- Auto-scaling policies
- Network and security configurations

---

### Dataflow (`dataflow`)
{: #dataflow-dataflow}

Extracts streaming and batch data processing jobs.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:dataflow:job` | Dataflow jobs | Type, state, pipeline, environment |

**Extracted Configuration:**
- Job configurations and states
- Pipeline definitions and transforms
- Execution environments and worker pools
- Streaming vs batch configurations
- Auto-scaling settings
- Service account permissions

---

### Cloud Pub/Sub (`pubsub`)
{: #cloud-pubsub-pubsub}

Extracts messaging service topics and subscriptions.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:pubsub:topic` | Pub/Sub topics | Message retention, schemas, encryption |
| `gcp:pubsub:subscription` | Subscriptions | Delivery type, filters, retry policy |

**Extracted Configuration:**
- Topic configurations and schemas
- Message retention duration
- Encryption settings (CMEK)
- Subscription settings (push/pull)
- Message filters
- Dead letter topic configurations
- Retry policies and acknowledgment deadlines

**Common Use Cases:**
- Audit message retention policies
- Verify encryption configurations
- Track dead letter queue settings
- Monitor subscription filters

---

## Security & Identity Services

### Identity and Access Management (`iam`)
{: #identity-and-access-management-iam}

Extracts IAM configurations, service accounts, and policies.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:iam:service-account` | Service accounts | Email, display name, OAuth2 client ID |
| `gcp:iam:iam-policy` | IAM policies | Bindings (role to members), audit configs |
| `gcp:iam:role` | Custom IAM roles | Permissions, stage (ALPHA, BETA, GA) |
| `gcp:iam:key` | Service account keys | Key type, algorithm, expiration |

**Extracted Configuration:**
- Service account metadata and OAuth2 settings
- Project, folder, and organization IAM policies
- Role bindings (members, roles, conditions)
- Custom role definitions and permissions
- Service account key metadata
- Audit configuration settings

**Common Use Cases:**
- Audit service account permissions
- Identify overly permissive IAM bindings
- Track custom role definitions
- Monitor service account key age and rotation

**Security Checks:**
- ✅ Least privilege IAM bindings
- ✅ Service account keys rotated regularly
- ✅ No user-managed keys for service accounts
- ✅ Conditional IAM policies where appropriate

---

### Cloud Armor (`armor`)
{: #cloud-armor-armor}

Extracts web application firewall and DDoS protection policies.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:armor:securitypolicy` | Security policies | Rules, default action, adaptive protection |
| `gcp:armor:securityrule` | Security rules | Priority, action, match conditions |

**Extracted Configuration:**
- Security policy configurations
- Rule definitions and priorities
- Match conditions (IP, geo, headers)
- Actions (allow, deny, rate-based ban)
- Adaptive protection settings
- Preconfigured WAF rules

**Common Use Cases:**
- Audit web application firewall rules
- Verify DDoS protection settings
- Track rule priorities and actions
- Monitor adaptive protection enablement

---

### Identity-Aware Proxy (`iap`)
{: #identity-aware-proxy-iap}

Extracts IAP configurations for secure application access.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:iap:web` | Web IAP configurations | OAuth settings, access policies |
| `gcp:iap:appengine` | App Engine IAP | Application-level settings |
| `gcp:iap:compute` | Compute Engine IAP | SSH/RDP tunnel settings |

**Extracted Configuration:**
- IAP-secured resource configurations
- OAuth client settings
- Access policies and member groups
- App Engine and Compute Engine IAP settings
- TCP forwarding configurations

---

## Management & Monitoring Services

### Cloud Logging (`logging`)
{: #cloud-logging-logging}

Extracts log routing, aggregation, and retention configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:logging:sink` | Log sinks | Destination, filter, inclusion |
| `gcp:logging:metric` | Log-based metrics | Filter, metric descriptor |
| `gcp:logging:exclusion` | Log exclusions | Filter, description |

**Extracted Configuration:**
- Log sink destinations (Cloud Storage, BigQuery, Pub/Sub)
- Sink filters and log selection
- Log-based metric definitions
- Log exclusion rules
- Retention policies
- Access control settings

**Common Use Cases:**
- Audit log export configurations
- Verify log retention policies
- Track log-based metrics
- Monitor exclusion rules for compliance

---

### Cloud Monitoring (`monitoring`)
{: #cloud-monitoring-monitoring}

Extracts alerting, notification, and uptime check configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:monitoring:alertpolicy` | Alert policies | Conditions, thresholds, notifications |
| `gcp:monitoring:notificationchannel` | Notification channels | Type (email, SMS, webhook), settings |
| `gcp:monitoring:uptimecheckconfig` | Uptime checks | Target, check type, frequency |

**Extracted Configuration:**
- Alert policy conditions and thresholds
- Notification channel configurations
- Uptime check targets and settings
- Metric filters and aggregations
- Alert documentation and display names

**Common Use Cases:**
- Inventory all monitoring configurations
- Audit alert policy coverage
- Verify notification channels
- Track uptime check configurations

---

### Resource Manager (`resource_manager`)
{: #resource-manager-resource_manager}

Extracts organizational hierarchy and resource metadata.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:resourcemanager:organization` | Organizations | Display name, directory customer ID |
| `gcp:resourcemanager:folder` | Folders | Display name, parent |
| `gcp:resourcemanager:project` | Projects | Name, ID, number, labels, parent |
| `gcp:resourcemanager:project-iam-policy` | Project IAM | Role bindings at project level |
| `gcp:resourcemanager:folder-iam-policy` | Folder IAM | Role bindings at folder level |
| `gcp:resourcemanager:org-iam-policy` | Organization IAM | Role bindings at org level |

**Extracted Configuration:**
- Organization, folder, and project hierarchy
- Resource labels and tags
- IAM policies at all hierarchy levels
- Project metadata (creation time, state)
- Parent-child relationships

**Common Use Cases:**
- Map organizational resource hierarchy
- Audit IAM policies across hierarchy
- Track resource labels for cost allocation
- Verify organizational policies

---

### Cloud Billing (`billing`)
{: #cloud-billing-billing}

Extracts billing account and budget configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:billing:account` | Billing accounts | Name, currency, master account |
| `gcp:billing:budget` | Budgets | Amount, threshold rules, notifications |
| `gcp:billing:project` | Project billing | Linked billing account |

**Extracted Configuration:**
- Billing account information
- Budget definitions and thresholds
- Budget alert threshold rules
- Project billing associations
- Billing account IAM policies

**Common Use Cases:**
- Track billing account associations
- Monitor budget configurations
- Verify budget alerts are configured
- Audit billing account access

---

## Integration & Orchestration Services

### Cloud Tasks (`tasks`)
{: #cloud-tasks-tasks}

Extracts task queue configurations and task definitions.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:tasks:queue` | Task queues | Rate limits, retry config, routing |
| `gcp:tasks:task` | Tasks | Schedule, payload, HTTP/App Engine target |

**Extracted Configuration:**
- Queue configurations and routing
- Rate limits and concurrency settings
- Task retry policies
- HTTP and App Engine target configurations
- Task schedules and payloads

---

### Cloud Scheduler (`scheduler`)
{: #cloud-scheduler-scheduler}

Extracts scheduled job configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `gcp:scheduler:job` | Scheduler jobs | Schedule (cron), target, retry config |

**Extracted Configuration:**
- Job schedules (cron expressions)
- Target configurations (HTTP, Pub/Sub, App Engine)
- Authentication settings
- Retry policies and configurations
- Execution history and status

**Common Use Cases:**
- Inventory all scheduled jobs
- Audit job authentication settings
- Verify retry configurations
- Track job execution patterns

---

## Extraction Examples

### Extract All GCP Resources

```bash
curl -X POST "http://localhost:8000/extraction/extract?provider=gcp"
```

### Extract Specific Services

```bash
# Compute and storage only
curl -X POST "http://localhost:8000/extraction/extract?provider=gcp&services=compute,storage"

# Security-related services
curl -X POST "http://localhost:8000/extraction/extract?provider=gcp&services=iam,armor,iap"

# Networking services
curl -X POST "http://localhost:8000/extraction/extract?provider=gcp&services=networking,dns,loadbalancer"
```

### Extract from Specific Projects

```bash
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gcp",
    "projects": ["project-1", "project-2"],
    "services": ["compute", "storage", "iam"]
  }'
```

---

## Authentication Requirements

### Service Account Permissions

To extract resources, the service account needs appropriate viewer/reader roles:

#### Minimum Required Roles:
```bash
# Compute resources
roles/compute.viewer

# Storage resources
roles/storage.objectViewer
roles/browser  # For listing buckets

# IAM resources
roles/iam.securityReviewer
roles/iam.roleViewer

# Kubernetes resources
roles/container.viewer

# BigQuery resources
roles/bigquery.metadataViewer

# Organization-level resources
roles/resourcemanager.organizationViewer
roles/resourcemanager.folderViewer

# Billing (optional)
roles/billing.viewer
```

#### Comprehensive Read-Only Access:
```bash
# Organization level - covers most services
roles/viewer

# Security-specific
roles/iam.securityReviewer
roles/securitycenter.adminViewer
```

### Setup Service Account

```bash
# Create service account
gcloud iam service-accounts create csp-scanner \
    --description="Cloud Artifact Extractor" \
    --display-name="CSP Scanner"

# Grant project-level permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/viewer"

# Grant IAM security reviewer
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.securityReviewer"

# Create and download key
gcloud iam service-accounts keys create csp-scanner-key.json \
    --iam-account=csp-scanner@PROJECT_ID.iam.gserviceaccount.com
```

---

## Common Extraction Patterns

### Security Audit Extraction
```bash
# Extract security-relevant resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gcp",
    "services": [
      "iam",
      "armor", 
      "iap",
      "storage",
      "networking",
      "compute"
    ]
  }'
```

### Cost Optimization Extraction
```bash
# Extract cost-related resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gcp",
    "services": [
      "compute",
      "storage",
      "bigquery",
      "dataproc",
      "billing"
    ]
  }'
```

### Compliance Audit Extraction
```bash
# Extract compliance-relevant resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gcp",
    "services": [
      "iam",
      "logging",
      "monitoring",
      "resource_manager",
      "storage",
      "networking"
    ]
  }'
```

---

## Troubleshooting

### Common Issues

#### Permission Denied Errors
```
Error: Permission denied on resource
```
**Solution**: Verify service account has appropriate viewer roles. Check with:
```bash
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:csp-scanner@PROJECT_ID.iam.gserviceaccount.com"
```

#### API Not Enabled
```
Error: API [service.googleapis.com] not enabled
```
**Solution**: Enable the required API:
```bash
gcloud services enable compute.googleapis.com
gcloud services enable storage-api.googleapis.com
# etc.
```

#### Invalid Credentials
```
Error: Could not load credentials
```
**Solution**: Verify `GCP_CREDENTIALS_PATH` points to valid service account key JSON file.

### Verification Commands

```bash
# Test authentication
gcloud auth activate-service-account --key-file=/path/to/key.json

# List accessible projects
gcloud projects list

# Verify API access
gcloud compute instances list --project=PROJECT_ID
gcloud storage buckets list --project=PROJECT_ID
```

---

## See Also

- [GCP Setup Guide]({{ '/cloud-providers-gcp.html' | relative_url }}) - Detailed authentication and configuration
- [Configuration Guide]({{ '/configuration.html' | relative_url }}) - Multi-project and region settings
- [API Reference]({{ '/api-reference.html' | relative_url }}) - Extraction API endpoints
- [Metadata Structure]({{ '/metadata-structure.html' | relative_url }}) - Output format specification

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
