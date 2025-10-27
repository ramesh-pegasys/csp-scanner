# app/extractors/s3.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)

class S3Extractor(BaseExtractor):
    """Extractor for S3 buckets and related resources"""
    
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="s3",
            version="1.0.0",
            description="Extracts S3 buckets and their configurations",
            resource_types=["bucket"],
            supports_regions=True,  # S3 operations require region specification
            requires_pagination=False  # list_buckets returns all buckets
        )
    
    async def extract(self, region: Optional[str] = None, 
                     filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract S3 resources"""
        # S3 buckets are global, but we need a region for the client
        # Use us-east-1 as default since list_buckets works from any region
        s3_region = region or 'us-east-1'
        
        artifacts = []
        
        # Use ThreadPoolExecutor for I/O-bound boto3 calls
        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor, 
                    self._extract_buckets, 
                    s3_region, 
                    filters
                )
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and handle exceptions
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"S3 extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))
        
        return artifacts
    
    def _extract_buckets(self, region: str, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract S3 buckets"""
        artifacts = []
        
        s3_client = self.session.client('s3', region_name=region)
        
        try:
            # List all buckets (this operation works from any region)
            response = s3_client.list_buckets()
            
            for bucket in response['Buckets']:
                try:
                    bucket_name = bucket['Name']
                    
                    # Get bucket location (region)
                    location_response = s3_client.get_bucket_location(Bucket=bucket_name)
                    bucket_region = location_response.get('LocationConstraint', 'us-east-1')
                    
                    # If bucket_region is None, it's us-east-1
                    if bucket_region is None:
                        bucket_region = 'us-east-1'
                    
                    # Get bucket versioning
                    versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
                    
                    # Get bucket encryption
                    try:
                        encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                        encryption_config = encryption.get('ServerSideEncryptionConfiguration', {})
                    except Exception:
                        # No encryption configured
                        encryption_config = {}
                    
                    # Get bucket policy
                    try:
                        policy = s3_client.get_bucket_policy(Bucket=bucket_name)
                        bucket_policy = policy.get('Policy', {})
                    except Exception:
                        # No bucket policy exists or access denied
                        bucket_policy = {}
                    
                    # Get bucket ACL
                    acl = s3_client.get_bucket_acl(Bucket=bucket_name)
                    
                    # Get bucket tags
                    try:
                        tags_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
                        tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
                    except Exception:
                        # No tags exist on bucket
                        tags = {}
                    
                    bucket_data = {
                        **bucket,
                        'region': bucket_region,
                        'versioning': versioning.get('Status'),
                        'encryption': encryption_config,
                        'policy': bucket_policy,
                        'acl': acl,
                        'tags': tags,
                    }
                    
                    artifact = self.transform({
                        'resource': bucket_data,
                        'resource_type': 'bucket'
                    })
                    
                    if self.validate(artifact):
                        artifacts.append(artifact)
                        
                except Exception as e:
                    logger.error(f"Failed to extract bucket {bucket.get('Name')}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to list S3 buckets: {e}")
        
        return artifacts
    
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform S3 resource to standardized format"""
        resource = raw_data['resource']
        resource_type = raw_data['resource_type']
        
        if resource_type == 'bucket':
            return {
                'resource_id': resource['Name'],
                'resource_type': 's3:bucket',
                'service': 's3',
                'region': resource.get('region'),
                'account_id': None,  # S3 doesn't expose account ID directly
                'configuration': {
                    'bucket_name': resource['Name'],
                    'creation_date': resource.get('CreationDate'),
                    'region': resource.get('region'),
                    'versioning_enabled': resource.get('versioning') == 'Enabled',
                    'encryption': resource.get('encryption', {}),
                    'policy': resource.get('policy', {}),
                    'acl': resource.get('acl', {}),
                    'tags': resource.get('tags', {}),
                },
                'raw': resource
            }
        
        return {}
