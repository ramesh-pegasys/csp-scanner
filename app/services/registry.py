# app/services/registry.py
from typing import Dict, List, Type, Optional
from app.extractors.base import BaseExtractor
from app.core.config import Settings
import logging

logger = logging.getLogger(__name__)

class ExtractorRegistry:
    """Registry for managing extractors"""
    
    def __init__(self, session, config: Settings):
        self.session = session
        self.config = config
        self._extractors: Dict[str, BaseExtractor] = {}
        self._register_default_extractors()
    
    def _register_default_extractors(self):
        """Register all available extractors"""
        from app.extractors.ec2 import EC2Extractor
        from app.extractors.s3 import S3Extractor
        from app.extractors.rds import RDSExtractor
        from app.extractors.lambda_extractor import LambdaExtractor
        from app.extractors.iam import IAMExtractor
        from app.extractors.vpc import VPCExtractor
        from app.extractors.apprunner import AppRunnerExtractor
        from app.extractors.ecs import ECSExtractor
        from app.extractors.eks import EKSExtractor
        from app.extractors.elb import ELBExtractor
        from app.extractors.cloudfront import CloudFrontExtractor
        from app.extractors.apigateway import APIGatewayExtractor
        from app.extractors.kms import KMSExtractor
        
        extractor_classes = [
            EC2Extractor,
            S3Extractor,
            RDSExtractor,
            LambdaExtractor,
            IAMExtractor,
            VPCExtractor,
            AppRunnerExtractor,
            ECSExtractor,
            EKSExtractor,
            ELBExtractor,
            CloudFrontExtractor,
            APIGatewayExtractor,
            KMSExtractor
        ]
        
        for extractor_class in extractor_classes:
            self.register(extractor_class)
    
    def register(self, extractor_class: Type[BaseExtractor]):
        """Register an extractor class"""
        try:
            extractor_config = self.config.extractors.get(
                extractor_class.__name__.replace('Extractor', '').lower(),
                {}
            )
            
            instance = extractor_class(self.session, extractor_config)
            service_name = instance.metadata.service_name
            
            self._extractors[service_name] = instance
            logger.info(f"Registered extractor: {service_name}")
            
        except Exception as e:
            logger.error(f"Failed to register {extractor_class.__name__}: {e}")
    
    def get(self, service_name: str) -> Optional[BaseExtractor]:
        """Get extractor by service name"""
        return self._extractors.get(service_name)
    
    def get_extractors(self, services: Optional[List[str]] = None) -> List[BaseExtractor]:
        """Get multiple extractors"""
        if services is None:
            return list(self._extractors.values())
        
        return [
            self._extractors[service]
            for service in services
            if service in self._extractors
        ]
    
    def list_services(self) -> List[str]:
        """List all registered services"""
        return list(self._extractors.keys())