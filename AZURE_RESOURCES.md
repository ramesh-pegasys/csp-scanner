# Azure Resources Support

This document lists the Azure resources currently supported by the CSP Scanner.

## Supported Azure Resources

### Compute (azure:compute)

#### Virtual Machines
- **Resource Type**: `azure:compute:virtual-machine`
- **Azure Resource**: `Microsoft.Compute/virtualMachines`
- **Extracted Information**:
  - VM size and configuration
  - OS disk details (type, size, encryption)
  - Network interfaces
  - Power state and provisioning status
  - Tags and metadata
  - Instance view (runtime information)

#### VM Scale Sets (VMSS)
- **Resource Type**: `azure:compute:vmss`
- **Azure Resource**: `Microsoft.Compute/virtualMachineScaleSets`
- **Extracted Information**:
  - SKU (name, tier, capacity)
  - Upgrade policy
  - Provisioning state
  - Tags and metadata

**Configuration Options** (`config/extractors.yaml`):
```yaml
azure:
  compute:
    max_workers: 10
    include_stopped: true
    include_vmss: true
```

---

### Storage (azure:storage)

#### Storage Accounts
- **Resource Type**: `azure:storage:account`
- **Azure Resource**: `Microsoft.Storage/storageAccounts`
- **Extracted Information**:
  - SKU and account kind
  - Access tier (Hot, Cool, Archive)
  - Encryption settings (key source, services)
  - HTTPS-only enforcement
  - Blob public access settings
  - Minimum TLS version
  - Network rules (firewall, virtual networks)
  - Blob service properties (retention policies)
  - Tags and metadata

**Configuration Options**:
```yaml
azure:
  storage:
    max_workers: 20
    check_access_policies: true
    check_blob_encryption: true
```

---

### Network (azure:network)

#### Network Security Groups (NSG)
- **Resource Type**: `azure:network:nsg`
- **Azure Resource**: `Microsoft.Network/networkSecurityGroups`
- **Extracted Information**:
  - Security rules (custom and default)
  - Rule properties: priority, direction, access, protocol
  - Source and destination configurations
  - Port ranges
  - Tags and metadata

#### Virtual Networks (VNet)
- **Resource Type**: `azure:network:vnet`
- **Azure Resource**: `Microsoft.Network/virtualNetworks`
- **Extracted Information**:
  - Address space (CIDR blocks)
  - Subnets and their configurations
  - NSG associations per subnet
  - DDoS protection status
  - Tags and metadata

#### Load Balancers
- **Resource Type**: `azure:network:load-balancer`
- **Azure Resource**: `Microsoft.Network/loadBalancers`
- **Extracted Information**:
  - SKU (Basic, Standard)
  - Frontend IP configurations (public/private)
  - Backend address pools
  - Load balancing rules
  - Health probes
  - Tags and metadata

**Configuration Options**:
```yaml
azure:
  network:
    max_workers: 10
    include_nsg_rules: true
    include_load_balancers: true
```

---

### Web (azure:web)

#### App Service Plans
- **Resource Type**: `azure:web:app-service-plan`
- **Azure Resource**: `Microsoft.Web/serverfarms`
- **Extracted Information**:
  - SKU (name, tier, size, capacity)
  - Number of sites
  - Maximum workers
  - Provisioning state
  - Tags and metadata

#### Web Apps
- **Resource Type**: `azure:web:web-app`
- **Azure Resource**: `Microsoft.Web/sites`
- **Extracted Information**:
  - Runtime stack (Linux/Windows FX versions)
  - HTTPS enforcement
  - Client certificate requirements
  - Site configuration
  - Provisioning state
  - Tags and metadata

#### Function Apps
- **Resource Type**: `azure:web:function-app`
- **Azure Resource**: `Microsoft.Web/sites` (with kind=functionapp)
- **Extracted Information**:
  - Runtime configuration
  - Function app settings
  - HTTPS and security settings
  - Provisioning state
  - Tags and metadata

**Configuration Options**:
```yaml
azure:
  web:
    max_workers: 10
    include_app_service_plans: true
    include_web_apps: true
    include_function_apps: true
```

---

### Key Vault (azure:keyvault)

#### Key Vaults
- **Resource Type**: `azure:keyvault:key-vault`
- **Azure Resource**: `Microsoft.KeyVault/vaults`
- **Extracted Information**:
  - Vault URI
  - SKU and access policies
  - Soft delete settings
  - Network ACLs (firewall rules)
  - Encryption settings
  - Access control settings
  - Tags and metadata

**Configuration Options**:
```yaml
azure:
  keyvault:
    max_workers: 10
    include_network_acls: true
    check_access_policies: true
```

---

### SQL Database (azure:sql)

#### SQL Servers
- **Resource Type**: `azure:sql:sql-server`
- **Azure Resource**: `Microsoft.Sql/servers`
- **Extracted Information**:
  - Server version and administrator login
  - Public network access settings
  - Minimal TLS version
  - Firewall rules
  - Provisioning state
  - Tags and metadata

#### SQL Databases
- **Resource Type**: `azure:sql:sql-database`
- **Azure Resource**: `Microsoft.Sql/servers/databases`
- **Extracted Information**:
  - Database collation and size
  - SKU and performance tier
  - Zone redundancy
  - Status and provisioning state
  - Server association
  - Tags and metadata

**Configuration Options**:
```yaml
azure:
  sql:
    max_workers: 10
    include_databases: true
    include_firewall_rules: true
    check_public_access: true
```

---

### Container Service (azure:containerservice)

#### AKS Clusters
- **Resource Type**: `azure:containerservice:aks-cluster`
- **Azure Resource**: `Microsoft.ContainerService/managedClusters`
- **Extracted Information**:
  - Kubernetes version
  - Node pools configuration
  - Network settings (CNI, service CIDR)
  - RBAC and API server access
  - Addon configurations
  - Agent pool profiles
  - Provisioning state
  - Tags and metadata

**Configuration Options**:
```yaml
azure:
  containerservice:
    max_workers: 10
    include_node_pools: true
    include_network_config: true
    check_rbac_settings: true
```

---

### Authorization (azure:authorization)

#### Role Definitions
- **Resource Type**: `azure:authorization:role-definition`
- **Azure Resource**: `Microsoft.Authorization/roleDefinitions`
- **Extracted Information**:
  - Role permissions (actions, not actions)
  - Assignable scopes
  - Role description and type
  - Custom vs built-in roles
  - Tags and metadata

#### Role Assignments
- **Resource Type**: `azure:authorization:role-assignment`
- **Azure Resource**: `Microsoft.Authorization/roleAssignments`
- **Extracted Information**:
  - Principal ID and type
  - Role definition reference
  - Assignment scope (subscription, resource group, resource)
  - Scope type analysis
  - Tags and metadata

**Configuration Options**:
```yaml
azure:
  authorization:
    max_workers: 10
    include_custom_roles: true
    include_role_assignments: true
    analyze_scope_hierarchy: true
```

---

## Metadata Format

All Azure resources include standardized metadata:

```json
{
  "cloud_provider": "azure",
  "resource_type": "azure:compute:virtual-machine",
  "metadata": {
    "resource_id": "/subscriptions/{sub-id}/resourceGroups/{rg}/providers/...",
    "service": "compute",
    "location": "eastus",
    "subscription_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "resource_group": "my-resource-group",
    "labels": {
      "environment": "production",
      "team": "platform"
    }
  },
  "configuration": {
    // Resource-specific configuration
  },
  "raw": {
    // Full Azure SDK response
  }
}
```

## Resource Coverage by Category

| Category | Supported | Planned | Not Planned |
|----------|-----------|---------|-------------|
| **Compute** | VM, VMSS | Container Instances, Batch | |
| **Storage** | Storage Accounts | File Shares, Disks | |
| **Network** | NSG, VNet, Load Balancer | Application Gateway, VPN Gateway, Firewall | |
| **Web** | App Service Plans, Web Apps, Function Apps | API Apps, Mobile Apps | |
| **Database** | SQL Servers, SQL Databases | Cosmos DB, MySQL, PostgreSQL | |
| **Container** | AKS Clusters | Container Instances | |
| **Security** | Key Vaults | Application Gateway WAF, Security Center | |
| **Identity** | Role Definitions, Role Assignments | Managed Identities, AD Groups | |
| **Management** | | Resource Groups, Policy Assignments | |
| **Analytics** | | Log Analytics, Application Insights | |
| **Integration** | | Service Bus, Event Grid | |

## Planned Additions

### Phase 2 Resources

#### Web Services
- **App Services** (`azure:web:app-service`)
  - Web app configurations
  - Deployment slots
  - Custom domains and SSL
  - Authentication settings

- **Function Apps** (`azure:web:function-app`)
  - Runtime and version
  - App settings
  - Triggers and bindings
  - Consumption vs Premium plan

#### Database Services
- **SQL Databases** (`azure:sql:database`)
  - Server configuration
  - Firewall rules
  - Encryption settings
  - Geo-replication

- **Cosmos DB** (`azure:cosmosdb:account`)
  - Consistency level
  - Geo-replication
  - Backup policy

#### Container Services
- **AKS Clusters** (`azure:containerservice:aks`)
  - Kubernetes version
  - Node pools
  - Network profile
  - RBAC configuration

- **Container Instances** (`azure:containerinstance:container-group`)
  - Container configurations
  - Network profile
  - Volume mounts

#### Security Services
- **Key Vaults** (`azure:keyvault:vault`)
  - Access policies
  - Network rules
  - Soft delete settings
  - Keys, secrets, certificates inventory

#### Identity & Access
- **Role Assignments** (`azure:authorization:role-assignment`)
  - Principal information
  - Role definition
  - Scope

## Usage Examples

### Extract All Azure Resources

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure"
  }'
```

### Extract Specific Azure Services

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "services": ["compute", "storage"]
  }'
```

### Extract from Specific Azure Regions

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "services": ["compute"],
    "regions": ["eastus", "westus2"]
  }'
```

### List Available Azure Services

```bash
curl http://localhost:8000/services?provider=azure
```

## Resource Type Naming Convention

Azure resource types follow the pattern:
```
azure:{service}:{resource-type}
```

Examples:
- `azure:compute:virtual-machine`
- `azure:storage:account`
- `azure:network:nsg`
- `azure:web:app-service`
- `azure:sql:database`

This matches the pattern used for AWS resources:
- `aws:ec2:instance`
- `aws:s3:bucket`
- `aws:rds:db-instance`

## Contributing

To add support for new Azure resources:

1. Create extractor in `app/extractors/azure/{service}.py`
2. Implement `get_metadata()`, `extract()`, and `transform()` methods
3. Register in `app/services/registry.py`
4. Add configuration to `config/extractors.yaml`
5. Update this documentation

See `AZURE_INTEGRATION_PLAN.md` for detailed implementation guide.
