# app/cloud/azure_session.py
"""
Azure session wrapper implementing CloudSession protocol.
"""

from typing import Any, Optional, Dict, List
from app.cloud.base import CloudSession, CloudProvider
import logging

logger = logging.getLogger(__name__)


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
        """
        Initialize Azure session wrapper.
        
        Args:
            subscription_id: Azure subscription ID
            credential: Azure credential object (if None, will create from other params)
            tenant_id: Azure tenant ID (for service principal auth)
            client_id: Azure client ID (for service principal auth)
            client_secret: Azure client secret (for service principal auth)
        """
        self.subscription_id = subscription_id
        self._clients: Dict[str, Any] = {}
        self._regions_cache: Optional[List[str]] = None
        
        # Initialize credential
        if credential:
            self.credential = credential
        elif tenant_id and client_id and client_secret:
            # Use service principal authentication
            try:
                from azure.identity import ClientSecretCredential  # type: ignore[import-untyped]
                self.credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                )
                logger.info("Initialized Azure session with service principal")
            except ImportError:
                logger.error("azure-identity not installed. Please install: pip install azure-identity")
                raise
        else:
            # Use default credential chain (environment vars, managed identity, Azure CLI, etc.)
            try:
                from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]
                self.credential = DefaultAzureCredential()
                logger.info("Initialized Azure session with DefaultAzureCredential")
            except ImportError:
                logger.error("azure-identity not installed. Please install: pip install azure-identity")
                raise
    
    @property
    def provider(self) -> CloudProvider:
        """Return Azure as the cloud provider"""
        return CloudProvider.AZURE
    
    def get_client(self, service: str, region: Optional[str] = None) -> Any:
        """
        Get Azure management client for a service.
        
        Args:
            service: Service name (e.g., 'compute', 'network', 'storage')
            region: Azure location (not used, kept for protocol compatibility)
        
        Returns:
            Azure management client instance
        
        Service mapping:
            - 'compute' -> ComputeManagementClient
            - 'network' -> NetworkManagementClient
            - 'storage' -> StorageManagementClient
            - 'web' -> WebSiteManagementClient
            - 'sql' -> SqlManagementClient
            - 'containerservice' -> ContainerServiceClient
            - 'keyvault' -> KeyVaultManagementClient
            - 'authorization' -> AuthorizationManagementClient
        """
        cache_key = f"{service}:{region}" if region else service
        
        if cache_key not in self._clients:
            self._clients[cache_key] = self._create_client(service)
        
        return self._clients[cache_key]
    
    def _create_client(self, service: str) -> Any:
        """Create appropriate Azure management client"""
        try:
            if service == "compute":
                from azure.mgmt.compute import ComputeManagementClient  # type: ignore[import-untyped]
                return ComputeManagementClient(self.credential, self.subscription_id)
            
            elif service == "network":
                from azure.mgmt.network import NetworkManagementClient  # type: ignore[import-untyped]
                return NetworkManagementClient(self.credential, self.subscription_id)
            
            elif service == "storage":
                from azure.mgmt.storage import StorageManagementClient  # type: ignore[import-untyped]
                return StorageManagementClient(self.credential, self.subscription_id)
            
            elif service == "web":
                from azure.mgmt.web import WebSiteManagementClient  # type: ignore[import-untyped]
                return WebSiteManagementClient(self.credential, self.subscription_id)
            
            elif service == "sql":
                from azure.mgmt.sql import SqlManagementClient  # type: ignore[import-untyped]
                return SqlManagementClient(self.credential, self.subscription_id)
            
            elif service == "containerservice":
                from azure.mgmt.containerservice import ContainerServiceClient  # type: ignore[import-untyped]
                return ContainerServiceClient(self.credential, self.subscription_id)
            
            elif service == "keyvault":
                from azure.mgmt.keyvault import KeyVaultManagementClient  # type: ignore[import-untyped]
                return KeyVaultManagementClient(self.credential, self.subscription_id)
            
            elif service == "authorization":
                from azure.mgmt.authorization import AuthorizationManagementClient  # type: ignore[import-untyped]
                return AuthorizationManagementClient(self.credential, self.subscription_id)
            
            elif service == "resource":
                from azure.mgmt.resource import ResourceManagementClient  # type: ignore[import-untyped]
                return ResourceManagementClient(self.credential, self.subscription_id)
            
            else:
                raise ValueError(f"Unknown Azure service: {service}")
        
        except ImportError as e:
            logger.error(f"Failed to import Azure SDK for {service}: {e}")
            logger.error(f"Please install: pip install azure-mgmt-{service}")
            raise
    
    def list_regions(self) -> List[str]:
        """
        List available Azure locations.
        
        Returns:
            List of Azure location names
        """
        if self._regions_cache is not None:
            return self._regions_cache
        
        try:
            from azure.mgmt.resource import SubscriptionClient  # type: ignore[import-untyped]
            
            sub_client = SubscriptionClient(self.credential)
            locations = sub_client.subscriptions.list_locations(self.subscription_id)
            self._regions_cache = [loc.name for loc in locations]
            return self._regions_cache
        
        except Exception as e:
            logger.error(f"Failed to list Azure locations: {e}")
            # Return a default set of locations
            return [
                "eastus",
                "eastus2",
                "westus",
                "westus2",
                "centralus",
                "northeurope",
                "westeurope",
                "uksouth",
                "southeastasia",
                "australiaeast",
            ]
