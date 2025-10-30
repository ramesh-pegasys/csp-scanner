"""Additional extractor tests that exercise data transformation paths without touching AWS.

These tests use lightweight mocks to mimic boto3 clients so we can execute the
extractor helpers and cover the rich transformation logic in app/extractors.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from app.extractors.aws.apigateway import APIGatewayExtractor
from app.extractors.aws.apprunner import AppRunnerExtractor
from app.extractors.aws.cloudfront import CloudFrontExtractor
from app.extractors.aws.ec2 import EC2Extractor
from app.extractors.aws.ecs import ECSExtractor
from app.extractors.aws.eks import EKSExtractor
from app.extractors.aws.elb import ELBExtractor
from app.extractors.aws.iam import IAMExtractor
from app.extractors.aws.kms import KMSExtractor
from app.extractors.aws.lambda_extractor import LambdaExtractor
from app.extractors.aws.rds import RDSExtractor
from app.extractors.aws.s3 import S3Extractor
from app.extractors.aws.vpc import VPCExtractor


class DummyPaginator:
    """Simple paginator mimic that yields the supplied pages for every call."""

    def __init__(self, pages):
        self._pages = pages

    def paginate(self, **kwargs):
        for page in self._pages:
            yield page


def make_session_with_clients(client_map):
    """Return a session mock that dispatches to the provided client_map."""

    session = Mock()

    def _client(service_name, region_name=None):
        key = (service_name, region_name)
        if key in client_map:
            return client_map[key]
        if service_name in client_map:
            return client_map[service_name]
        raise KeyError(f"No mock client for {service_name!r} / {region_name!r}")

    session.get_client = Mock(side_effect=_client)
    session.client = Mock(side_effect=_client)
    return session


def test_s3_extractor_collects_bucket_artifacts():
    extractor_cls = S3Extractor
    s3_client = Mock()
    s3_client.list_buckets.return_value = {
        "Buckets": [{"Name": "bucket-1", "CreationDate": datetime(2024, 1, 1)}]
    }
    s3_client.get_bucket_location.return_value = {"LocationConstraint": None}
    s3_client.get_bucket_versioning.return_value = {"Status": "Enabled"}
    s3_client.get_bucket_encryption.side_effect = Exception("no encryption configured")
    s3_client.get_bucket_policy.side_effect = Exception("no policy")
    s3_client.get_bucket_acl.return_value = {"Grants": []}
    s3_client.get_bucket_tagging.side_effect = Exception("no tags")

    session = make_session_with_clients({("s3", "us-west-2"): s3_client})

    extractor = extractor_cls(session, {})
    artifacts = extractor._extract_buckets("us-west-2", None)

    assert len(artifacts) == 1
    bucket = artifacts[0]
    assert bucket["cloud_provider"] == "aws"
    assert bucket["resource_type"] == "aws:s3:bucket"
    assert bucket["metadata"]["resource_id"] == "bucket-1"
    assert bucket["metadata"]["region"] == "us-east-1"
    assert bucket["configuration"]["bucket_name"] == "bucket-1"
    assert bucket["configuration"]["versioning_enabled"] is True
    # Error branches fall back to empty structures
    assert bucket["configuration"]["encryption"] == {}
    assert bucket["metadata"]["labels"] == {}


def test_apigateway_extractor_builds_all_artifact_types():
    api_client = Mock()
    rest_api_page = {"items": [{"id": "api1", "name": "demo", "createdDate": "now"}]}
    resource_page = {
        "items": [
            {
                "id": "res1",
                "path": "/",
                "resourceMethods": {
                    "GET": {
                        "httpMethod": "GET",
                        "authorizationType": "NONE",
                        "apiKeyRequired": False,
                        "requestModels": {},
                        "requestParameters": {},
                        "methodResponses": {},
                        "methodIntegration": {},
                    }
                },
            }
        ]
    }
    deployment_page = {
        "items": [{"id": "dep1", "description": "desc", "createdDate": "2024-01-01"}]
    }
    paginators = {
        "get_rest_apis": DummyPaginator([rest_api_page]),
        "get_resources": DummyPaginator([resource_page]),
        "get_deployments": DummyPaginator([deployment_page]),
    }
    api_client.get_paginator.side_effect = lambda name: paginators[name]
    api_client.get_stages.return_value = {
        "item": [
            {
                "stageName": "prod",
                "deploymentId": "dep1",
                "description": "prod stage",
                "variables": {},
            }
        ]
    }

    session = make_session_with_clients({("apigateway", "us-east-1"): api_client})
    extractor = APIGatewayExtractor(session, {})
    extractor.validate = lambda _: True

    artifacts = extractor._extract_rest_apis("us-east-1", None)

    types = {item["resource_type"] for item in artifacts}
    assert types == {
        "apigateway:rest-api",
        "apigateway:resource",
        "apigateway:method",
        "apigateway:deployment",
        "apigateway:stage",
    }


def test_apprunner_extractor_walks_services_and_connections():
    apprunner_client = Mock()

    service_pages = [
        {
            "ServiceSummaryList": [{"ServiceArn": "arn1", "ServiceName": "svc1"}],
            "NextToken": "token",
        },
        {"ServiceSummaryList": [{"ServiceArn": "arn2", "ServiceName": "svc2"}]},
    ]

    def list_services(NextToken=None):
        return service_pages[1] if NextToken else service_pages[0]

    apprunner_client.list_services.side_effect = list_services
    apprunner_client.describe_service.side_effect = [
        {
            "Service": {
                "ServiceName": "svc1",
                "ServiceArn": "arn1",
                "Status": "ACTIVE",
                "Tags": {"team": "security"},
            }
        },
        {
            "Service": {
                "ServiceName": "svc2",
                "ServiceArn": "arn2",
                "Status": "INACTIVE",
                "Tags": {},
            }
        },
    ]

    connection_pages = [
        {
            "ConnectionSummaryList": [
                {"ConnectionArn": "conn-arn", "ConnectionName": "github"}
            ],
            "NextToken": None,
        }
    ]
    apprunner_client.list_connections.side_effect = (
        lambda NextToken=None: connection_pages[0]
    )
    apprunner_client.describe_connection.return_value = {
        "Connection": {
            "ConnectionName": "github",
            "ConnectionArn": "conn-arn",
            "ProviderType": "GITHUB",
            "Status": "AVAILABLE",
            "Tags": {"env": "dev"},
        }
    }

    session = make_session_with_clients({("apprunner", "us-east-1"): apprunner_client})
    extractor = AppRunnerExtractor(session, {})
    extractor.validate = lambda _: True

    services = extractor._extract_services("us-east-1", None)
    connections = extractor._extract_connections("us-east-1", None)

    assert {svc["resource_id"] for svc in services} == {"svc1", "svc2"}
    assert connections[0]["resource_type"] == "apprunner:connection"


def test_cloudfront_extractor_handles_distribution_and_oai():
    cloudfront_client = Mock()
    sts_client = Mock()
    sts_client.get_caller_identity.return_value = {"Account": "123456789012"}

    distribution_pages = [
        {
            "DistributionList": {
                "Items": [{"Id": "dist1", "ARN": "arn:dist1", "Status": "Deployed"}]
            }
        }
    ]
    paginators = {
        "list_distributions": DummyPaginator(distribution_pages),
        "list_cloud_front_origin_access_identities": DummyPaginator(
            [{"CloudFrontOriginAccessIdentityList": {"Items": [{"Id": "oai1"}]}}]
        ),
    }
    cloudfront_client.get_paginator.side_effect = lambda name: paginators[name]
    cloudfront_client.get_distribution.return_value = {
        "Distribution": {
            "Id": "dist1",
            "ARN": "arn:dist1",
            "Status": "Deployed",
            "DistributionConfig": {
                "CallerReference": "ref",
                "Aliases": {"Items": ["dist.example.com"]},
                "Origins": {},
                "DefaultCacheBehavior": {},
                "CacheBehaviors": {},
                "CustomErrorResponses": {},
                "Enabled": True,
                "PriceClass": "PriceClass_100",
                "ViewerCertificate": {},
            },
        }
    }
    cloudfront_client.list_tags_for_resource.side_effect = Exception("no tags")
    cloudfront_client.get_cloud_front_origin_access_identity.return_value = {
        "CloudFrontOriginAccessIdentity": {
            "Id": "oai1",
            "S3CanonicalUserId": "abc123",
            "CloudFrontOriginAccessIdentityConfig": {
                "CallerReference": "oai-ref",
                "Comment": "test",
            },
        },
    }

    session = make_session_with_clients(
        {"cloudfront": cloudfront_client, "sts": sts_client}
    )
    extractor = CloudFrontExtractor(session, {})
    extractor.validate = lambda _: True

    distributions = extractor._extract_distributions(None)
    oais = extractor._extract_origin_access_identities(None)

    assert distributions[0]["resource_type"] == "cloudfront:distribution"
    assert distributions[0]["configuration"]["tags"] == []
    assert oais[0]["resource_type"] == "cloudfront:origin-access-identity"


def test_ec2_extractor_region_captures_instances_and_security_groups():
    extractor_cls = EC2Extractor
    ec2_client = Mock()
    paginators = {
        "describe_instances": DummyPaginator(
            [
                {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": "i-123",
                                    "InstanceType": "t3.micro",
                                    "OwnerId": "123456789012",
                                    "SecurityGroups": [{"GroupId": "sg-1"}],
                                    "State": {"Name": "running"},
                                    "Tags": [{"Key": "Name", "Value": "demo"}],
                                }
                            ]
                        }
                    ]
                }
            ]
        ),
        "describe_security_groups": DummyPaginator(
            [
                {
                    "SecurityGroups": [
                        {
                            "GroupId": "sg-1",
                            "GroupName": "default",
                            "Description": "default group",
                            "OwnerId": "123456789012",
                            "Tags": [{"Key": "Env", "Value": "test"}],
                        }
                    ]
                }
            ]
        ),
    }
    ec2_client.get_paginator.side_effect = lambda name: paginators[name]

    session = make_session_with_clients({("ec2", "us-east-1"): ec2_client})
    extractor = extractor_cls(session, {})

    artifacts = extractor._extract_region("us-east-1", None)

    resource_types = {item["resource_type"] for item in artifacts}
    assert resource_types == {"aws:ec2:instance", "aws:ec2:security-group"}


def test_ecs_extractor_traverses_clusters_services_tasks_and_task_defs():
    ecs_client = Mock()
    paginators = {
        "list_clusters": DummyPaginator([{"clusterArns": ["arn:cluster/demo"]}]),
        "list_services": DummyPaginator([{"serviceArns": ["arn:service/demo"]}]),
        "list_tasks": DummyPaginator([{"taskArns": ["arn:task/demo/123"]}]),
        "list_task_definitions": DummyPaginator(
            [{"taskDefinitionArns": ["arn:taskdef/demo:1"]}]
        ),
    }
    ecs_client.get_paginator.side_effect = lambda name: paginators[name]
    ecs_client.describe_clusters.return_value = {
        "clusters": [
            {
                "clusterName": "demo",
                "clusterArn": "arn:cluster/demo",
                "status": "ACTIVE",
                "statistics": [],
                "settings": [],
                "configuration": {},
                "tags": {},
            }
        ]
    }
    ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "orders",
                "serviceArn": "arn:service/demo/orders",
                "clusterArn": "arn:cluster/demo",
                "desiredCount": 2,
                "runningCount": 2,
                "pendingCount": 0,
                "launchType": "FARGATE",
                "tags": {},
            }
        ]
    }
    ecs_client.describe_tasks.return_value = {
        "tasks": [
            {
                "taskArn": "arn:task/demo/123",
                "clusterArn": "arn:cluster/demo",
                "taskDefinitionArn": "arn:taskdef/demo:1",
                "lastStatus": "RUNNING",
                "desiredStatus": "RUNNING",
                "containers": [],
                "tags": {},
            }
        ]
    }
    ecs_client.describe_task_definition.return_value = {
        "taskDefinition": {
            "family": "demo",
            "revision": 1,
            "taskDefinitionArn": "arn:taskdef/demo:1",
            "status": "ACTIVE",
            "compatibilities": [],
            "requiresCompatibilities": [],
            "cpu": "256",
            "memory": "512",
            "containerDefinitions": [],
            "tags": {},
        }
    }

    session = make_session_with_clients({("ecs", "us-east-1"): ecs_client})
    extractor = ECSExtractor(session, {})
    extractor.validate = lambda _: True

    cluster_artifacts = extractor._extract_clusters("us-east-1", None)
    task_def_artifacts = extractor._extract_task_definitions("us-east-1", None)

    resource_types = {item["resource_type"] for item in cluster_artifacts}
    assert resource_types == {"ecs:cluster", "ecs:service", "ecs:task"}
    assert task_def_artifacts[0]["resource_type"] == "ecs:task-definition"


def test_eks_extractor_loads_cluster_nodegroup_and_fargate():
    eks_client = Mock()
    paginators = {
        "list_clusters": DummyPaginator([{"clusters": ["demo-cluster"]}]),
        "list_nodegroups": DummyPaginator([{"nodegroups": ["ng-1"]}]),
        "list_fargate_profiles": DummyPaginator([{"fargateProfileNames": ["fp-1"]}]),
    }
    eks_client.get_paginator.side_effect = lambda name: paginators[name]
    eks_client.describe_cluster.return_value = {
        "cluster": {
            "name": "demo-cluster",
            "arn": "arn:cluster/demo",
            "status": "ACTIVE",
            "tags": {},
            "resourcesVpcConfig": {},
        }
    }
    eks_client.describe_nodegroup.return_value = {
        "nodegroup": {
            "nodegroupName": "ng-1",
            "clusterName": "demo-cluster",
            "status": "ACTIVE",
            "scalingConfig": {},
            "instanceTypes": ["t3.medium"],
        }
    }
    eks_client.describe_fargate_profile.return_value = {
        "fargateProfile": {
            "fargateProfileName": "fp-1",
            "clusterName": "demo-cluster",
            "status": "ACTIVE",
            "selectors": [],
        }
    }

    session = make_session_with_clients({("eks", "us-east-1"): eks_client})
    extractor = EKSExtractor(session, {})
    extractor.validate = lambda _: True

    artifacts = extractor._extract_clusters("us-east-1", None)
    resource_types = {item["resource_type"] for item in artifacts}
    assert resource_types == {"eks:cluster", "eks:nodegroup", "eks:fargate-profile"}


def test_elb_extractor_collects_load_balancers_and_target_groups():
    elbv2_client = Mock()
    paginators = {
        "describe_load_balancers": DummyPaginator(
            [
                {
                    "LoadBalancers": [
                        {
                            "LoadBalancerArn": "arn:lb/demo",
                            "LoadBalancerName": "lb-1",
                            "Type": "application",
                            "DNSName": "lb.example.com",
                            "AvailabilityZones": [],
                            "SecurityGroups": [],
                            "Scheme": "internet-facing",
                            "State": {},
                        }
                    ]
                }
            ]
        ),
        "describe_target_groups": DummyPaginator(
            [
                {
                    "TargetGroups": [
                        {
                            "TargetGroupArn": "arn:tg/demo",
                            "TargetGroupName": "tg-1",
                            "Protocol": "HTTP",
                            "Port": 80,
                            "VpcId": "vpc-1",
                        }
                    ]
                }
            ]
        ),
    }
    elbv2_client.get_paginator.side_effect = lambda name: paginators[name]
    elbv2_client.describe_listeners.return_value = {
        "Listeners": [{"ListenerArn": "arn:listener/demo", "Port": 443}]
    }
    elbv2_client.describe_tags.return_value = {
        "TagDescriptions": [{"Tags": [{"Key": "env", "Value": "prod"}]}]
    }
    elbv2_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [
            {"Target": {"Id": "i-123"}, "TargetHealth": {"State": "healthy"}}
        ]
    }

    session = make_session_with_clients({("elbv2", "us-east-1"): elbv2_client})
    extractor = ELBExtractor(session, {})
    extractor.validate = lambda _: True

    lbs = extractor._extract_load_balancers("us-east-1", None)
    tgs = extractor._extract_target_groups("us-east-1", None)

    assert lbs[0]["resource_type"] == "elb:application"
    assert tgs[0]["resource_type"] == "elb:target-group"
    assert tgs[0]["configuration"]["targets"][0]["Target"]["Id"] == "i-123"


def test_iam_extractor_captures_all_identity_types():
    iam_client = Mock()
    paginators = {
        "list_users": DummyPaginator(
            [
                {
                    "Users": [
                        {
                            "UserName": "alice",
                            "UserId": "AID1",
                            "Arn": "arn:aws:iam::123456789012:user/alice",
                            "CreateDate": datetime(2024, 1, 1),
                        }
                    ]
                }
            ]
        ),
        "list_roles": DummyPaginator(
            [
                {
                    "Roles": [
                        {
                            "RoleName": "AdminRole",
                            "RoleId": "RID1",
                            "Arn": "arn:aws:iam::123456789012:role/AdminRole",
                            "CreateDate": datetime(2024, 1, 2),
                        }
                    ]
                }
            ]
        ),
        "list_policies": DummyPaginator(
            [
                {
                    "Policies": [
                        {
                            "PolicyName": "CustomPolicy",
                            "PolicyId": "PID1",
                            "Arn": "arn:aws:iam::123456789012:policy/CustomPolicy",
                            "DefaultVersionId": "v1",
                            "AttachmentCount": 1,
                            "CreateDate": datetime(2024, 1, 3),
                        }
                    ]
                }
            ]
        ),
        "list_groups": DummyPaginator(
            [
                {
                    "Groups": [
                        {
                            "GroupName": "Admins",
                            "GroupId": "GID1",
                            "Arn": "arn:aws:iam::123456789012:group/Admins",
                            "CreateDate": datetime(2024, 1, 4),
                        }
                    ]
                }
            ]
        ),
    }
    iam_client.get_paginator.side_effect = lambda name: paginators[name]
    iam_client.list_attached_user_policies.return_value = {
        "AttachedPolicies": [{"PolicyName": "Policy1", "PolicyArn": "arn:policy"}]
    }
    iam_client.list_user_policies.return_value = {"PolicyNames": ["InlinePolicy"]}
    iam_client.list_groups_for_user.return_value = {"Groups": [{"GroupName": "Admins"}]}
    iam_client.list_access_keys.return_value = {
        "AccessKeyMetadata": [{"AccessKeyId": "AKIA", "Status": "Active"}]
    }
    iam_client.list_mfa_devices.return_value = {
        "MFADevices": [{"SerialNumber": "device"}]
    }
    iam_client.list_attached_role_policies.return_value = {
        "AttachedPolicies": [
            {"PolicyName": "RolePolicy", "PolicyArn": "arn:rolepolicy"}
        ]
    }
    iam_client.list_role_policies.return_value = {"PolicyNames": ["RoleInline"]}
    iam_client.get_policy_version.return_value = {
        "PolicyVersion": {"Document": {"Statement": []}}
    }
    iam_client.list_attached_group_policies.return_value = {
        "AttachedPolicies": [
            {"PolicyName": "GroupPolicy", "PolicyArn": "arn:grouppolicy"}
        ]
    }
    iam_client.list_group_policies.return_value = {"PolicyNames": ["GroupInline"]}

    session = make_session_with_clients({"iam": iam_client})
    extractor = IAMExtractor(session, {})
    extractor.validate = lambda _: True

    users = extractor._extract_users(iam_client)
    roles = extractor._extract_roles(iam_client)
    policies = extractor._extract_policies(iam_client)
    groups = extractor._extract_groups(iam_client)

    assert users[0]["configuration"]["mfa_enabled"] is True
    assert roles[0]["resource_type"] == "iam:role"
    assert policies[0]["configuration"]["policy_document"] == {"Statement": []}
    assert groups[0]["configuration"]["group_name"] == "Admins"


def test_kms_extractor_collects_keys_aliases_and_grants():
    kms_client = Mock()
    paginators = {
        "list_keys": DummyPaginator([{"Keys": [{"KeyId": "key-1"}]}]),
        "list_aliases": DummyPaginator(
            [
                {
                    "Aliases": [
                        {
                            "AliasName": "alias/my-key",
                            "AliasArn": "arn:alias/my-key",
                            "TargetKeyId": "key-1",
                            "CreationDate": datetime(2024, 1, 1),
                            "LastUpdatedDate": datetime(2024, 1, 2),
                        },
                        {
                            "AliasName": "alias/aws/s3",
                            "AliasArn": "arn:alias/aws/s3",
                            "TargetKeyId": "aws-managed",
                        },
                    ]
                }
            ]
        ),
    }
    kms_client.get_paginator.side_effect = lambda name: paginators[name]
    kms_client.describe_key.return_value = {
        "KeyMetadata": {
            "KeyId": "key-1",
            "Arn": "arn:key-1",
            "KeyManager": "CUSTOMER",
            "KeyState": "Enabled",
            "KeyUsage": "ENCRYPT_DECRYPT",
            "KeySpec": "SYMMETRIC_DEFAULT",
            "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
            "EncryptionAlgorithms": ["SYMMETRIC_DEFAULT"],
            "SigningAlgorithms": [],
            "Description": "Demo key",
        }
    }
    kms_client.get_key_policy.return_value = {"Policy": {"Statement": []}}
    kms_client.get_key_rotation_status.return_value = {"KeyRotationEnabled": True}
    kms_client.list_grants.return_value = {
        "Grants": [
            {
                "GrantId": "grant-1",
                "KeyId": "key-1",
                "GranteePrincipal": "arn:aws:iam::123456789012:role/Operator",
                "Operations": ["Encrypt"],
            }
        ]
    }
    kms_client.list_resource_tags.return_value = {
        "Tags": [{"TagKey": "env", "TagValue": "dev"}]
    }

    session = make_session_with_clients({("kms", "us-east-1"): kms_client})
    extractor = KMSExtractor(session, {})
    extractor.validate = lambda _: True

    key_artifacts = extractor._extract_keys("us-east-1", None)
    alias_artifacts = extractor._extract_aliases("us-east-1", None)

    resource_types = {item["resource_type"] for item in key_artifacts}
    assert {"kms:key", "kms:grant"} <= resource_types
    assert alias_artifacts[0]["resource_type"] == "kms:alias"


def test_lambda_extractor_region_covers_functions_layers_and_mappings():
    lambda_client = Mock()
    paginators = {
        "list_functions": DummyPaginator(
            [
                {
                    "Functions": [
                        {
                            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:demo",
                            "FunctionName": "demo",
                            "Runtime": "python3.11",
                            "Role": "arn:aws:iam::123456789012:role/lambda",
                            "Handler": "handler.handler",
                            "CodeSize": 1024,
                            "Timeout": 3,
                            "MemorySize": 128,
                            "Environment": {},
                            "Version": "$LATEST",
                        }
                    ]
                }
            ]
        ),
        "list_layers": DummyPaginator(
            [
                {
                    "Layers": [
                        {
                            "LayerArn": "arn:aws:lambda:us-east-1:123456789012:layer:demo:1",
                            "LayerName": "demo-layer",
                            "Version": 1,
                        }
                    ]
                }
            ]
        ),
        "list_event_source_mappings": DummyPaginator(
            [
                {
                    "EventSourceMappings": [
                        {
                            "UUID": "uuid-1",
                            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:demo",
                            "EventSourceArn": "arn:aws:sqs:us-east-1:123456789012:queue",
                            "State": "Enabled",
                        }
                    ]
                }
            ]
        ),
    }
    lambda_client.get_paginator.side_effect = lambda name: paginators[name]

    session = make_session_with_clients(
        {("lambda", "us-east-1"): lambda_client, "ec2": Mock()}
    )
    extractor = LambdaExtractor(session, {})
    extractor.validate = lambda _: True

    artifacts = extractor._extract_region("us-east-1", None)

    resource_types = {item["resource_type"] for item in artifacts}
    assert resource_types == {
        "aws:lambda:function",
        "aws:lambda:layer",
        "aws:lambda:event-source-mapping",
    }


def test_rds_extractor_region_covers_all_resource_types():
    rds_client = Mock()
    paginators = {
        "describe_db_instances": DummyPaginator(
            [
                {
                    "DBInstances": [
                        {
                            "DBInstanceIdentifier": "db-1",
                            "DBInstanceClass": "db.t3.micro",
                            "Engine": "postgres",
                            "EngineVersion": "14",
                            "DBInstanceStatus": "available",
                        }
                    ]
                }
            ]
        ),
        "describe_db_clusters": DummyPaginator(
            [
                {
                    "DBClusters": [
                        {
                            "DBClusterIdentifier": "cluster-1",
                            "Engine": "aurora-postgresql",
                            "Status": "available",
                        }
                    ]
                }
            ]
        ),
        "describe_db_snapshots": DummyPaginator(
            [
                {
                    "DBSnapshots": [
                        {
                            "DBSnapshotIdentifier": "snapshot-1",
                            "DBInstanceIdentifier": "db-1",
                            "SnapshotType": "manual",
                        }
                    ]
                }
            ]
        ),
        "describe_db_cluster_snapshots": DummyPaginator(
            [
                {
                    "DBClusterSnapshots": [
                        {
                            "DBClusterSnapshotIdentifier": "cluster-snap-1",
                            "DBClusterIdentifier": "cluster-1",
                            "SnapshotType": "manual",
                        }
                    ]
                }
            ]
        ),
    }
    rds_client.get_paginator.side_effect = lambda name: paginators[name]

    session = make_session_with_clients({("rds", "us-east-1"): rds_client})
    extractor = RDSExtractor(session, {})
    extractor.validate = lambda _: True

    artifacts = extractor._extract_region("us-east-1", None)
    resource_types = {item["resource_type"] for item in artifacts}
    assert resource_types == {
        "rds:db-instance",
        "rds:db-cluster",
        "rds:db-snapshot",
        "rds:db-cluster-snapshot",
    }


def test_vpc_extractor_gathers_all_network_components():
    ec2_client = Mock()
    paginators = {
        "describe_vpcs": DummyPaginator(
            [{"Vpcs": [{"VpcId": "vpc-1", "CidrBlock": "10.0.0.0/16", "Tags": []}]}]
        ),
        "describe_subnets": DummyPaginator(
            [
                {
                    "Subnets": [
                        {
                            "SubnetId": "subnet-1",
                            "VpcId": "vpc-1",
                            "CidrBlock": "10.0.1.0/24",
                            "AvailabilityZone": "us-east-1a",
                            "Tags": [],
                        }
                    ]
                }
            ]
        ),
        "describe_internet_gateways": DummyPaginator(
            [
                {
                    "InternetGateways": [
                        {"InternetGatewayId": "igw-1", "Attachments": [], "Tags": []}
                    ]
                }
            ]
        ),
        "describe_nat_gateways": DummyPaginator(
            [{"NatGateways": [{"NatGatewayId": "nat-1", "SubnetId": "subnet-1"}]}]
        ),
        "describe_route_tables": DummyPaginator(
            [
                {
                    "RouteTables": [
                        {
                            "RouteTableId": "rtb-1",
                            "Routes": [],
                            "Associations": [],
                            "Tags": [],
                        }
                    ]
                }
            ]
        ),
        "describe_network_acls": DummyPaginator(
            [
                {
                    "NetworkAcls": [
                        {
                            "NetworkAclId": "acl-1",
                            "VpcId": "vpc-1",
                            "Entries": [],
                            "Associations": [],
                            "Tags": [],
                        }
                    ]
                }
            ]
        ),
    }
    ec2_client.get_paginator.side_effect = lambda name: paginators[name]

    session = make_session_with_clients({("ec2", "us-east-1"): ec2_client})
    extractor = VPCExtractor(session, {})
    extractor.validate = lambda _: True

    artifacts = extractor._extract_region("us-east-1", None)

    resource_types = {item["resource_type"] for item in artifacts}
    assert resource_types == {
        "vpc:vpc",
        "vpc:subnet",
        "vpc:internet-gateway",
        "vpc:nat-gateway",
        "vpc:route-table",
        "vpc:network-acl",
    }
