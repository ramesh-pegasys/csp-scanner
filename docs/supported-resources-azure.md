---
layout: default
title: Azure Supported Resources
parent: Supported Resources
nav_order: 2
has_children: false
---

# Azure Supported Resources

The following Azure resource extractors are supported:

- authorization
- compute
- containerservice
- keyvault
- network
- sql
- storage
- web

## Detailed Resource Information

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
