# Azure Integration Plan for CSP Scanner

## Overview
This document outlines the plan to extend the CSP Scanner to support Azure resources alongside AWS, maintaining the same architectural patterns while enabling multi-cloud scanning capabilities.

## Current Architecture Summary

### Existing Components
- **BaseExtractor**: Abstract base class for all extractors (already has multi-cloud support in metadata)
- **ExtractorRegistry**: Manages extractor instances (currently AWS-only)
- **Individual Extractors**: AWS service-specific extractors (EC2, S3, RDS, etc.)
- **ExtractionOrchestrator**: Coordinates extraction and transport (cloud-agnostic)
- **Transport Layer**: Sends artifacts to scanner (cloud-agnostic)
- **Configuration**: Manages settings and credentials (AWS-only)

### Current Flow
```
main.py → boto3.Session → ExtractorRegistry → AWS Extractors → Orchestrator → Transport
```

## Azure SDK Selection

### Recommended: Azure SDK for Python
**NOT Bicep** - Bicep is an Infrastructure as Code (IaC) language for deploying Azure resources, not for reading/scanning existing resources.

**Azure SDK for Python** is the boto3 equivalent for Azure:
- **Core Package**: `azure-identity` for authentication
- **Management Packages**: Individual SDKs for each service
  - `azure-mgmt-compute` - Virtual Machines, Scale Sets, Disks
  - `azure-mgmt-network` - Virtual Networks, NSGs, Load Balancers, Application Gateways
  - `azure-mgmt-storage` - Storage Accounts, Blob Services
  - `azure-mgmt-web` - App Services, Function Apps
  - `azure-mgmt-sql` - SQL Databases, SQL Servers
  - `azure-mgmt-containerservice` - AKS clusters
  - `azure-mgmt-containerinstance` - Container Instances
  - `azure-mgmt-keyvault` - Key Vaults
  - `azure-mgmt-monitor` - Monitoring, Diagnostics
  - `azure-mgmt-authorization` - RBAC, Role Assignments

### Authentication Methods
```python
from azure.identity import DefaultAzureCredential, ClientSecretCredential

# Option 1: DefaultAzureCredential (recommended for production)
# Tries multiple auth methods: environment vars, managed identity, Azure CLI, etc.
credential = DefaultAzureCredential()

# Option 2: Service Principal (explicit credentials)
credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)
```

## Implementation Plan

### Phase 1: Cloud Session Abstraction Layer

Create a provider-agnostic session interface to decouple extractors from specific cloud SDKs.

#### 1.1 Create Cloud Session Protocol
**File**: `app/cloud/__init__.py`
```python
from typing import Protocol, Any, Optional
from enum import Enum

class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"

class CloudSession(Protocol):
    """Protocol for cloud provider sessions"""
    
    @property
    def provider(self) -> CloudProvider:
        """Return the cloud provider type"""
        ...
    
    def get_client(self, service: str, region: Optional[str] = None) -> Any:
        """Get a client for a specific service"""
        ...
    
    def list_regions(self) -> list[str]:
        """List available regions/locations"""
        ...
```

#### 1.2 AWS Session Wrapper
**File**: `app/cloud/aws_session.py`
```python
import boto3
from typing import Any, Optional
from .base import CloudSession, CloudProvider

class AWSSession:
    """Wrapper around boto3.Session implementing CloudSession protocol"""
    
    def __init__(self, boto_session: boto3.Session):
        self._session = boto_session
    
    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AWS
    
    def get_client(self, service: str, region: Optional[str] = None):
        return self._session.client(service, region_name=region)
    
    def list_regions(self) -> list[str]:
        ec2_client = self._session.client("ec2")
        response = ec2_client.describe_regions(AllRegions=False)
        return [region["RegionName"] for region in response["Regions"]]
```

#### 1.3 Azure Session Wrapper
**File**: `app/cloud/azure_session.py`
```python
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from typing import Any, Optional, Dict
from .base import CloudSession, CloudProvider

class AzureSession:
    """Azure session wrapper implementing CloudSession protocol"""
    
    def __init__(
        self,
        subscription_id: str,
        credential: Optional[Any] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.subscription_id = subscription_id
        
        # Use provided credential or create from client credentials
        if credential:
            self.credential = credential
        elif tenant_id and client_id and client_secret:
            self.credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            # Use default credential chain
            self.credential = DefaultAzureCredential()
        
        self._clients: Dict[str, Any] = {}
    
    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AZURE
    
    def get_client(self, service: str, region: Optional[str] = None):
        """
        Get Azure management client for a service.
        
        Service mapping:
        - 'compute' -> ComputeManagementClient
        - 'network' -> NetworkManagementClient
        - 'storage' -> StorageManagementClient
        - 'web' -> WebSiteManagementClient
        - etc.
        """
        cache_key = f"{service}:{region}" if region else service
        
        if cache_key not in self._clients:
            self._clients[cache_key] = self._create_client(service)
        
        return self._clients[cache_key]
    
    def _create_client(self, service: str):
        """Create appropriate Azure management client"""
        if service == "compute":
            from azure.mgmt.compute import ComputeManagementClient
            return ComputeManagementClient(self.credential, self.subscription_id)
        elif service == "network":
            from azure.mgmt.network import NetworkManagementClient
            return NetworkManagementClient(self.credential, self.subscription_id)
        elif service == "storage":
            from azure.mgmt.storage import StorageManagementClient
            return StorageManagementClient(self.credential, self.subscription_id)
        elif service == "web":
            from azure.mgmt.web import WebSiteManagementClient
            return WebSiteManagementClient(self.credential, self.subscription_id)
        elif service == "sql":
            from azure.mgmt.sql import SqlManagementClient
            return SqlManagementClient(self.credential, self.subscription_id)
        elif service == "containerservice":
            from azure.mgmt.containerservice import ContainerServiceClient
            return ContainerServiceClient(self.credential, self.subscription_id)
        elif service == "keyvault":
            from azure.mgmt.keyvault import KeyVaultManagementClient
            return KeyVaultManagementClient(self.credential, self.subscription_id)
        else:
            raise ValueError(f"Unknown Azure service: {service}")
    
    def list_regions(self) -> list[str]:
        """List available Azure locations"""
        from azure.mgmt.resource import SubscriptionClient
        
        sub_client = SubscriptionClient(self.credential)
        locations = sub_client.subscriptions.list_locations(self.subscription_id)
        return [loc.name for loc in locations]
```

### Phase 2: Configuration Updates

#### 2.1 Extend Settings for Multi-Cloud
**File**: `app/core/config.py`
```python
class Settings(BaseSettings):
    # ... existing AWS config ...
    
    # Azure Configuration
    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_default_location: str = "eastus"
    
    # Multi-cloud
    enabled_providers: List[str] = ["aws"]  # Can be ["aws", "azure", "gcp"]
    
    @property
    def is_aws_enabled(self) -> bool:
        return "aws" in self.enabled_providers
    
    @property
    def is_azure_enabled(self) -> bool:
        return "azure" in self.enabled_providers
```

#### 2.2 Update Extractor Configuration
**File**: `config/extractors.yaml`
```yaml
# AWS Extractors
aws:
  ec2:
    max_workers: 10
    include_stopped: true
  s3:
    max_workers: 20
    check_bucket_policies: true
  # ... other AWS extractors ...

# Azure Extractors
azure:
  compute:
    max_workers: 10
    include_stopped: true
    include_vmss: true  # Virtual Machine Scale Sets
  storage:
    max_workers: 20
    check_access_policies: true
    check_blob_encryption: true
  network:
    max_workers: 10
    include_nsg_rules: true
  web:
    max_workers: 15
    include_app_settings: true
  sql:
    max_workers: 10
    include_firewall_rules: true
```

### Phase 3: Update Base Extractor

#### 3.1 Modify BaseExtractor to Use CloudSession
**File**: `app/extractors/base.py`
```python
from typing import Protocol, Union
import boto3

# Import cloud sessions
from app.cloud.base import CloudSession, CloudProvider

class BaseExtractor(ABC):
    """Base class for all cloud resource extractors"""
    
    def __init__(
        self, 
        session: Union[boto3.Session, CloudSession], 
        config: Dict[str, Any]
    ):
        # Support both old boto3.Session and new CloudSession
        if isinstance(session, boto3.Session):
            # Wrap boto3 session for backward compatibility
            from app.cloud.aws_session import AWSSession
            self.session = AWSSession(session)
        else:
            self.session = session
        
        self.config = config
        self.metadata = self.get_metadata()
        self.cloud_provider: CloudProvider = self.metadata.cloud_provider
```

### Phase 4: Update Registry for Multi-Cloud

#### 4.1 Enhanced ExtractorRegistry
**File**: `app/services/registry.py`
```python
from typing import Dict, List, Optional
from app.cloud.base import CloudProvider, CloudSession

class ExtractorRegistry:
    """Registry for managing extractors across multiple cloud providers"""
    
    def __init__(self, sessions: Dict[CloudProvider, CloudSession], config: Settings):
        self.sessions = sessions
        self.config = config
        self._extractors: Dict[str, BaseExtractor] = {}
        self._register_extractors()
    
    def _register_extractors(self):
        """Register extractors for all enabled cloud providers"""
        for provider, session in self.sessions.items():
            if provider == CloudProvider.AWS:
                self._register_aws_extractors(session)
            elif provider == CloudProvider.AZURE:
                self._register_azure_extractors(session)
    
    def _register_aws_extractors(self, session: CloudSession):
        """Register AWS extractors"""
        from app.extractors.ec2 import EC2Extractor
        from app.extractors.s3 import S3Extractor
        # ... import other AWS extractors ...
        
        aws_config = self.config.extractors.get("aws", {})
        
        for extractor_class in [EC2Extractor, S3Extractor, ...]:
            self._register_extractor(extractor_class, session, aws_config)
    
    def _register_azure_extractors(self, session: CloudSession):
        """Register Azure extractors"""
        from app.extractors.azure.compute import AzureComputeExtractor
        from app.extractors.azure.storage import AzureStorageExtractor
        from app.extractors.azure.network import AzureNetworkExtractor
        # ... import other Azure extractors ...
        
        azure_config = self.config.extractors.get("azure", {})
        
        for extractor_class in [AzureComputeExtractor, AzureStorageExtractor, ...]:
            self._register_extractor(extractor_class, session, azure_config)
    
    def _register_extractor(
        self, 
        extractor_class: Type[BaseExtractor],
        session: CloudSession,
        provider_config: Dict[str, Any]
    ):
        """Register a single extractor"""
        try:
            service_name = extractor_class.__name__.replace("Extractor", "").lower()
            extractor_config = provider_config.get(service_name, {})
            
            instance = extractor_class(session, extractor_config)
            key = f"{instance.metadata.cloud_provider}:{instance.metadata.service_name}"
            
            self._extractors[key] = instance
            logger.info(f"Registered extractor: {key}")
        except Exception as e:
            logger.error(f"Failed to register {extractor_class.__name__}: {e}")
    
    def get(self, service_name: str, provider: Optional[CloudProvider] = None) -> Optional[BaseExtractor]:
        """Get extractor by service name and optionally provider"""
        if provider:
            key = f"{provider}:{service_name}"
            return self._extractors.get(key)
        
        # Search all providers
        for key, extractor in self._extractors.items():
            if key.endswith(f":{service_name}"):
                return extractor
        return None
    
    def get_extractors(
        self,
        services: Optional[List[str]] = None,
        provider: Optional[CloudProvider] = None
    ) -> List[BaseExtractor]:
        """Get multiple extractors, optionally filtered by provider"""
        extractors = list(self._extractors.values())
        
        if provider:
            extractors = [e for e in extractors if e.cloud_provider == provider]
        
        if services:
            extractors = [e for e in extractors if e.metadata.service_name in services]
        
        return extractors
```

### Phase 5: Create Azure Extractors

#### 5.1 Directory Structure
```
app/extractors/azure/
├── __init__.py
├── base.py              # Azure-specific base class if needed
├── compute.py           # Virtual Machines, Scale Sets
├── storage.py           # Storage Accounts, Blobs
├── network.py           # VNets, NSGs, Load Balancers
├── web.py               # App Services, Function Apps
├── sql.py               # SQL Databases
├── containerservice.py  # AKS
├── keyvault.py          # Key Vaults
└── authorization.py     # RBAC, Role Assignments
```

#### 5.2 Example: Azure Compute Extractor
**File**: `app/extractors/azure/compute.py`
```python
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)

class AzureComputeExtractor(BaseExtractor):
    """Extractor for Azure Virtual Machines and related resources"""
    
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="compute",
            version="1.0.0",
            description="Extracts Azure Virtual Machines and Scale Sets",
            resource_types=["virtual-machine", "vmss"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )
    
    async def extract(
        self,
        region: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure compute resources"""
        locations = [region] if region else self.session.list_regions()
        artifacts = []
        
        with ThreadPoolExecutor(max_workers=self.config.get("max_workers", 10)) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_location, loc, filters)
                for loc in locations
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Azure compute extraction error: {result}")
            else:
                artifacts.extend(result)
        
        return artifacts
    
    def _extract_location(
        self,
        location: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract compute resources from a specific location"""
        artifacts = []
        compute_client = self.session.get_client("compute", location)
        
        # Extract Virtual Machines
        try:
            vms = self._extract_virtual_machines(compute_client, location)
            artifacts.extend(vms)
        except Exception as e:
            logger.error(f"Failed to extract VMs in {location}: {e}")
        
        # Extract VM Scale Sets if configured
        if self.config.get("include_vmss", True):
            try:
                vmss = self._extract_vmss(compute_client, location)
                artifacts.extend(vmss)
            except Exception as e:
                logger.error(f"Failed to extract VMSS in {location}: {e}")
        
        return artifacts
    
    def _extract_virtual_machines(
        self,
        compute_client,
        location: str
    ) -> List[Dict[str, Any]]:
        """Extract Virtual Machines"""
        artifacts = []
        
        # List all VMs in subscription
        vms = compute_client.virtual_machines.list_all()
        
        for vm in vms:
            # Filter by location if needed
            if vm.location != location:
                continue
            
            # Get instance view for runtime information
            try:
                instance_view = compute_client.virtual_machines.instance_view(
                    resource_group_name=self._get_resource_group(vm.id),
                    vm_name=vm.name
                )
            except Exception:
                instance_view = None
            
            artifact = self.transform({
                "resource": vm,
                "instance_view": instance_view,
                "location": location,
                "resource_type": "virtual-machine"
            })
            
            if self.validate(artifact):
                artifacts.append(artifact)
        
        return artifacts
    
    def _extract_vmss(self, compute_client, location: str) -> List[Dict[str, Any]]:
        """Extract VM Scale Sets"""
        artifacts = []
        
        vmss_list = compute_client.virtual_machine_scale_sets.list_all()
        
        for vmss in vmss_list:
            if vmss.location != location:
                continue
            
            artifact = self.transform({
                "resource": vmss,
                "location": location,
                "resource_type": "vmss"
            })
            
            if self.validate(artifact):
                artifacts.append(artifact)
        
        return artifacts
    
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure VM resource to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]
        resource_type = raw_data["resource_type"]
        
        if resource_type == "virtual-machine":
            # Extract resource group from resource ID
            resource_group = self._get_resource_group(resource.id)
            
            # Get tags
            tags = resource.tags or {}
            
            # Build configuration
            config = {
                "vm_size": resource.hardware_profile.vm_size,
                "os_type": resource.storage_profile.os_disk.os_type,
                "os_disk": {
                    "name": resource.storage_profile.os_disk.name,
                    "disk_size_gb": resource.storage_profile.os_disk.disk_size_gb,
                    "managed_disk_id": resource.storage_profile.os_disk.managed_disk.id if resource.storage_profile.os_disk.managed_disk else None,
                },
                "network_interfaces": [nic.id for nic in resource.network_profile.network_interfaces],
                "provisioning_state": resource.provisioning_state,
            }
            
            # Add instance view data if available
            if "instance_view" in raw_data and raw_data["instance_view"]:
                instance_view = raw_data["instance_view"]
                config["power_state"] = self._get_power_state(instance_view)
                config["statuses"] = [
                    {"code": status.code, "display_status": status.display_status}
                    for status in instance_view.statuses
                ]
            
            return {
                "cloud_provider": "azure",
                "resource_type": "azure:compute:virtual-machine",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="compute",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": config,
                "raw": self._serialize_azure_resource(resource),
            }
        
        elif resource_type == "vmss":
            resource_group = self._get_resource_group(resource.id)
            tags = resource.tags or {}
            
            return {
                "cloud_provider": "azure",
                "resource_type": "azure:compute:vmss",
                "metadata": self.create_metadata_object(
                    resource_id=resource.id,
                    service="compute",
                    region=location,
                    subscription_id=self._get_subscription_id(resource.id),
                    resource_group=resource_group,
                    tags=tags,
                ),
                "configuration": {
                    "sku": {
                        "name": resource.sku.name,
                        "tier": resource.sku.tier,
                        "capacity": resource.sku.capacity,
                    },
                    "upgrade_policy": resource.upgrade_policy.mode if resource.upgrade_policy else None,
                    "provisioning_state": resource.provisioning_state,
                },
                "raw": self._serialize_azure_resource(resource),
            }
        
        return {}
    
    def _get_resource_group(self, resource_id: str) -> str:
        """Extract resource group from Azure resource ID"""
        # Azure resource ID format: /subscriptions/{sub}/resourceGroups/{rg}/...
        parts = resource_id.split("/")
        try:
            rg_index = parts.index("resourceGroups")
            return parts[rg_index + 1]
        except (ValueError, IndexError):
            return ""
    
    def _get_subscription_id(self, resource_id: str) -> str:
        """Extract subscription ID from Azure resource ID"""
        parts = resource_id.split("/")
        try:
            sub_index = parts.index("subscriptions")
            return parts[sub_index + 1]
        except (ValueError, IndexError):
            return ""
    
    def _get_power_state(self, instance_view) -> str:
        """Extract power state from instance view"""
        for status in instance_view.statuses:
            if status.code.startswith("PowerState/"):
                return status.code.split("/")[1]
        return "unknown"
    
    def _serialize_azure_resource(self, resource) -> Dict[str, Any]:
        """Convert Azure SDK model to dictionary"""
        # Azure SDK models have as_dict() method
        if hasattr(resource, "as_dict"):
            return resource.as_dict()
        return {}
```

#### 5.3 Example: Azure Storage Extractor
**File**: `app/extractors/azure/storage.py`
```python
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)

class AzureStorageExtractor(BaseExtractor):
    """Extractor for Azure Storage Accounts"""
    
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="storage",
            version="1.0.0",
            description="Extracts Azure Storage Accounts and configurations",
            resource_types=["storage-account"],
            cloud_provider="azure",
            supports_regions=True,
            requires_pagination=False,
        )
    
    async def extract(
        self,
        region: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract Azure storage resources"""
        artifacts = []
        
        with ThreadPoolExecutor(max_workers=self.config.get("max_workers", 20)) as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                self._extract_storage_accounts,
                region,
                filters
            )
        
        artifacts.extend(result)
        return artifacts
    
    def _extract_storage_accounts(
        self,
        location: Optional[str],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract storage accounts"""
        artifacts = []
        storage_client = self.session.get_client("storage")
        
        # List all storage accounts in subscription
        storage_accounts = storage_client.storage_accounts.list()
        
        for account in storage_accounts:
            # Filter by location if specified
            if location and account.location != location:
                continue
            
            # Get additional properties
            resource_group = self._get_resource_group(account.id)
            
            # Get blob service properties if configured
            blob_properties = None
            if self.config.get("check_blob_encryption", True):
                try:
                    blob_properties = storage_client.blob_services.get_service_properties(
                        resource_group_name=resource_group,
                        account_name=account.name
                    )
                except Exception as e:
                    logger.warning(f"Failed to get blob properties for {account.name}: {e}")
            
            artifact = self.transform({
                "resource": account,
                "blob_properties": blob_properties,
                "location": account.location,
                "resource_type": "storage-account"
            })
            
            if self.validate(artifact):
                artifacts.append(artifact)
        
        return artifacts
    
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Azure Storage Account to standardized format"""
        resource = raw_data["resource"]
        location = raw_data["location"]
        
        resource_group = self._get_resource_group(resource.id)
        tags = resource.tags or {}
        
        # Build configuration
        config = {
            "sku": {
                "name": resource.sku.name,
                "tier": resource.sku.tier,
            },
            "kind": resource.kind,
            "access_tier": resource.access_tier,
            "https_only": resource.enable_https_traffic_only,
            "allow_blob_public_access": resource.allow_blob_public_access,
            "minimum_tls_version": resource.minimum_tls_version,
            "encryption": {
                "key_source": resource.encryption.key_source if resource.encryption else None,
                "services": {}
            },
            "network_rule_set": self._get_network_rules(resource),
        }
        
        # Add encryption services
        if resource.encryption and resource.encryption.services:
            if resource.encryption.services.blob:
                config["encryption"]["services"]["blob"] = {
                    "enabled": resource.encryption.services.blob.enabled
                }
            if resource.encryption.services.file:
                config["encryption"]["services"]["file"] = {
                    "enabled": resource.encryption.services.file.enabled
                }
        
        # Add blob properties if available
        if raw_data.get("blob_properties"):
            blob_props = raw_data["blob_properties"]
            config["blob_properties"] = {
                "delete_retention_policy": {
                    "enabled": blob_props.delete_retention_policy.enabled if blob_props.delete_retention_policy else False,
                    "days": blob_props.delete_retention_policy.days if blob_props.delete_retention_policy else None,
                }
            }
        
        return {
            "cloud_provider": "azure",
            "resource_type": "azure:storage:account",
            "metadata": self.create_metadata_object(
                resource_id=resource.id,
                service="storage",
                region=location,
                subscription_id=self._get_subscription_id(resource.id),
                resource_group=resource_group,
                tags=tags,
            ),
            "configuration": config,
            "raw": self._serialize_azure_resource(resource),
        }
    
    def _get_network_rules(self, resource) -> Dict[str, Any]:
        """Extract network rules from storage account"""
        if not resource.network_rule_set:
            return {}
        
        return {
            "default_action": resource.network_rule_set.default_action,
            "bypass": resource.network_rule_set.bypass,
            "ip_rules": [
                {"value": rule.ip_address_or_range, "action": rule.action}
                for rule in (resource.network_rule_set.ip_rules or [])
            ],
            "virtual_network_rules": [
                {"id": rule.virtual_network_resource_id, "action": rule.action}
                for rule in (resource.network_rule_set.virtual_network_rules or [])
            ],
        }
    
    def _get_resource_group(self, resource_id: str) -> str:
        """Extract resource group from Azure resource ID"""
        parts = resource_id.split("/")
        try:
            rg_index = parts.index("resourceGroups")
            return parts[rg_index + 1]
        except (ValueError, IndexError):
            return ""
    
    def _get_subscription_id(self, resource_id: str) -> str:
        """Extract subscription ID from Azure resource ID"""
        parts = resource_id.split("/")
        try:
            sub_index = parts.index("subscriptions")
            return parts[sub_index + 1]
        except (ValueError, IndexError):
            return ""
    
    def _serialize_azure_resource(self, resource) -> Dict[str, Any]:
        """Convert Azure SDK model to dictionary"""
        if hasattr(resource, "as_dict"):
            return resource.as_dict()
        return {}
```

### Phase 6: Update Main Application

#### 6.1 Multi-Cloud Initialization
**File**: `app/main.py`
```python
import importlib
import logging
import boto3
from typing import Dict
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.cloud.base import CloudProvider, CloudSession
from app.cloud.aws_session import AWSSession
from app.cloud.azure_session import AzureSession
from app.core.config import get_settings
from app.services.registry import ExtractorRegistry
from app.services.orchestrator import ExtractionOrchestrator
from app.transport.base import TransportFactory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
scheduler = AsyncIOScheduler()
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global orchestrator
    
    settings = get_settings()
    logger.info("Starting Cloud Artifact Extractor")
    
    # Initialize cloud sessions based on enabled providers
    sessions: Dict[CloudProvider, CloudSession] = {}
    
    # Initialize AWS if enabled
    if settings.is_aws_enabled:
        boto_session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        )
        sessions[CloudProvider.AWS] = AWSSession(boto_session)
        logger.info("Initialized AWS session")
    
    # Initialize Azure if enabled
    if settings.is_azure_enabled:
        azure_session = AzureSession(
            subscription_id=settings.azure_subscription_id,
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
        )
        sessions[CloudProvider.AZURE] = azure_session
        logger.info("Initialized Azure session")
    
    # Initialize registry with all sessions
    registry = ExtractorRegistry(sessions, settings)
    
    # Create transport
    transport = TransportFactory.create(
        settings.transport_type,
        settings.transport_config
    )
    
    orchestrator = ExtractionOrchestrator(
        registry=registry,
        transport=transport,
        config=settings.orchestrator_config
    )
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")
    
    # Store in app state
    app.state.orchestrator = orchestrator
    app.state.scheduler = scheduler
    app.state.registry = registry
    
    yield
    
    # Shutdown
    logger.info("Shutting down")
    scheduler.shutdown()
    
    if hasattr(transport, "close"):
        await transport.close()
    elif hasattr(transport, "disconnect"):
        await transport.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Cloud Artifact Extractor",
    description="Extract AWS and Azure cloud artifacts and send to policy scanner",
    version="2.0.0",
    lifespan=lifespan,
)

# Include routes
from app.api.routes import extraction, schedules, health
app.include_router(extraction.router)
app.include_router(schedules.router)
app.include_router(health.router)
```

### Phase 7: Update API Routes

#### 7.1 Enhanced Extraction Endpoint
**File**: `app/api/routes/extraction.py`
```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from app.cloud.base import CloudProvider

router = APIRouter(prefix="/api/v1/extract", tags=["extraction"])

class ExtractionRequest(BaseModel):
    provider: Optional[CloudProvider] = None  # None = all providers
    services: Optional[List[str]] = None  # None = all services
    regions: Optional[List[str]] = None  # None = all regions
    filters: Optional[dict] = None
    batch_size: int = 100

@router.post("")
async def start_extraction(request: ExtractionRequest, app_request: Request):
    """Start extraction job for specified cloud provider(s) and services"""
    orchestrator = app_request.app.state.orchestrator
    
    # Validate provider
    if request.provider and request.provider not in [CloudProvider.AWS, CloudProvider.AZURE]:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")
    
    # Filter services by provider if specified
    services_to_extract = request.services
    if request.provider:
        # Get only services for the specified provider
        registry = app_request.app.state.registry
        available_services = [
            e.metadata.service_name
            for e in registry.get_extractors(provider=request.provider)
        ]
        
        if services_to_extract:
            # Validate services exist for provider
            invalid_services = set(services_to_extract) - set(available_services)
            if invalid_services:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid services for {request.provider}: {invalid_services}"
                )
        else:
            services_to_extract = available_services
    
    job_id = await orchestrator.run_extraction(
        services=services_to_extract,
        regions=request.regions,
        filters=request.filters,
        batch_size=request.batch_size,
    )
    
    return {"job_id": job_id, "status": "started"}

@router.get("/providers")
async def list_providers(app_request: Request):
    """List enabled cloud providers"""
    registry = app_request.app.state.registry
    providers = list(set(e.cloud_provider for e in registry.get_extractors()))
    
    return {
        "providers": [p.value for p in providers],
        "total": len(providers)
    }

@router.get("/services")
async def list_services(
    app_request: Request,
    provider: Optional[CloudProvider] = None
):
    """List available services, optionally filtered by provider"""
    registry = app_request.app.state.registry
    extractors = registry.get_extractors(provider=provider)
    
    services_by_provider = {}
    for extractor in extractors:
        provider_key = extractor.cloud_provider.value
        if provider_key not in services_by_provider:
            services_by_provider[provider_key] = []
        services_by_provider[provider_key].append({
            "service": extractor.metadata.service_name,
            "description": extractor.metadata.description,
            "resource_types": extractor.metadata.resource_types,
        })
    
    return services_by_provider
```

### Phase 8: Update Dependencies

#### 8.1 requirements.txt
```txt
# Existing dependencies
fastapi==0.119.1
uvicorn[standard]==0.37.0
pydantic==2.12.0
pydantic-settings==2.11.0
httpx==0.28.1
tenacity==9.1.2
apscheduler==3.11.0
pyyaml==6.0.3
python-multipart==0.0.20
python-json-logger==4.0.0

# AWS
boto3==1.40.57
botocore==1.40.57

# Azure
azure-identity==1.19.0
azure-mgmt-compute==33.0.0
azure-mgmt-network==28.0.0
azure-mgmt-storage==21.2.1
azure-mgmt-web==7.4.0
azure-mgmt-sql==4.0.0
azure-mgmt-containerservice==33.0.0
azure-mgmt-containerinstance==10.1.0
azure-mgmt-keyvault==10.3.1
azure-mgmt-monitor==6.0.2
azure-mgmt-authorization==4.0.0
azure-mgmt-resource==23.2.0

# Development
pytest==8.4.2
pytest-asyncio==1.2.0
pytest-cov==7.0.0
black==25.9.0
flake8==6.1.0
mypy==1.18.2
```

## Migration Strategy

### Backward Compatibility
1. Keep existing AWS-only configuration working
2. Azure is opt-in via `enabled_providers` setting
3. Existing AWS extractors continue to work unchanged

### Gradual Rollout
1. **Phase 1**: Deploy abstraction layer (no breaking changes)
2. **Phase 2**: Add Azure configuration (optional)
3. **Phase 3**: Deploy first Azure extractor (compute)
4. **Phase 4**: Add remaining Azure extractors
5. **Phase 5**: Update API documentation

### Testing Strategy
1. Unit tests for each Azure extractor
2. Integration tests with Azure test subscriptions
3. End-to-end tests with both AWS and Azure
4. Backward compatibility tests for AWS-only setups

## Azure Resource Mapping

### Priority Azure Resources (Phase 1)
1. **Virtual Machines** → `azure:compute:virtual-machine`
2. **Storage Accounts** → `azure:storage:account`
3. **Network Security Groups** → `azure:network:nsg`
4. **App Services** → `azure:web:app-service`
5. **SQL Databases** → `azure:sql:database`

### Additional Azure Resources (Phase 2)
6. **AKS Clusters** → `azure:containerservice:aks`
7. **Key Vaults** → `azure:keyvault:vault`
8. **Function Apps** → `azure:web:function-app`
9. **Load Balancers** → `azure:network:load-balancer`
10. **Application Gateways** → `azure:network:application-gateway`

## Configuration Examples

### Environment Variables (.env)
```bash
# Enable both providers
ENABLED_PROVIDERS=["aws", "azure"]

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1

# Azure Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_DEFAULT_LOCATION=eastus
```

### YAML Configuration (config/production.yaml)
```yaml
enabled_providers:
  - aws
  - azure

aws_default_region: us-east-1
azure_default_location: eastus

transport_type: http
scanner_endpoint_url: https://scanner.example.com

extractors:
  aws:
    ec2:
      max_workers: 10
    s3:
      max_workers: 20
  
  azure:
    compute:
      max_workers: 10
      include_vmss: true
    storage:
      max_workers: 20
      check_blob_encryption: true
```

## Documentation Updates

### README.md
- Add Azure setup instructions
- Document Azure authentication methods
- Add Azure resource type mappings
- Update API examples with Azure

### New Azure-Specific Docs
- **AZURE_SETUP.md**: Detailed Azure setup guide
- **AZURE_PERMISSIONS.md**: Required Azure permissions
- **AZURE_RESOURCES.md**: Supported Azure resource types

## Summary

This plan provides a comprehensive approach to adding Azure support while:
1. **Maintaining backward compatibility** with existing AWS-only deployments
2. **Following the same architectural patterns** used for AWS
3. **Using Azure SDK for Python** (the boto3 equivalent for Azure)
4. **Enabling multi-cloud scanning** with minimal configuration changes
5. **Reusing existing transport and orchestration** layers

The implementation is phased to allow gradual rollout and testing, with clear separation between AWS and Azure code while keeping the core framework cloud-agnostic.
