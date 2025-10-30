# app/extractors/rds.py
from typing import List, Dict, Any, Optional, cast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class RDSExtractor(BaseExtractor):
    """Extractor for RDS database instances and related resources"""

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="rds",
            version="1.0.0",
            description="Extracts RDS DB instances, clusters, and snapshots",
            resource_types=[
                "db-instance",
                "db-cluster",
                "db-snapshot",
                "db-cluster-snapshot",
            ],
            supports_regions=True,
            requires_pagination=True,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract RDS resources"""
        regions = [region] if region else self._get_all_regions()

        artifacts = []

        # Use ThreadPoolExecutor for I/O-bound boto3 calls
        with ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        ) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._extract_region, reg, filters)
                for reg in regions
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and handle exceptions
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Extraction error: {result}")
            else:
                artifacts.extend(cast(List[Dict[str, Any]], result))

        return artifacts

    def _extract_region(
        self, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract RDS resources from a specific region"""
        rds_client = self._get_client("rds", region=region)
        artifacts = []

        # Extract DB instances
        try:
            db_instances = self._extract_db_instances(rds_client, region, filters)
            artifacts.extend(db_instances)
        except Exception as e:
            logger.error(f"Failed to extract DB instances in {region}: {e}")

        # Extract DB clusters
        try:
            db_clusters = self._extract_db_clusters(rds_client, region, filters)
            artifacts.extend(db_clusters)
        except Exception as e:
            logger.error(f"Failed to extract DB clusters in {region}: {e}")

        # Extract DB snapshots
        try:
            db_snapshots = self._extract_db_snapshots(rds_client, region, filters)
            artifacts.extend(db_snapshots)
        except Exception as e:
            logger.error(f"Failed to extract DB snapshots in {region}: {e}")

        # Extract DB cluster snapshots
        try:
            db_cluster_snapshots = self._extract_db_cluster_snapshots(
                rds_client, region, filters
            )
            artifacts.extend(db_cluster_snapshots)
        except Exception as e:
            logger.error(f"Failed to extract DB cluster snapshots in {region}: {e}")

        return artifacts

    def _extract_db_instances(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract RDS DB instances"""
        artifacts = []

        paginator = client.get_paginator("describe_db_instances")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for db_instance in page["DBInstances"]:
                artifact = self.transform(
                    {
                        "resource": db_instance,
                        "region": region,
                        "resource_type": "db-instance",
                    }
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_db_clusters(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract RDS DB clusters"""
        artifacts = []

        paginator = client.get_paginator("describe_db_clusters")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for db_cluster in page["DBClusters"]:
                artifact = self.transform(
                    {
                        "resource": db_cluster,
                        "region": region,
                        "resource_type": "db-cluster",
                    }
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_db_snapshots(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract RDS DB snapshots"""
        artifacts = []

        paginator = client.get_paginator("describe_db_snapshots")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for snapshot in page["DBSnapshots"]:
                artifact = self.transform(
                    {
                        "resource": snapshot,
                        "region": region,
                        "resource_type": "db-snapshot",
                    }
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _extract_db_cluster_snapshots(
        self, client, region: str, filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract RDS DB cluster snapshots"""
        artifacts = []

        paginator = client.get_paginator("describe_db_cluster_snapshots")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for snapshot in page["DBClusterSnapshots"]:
                artifact = self.transform(
                    {
                        "resource": snapshot,
                        "region": region,
                        "resource_type": "db-cluster-snapshot",
                    }
                )
                if self.validate(artifact):
                    artifacts.append(artifact)

        return artifacts

    def _get_all_regions(self) -> List[str]:
        """Get all enabled regions (using EC2 as reference)"""
        ec2_client = self._get_client("ec2")
        response = ec2_client.describe_regions(AllRegions=False)
        return [region["RegionName"] for region in response["Regions"]]

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform RDS resource to standardized format"""
        resource = raw_data["resource"]
        region = raw_data["region"]
        resource_type = raw_data["resource_type"]

        if resource_type == "db-instance":
            return {
                "resource_id": resource["DBInstanceIdentifier"],
                "resource_type": "rds:db-instance",
                "service": "rds",
                "region": region,
                "account_id": None,  # RDS doesn't include account ID in response
                "configuration": {
                    "db_instance_identifier": resource["DBInstanceIdentifier"],
                    "db_instance_class": resource.get("DBInstanceClass"),
                    "engine": resource.get("Engine"),
                    "engine_version": resource.get("EngineVersion"),
                    "db_instance_status": resource.get("DBInstanceStatus"),
                    "master_username": resource.get("MasterUsername"),
                    "allocated_storage": resource.get("AllocatedStorage"),
                    "instance_create_time": resource.get("InstanceCreateTime"),
                    "preferred_backup_window": resource.get("PreferredBackupWindow"),
                    "backup_retention_period": resource.get("BackupRetentionPeriod"),
                    "availability_zone": resource.get("AvailabilityZone"),
                    "preferred_maintenance_window": resource.get(
                        "PreferredMaintenanceWindow"
                    ),
                    "multi_az": resource.get("MultiAZ"),
                    "iops": resource.get("Iops"),
                    "secondary_availability_zone": resource.get(
                        "SecondaryAvailabilityZone"
                    ),
                    "publicly_accessible": resource.get("PubliclyAccessible"),
                    "storage_type": resource.get("StorageType"),
                    "tde_credential_arn": resource.get("TdeCredentialArn"),
                    "db_instance_arn": resource.get("DBInstanceArn"),
                    "tag_list": resource.get("TagList", []),
                    "vpc_security_groups": resource.get("VpcSecurityGroups", []),
                    "db_subnet_group": resource.get("DBSubnetGroup"),
                    "pending_modified_values": resource.get("PendingModifiedValues"),
                    "latest_restorable_time": resource.get("LatestRestorableTime"),
                    "auto_minor_version_upgrade": resource.get(
                        "AutoMinorVersionUpgrade"
                    ),
                    "read_replica_db_instance_identifiers": resource.get(
                        "ReadReplicaDBInstanceIdentifiers", []
                    ),
                    "read_replica_source_db_instance_identifier": resource.get(
                        "ReadReplicaSourceDBInstanceIdentifier"
                    ),
                    "replica_mode": resource.get("ReplicaMode"),
                    "license_model": resource.get("LicenseModel"),
                    "option_group_memberships": resource.get(
                        "OptionGroupMemberships", []
                    ),
                    "character_set_name": resource.get("CharacterSetName"),
                    "nchar_character_set_name": resource.get("NcharCharacterSetName"),
                    "default_timezone": resource.get("DefaultTimezone"),
                    "db_name": resource.get("DBName"),
                    "creation_date": resource.get("InstanceCreateTime"),
                },
                "raw": resource,  # Include full resource for comprehensive scanning
            }
        elif resource_type == "db-cluster":
            return {
                "resource_id": resource["DBClusterIdentifier"],
                "resource_type": "rds:db-cluster",
                "service": "rds",
                "region": region,
                "account_id": None,
                "configuration": {
                    "db_cluster_identifier": resource["DBClusterIdentifier"],
                    "engine": resource.get("Engine"),
                    "engine_version": resource.get("EngineVersion"),
                    "status": resource.get("Status"),
                    "master_username": resource.get("MasterUsername"),
                    "database_name": resource.get("DatabaseName"),
                    "creation_time": resource.get("ClusterCreateTime"),
                    "backup_retention_period": resource.get("BackupRetentionPeriod"),
                    "preferred_backup_window": resource.get("PreferredBackupWindow"),
                    "preferred_maintenance_window": resource.get(
                        "PreferredMaintenanceWindow"
                    ),
                    "port": resource.get("Port"),
                    "multi_az": resource.get("MultiAZ"),
                    "engine_mode": resource.get("EngineMode"),
                    "scaling_configuration": resource.get("ScalingConfiguration"),
                    "deletion_protection": resource.get("DeletionProtection"),
                    "http_endpoint_enabled": resource.get("HttpEndpointEnabled"),
                    "activity_stream_mode": resource.get("ActivityStreamMode"),
                    "activity_stream_status": resource.get("ActivityStreamStatus"),
                    "copy_tags_to_snapshot": resource.get("CopyTagsToSnapshot"),
                    "cross_account_clone": resource.get("CrossAccountClone"),
                    "domain_memberships": resource.get("DomainMemberships", []),
                    "tag_list": resource.get("TagList", []),
                    "global_cluster_identifier": resource.get(
                        "GlobalClusterIdentifier"
                    ),
                    "reader_endpoint": resource.get("ReaderEndpoint"),
                    "custom_endpoints": resource.get("CustomEndpoints", []),
                    "failover_priority": resource.get("FailoverPriority"),
                    "promoted_to_global_cluster": resource.get(
                        "PromotedToGlobalCluster"
                    ),
                },
                "raw": resource,
            }
        elif resource_type == "db-snapshot":
            return {
                "resource_id": resource["DBSnapshotIdentifier"],
                "resource_type": "rds:db-snapshot",
                "service": "rds",
                "region": region,
                "account_id": None,
                "configuration": {
                    "db_snapshot_identifier": resource["DBSnapshotIdentifier"],
                    "db_instance_identifier": resource.get("DBInstanceIdentifier"),
                    "snapshot_create_time": resource.get("SnapshotCreateTime"),
                    "engine": resource.get("Engine"),
                    "allocated_storage": resource.get("AllocatedStorage"),
                    "status": resource.get("Status"),
                    "port": resource.get("Port"),
                    "availability_zone": resource.get("AvailabilityZone"),
                    "vpc_id": resource.get("VpcId"),
                    "instance_create_time": resource.get("InstanceCreateTime"),
                    "master_username": resource.get("MasterUsername"),
                    "engine_version": resource.get("EngineVersion"),
                    "license_model": resource.get("LicenseModel"),
                    "snapshot_type": resource.get("SnapshotType"),
                    "iops": resource.get("Iops"),
                    "option_group_name": resource.get("OptionGroupName"),
                    "percent_progress": resource.get("PercentProgress"),
                    "source_region": resource.get("SourceRegion"),
                    "source_db_snapshot_identifier": resource.get(
                        "SourceDBSnapshotIdentifier"
                    ),
                    "storage_type": resource.get("StorageType"),
                    "tde_credential_arn": resource.get("TdeCredentialArn"),
                    "encrypted": resource.get("Encrypted"),
                    "kms_key_id": resource.get("KmsKeyId"),
                    "db_snapshot_arn": resource.get("DBSnapshotArn"),
                    "timezone": resource.get("Timezone"),
                    "iam_database_authentication_enabled": resource.get(
                        "IAMDatabaseAuthenticationEnabled"
                    ),
                    "processor_features": resource.get("ProcessorFeatures", []),
                    "tag_list": resource.get("TagList", []),
                },
                "raw": resource,
            }
        elif resource_type == "db-cluster-snapshot":
            return {
                "resource_id": resource["DBClusterSnapshotIdentifier"],
                "resource_type": "rds:db-cluster-snapshot",
                "service": "rds",
                "region": region,
                "account_id": None,
                "configuration": {
                    "db_cluster_snapshot_identifier": resource[
                        "DBClusterSnapshotIdentifier"
                    ],
                    "db_cluster_identifier": resource.get("DBClusterIdentifier"),
                    "snapshot_create_time": resource.get("SnapshotCreateTime"),
                    "engine": resource.get("Engine"),
                    "status": resource.get("Status"),
                    "port": resource.get("Port"),
                    "vpc_id": resource.get("VpcId"),
                    "cluster_create_time": resource.get("ClusterCreateTime"),
                    "master_username": resource.get("MasterUsername"),
                    "engine_version": resource.get("EngineVersion"),
                    "license_model": resource.get("LicenseModel"),
                    "snapshot_type": resource.get("SnapshotType"),
                    "percent_progress": resource.get("PercentProgress"),
                    "storage_encrypted": resource.get("StorageEncrypted"),
                    "kms_key_id": resource.get("KmsKeyId"),
                    "db_cluster_snapshot_arn": resource.get("DBClusterSnapshotArn"),
                    "source_db_cluster_snapshot_arn": resource.get(
                        "SourceDBClusterSnapshotArn"
                    ),
                    "iam_database_authentication_enabled": resource.get(
                        "IAMDatabaseAuthenticationEnabled"
                    ),
                    "tag_list": resource.get("TagList", []),
                },
                "raw": resource,
            }

        return {}
