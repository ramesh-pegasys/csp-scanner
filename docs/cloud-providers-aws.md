---
layout: default
title: AWS Setup
parent: Cloud Providers
nav_order: 1
---

# Amazon Web Services (AWS)

## Authentication Methods

### 1. IAM User Credentials (Development/Testing)

**Create IAM User:**
1. Go to AWS IAM Console
2. Create a new IAM user
3. Attach appropriate policies (e.g., `ReadOnlyAccess` or specific service read permissions)
4. Generate access keys

**Configure Credentials:**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### 2. AWS CLI Configuration

If you have AWS CLI installed:

```bash
aws configure
```

This creates credentials in `~/.aws/credentials` and region in `~/.aws/config`.

### 3. IAM Roles (Recommended for Production)

When running on EC2/ECS/EKS, use IAM roles attached to the instance/service.

**No explicit credentials needed** - the application automatically uses the instance role.

### 4. Environment Variables

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="secret..."
export AWS_DEFAULT_REGION="us-east-1"
export AWS_SESSION_TOKEN="token..."  # For temporary credentials
```

### 5. AWS Profile

```bash
export AWS_PROFILE="production"
```

Uses the specified profile from `~/.aws/credentials`.

## Required Permissions

For comprehensive scanning, your credentials should have read-only access to these services:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:Describe*",
                "s3:List*",
                "s3:Get*",
                "rds:Describe*",
                "lambda:List*",
                "lambda:Get*",
                "vpc:Describe*",
                "cloudfront:List*",
                "apigateway:GET",
                "elasticloadbalancing:Describe*",
                "ecs:Describe*",
                "ecs:List*",
                "eks:Describe*",
                "eks:List*",
                "apprunner:Describe*",
                "apprunner:List*",
                "kms:Describe*",
                "kms:List*",
                "iam:List*",
                "iam:Get*"
            ],
            "Resource": "*"
        }
    ]
}
```

**Predefined Policy:** `ReadOnlyAccess`

## Verification

Test your AWS credentials:

```bash
# Using AWS CLI
aws sts get-caller-identity

# Using Python
python -c "import boto3; print(boto3.Session().get_credentials())"
```

## Supported AWS Services

- **EC2**: Instances, Security Groups, Network Interfaces
- **S3**: Buckets with policies and configurations
- **RDS**: Database instances and clusters
- **Lambda**: Functions with configurations
- **IAM**: Users, Roles, Policies
- **VPC**: VPCs, Subnets, Route Tables, NAT Gateways
- **ECS**: Clusters, Services, Task Definitions
- **EKS**: Kubernetes clusters
- **ELB**: Application and Network Load Balancers
- **AppRunner**: Services
- **CloudFront**: Distributions
- **API Gateway**: REST APIs
- **KMS**: Keys and key policies

## Security Best Practices

1. **Use IAM Roles** instead of access keys when possible
2. **Rotate access keys** regularly
3. **Apply least privilege** principle
4. **Use MFA** for IAM users
5. **Monitor with CloudTrail** for audit logs

## Troubleshooting

### "Unable to locate credentials"
- Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set
- Verify credentials are not expired
- Test with `aws sts get-caller-identity`

### "Access denied"
- Verify IAM permissions include required actions
- Check if MFA is required for the operation
- Ensure you're using the correct AWS account/region

### "Region not supported"
- Some services have limited regional availability
- Check AWS service availability by region

## Production Deployment

- Use IAM roles on EC2/ECS/EKS
- Store credentials in AWS Secrets Manager or Parameter Store
- Use AWS Config for compliance monitoring

## Cost Optimization

- Use Spot Instances for testing
- Leverage AWS Free Tier for development
- Monitor costs with Cost Explorer
