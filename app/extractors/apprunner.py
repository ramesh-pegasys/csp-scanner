# app/extractors/apprunner.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)

class AppRunnerExtractor(BaseExtractor):
    """Extractor for AWS App Runner services"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="apprunner",
            version="1.0.0",
            description="Extracts App Runner services and configurations",
            resource_types=["service", "connection"],
            supports_regions=True,
            requires_pagination=True
        )

    async def extract(self, region: Optional[str] = None,
                     filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract App Runner resources"""
        # Use us-east-1 as default region if none provided
        region = region or 'us-east-1'

        artifacts = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_services, region, filters),
                loop.run_in_executor(executor, self._extract_connections, region, filters)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"App Runner extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_services(self, region: str, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract App Runner services"""
        artifacts = []
        client = self.session.client('apprunner', region_name=region)

        try:
            # App Runner list_services doesn't support pagination
            next_token = None
            while True:
                if next_token:
                    response = client.list_services(NextToken=next_token)
                else:
                    response = client.list_services()
                
                for service in response.get('ServiceSummaryList', []):
                    try:
                        # Get detailed service information
                        service_arn = service['ServiceArn']
                        details = client.describe_service(ServiceArn=service_arn)

                        artifact = self.transform({
                            'resource': details['Service'],
                            'resource_type': 'service',
                            'region': region
                        })

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(f"Failed to extract App Runner service {service.get('ServiceName')}: {e}")
                
                next_token = response.get('NextToken')
                if not next_token:
                    break

        except Exception as e:
            logger.error(f"Failed to list App Runner services: {e}")

        return artifacts

    def _extract_connections(self, region: str, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract App Runner connections"""
        artifacts = []
        client = self.session.client('apprunner', region_name=region)

        try:
            # App Runner list_connections doesn't support pagination
            next_token = None
            while True:
                if next_token:
                    response = client.list_connections(NextToken=next_token)
                else:
                    response = client.list_connections()
                
                for connection in response.get('ConnectionSummaryList', []):
                    try:
                        # Get detailed connection information
                        connection_arn = connection['ConnectionArn']
                        details = client.describe_connection(ConnectionArn=connection_arn)

                        artifact = self.transform({
                            'resource': details['Connection'],
                            'resource_type': 'connection',
                            'region': region
                        })

                        if self.validate(artifact):
                            artifacts.append(artifact)

                    except Exception as e:
                        logger.error(f"Failed to extract App Runner connection {connection.get('ConnectionName')}: {e}")
                
                next_token = response.get('NextToken')
                if not next_token:
                    break

        except Exception as e:
            logger.error(f"Failed to list App Runner connections: {e}")

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform App Runner resource to standardized format"""
        resource = raw_data['resource']
        resource_type = raw_data['resource_type']
        region = raw_data.get('region')

        if resource_type == 'service':
            return {
                'resource_id': resource['ServiceName'],
                'resource_type': 'apprunner:service',
                'service': 'apprunner',
                'region': region,
                'account_id': None,
                'configuration': {
                    'service_name': resource['ServiceName'],
                    'service_arn': resource['ServiceArn'],
                    'service_url': resource.get('ServiceUrl'),
                    'status': resource['Status'],
                    'source_configuration': resource.get('SourceConfiguration', {}),
                    'instance_configuration': resource.get('InstanceConfiguration', {}),
                    'health_check_configuration': resource.get('HealthCheckConfiguration', {}),
                    'auto_scaling_configuration': resource.get('AutoScalingConfigurationSummary', {}),
                    'network_configuration': resource.get('NetworkConfiguration', {}),
                    'observability_configuration': resource.get('ObservabilityConfiguration', {}),
                    'tags': resource.get('Tags', {}),
                },
                'raw': resource
            }

        elif resource_type == 'connection':
            return {
                'resource_id': resource['ConnectionName'],
                'resource_type': 'apprunner:connection',
                'service': 'apprunner',
                'region': region,
                'account_id': None,
                'configuration': {
                    'connection_name': resource['ConnectionName'],
                    'connection_arn': resource['ConnectionArn'],
                    'provider_type': resource['ProviderType'],
                    'status': resource['Status'],
                    'created_at': resource.get('CreatedAt'),
                    'tags': resource.get('Tags', {}),
                },
                'raw': resource
            }

        return {}