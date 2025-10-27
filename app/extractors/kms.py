# app/extractors/kms.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)

class KMSExtractor(BaseExtractor):
    """Extractor for AWS Key Management Service resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="kms",
            version="1.0.0",
            description="Extracts KMS keys, aliases, and grants",
            resource_types=["key", "alias", "grant"],
            supports_regions=True,
            requires_pagination=True
        )

    async def extract(self, region: Optional[str] = None,
                     filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract KMS resources"""
        # Use us-east-1 as default region if none provided
        region = region or 'us-east-1'

        artifacts = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_keys, region, filters),
                loop.run_in_executor(executor, self._extract_aliases, region, filters)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"KMS extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_keys(self, region: str, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract KMS keys"""
        artifacts = []
        client = self.session.client('kms', region_name=region)

        try:
            paginator = client.get_paginator('list_keys')
            for page in paginator.paginate():
                for key in page['Keys']:
                    try:
                        key_id = key['KeyId']

                        # Get detailed key information
                        key_response = client.describe_key(KeyId=key_id)
                        key_metadata = key_response['KeyMetadata']

                        # Get key policy
                        policy = {}
                        try:
                            policy_response = client.get_key_policy(KeyId=key_id, PolicyName='default')
                            policy = policy_response['Policy']
                        except Exception as e:
                            logger.warning(f"Failed to get policy for key {key_id}: {e}")

                        # Get key rotation status
                        rotation_status = {}
                        try:
                            rotation_response = client.get_key_rotation_status(KeyId=key_id)
                            rotation_status = {
                                'key_rotation_enabled': rotation_response.get('KeyRotationEnabled', False)
                            }
                        except Exception as e:
                            logger.warning(f"Failed to get rotation status for key {key_id}: {e}")

                        # Get grants for this key
                        grants = []
                        try:
                            grants_response = client.list_grants(KeyId=key_id)
                            grants = grants_response['Grants']
                        except Exception as e:
                            logger.warning(f"Failed to get grants for key {key_id}: {e}")

                        # Get tags
                        tags = []
                        try:
                            tags_response = client.list_resource_tags(KeyId=key_id)
                            tags = tags_response['Tags']
                        except Exception as e:
                            logger.warning(f"Failed to get tags for key {key_id}: {e}")

                        key_data = {
                            **key_metadata,
                            'policy': policy,
                            'rotation_status': rotation_status,
                            'grants': grants,
                            'tags': tags
                        }

                        # Extract the key
                        key_artifact = self.transform({
                            'resource': key_data,
                            'resource_type': 'key',
                            'region': region
                        })
                        if self.validate(key_artifact):
                            artifacts.append(key_artifact)

                        # Extract grants as separate artifacts
                        for grant in grants:
                            grant_artifact = self.transform({
                                'resource': grant,
                                'resource_type': 'grant',
                                'region': region,
                                'key_id': key_id
                            })
                            if self.validate(grant_artifact):
                                artifacts.append(grant_artifact)

                    except Exception as e:
                        logger.error(f"Failed to extract KMS key {key.get('KeyId')}: {e}")

        except Exception as e:
            logger.error(f"Failed to list KMS keys: {e}")

        return artifacts

    def _extract_aliases(self, region: str, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract KMS aliases"""
        artifacts = []
        client = self.session.client('kms', region_name=region)

        try:
            paginator = client.get_paginator('list_aliases')
            for page in paginator.paginate():
                for alias in page['Aliases']:
                    try:
                        # Skip AWS managed aliases (they start with 'alias/aws/')
                        if alias['AliasName'].startswith('alias/aws/'):
                            continue

                        alias_artifact = self.transform({
                            'resource': alias,
                            'resource_type': 'alias',
                            'region': region
                        })

                        if self.validate(alias_artifact):
                            artifacts.append(alias_artifact)

                    except Exception as e:
                        logger.error(f"Failed to extract KMS alias {alias.get('AliasName')}: {e}")

        except Exception as e:
            logger.error(f"Failed to list KMS aliases: {e}")

        return artifacts

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform KMS resource to standardized format"""
        resource = raw_data['resource']
        resource_type = raw_data['resource_type']
        region = raw_data.get('region')

        if resource_type == 'key':
            return {
                'resource_id': resource['KeyId'],
                'resource_type': 'kms:key',
                'service': 'kms',
                'region': region,
                'account_id': None,
                'configuration': {
                    'key_id': resource['KeyId'],
                    'arn': resource.get('Arn'),
                    'creation_date': resource.get('CreationDate'),
                    'key_manager': resource.get('KeyManager'),
                    'key_state': resource.get('KeyState'),
                    'key_usage': resource.get('KeyUsage'),
                    'key_spec': resource.get('KeySpec'),
                    'customer_master_key_spec': resource.get('CustomerMasterKeySpec'),
                    'encryption_algorithms': resource.get('EncryptionAlgorithms', []),
                    'signing_algorithms': resource.get('SigningAlgorithms', []),
                    'key_rotation_status': resource.get('rotation_status', {}),
                    'policy': resource.get('policy', {}),
                    'description': resource.get('Description'),
                    'origin': resource.get('Origin'),
                    'valid_to': resource.get('ValidTo'),
                    'tags': resource.get('tags', []),
                },
                'raw': resource
            }

        elif resource_type == 'alias':
            return {
                'resource_id': resource['AliasName'],
                'resource_type': 'kms:alias',
                'service': 'kms',
                'region': region,
                'account_id': None,
                'configuration': {
                    'alias_name': resource['AliasName'],
                    'alias_arn': resource.get('AliasArn'),
                    'target_key_id': resource.get('TargetKeyId'),
                    'creation_date': resource.get('CreationDate'),
                    'last_updated_date': resource.get('LastUpdatedDate'),
                },
                'raw': resource
            }

        elif resource_type == 'grant':
            return {
                'resource_id': f"{raw_data.get('key_id', 'unknown')}/{resource['KeyId']}/{resource.get('GrantId', 'unknown')}",
                'resource_type': 'kms:grant',
                'service': 'kms',
                'region': region,
                'account_id': None,
                'configuration': {
                    'grant_id': resource.get('GrantId'),
                    'key_id': resource.get('KeyId'),
                    'grantee_principal': resource.get('GranteePrincipal'),
                    'retiring_principal': resource.get('RetiringPrincipal'),
                    'operations': resource.get('Operations', []),
                    'constraints': resource.get('Constraints', {}),
                    'creation_date': resource.get('CreationDate'),
                    'grant_token': resource.get('GrantToken'),
                },
                'raw': resource
            }

        return {}