---
layout: default
title: AWS Supported Resources
parent: Supported Resources
nav_order: 1
has_children: false
---

# AWS Supported Resources

The following AWS resource extractors are supported:

- apigateway
- apprunner
- cloudfront
- ec2
- ecs
- eks
- elb
- iam
- kms
- lambda_extractor
- rds
- s3
- vpc

## Detailed Resource Information

### Compute Services

#### EC2 Instances (`aws:ec2:instance`)
- **Description**: Virtual machines and their configurations
- **Extracted Data**:
  - Instance ID, type, state, and AMI
  - Network interfaces, security groups, and subnets
  - EBS volumes and their configurations
  - Tags, key pairs, and instance metadata
  - Launch time and availability zone
- **Configuration Options**:
  - `max_workers`: Parallel extraction workers
  - `include_stopped`: Include stopped instances
  - `include_terminated`: Include terminated instances

#### EC2 Security Groups (`aws:ec2:security-group`)
- **Description**: Security group rules and configurations
- **Extracted Data**:
  - Inbound and outbound rules
  - Referenced security groups and CIDR blocks
  - VPC association and description
  - Tags and metadata

### Storage Services

#### S3 Buckets (`aws:s3:bucket`)
- **Description**: S3 bucket configurations and policies
- **Extracted Data**:
  - Bucket policies and ACLs
  - Versioning, encryption, and logging settings
  - CORS configuration and lifecycle rules
  - Public access block settings
  - Replication and analytics configurations
- **Configuration Options**:
  - `include_bucket_policies`: Extract bucket policies
  - `include_bucket_acl`: Extract bucket ACLs
  - `check_public_access`: Check for public access

### Database Services

#### RDS Instances (`aws:rds:db-instance`)
- **Description**: Relational database instances
- **Extracted Data**:
  - Engine type, version, and instance class
  - Storage configuration and backup settings
  - Multi-AZ deployment and read replicas
  - Security groups and subnet groups
  - Parameter groups and option groups

#### RDS Clusters (`aws:rds:db-cluster`)
- **Description**: Aurora and other clustered databases
- **Extracted Data**:
  - Cluster configuration and member instances
  - Global database settings
  - Backup and maintenance windows

### Serverless Services

#### Lambda Functions (`aws:lambda:function`)
- **Description**: Serverless function configurations
- **Extracted Data**:
  - Runtime, handler, and memory settings
  - Environment variables and VPC configuration
  - IAM role and permissions
  - Event source mappings and aliases
- **Configuration Options**:
  - `include_versions`: Extract function versions
  - `include_aliases`: Extract function aliases

### Identity & Access Management

#### IAM Users (`aws:iam:user`)
- **Description**: IAM user accounts and configurations
- **Extracted Data**:
  - User policies and attached managed policies
  - Access keys and their status
  - MFA devices and password settings
  - Groups and inline policies

#### IAM Roles (`aws:iam:role`)
- **Description**: IAM roles and their trust relationships
- **Extracted Data**:
  - Assume role policies and permissions
  - Attached managed policies
  - Instance profiles and role usage

#### IAM Policies (`aws:iam:policy`)
- **Description**: IAM policies (managed and inline)
- **Extracted Data**:
  - Policy documents and versions
  - Attachment information
  - AWS managed vs customer managed

### Networking Services

#### VPCs (`aws:vpc:vpc`)
- **Description**: Virtual private clouds
- **Extracted Data**:
  - CIDR blocks and tenancy
  - DHCP options and DNS settings
  - Associated subnets and route tables

#### Subnets (`aws:vpc:subnet`)
- **Description**: VPC subnets
- **Extracted Data**:
  - CIDR block and availability zone
  - Route table and network ACL associations
  - Public/private subnet designation

#### Security Groups (`aws:vpc:security-group`)
- **Description**: VPC security groups
- **Extracted Data**:
  - Inbound and outbound rules
  - Referenced security groups

### Container Services

#### ECS Clusters (`aws:ecs:cluster`)
- **Description**: ECS container clusters
- **Extracted Data**:
  - Cluster configuration and capacity providers
  - Running tasks and services count
  - Networking and logging settings

#### ECS Services (`aws:ecs:service`)
- **Description**: ECS services
- **Extracted Data**:
  - Task definition and desired count
  - Load balancer configuration
  - Network configuration and security groups

#### EKS Clusters (`aws:eks:cluster`)
- **Description**: Elastic Kubernetes Service clusters
- **Extracted Data**:
  - Kubernetes version and platform version
  - VPC and subnet configuration
  - Security groups and IAM roles
  - Logging and monitoring settings

### Load Balancing

#### ELB Application Load Balancers (`aws:elb:application-load-balancer`)
- **Description**: ALB configurations
- **Extracted Data**:
  - Listeners and target groups
  - Security policies and SSL settings
  - Access logs and deletion protection

#### ELB Network Load Balancers (`aws:elb:network-load-balancer`)
- **Description**: NLB configurations
- **Extracted Data**:
  - Listeners and target groups
  - Cross-zone load balancing
  - Elastic IPs and subnet mappings

### Content Delivery

#### CloudFront Distributions (`aws:cloudfront:distribution`)
- **Description**: CDN distributions
- **Extracted Data**:
  - Origins and behaviors
  - SSL certificates and custom domains
  - Geographic restrictions and caching policies

### API Management

#### API Gateway REST APIs (`aws:apigateway:rest-api`)
- **Description**: API Gateway configurations
- **Extracted Data**:
  - API endpoints and methods
  - Authorizers and API keys
  - Stages and deployments
  - Usage plans and throttling

### Key Management

#### KMS Keys (`aws:kms:key`)
- **Description**: KMS encryption keys
- **Extracted Data**:
  - Key specifications and usage
  - Key policies and grants
  - Rotation settings and aliases

### App Runner

#### App Runner Services (`aws:apprunner:service`)
- **Description**: App Runner applications
- **Extracted Data**:
  - Source configuration and runtime
  - Network settings and custom domains
  - Health checks and scaling configuration
