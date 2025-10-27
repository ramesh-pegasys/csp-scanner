# app/extractors/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import boto3

@dataclass
class ExtractorMetadata:
    """Metadata about the extractor"""
    service_name: str
    version: str
    description: str
    resource_types: List[str]
    supports_regions: bool = True
    requires_pagination: bool = True

class BaseExtractor(ABC):
    """Base class for all AWS resource extractors"""
    
    def __init__(self, session: boto3.Session, config: Dict[str, Any]):
        self.session = session
        self.config = config
        self.metadata = self.get_metadata()
    
    @abstractmethod
    def get_metadata(self) -> ExtractorMetadata:
        """Return metadata about this extractor"""
        pass
    
    @abstractmethod
    async def extract(self, region: Optional[str] = None, 
                     filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extract resources from AWS
        
        Args:
            region: AWS region (None for global services)
            filters: Optional filters to apply
            
        Returns:
            List of resource configurations as dictionaries
        """
        pass
    
    @abstractmethod
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw AWS API response to standardized format
        
        Args:
            raw_data: Raw response from AWS API
            
        Returns:
            Standardized artifact dictionary
        """
        pass
    
    def validate(self, artifact: Dict[str, Any]) -> bool:
        """
        Validate artifact before sending to scanner
        
        Args:
            artifact: Transformed artifact
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['resource_id', 'resource_type', 'service', 'configuration']
        return all(field in artifact for field in required_fields)