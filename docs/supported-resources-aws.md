---
layout: default
title: AWS Supported Resources
parent: Supported Resources
nav_order: 1
has_children: false
---

# AWS Supported Resources

This document provides a comprehensive reference for all Amazon Web Services (AWS) resources supported by the Cloud Artifact Extractor.

**Total Services**: 13 extractors covering 60+ resource types

## Service Extractors

### Quick Service List

<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-family: monospace;">
  <a href="#api-gateway-apigateway">apigateway</a>
  <a href="#app-runner-apprunner">apprunner</a>
  <a href="#cloudfront-cloudfront">cloudfront</a>
  <a href="#ec2-elastic-compute-cloud-ec2">ec2</a>
  <a href="#ecs-elastic-container-service-ecs">ecs</a>
  <a href="#eks-elastic-kubernetes-service-eks">eks</a>
  <a href="#elb-elastic-load-balancing-elb">elb</a>
  <a href="#iam-identity--access-management-iam">iam</a>
  <a href="#kms-key-management-service-kms">kms</a>
  <a href="#lambda-lambda_extractor">lambda_extractor</a>
  <a href="#rds-relational-database-service-rds">rds</a>
  <a href="#s3-simple-storage-service-s3">s3</a>
  <a href="#vpc-virtual-private-cloud-vpc">vpc</a>
</div>

---

## EC2 (Elastic Compute Cloud) (`ec2`)
{: #ec2-elastic-compute-cloud-ec2}

Extracts Amazon EC2 instances, security groups, network interfaces, and related compute resources.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:ec2:instance` | EC2 virtual machines | Instance type, state, AMI, network, volumes, tags |
| `aws:ec2:security-group` | Security groups | Inbound/outbound rules, VPC, referenced groups |
| `aws:ec2:network-interface` | Elastic Network Interfaces | IP addresses, security groups, attachments |
| `aws:ec2:volume` | EBS volumes | Size, type, encryption, IOPS, attachments |
| `aws:ec2:snapshot` | EBS snapshots | Volume ID, encryption, progress, description |
| `aws:ec2:ami` | Amazon Machine Images | Name, OS, architecture, virtualization type |

**Extracted Configuration:**

### EC2 Instances
- Instance ID, type, and state (running, stopped, terminated)
- Amazon Machine Image (AMI) and platform
- VPC, subnet, and availability zone placement
- Network interfaces and private/public IP addresses
- Security groups and key pair associations
- EBS volumes (root and additional data volumes)
- Instance metadata and user data
- IAM instance profile
- Monitoring and detailed monitoring status
- Tags and resource metadata
- Launch time and termination protection
- Placement groups and tenancy

### Security Groups
- Inbound and outbound rule definitions
- Protocol, port ranges, and IP CIDR blocks
- Referenced security groups (source/destination)
- VPC association
- Group name and description
- Tags and creation metadata

### Network Interfaces
- Primary and secondary IP addresses
- Elastic IP associations
- Security group attachments
- Subnet and VPC association
- Attachment information (instance ID, device index)
- Source/destination check status
- Interface type and status

**Configuration Options:**
- `max_workers`: Number of parallel extraction workers
- `include_stopped`: Include stopped instances (default: true)
- `include_terminated`: Include terminated instances (default: false)

**Common Use Cases:**
- Inventory all EC2 instances across regions and accounts
- Audit security group rules for overly permissive access
- Track unattached EBS volumes and snapshots
- Verify instance encryption and monitoring settings
- Monitor instance types for cost optimization

**Security Checks:**
- ✅ IMDSv2 enabled (metadata service version 2)
- ✅ EBS volumes encrypted at rest
- ✅ Security groups follow least privilege
- ✅ No instances with 0.0.0.0/0 SSH access (port 22)
- ✅ Termination protection enabled for critical instances
- ✅ Detailed monitoring enabled
- ✅ No overly broad security group rules

**Example Extraction:**
```bash
curl -X POST "http://localhost:8000/extraction/extract?services=ec2&provider=aws"
```

---

## S3 (Simple Storage Service) (`s3`)
{: #s3-simple-storage-service-s3}

Extracts Amazon S3 bucket configurations, policies, and access controls.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:s3:bucket` | S3 buckets | Name, region, encryption, versioning, policies, logging |
| `aws:s3:bucket-policy` | Bucket policies | Policy document, public access settings |
| `aws:s3:bucket-acl` | Access Control Lists | Grants, permissions, grantees |

**Extracted Configuration:**
- Bucket name and region
- Bucket policies and policy status
- Access Control Lists (ACLs)
- Versioning configuration
- Server-side encryption settings (SSE-S3, SSE-KMS, SSE-C)
- Logging configuration (access logs)
- CORS configuration
- Lifecycle rules and transitions
- Public access block settings
- Replication configuration (cross-region, same-region)
- Analytics and inventory configurations
- Object Lock configuration
- Website hosting settings
- Transfer acceleration status
- Requester pays configuration
- Bucket tags

**Configuration Options:**
- `include_bucket_policies`: Extract bucket policies (default: true)
- `include_bucket_acl`: Extract bucket ACLs (default: true)
- `check_public_access`: Check for public access (default: true)

**Common Use Cases:**
- Identify publicly accessible S3 buckets
- Audit bucket encryption configurations
- Verify versioning and lifecycle policies
- Track bucket policies for compliance
- Monitor cross-region replication settings

**Security Checks:**
- ✅ Public access blocked (all four settings)
- ✅ Server-side encryption enabled
- ✅ Versioning enabled for critical buckets
- ✅ Access logging enabled
- ✅ SSL/TLS required for bucket access
- ✅ No overly permissive bucket policies
- ✅ MFA delete enabled for versioned buckets

**Example Extraction:**
```bash
curl -X POST "http://localhost:8000/extraction/extract?services=s3&provider=aws"
```

---

## RDS (Relational Database Service) (`rds`)
{: #rds-relational-database-service-rds}

Extracts Amazon RDS database instances, clusters, and snapshots.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:rds:db-instance` | RDS database instances | Engine, version, class, storage, backups, Multi-AZ |
| `aws:rds:db-cluster` | Aurora/RDS clusters | Members, endpoints, backup, global databases |
| `aws:rds:db-snapshot` | Database snapshots | Source DB, encryption, status, creation time |
| `aws:rds:db-cluster-snapshot` | Cluster snapshots | Source cluster, encryption, status |
| `aws:rds:db-parameter-group` | Parameter groups | Parameters, engine family |
| `aws:rds:db-subnet-group` | Subnet groups | Subnets, VPC, availability zones |

**Extracted Configuration:**

### RDS Instances
- Database engine (MySQL, PostgreSQL, SQL Server, Oracle, MariaDB)
- Engine version and instance class
- Storage type (gp2, gp3, io1, magnetic) and allocated storage
- IOPS and throughput configuration
- Multi-AZ deployment status
- Read replica configuration
- VPC security groups and DB subnet groups
- Parameter groups and option groups
- Backup retention period and backup window
- Maintenance window and auto minor version upgrade
- Encryption at rest (KMS key)
- Enhanced monitoring and Performance Insights
- IAM database authentication
- Deletion protection
- Tags and metadata

### RDS Clusters
- Cluster configuration and member instances
- Cluster endpoints (writer, reader, custom)
- Global database settings and cross-region replication
- Backup and maintenance windows
- Encryption settings
- Serverless v2 scaling configuration (Aurora)
- Database activity streams

**Common Use Cases:**
- Inventory all RDS instances and clusters
- Audit database encryption settings
- Verify Multi-AZ and backup configurations
- Track database versions for patching
- Monitor Performance Insights enablement

**Security Checks:**
- ✅ Encryption at rest enabled
- ✅ Encryption in transit (SSL/TLS) required
- ✅ Multi-AZ enabled for production databases
- ✅ Automated backups enabled with adequate retention
- ✅ Enhanced monitoring enabled
- ✅ IAM database authentication enabled
- ✅ Deletion protection enabled
- ✅ Public accessibility disabled

---

## Lambda (`lambda_extractor`)
{: #lambda-lambda_extractor}

Extracts AWS Lambda function configurations, layers, and event source mappings.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:lambda:function` | Lambda functions | Runtime, handler, memory, timeout, role, VPC, environment |
| `aws:lambda:layer` | Lambda layers | Compatible runtimes, version, ARN, permissions |
| `aws:lambda:event-source-mapping` | Event source mappings | Source ARN, batch size, function, error handling |
| `aws:lambda:alias` | Function aliases | Version, routing config, description |
| `aws:lambda:function-url-config` | Function URLs | Auth type, CORS, URL endpoint |

**Extracted Configuration:**
- Function runtime (Node.js, Python, Java, Go, .NET, Ruby, Custom)
- Handler function and code location
- Memory allocation and timeout settings
- Environment variables and configuration
- IAM execution role and permissions
- VPC configuration (subnets, security groups)
- Layers and layer versions
- Reserved concurrent executions
- Dead letter queue (DLQ) configuration
- Tracing configuration (X-Ray)
- File system configurations (EFS)
- Code signing configuration
- Architecture (x86_64, arm64)
- Ephemeral storage configuration
- Event source mappings (SQS, Kinesis, DynamoDB Streams, etc.)
- Function aliases and versions
- Function URL configurations
- Tags and metadata

**Configuration Options:**
- `include_versions`: Extract all function versions (default: false)
- `include_aliases`: Extract function aliases (default: true)

**Common Use Cases:**
- Inventory all Lambda functions across regions
- Audit function runtime versions for updates
- Verify IAM execution role permissions
- Track VPC configurations and network access
- Monitor reserved concurrency settings

**Security Checks:**
- ✅ Functions use supported runtimes (not deprecated)
- ✅ IAM roles follow least privilege
- ✅ Environment variables don't contain secrets
- ✅ VPC configuration for data access functions
- ✅ X-Ray tracing enabled
- ✅ Code signing configured for production functions
- ✅ Dead letter queues configured for async invocations

---

## IAM (Identity & Access Management) (`iam`)
{: #iam-identity--access-management-iam}

Extracts AWS IAM users, roles, policies, and groups.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:iam:user` | IAM users | Access keys, MFA, policies, groups, password settings |
| `aws:iam:role` | IAM roles | Trust policy, attached policies, instance profiles |
| `aws:iam:policy` | IAM policies | Policy document, versions, attachments, type |
| `aws:iam:group` | IAM groups | Members, attached policies, inline policies |
| `aws:iam:instance-profile` | Instance profiles | Roles, EC2 associations |

**Extracted Configuration:**

### IAM Users
- User name and ARN
- Access keys and their status (active/inactive)
- Access key age and last used information
- MFA devices (virtual, hardware)
- Password last used and password age
- Attached managed policies
- Inline policies
- Group memberships
- Permissions boundary
- Tags

### IAM Roles
- Role name and ARN
- Assume role policy (trust policy)
- Attached managed policies
- Inline policies
- Instance profiles
- Maximum session duration
- Permissions boundary
- Last used information
- Tags

### IAM Policies
- Policy name, ARN, and ID
- Policy document (JSON)
- Policy versions
- Default version
- Attachment count (users, groups, roles)
- AWS managed vs customer managed
- Permissions boundary usage
- Creation and update timestamps

### IAM Groups
- Group name and ARN
- Member users
- Attached managed policies
- Inline policies
- Creation date

**Common Use Cases:**
- Audit IAM user access keys and rotation
- Identify users without MFA enabled
- Track overly permissive policies
- Verify least privilege access
- Monitor unused credentials and roles

**Security Checks:**
- ✅ MFA enabled for all IAM users
- ✅ Access keys rotated regularly (< 90 days)
- ✅ No root account access keys
- ✅ Policies follow least privilege principle
- ✅ No inline policies (prefer managed policies)
- ✅ Unused credentials disabled
- ✅ Password policy enforced
- ✅ No wildcard (*) permissions in custom policies

---

## VPC (Virtual Private Cloud) (`vpc`)
{: #vpc-virtual-private-cloud-vpc}

Extracts AWS VPC configurations including networks, subnets, security groups, and routing.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:vpc:vpc` | Virtual private clouds | CIDR blocks, DNS, DHCP options, tenancy |
| `aws:vpc:subnet` | VPC subnets | CIDR, AZ, route table, public/private designation |
| `aws:vpc:security-group` | Security groups | Inbound/outbound rules, referenced groups |
| `aws:vpc:route-table` | Route tables | Routes, subnet associations, gateways |
| `aws:vpc:network-acl` | Network ACLs | Inbound/outbound rules, subnet associations |
| `aws:vpc:internet-gateway` | Internet gateways | VPC attachments, state |
| `aws:vpc:nat-gateway` | NAT gateways | Elastic IP, subnet, state, connectivity type |
| `aws:vpc:vpc-endpoint` | VPC endpoints | Service name, type, route tables, subnets |
| `aws:vpc:vpc-peering-connection` | VPC peering | Accepter/requester VPCs, status |

**Extracted Configuration:**

### VPCs
- VPC CIDR blocks (IPv4 and IPv6)
- Instance tenancy (default, dedicated)
- DNS resolution and DNS hostnames settings
- DHCP options set
- Default security group and network ACL
- Flow logs configuration
- Tags

### Subnets
- Subnet CIDR block and availability zone
- VPC association
- Route table associations
- Network ACL associations
- Public/private subnet designation (auto-assign public IP)
- IPv6 CIDR blocks
- Tags

### Security Groups
- Inbound and outbound rule definitions
- Protocol, port ranges, and IP CIDR blocks
- Referenced security groups (source/destination)
- VPC association
- Group description
- Tags

### Route Tables
- Route definitions (destination, target)
- Internet gateway, NAT gateway, VPC peering routes
- Subnet associations
- Propagated routes
- Tags

### Network ACLs
- Inbound and outbound rules
- Rule numbers and priorities
- Allow/deny actions
- Protocol and port specifications
- Subnet associations
- Tags

### NAT Gateways
- Elastic IP address allocation
- Subnet placement and availability zone
- State (pending, available, deleting, deleted)
- Connectivity type (public, private)
- Tags

**Common Use Cases:**
- Map VPC network architecture
- Audit security group rules for compliance
- Identify unused network resources
- Verify route table configurations
- Track VPC peering connections

**Security Checks:**
- ✅ Flow logs enabled for VPCs
- ✅ No security groups allowing 0.0.0.0/0 on all ports
- ✅ Default security group restricts all traffic
- ✅ Network ACLs reviewed for proper rules
- ✅ Private subnets use NAT gateway for outbound
- ✅ VPC endpoints used for AWS services

---

## ECS (Elastic Container Service) (`ecs`)
{: #ecs-elastic-container-service-ecs}

Extracts Amazon ECS cluster, service, and task configurations.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:ecs:cluster` | ECS clusters | Capacity providers, settings, container insights |
| `aws:ecs:service` | ECS services | Task definition, desired count, load balancer, network config |
| `aws:ecs:task` | ECS tasks | Task definition, containers, network, status |
| `aws:ecs:task-definition` | Task definitions | Container definitions, CPU, memory, network mode |
| `aws:ecs:container-instance` | Container instances | EC2 instance, agent status, registered resources |

**Extracted Configuration:**

### ECS Clusters
- Cluster name and ARN
- Capacity providers (Fargate, Fargate Spot, EC2)
- Default capacity provider strategy
- Container Insights enablement
- Running tasks and services count
- Registered container instances
- Settings and configuration
- Tags

### ECS Services
- Service name and ARN
- Task definition (family and revision)
- Desired count, running count, pending count
- Launch type (EC2, Fargate)
- Platform version (Fargate)
- Load balancer configuration (ALB, NLB, CLB)
- Network configuration (VPC, subnets, security groups)
- Service discovery configuration
- Deployment configuration (min/max healthy percent)
- Auto-scaling policies
- Scheduling strategy (REPLICA, DAEMON)
- Tags

### Task Definitions
- Family and revision
- Container definitions (image, CPU, memory, ports)
- Task role and execution role ARNs
- Network mode (bridge, host, awsvpc, none)
- Volumes (EBS, EFS, bind mounts)
- Task size (CPU and memory)
- Launch type compatibility
- Logging configuration (CloudWatch, Splunk, etc.)
- Environment variables and secrets
- Health checks

**Common Use Cases:**
- Inventory ECS clusters and services
- Audit task definitions and container images
- Verify network configurations and security groups
- Track service scaling configurations
- Monitor Container Insights enablement

**Security Checks:**
- ✅ Container Insights enabled
- ✅ Task roles follow least privilege
- ✅ Secrets stored in Secrets Manager or Parameter Store
- ✅ No hardcoded credentials in task definitions
- ✅ Network mode properly configured (awsvpc for Fargate)
- ✅ Container images from trusted registries
- ✅ Read-only root filesystem where possible

---

## EKS (Elastic Kubernetes Service) (`eks`)
{: #eks-elastic-kubernetes-service-eks}

Extracts Amazon EKS cluster configurations, node groups, and Fargate profiles.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:eks:cluster` | EKS clusters | K8s version, VPC, security groups, logging, add-ons |
| `aws:eks:nodegroup` | Managed node groups | Instance types, scaling, AMI, subnets, labels, taints |
| `aws:eks:fargate-profile` | Fargate profiles | Selectors, pod execution role, subnets |
| `aws:eks:addon` | EKS add-ons | Add-on version, configuration, service account |

**Extracted Configuration:**

### EKS Clusters
- Cluster name and ARN
- Kubernetes version and platform version
- Endpoint (public, private access)
- VPC configuration and subnet IDs
- Security group IDs
- Cluster IAM role
- Control plane logging (API, audit, authenticator, controller manager, scheduler)
- Encryption configuration (secrets encryption with KMS)
- Certificate authority data
- OIDC identity provider
- Add-ons (VPC CNI, CoreDNS, kube-proxy, EBS CSI driver)
- Status and health
- Tags

### Node Groups
- Node group name and ARN
- Instance types and AMI type
- Desired, minimum, and maximum size
- Disk size and volume type
- Subnets and availability zones
- Remote access configuration (EC2 key pair, source security groups)
- Node role ARN
- Labels and taints
- Launch template
- Auto-scaling group
- Update configuration
- Health status
- Tags

### Fargate Profiles
- Profile name and ARN
- Pod execution role ARN
- Subnet IDs
- Selectors (namespace and labels)
- Status
- Tags

**Common Use Cases:**
- Inventory EKS clusters across regions
- Audit Kubernetes versions for updates
- Verify control plane logging enabled
- Track node group scaling configurations
- Monitor add-on versions

**Security Checks:**
- ✅ Private endpoint access enabled
- ✅ Public endpoint access restricted (CIDR whitelist)
- ✅ Control plane logging enabled (all log types)
- ✅ Secrets encryption enabled with KMS
- ✅ IAM roles for service accounts (IRSA) configured
- ✅ Network policies enabled
- ✅ Security groups properly configured
- ✅ Latest supported Kubernetes version

---

## ELB (Elastic Load Balancing) (`elb`)
{: #elb-elastic-load-balancing-elb}

Extracts AWS Elastic Load Balancer configurations including ALB, NLB, and target groups.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:elb:application-load-balancer` | Application Load Balancers | Listeners, rules, target groups, SSL, WAF |
| `aws:elb:network-load-balancer` | Network Load Balancers | Listeners, target groups, IPs, cross-zone |
| `aws:elb:classic-load-balancer` | Classic Load Balancers | Listeners, instances, health checks |
| `aws:elb:target-group` | Target groups | Targets, health checks, protocol, stickiness |
| `aws:elb:listener` | Listeners | Protocol, port, rules, certificates |

**Extracted Configuration:**

### Application Load Balancers (ALB)
- Load balancer name, ARN, and DNS name
- Scheme (internet-facing, internal)
- VPC and availability zones
- Security groups
- Listeners and listener rules
- Target groups and routing
- SSL certificates and policies
- Access logs (S3 bucket, prefix, enabled)
- Connection logs
- Deletion protection
- HTTP/2 and gRPC support
- Desync mitigation mode
- Drop invalid header fields
- WAF web ACL association
- Tags

### Network Load Balancers (NLB)
- Load balancer name, ARN, and DNS name
- Scheme (internet-facing, internal)
- VPC and availability zones
- Subnet mappings and elastic IPs
- Listeners and target groups
- Cross-zone load balancing
- Access logs
- Deletion protection
- Preserve source IP
- Proxy protocol v2
- Tags

### Target Groups
- Target group name and ARN
- Protocol and port
- VPC
- Target type (instance, IP, Lambda, ALB)
- Registered targets and health status
- Health check configuration (protocol, path, interval, timeout)
- Stickiness settings
- Deregistration delay
- Load balancing algorithm
- Tags

**Common Use Cases:**
- Inventory load balancers across regions
- Audit SSL/TLS configurations and certificates
- Verify access logging enabled
- Track target group health checks
- Monitor deletion protection settings

**Security Checks:**
- ✅ Access logs enabled
- ✅ Deletion protection enabled
- ✅ SSL/TLS listeners using secure policies
- ✅ No insecure protocols (HTTP for sensitive data)
- ✅ Drop invalid header fields enabled (ALB)
- ✅ WAF associated (for public-facing ALBs)
- ✅ Security groups properly configured

---

## CloudFront (`cloudfront`)
{: #cloudfront-cloudfront}

Extracts Amazon CloudFront distribution configurations and origin access identities.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:cloudfront:distribution` | CloudFront distributions | Origins, behaviors, SSL, caching, geo-restrictions |
| `aws:cloudfront:origin-access-identity` | Origin access identities | S3 canonical user ID, comment |
| `aws:cloudfront:origin-access-control` | Origin access control | Signing behavior, origin type |

**Extracted Configuration:**

### CloudFront Distributions
- Distribution ID and ARN
- Domain name and alternate domain names (CNAMEs)
- Origins (S3, custom HTTP/HTTPS, MediaStore, MediaPackage)
- Origin access identity or origin access control
- Cache behaviors (default and additional)
- Path patterns and precedence
- Viewer protocol policy (HTTP/HTTPS, redirect to HTTPS, HTTPS only)
- Allowed HTTP methods
- Caching and TTL settings
- Cache policies and origin request policies
- SSL/TLS certificate (CloudFront default, ACM, IAM)
- Minimum SSL protocol version
- Geographic restrictions (whitelist, blacklist)
- Web Application Firewall (WAF) web ACL
- Logging configuration (S3 bucket, prefix)
- Price class and enabled status
- HTTP versions (HTTP/2, HTTP/3)
- IPv6 enabled
- Tags

**Common Use Cases:**
- Inventory CloudFront distributions
- Audit SSL/TLS configurations
- Verify WAF associations
- Track origin configurations
- Monitor logging settings

**Security Checks:**
- ✅ HTTPS required (redirect or HTTPS only)
- ✅ Minimum TLS version 1.2 or higher
- ✅ Origin access identity/control configured for S3 origins
- ✅ WAF web ACL associated
- ✅ Logging enabled
- ✅ Custom SSL certificate from ACM
- ✅ Geographic restrictions configured (if required)

---

## API Gateway (`apigateway`)
{: #api-gateway-apigateway}

Extracts AWS API Gateway REST API configurations, resources, methods, and stages.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:apigateway:rest-api` | REST APIs | Name, endpoints, authorizers, API keys |
| `aws:apigateway:resource` | API resources | Path, parent, methods |
| `aws:apigateway:method` | API methods | HTTP method, authorization, integration |
| `aws:apigateway:stage` | API stages | Deployment, variables, throttling, logging |
| `aws:apigateway:deployment` | Deployments | Stage, description, created date |
| `aws:apigateway:authorizer` | Authorizers | Type, provider, identity source |
| `aws:apigateway:usage-plan` | Usage plans | Throttle, quota, API stages |

**Extracted Configuration:**

### REST APIs
- API ID, name, and description
- Endpoint configuration (edge, regional, private)
- API key source
- Policy document (resource policies)
- Binary media types
- Minimum compression size
- Disable execute API endpoint
- Tags

### Resources and Methods
- Resource path and path part
- Parent resource relationships
- HTTP methods (GET, POST, PUT, DELETE, etc.)
- Authorization type (NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS)
- API key required
- Request validators
- Request parameters and models
- Integration type (HTTP, AWS, MOCK, HTTP_PROXY, AWS_PROXY)
- Integration endpoints and credentials
- Method responses

### Stages
- Stage name and description
- Deployment ID
- Stage variables
- Throttling settings (rate limit, burst limit)
- Cache cluster settings
- Cache encryption
- CloudWatch logging (INFO, ERROR)
- Access logging (format, destination ARN)
- X-Ray tracing enabled
- Client certificate ID
- Tags

### Authorizers
- Authorizer type (TOKEN, REQUEST, COGNITO_USER_POOLS)
- Identity source (header, query parameter)
- Authorizer URI (Lambda function)
- Authorizer credentials
- Identity validation expression
- Result TTL in cache

**Common Use Cases:**
- Inventory API Gateway REST APIs
- Audit authorization configurations
- Verify logging and monitoring settings
- Track usage plans and throttling
- Monitor stage configurations

**Security Checks:**
- ✅ Authorization enabled on methods
- ✅ API keys required where appropriate
- ✅ CloudWatch logging enabled
- ✅ X-Ray tracing enabled
- ✅ Resource policies configured (for private APIs)
- ✅ Usage plans and throttling configured
- ✅ SSL certificate configured for custom domains

---

## KMS (Key Management Service) (`kms`)
{: #kms-key-management-service-kms}

Extracts AWS KMS encryption keys, aliases, and grants.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:kms:key` | KMS keys | Key spec, usage, state, rotation, policy |
| `aws:kms:alias` | Key aliases | Alias name, target key |
| `aws:kms:grant` | Key grants | Operations, grantee principal, constraints |

**Extracted Configuration:**

### KMS Keys
- Key ID and ARN
- Key state (enabled, disabled, pending deletion)
- Customer master key spec (SYMMETRIC_DEFAULT, RSA, ECC)
- Key usage (ENCRYPT_DECRYPT, SIGN_VERIFY)
- Origin (AWS_KMS, EXTERNAL, AWS_CLOUDHSM)
- Key manager (AWS, CUSTOMER)
- Creation date and deletion date
- Key policy document
- Key rotation enabled status
- Multi-region key properties
- Description
- Tags

### Aliases
- Alias name and ARN
- Target key ID
- Creation date

### Grants
- Grant ID and name
- Key ID
- Grantee principal (IAM role/user ARN)
- Operations (Encrypt, Decrypt, GenerateDataKey, etc.)
- Constraints (encryption context)
- Retiring principal
- Creation date

**Common Use Cases:**
- Inventory KMS keys across regions
- Audit key policies and access
- Verify key rotation enabled
- Track key usage and grants
- Monitor key states and deletion

**Security Checks:**
- ✅ Key rotation enabled for customer-managed keys
- ✅ Key policies follow least privilege
- ✅ Keys not pending deletion (unless intended)
- ✅ Multi-region keys used appropriately
- ✅ Grants reviewed regularly
- ✅ External keys properly managed
- ✅ CloudTrail logging enabled for key usage

---

## App Runner (`apprunner`)
{: #app-runner-apprunner}

Extracts AWS App Runner service configurations and source connections.

| Resource Type | Description | Key Attributes |
|--------------|-------------|----------------|
| `aws:apprunner:service` | App Runner services | Source, runtime, network, health checks, scaling |
| `aws:apprunner:connection` | Source connections | Provider, status, connection name |

**Extracted Configuration:**

### App Runner Services
- Service name and ARN
- Service ID and URL
- Source configuration:
  - Code repository (GitHub, Bitbucket)
  - Container image registry (ECR Public, ECR)
  - Source directory and build command
  - Runtime (Python, Node.js, Java, .NET, Go, PHP, Ruby)
- Instance configuration:
  - CPU and memory
  - Instance role ARN
- Auto-scaling configuration:
  - Min/max size
  - Concurrency settings
- Health check configuration:
  - Protocol, path, interval, timeout
  - Healthy/unhealthy threshold
- Network configuration:
  - VPC connector
  - Egress type (public, VPC)
- Observability configuration:
  - CloudWatch Logs
  - X-Ray tracing
- Custom domain associations
- Encryption configuration (KMS key)
- Status and deployment status
- Tags

### App Runner Connections
- Connection name and ARN
- Provider type (GITHUB, BITBUCKET_CLOUD)
- Connection status
- Creation time

**Common Use Cases:**
- Inventory App Runner services
- Audit service configurations and scaling
- Verify network and VPC configurations
- Track custom domain associations
- Monitor health check settings

**Security Checks:**
- ✅ VPC connector configured for private resources
- ✅ IAM instance role follows least privilege
- ✅ Custom domain SSL/TLS configured
- ✅ Observability enabled (logs, tracing)
- ✅ Auto-scaling configured appropriately
- ✅ Health checks properly configured

---

## Extraction Examples

### Extract All AWS Resources

```bash
curl -X POST "http://localhost:8000/extraction/extract?provider=aws"
```

### Extract Specific Services

```bash
# Compute and storage only
curl -X POST "http://localhost:8000/extraction/extract?provider=aws&services=ec2,s3"

# Security-related services
curl -X POST "http://localhost:8000/extraction/extract?provider=aws&services=iam,kms,vpc"

# Networking services
curl -X POST "http://localhost:8000/extraction/extract?provider=aws&services=vpc,elb,cloudfront"

# Container services
curl -X POST "http://localhost:8000/extraction/extract?provider=aws&services=ecs,eks,lambda_extractor"
```

### Extract from Specific Regions and Accounts

```bash
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "accounts": ["123456789012", "210987654321"],
    "regions": ["us-east-1", "us-west-2"],
    "services": ["ec2", "s3", "rds"]
  }'
```

---

## Authentication Requirements

### IAM Permissions

To extract resources, the IAM user or role needs appropriate read-only permissions:

#### Minimum Required Policy (ReadOnlyAccess)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:GetBucket*",
        "s3:GetObject*",
        "s3:List*",
        "rds:Describe*",
        "lambda:Get*",
        "lambda:List*",
        "iam:Get*",
        "iam:List*",
        "kms:Describe*",
        "kms:List*",
        "elasticloadbalancing:Describe*",
        "ecs:Describe*",
        "ecs:List*",
        "eks:Describe*",
        "eks:List*",
        "cloudfront:Get*",
        "cloudfront:List*",
        "apigateway:GET",
        "apprunner:Describe*",
        "apprunner:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Recommended Managed Policies

```bash
# Attach ReadOnlyAccess managed policy
aws iam attach-user-policy \
  --user-name csp-scanner-user \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Or SecurityAudit for security-focused extraction
aws iam attach-user-policy \
  --user-name csp-scanner-user \
  --policy-arn arn:aws:iam::aws:policy/SecurityAudit
```

### Setup IAM User

```bash
# Create IAM user
aws iam create-user --user-name csp-scanner-user

# Attach ReadOnlyAccess policy
aws iam attach-user-policy \
  --user-name csp-scanner-user \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Create access key
aws iam create-access-key --user-name csp-scanner-user
```

### Setup IAM Role (for EC2/ECS/Lambda)

```bash
# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name csp-scanner-role \
  --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam attach-role-policy \
  --role-name csp-scanner-role \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name csp-scanner-profile

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name csp-scanner-profile \
  --role-name csp-scanner-role
```

### Configure Multiple Accounts

```yaml
# config/production.yaml
aws_accounts:
  - account_id: "123456789012"
    regions:
      - "us-east-1"
      - "us-west-2"
      - "eu-west-1"
  - account_id: "210987654321"
    regions:
      - "us-east-1"
      - "ap-southeast-1"

aws_access_key_id: "AKIAIOSFODNN7EXAMPLE"
aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

---

## Common Extraction Patterns

### Security Audit Extraction

```bash
# Extract security-relevant resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "services": [
      "iam",
      "kms",
      "vpc",
      "s3",
      "rds",
      "ec2"
    ]
  }'
```

### Cost Optimization Extraction

```bash
# Extract cost-related resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "services": [
      "ec2",
      "s3",
      "rds",
      "elb",
      "lambda_extractor"
    ]
  }'
```

### Compliance Audit Extraction

```bash
# Extract compliance-relevant resources
curl -X POST "http://localhost:8000/extraction/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "services": [
      "iam",
      "s3",
      "rds",
      "kms",
      "vpc",
      "cloudfront"
    ]
  }'
```

---

## Troubleshooting

### Common Issues

#### Access Denied Errors

```
Error: User is not authorized to perform action
```

**Solution**: Verify IAM permissions:
```bash
aws iam get-user-policy --user-name csp-scanner-user --policy-name scanner-policy
aws iam list-attached-user-policies --user-name csp-scanner-user
```

#### Invalid Credentials

```
Error: The security token included in the request is invalid
```

**Solution**: Verify credentials are correct:
```bash
aws sts get-caller-identity
```

#### Region Not Available

```
Error: Region not available or accessible
```

**Solution**: List available regions:
```bash
aws ec2 describe-regions --query 'Regions[].RegionName' --output table
```

#### Rate Limiting

```
Error: Rate exceeded
```

**Solution**: Configure throttling in extractor settings or request limit increase from AWS Support.

### Verification Commands

```bash
# Test AWS credentials
aws sts get-caller-identity

# List accessible regions
aws ec2 describe-regions

# Verify resource access
aws ec2 describe-instances --region us-east-1
aws s3 ls
aws rds describe-db-instances --region us-east-1
```

---

## See Also

- [AWS Setup Guide]({{ '/cloud-providers-aws.html' | relative_url }}) - Detailed authentication and configuration
- [Configuration Guide]({{ '/configuration.html' | relative_url }}) - Multi-account and region settings
- [API Reference]({{ '/api-reference.html' | relative_url }}) - Extraction API endpoints
- [Metadata Structure]({{ '/metadata-structure.html' | relative_url }}) - Output format specification
