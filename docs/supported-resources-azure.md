---
layout: default
title: Azure Supported Resources
parent: Supported Resources
nav_order: 2
has_children: false
---

# Azure Supported Resources

This document provides a comprehensive reference for all Microsoft Azure resources supported by the Cloud Artifact Extractor.

**Total Services**: 8 extractors covering 20+ resource types

## Service Extractors

### Quick Service List

<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-family: monospace;">
  <a href="#authorization-authorization">authorization</a>
  <a href="#compute-compute">compute</a>
  <a href="#container-service-containerservice">containerservice</a>
  <a href="#key-vault-keyvault">keyvault</a>
  <a href="#networking-network">network</a>
  <a href="#sql-database-sql">sql</a>
  <a href="#storage-storage">storage</a>
  <a href="#web--app-services-web">web</a>
</div>

---

## Compute (`compute`)
{: #compute-compute}

Extracts Azure Virtual Machines and VM Scale Sets configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:compute:virtual-machine` | Virtual machines | VM size, OS, disks, network, power state, tags |
| `azure:compute:vmss` | VM Scale Sets | SKU, capacity, upgrade policy, scaling settings |
| `azure:compute:disk` | Managed disks | Disk size, type, encryption, attached VM |
| `azure:compute:availability-set` | Availability sets | Fault domains, update domains, VMs |
| `azure:compute:image` | Custom VM images | OS type, source, replication regions |

**Extracted Configuration:**

### Virtual Machines
- VM size and hardware configuration
- Operating system disk configuration
- Data disk attachments and settings
- Network interface associations
- Network security group assignments
- Power state and provisioning status
- Availability set membership
- Managed identity assignments
- Boot diagnostics settings
- Tags and custom metadata

### VM Scale Sets
- SKU and capacity configuration
- Instance count and scaling settings
- Upgrade policy (automatic, manual, rolling)
- Network and load balancer configuration
- Auto-scaling rules and thresholds
- Health probe settings
- OS and custom extension configurations

**Common Use Cases:**
- Inventory all VMs across subscriptions
- Audit VM sizes and costs
- Verify encryption configurations
- Track unattached managed disks
- Monitor VM scale set auto-scaling

**Security Checks:**
- ✅ Managed identity enabled for VMs
- ✅ OS disk encryption enabled
- ✅ NSGs properly configured
- ✅ Boot diagnostics enabled
- ✅ No VMs with public IPs (where not required)

**Example Extraction:**
```bash
curl -X POST "http://localhost:8000/extraction/extract?services=compute&provider=azure"
```

---

## Storage (`storage`)
{: #storage-storage}

Extracts Azure Storage Account configurations including Blob, File, Queue, and Table services.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:storage:account` | Storage accounts | Kind, SKU, replication, encryption, network rules |
| `azure:storage:blob-container` | Blob containers | Public access, encryption, metadata |
| `azure:storage:file-share` | File shares | Quota, protocol, access tier |
| `azure:storage:queue` | Storage queues | Metadata, message count |
| `azure:storage:table` | Storage tables | Metadata, access level |

**Extracted Configuration:**
- Account kind (StorageV2, BlobStorage, FileStorage, BlockBlobStorage)
- SKU tier (Standard, Premium) and replication type
- Access tier (Hot, Cool, Archive)
- Encryption settings (Microsoft-managed, customer-managed keys)
- Network rules and firewall configurations
- Virtual network service endpoints
- Blob service properties:
  - Soft delete settings
  - Versioning and change feed
  - CORS rules
  - Static website hosting
- File service properties and SMB settings
- Queue and table service configurations
- Shared access signature (SAS) policies
- Data Lake Gen2 hierarchical namespace

**Common Use Cases:**
- Identify publicly accessible storage accounts
- Audit encryption configurations
- Verify network access restrictions
- Track storage account costs by SKU
- Monitor blob soft delete settings

**Security Checks:**
- ✅ HTTPS-only traffic required
- ✅ Public blob access disabled
- ✅ Encryption at rest enabled
- ✅ Network rules configured (not open to all networks)
- ✅ Soft delete enabled for blobs
- ✅ Minimum TLS version set to 1.2
- ✅ Storage account key access limited

**Example Extraction:**
```bash
curl -X POST "http://localhost:8000/extraction/extract?services=storage&provider=azure"
```

---

## Networking (`network`)
{: #networking-network}

Extracts Azure networking resources including VNets, NSGs, load balancers, and application gateways.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:network:vnet` | Virtual networks | Address space, subnets, DNS, peering |
| `azure:network:subnet` | Subnets | Address prefix, NSG, route table, service endpoints |
| `azure:network:nsg` | Network security groups | Security rules, priorities, associated resources |
| `azure:network:nsg-rule` | NSG security rules | Priority, direction, action, protocol, ports |
| `azure:network:load-balancer` | Load balancers | SKU, frontend/backend config, rules, probes |
| `azure:network:application-gateway` | Application gateways | SKU, WAF config, backend pools, routing rules |
| `azure:network:public-ip` | Public IP addresses | Allocation method, SKU, DNS name, associated resource |
| `azure:network:network-interface` | Network interfaces | Private/public IPs, NSG, VM association |
| `azure:network:route-table` | Route tables | Routes, associated subnets |
| `azure:network:nat-gateway` | NAT gateways | Public IPs, idle timeout, associated subnets |

**Extracted Configuration:**

### Virtual Networks
- Address space and CIDR blocks
- Subnet configurations and delegations
- DNS server settings
- DDoS protection status
- VNet peering connections
- Service endpoints and private link

### Network Security Groups
- Security rule definitions
- Rule priorities and precedence
- Allowed/denied traffic flows
- Source/destination configurations
- Protocol and port specifications
- Associated subnets and NICs

### Load Balancers
- SKU (Basic, Standard)
- Frontend IP configurations
- Backend address pools
- Load balancing rules
- Health probes and intervals
- Inbound NAT rules
- Outbound rules

### Application Gateways
- SKU and capacity settings
- WAF configuration and rules
- Backend pools and targets
- HTTP settings and listeners
- Routing rules and path-based routing
- SSL certificates and policies
- Auto-scaling configuration

**Common Use Cases:**
- Audit NSG rules for overly permissive access
- Map VNet peering relationships
- Identify resources with public IPs
- Verify load balancer health probes
- Track application gateway WAF rules

**Security Checks:**
- ✅ NSG rules follow least privilege
- ✅ DDoS protection enabled on VNets
- ✅ Service endpoints configured for PaaS services
- ✅ No NSG rules allowing 0.0.0.0/0 on sensitive ports
- ✅ WAF enabled on application gateways
- ✅ Network watcher enabled for flow logs

---

## Web & App Services (`web`)
{: #web--app-services-web}

Extracts Azure App Service configurations including Web Apps, Function Apps, and App Service Plans.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:web:app-service-plan` | App Service plans | SKU, capacity, OS, worker size |
| `azure:web:web-app` | Web applications | Runtime stack, app settings, SSL, authentication |
| `azure:web:function-app` | Function apps | Runtime, version, app settings, bindings |
| `azure:web:app-service-certificate` | SSL certificates | Thumbprint, expiration, key vault secret |

**Extracted Configuration:**

### App Service Plans
- SKU tier and size (Free, Shared, Basic, Standard, Premium, Isolated)
- Operating system (Windows, Linux)
- Worker size and instance count
- Auto-scale settings
- Geographic location
- Reserved instance status
- Per-site scaling configuration

### Web Apps
- Runtime stack (Node.js, Python, .NET, Java, PHP)
- Runtime version
- App settings and connection strings
- Custom domains and SSL certificates
- Authentication and authorization configuration
- Deployment slots and settings
- Always On and HTTP/HTTPS settings
- CORS configuration
- Application Insights integration
- Managed identity assignments

### Function Apps
- Runtime environment (.NET, Node.js, Python, Java, PowerShell)
- Runtime version
- Function configurations and triggers
- App settings and environment variables
- Storage account connections
- Deployment method
- Scale settings and limits
- Durable functions configuration

**Common Use Cases:**
- Inventory all web applications and function apps
- Audit runtime versions for updates
- Verify HTTPS-only enforcement
- Track custom domain and SSL certificate expiration
- Monitor app service plan capacity

**Security Checks:**
- ✅ HTTPS-only traffic enforced
- ✅ Minimum TLS version set to 1.2
- ✅ Authentication enabled (where appropriate)
- ✅ Managed identity used for Azure resource access
- ✅ Remote debugging disabled
- ✅ FTP/FTPS access restricted or disabled
- ✅ Client certificates required (where appropriate)

---

## SQL Database (`sql`)
{: #sql-database-sql}

Extracts Azure SQL Server and SQL Database configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:sql:sql-server` | SQL servers | Admin, firewall rules, VNet rules, audit settings |
| `azure:sql:sql-database` | SQL databases | SKU, collation, backup config, geo-redundancy |
| `azure:sql:elastic-pool` | Elastic pools | SKU, DTU/vCore, database limits |
| `azure:sql:firewall-rule` | Server firewall rules | Start/end IP, rule name |

**Extracted Configuration:**

### SQL Servers
- Server administrator account
- Active Directory administrator
- Server version and location
- Firewall rules (IP ranges)
- Virtual network rules
- Private endpoint connections
- Security alert policies
- Vulnerability assessment settings
- Audit logging configuration
- Transparent Data Encryption (TDE) settings
- Minimum TLS version

### SQL Databases
- Database SKU and pricing tier
- Service tier (Basic, Standard, Premium, Hyperscale)
- Compute tier (Provisioned, Serverless)
- DTU or vCore configuration
- Collation and compatibility level
- Max database size
- Backup retention period
- Geo-redundancy and replication
- Long-term retention policies
- Advanced Threat Protection
- Data encryption settings
- Automatic tuning configuration

**Common Use Cases:**
- Audit SQL Server firewall rules
- Verify TDE encryption enabled
- Track database backup configurations
- Monitor SQL Server versions for updates
- Identify databases without threat protection

**Security Checks:**
- ✅ Azure AD authentication enabled
- ✅ Transparent Data Encryption (TDE) enabled
- ✅ Advanced Threat Protection enabled
- ✅ Auditing enabled and configured
- ✅ No firewall rules allowing 0.0.0.0 - 255.255.255.255
- ✅ Minimum TLS version set to 1.2
- ✅ Public network access restricted where possible
- ✅ Vulnerability assessments configured

---

## Container Service (`containerservice`)
{: #container-service-containerservice}

Extracts Azure Kubernetes Service (AKS) cluster configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:containerservice:aks-cluster` | AKS clusters | K8s version, node pools, network, RBAC, add-ons |
| `azure:containerservice:node-pool` | Agent node pools | VM size, count, OS type, scaling settings |

**Extracted Configuration:**

### AKS Clusters
- Kubernetes version
- DNS prefix and FQDN
- Location and resource group
- Network profile (plugin, policy, service CIDR, DNS service IP)
- Network plugin (kubenet, Azure CNI)
- Load balancer SKU
- API server access profile (authorized IP ranges)
- Azure AD integration settings
- RBAC configuration
- Managed identity configuration
- Add-ons and monitoring:
  - Azure Monitor for containers
  - HTTP application routing
  - Virtual node
  - Azure Policy
  - Azure Key Vault secrets provider
- Auto-scaler profile
- Azure Active Directory pod identity
- Private cluster settings

### Node Pools
- VM size and OS type (Linux, Windows)
- Node count and scaling limits
- Availability zones
- Auto-scaling settings (min/max nodes)
- OS disk size and type
- Node labels and taints
- Upgrade settings (surge upgrade)
- Spot instance configuration
- Mode (System, User)

**Common Use Cases:**
- Inventory AKS clusters across subscriptions
- Audit Kubernetes versions for updates
- Verify RBAC and Azure AD integration
- Track node pool configurations and scaling
- Monitor cluster add-ons and monitoring

**Security Checks:**
- ✅ RBAC enabled
- ✅ Azure AD integration configured
- ✅ Azure Policy add-on enabled
- ✅ API server authorized IP ranges configured
- ✅ Private cluster enabled (where appropriate)
- ✅ Azure Monitor for containers enabled
- ✅ Network policies enabled
- ✅ Managed identity used (not service principal)

---

## Key Vault (`keyvault`)
{: #key-vault-keyvault}

Extracts Azure Key Vault configurations for secrets, keys, and certificates management.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:keyvault:key-vault` | Key vaults | SKU, access policies, network ACLs, soft delete |
| `azure:keyvault:secret` | Secrets | Name, enabled status, expiration |
| `azure:keyvault:key` | Cryptographic keys | Key type, size, operations, expiration |
| `azure:keyvault:certificate` | Certificates | Thumbprint, subject, expiration, key properties |

**Extracted Configuration:**

### Key Vault
- SKU (Standard, Premium)
- Vault URI
- Tenant ID and location
- Access policies:
  - Principal (user, service principal, managed identity)
  - Key permissions
  - Secret permissions
  - Certificate permissions
  - Storage permissions
- Network ACLs:
  - Default action (allow/deny)
  - IP rules and virtual network rules
  - Bypass settings (AzureServices, None)
- Soft delete and purge protection settings
- Enable for Azure deployment/disk encryption/template deployment
- Private endpoint connections
- RBAC authorization mode
- Resource locks

### Secrets, Keys, and Certificates
- Name and version
- Enabled/disabled status
- Creation and update timestamps
- Expiration date
- Attributes (content type, tags)
- Key vault reference

**Common Use Cases:**
- Audit Key Vault access policies
- Verify network access restrictions
- Track secret and certificate expiration
- Monitor soft delete and purge protection
- Identify Key Vaults without RBAC

**Security Checks:**
- ✅ Soft delete enabled
- ✅ Purge protection enabled
- ✅ Network ACLs configured (not open to all networks)
- ✅ Private endpoint connections used
- ✅ Diagnostic logging enabled
- ✅ RBAC authorization enabled
- ✅ No overly permissive access policies
- ✅ Secrets and certificates have expiration dates

---

## Authorization (`authorization`)
{: #authorization-authorization}

Extracts Azure Role-Based Access Control (RBAC) role definitions and role assignments.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `azure:authorization:role-definition` | RBAC roles | Permissions, assignable scopes, role type |
| `azure:authorization:role-assignment` | Role assignments | Principal, role, scope, condition |

**Extracted Configuration:**

### Role Definitions
- Role name and description
- Role type (BuiltInRole, CustomRole)
- Assignable scopes (subscription, resource group, resource)
- Permissions:
  - Actions (allowed operations)
  - NotActions (denied operations)
  - DataActions (data plane operations)
  - NotDataActions (denied data operations)
- Role ID and creation timestamp

### Role Assignments
- Principal ID and type (User, Group, ServicePrincipal, ManagedIdentity)
- Principal name and email (if available)
- Role definition name and ID
- Scope (subscription, resource group, resource)
- Assignment conditions (ABAC)
- Delegated managed identity resource ID
- Assignment description

**Common Use Cases:**
- Audit RBAC role assignments across subscriptions
- Identify custom role definitions
- Track privileged role assignments (Owner, Contributor)
- Verify least privilege access
- Monitor service principal and managed identity permissions
- Review conditional access policies

**Security Checks:**
- ✅ Least privilege principle applied
- ✅ No wildcard (*) permissions in custom roles
- ✅ Owner role assignments limited
- ✅ Service principals have minimal required permissions
- ✅ Role assignments reviewed regularly
- ✅ Conditional access policies used where appropriate
- ✅ No direct user assignments (prefer groups)

**Example Extraction:**
```bash
# Extract RBAC configurations
curl -X POST "http://localhost:8000/extraction/extract?services=authorization&provider=azure"
```

---

## Extraction Examples

### Extract All Azure Resources

```bash
curl -X POST "http://localhost:8000/extraction/extract?provider=azure"
```

### Extract Specific Services

```bash
# Compute and storage only
curl -X POST "http://localhost:8000/extraction/extract?provider=azure&services=compute,storage"

# Security-related services
curl -X POST "http://localhost:8000/extraction/extract?provider=azure&services=keyvault,authorization,network"

# Web and database services
curl -X POST "http://localhost:8000/extraction/extract?provider=azure&services=web,sql"
```

### Extract from Specific Subscriptions

```bash
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "subscriptions": ["sub-1", "sub-2"],
    "services": ["compute", "storage", "network"]
  }'
```

---

## Authentication Requirements

### Service Principal Permissions

To extract resources, the service principal needs appropriate Reader roles:

#### Minimum Required Roles:

```bash
# Subscription-level Reader role
az role assignment create \
  --assignee <service-principal-id> \
  --role "Reader" \
  --scope "/subscriptions/<subscription-id>"

# For RBAC data
az role assignment create \
  --assignee <service-principal-id> \
  --role "User Access Administrator" \
  --scope "/subscriptions/<subscription-id>"
```

#### Recommended Roles:

- **Reader**: Read-only access to all resources
- **Security Reader**: Additional security-specific read permissions
- **Key Vault Reader**: For Key Vault metadata (use access policies for secrets)

### Setup Service Principal

```bash
# Create service principal with Reader role
az ad sp create-for-rbac \
  --name "csp-scanner-sp" \
  --role "Reader" \
  --scopes "/subscriptions/<subscription-id>"

# Add Security Reader role
az role assignment create \
  --assignee <service-principal-app-id> \
  --role "Security Reader" \
  --scope "/subscriptions/<subscription-id>"

# Output provides:
# - appId (AZURE_CLIENT_ID)
# - password (AZURE_CLIENT_SECRET)
# - tenant (AZURE_TENANT_ID)
```

### Configure Multiple Subscriptions

```yaml
# config/production.yaml
azure_subscriptions:
  - subscription_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    locations:
      - "eastus"
      - "westus2"
  - subscription_id: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
    locations:
      - "westeurope"
      - "northeurope"

azure_tenant_id: "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"
azure_client_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
azure_client_secret: "your-client-secret"
```

---

## Common Extraction Patterns

### Security Audit Extraction

```bash
# Extract security-relevant resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "services": [
      "authorization",
      "keyvault",
      "network",
      "storage",
      "sql"
    ]
  }'
```

### Cost Optimization Extraction

```bash
# Extract cost-related resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "services": [
      "compute",
      "storage",
      "sql",
      "web"
    ]
  }'
```

### Compliance Audit Extraction

```bash
# Extract compliance-relevant resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "services": [
      "authorization",
      "network",
      "storage",
      "keyvault",
      "sql",
      "compute"
    ]
  }'
```

---

## Troubleshooting

### Common Issues

#### Permission Denied Errors

```
Error: AuthorizationFailed - Principal does not have access
```

**Solution**: Verify service principal has Reader role:
```bash
az role assignment list \
  --assignee <service-principal-app-id> \
  --scope "/subscriptions/<subscription-id>"
```

#### Invalid Credentials

```
Error: Invalid client secret
```

**Solution**: Verify credentials are correct:
```bash
az login --service-principal \
  -u <client-id> \
  -p <client-secret> \
  --tenant <tenant-id>
```

#### Subscription Not Found

```
Error: Subscription not found or not accessible
```

**Solution**: List accessible subscriptions:
```bash
az account list --output table
```

### Verification Commands

```bash
# Test authentication
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID

# List accessible subscriptions
az account list --output table

# Verify resource access
az vm list --subscription <subscription-id>
az storage account list --subscription <subscription-id>
az network vnet list --subscription <subscription-id>
```

---

## See Also

- [Azure Setup Guide]({{ '/cloud-providers-azure.html' | relative_url }}) - Detailed authentication and configuration
- [Configuration Guide]({{ '/configuration.html' | relative_url }}) - Multi-subscription and location settings
- [API Reference]({{ '/api-reference.html' | relative_url }}) - Extraction API endpoints
- [Metadata Structure]({{ '/metadata-structure.html' | relative_url }}) - Output format specification
