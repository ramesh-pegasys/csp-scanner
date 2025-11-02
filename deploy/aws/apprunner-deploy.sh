#!/bin/bash
# AWS App Runner Deployment Script
# Deploy Cloud Artifact Extractor to AWS App Runner

set -e

# Configuration
APP_NAME="cloud-artifact-extractor"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP_NAME}"
DOCKER_IMAGE_TAG="${DOCKER_IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== AWS App Runner Deployment ===${NC}"

# Validate prerequisites
echo "Checking prerequisites..."
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: AWS_ACCOUNT_ID environment variable not set${NC}"
    exit 1
fi

# Build and push Docker image to ECR
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t ${APP_NAME}:${DOCKER_IMAGE_TAG} -f Dockerfile .

echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_URI}

# Create ECR repository if it doesn't exist
echo -e "${YELLOW}Ensuring ECR repository exists...${NC}"
aws ecr create-repository \
    --repository-name ${APP_NAME} \
    --region ${AWS_REGION} \
    --image-scan-on-push \
    2>/dev/null || true

echo -e "${YELLOW}Pushing image to ECR...${NC}"
docker tag ${APP_NAME}:${DOCKER_IMAGE_TAG} ${ECR_REPO_URI}:${DOCKER_IMAGE_TAG}
docker tag ${APP_NAME}:${DOCKER_IMAGE_TAG} ${ECR_REPO_URI}:latest
docker push ${ECR_REPO_URI}:${DOCKER_IMAGE_TAG}
docker push ${ECR_REPO_URI}:latest

# Get image URI
IMAGE_URI="${ECR_REPO_URI}:${DOCKER_IMAGE_TAG}"

# Create or update App Runner service
echo -e "${YELLOW}Creating/Updating App Runner service...${NC}"

# Check if service exists
if aws apprunner describe-service \
    --service-arn "arn:aws:apprunner:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${APP_NAME}/apprunner-service" \
    --region ${AWS_REGION} 2>/dev/null; then
    
    echo "Updating existing App Runner service..."
    aws apprunner update-service \
        --service-arn "arn:aws:apprunner:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${APP_NAME}/apprunner-service" \
        --source-configuration ImageRepository="{ImageIdentifier=${IMAGE_URI},ImageRepositoryType=ECR,ImageConfiguration={Port=8000}}" \
        --region ${AWS_REGION}
else
    echo "Creating new App Runner service..."
    
    # Create IAM role for App Runner
    echo "Creating IAM role for App Runner..."
    ROLE_NAME="${APP_NAME}-apprunner-role"
    
    # Check if role exists
    if ! aws iam get-role --role-name ${ROLE_NAME} 2>/dev/null; then
        aws iam create-role \
            --role-name ${ROLE_NAME} \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "apprunner.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }]
            }'
        
        # Attach policies
        aws iam attach-role-policy \
            --role-name ${ROLE_NAME} \
            --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
    fi
    
    ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
    
    # Create App Runner service
    aws apprunner create-service \
        --service-name apprunner-service \
        --source-configuration ImageRepository="{ImageIdentifier=${IMAGE_URI},ImageRepositoryType=ECR,ImageConfiguration={Port=8000,RuntimeEnvironmentVariables={ENABLED_PROVIDERS='[\"aws\",\"azure\",\"gcp\"]',DEBUG='false'}}}" \
        --instance-configuration InstanceRoleArn=${ROLE_ARN} \
        --region ${AWS_REGION}
fi

echo -e "${GREEN}✓ App Runner deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Check service status: aws apprunner describe-service --service-arn <service-arn> --region ${AWS_REGION}"
echo "2. View logs: aws logs tail /aws/apprunner/${APP_NAME}/apprunner-service/service-logs --follow"
echo "3. Get service URL from AWS Console: https://console.aws.amazon.com/apprunner/home?region=${AWS_REGION}"
