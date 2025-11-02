#!/bin/bash
# AWS EKS Deployment Script
# Create and deploy to AWS EKS cluster

set -e

# Configuration
APP_NAME="cloud-artifact-extractor"
CLUSTER_NAME="${CLUSTER_NAME:-${APP_NAME}-eks-cluster}"
AWS_REGION="${AWS_REGION:-us-east-1}"
NODE_GROUP_NAME="${APP_NAME}-node-group"
NODE_COUNT="${NODE_COUNT:-2}"
NODE_INSTANCE_TYPE="${NODE_INSTANCE_TYPE:-t3.medium}"
K8S_VERSION="${K8S_VERSION:-1.28}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== AWS EKS Kubernetes Deployment ===${NC}"

# Validate prerequisites
command -v aws >/dev/null 2>&1 || { echo "AWS CLI required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }
command -v eksctl >/dev/null 2>&1 || { echo "eksctl required. Install from: https://eksctl.io/"; exit 1; }

# Check if cluster exists
echo -e "${YELLOW}Checking for existing EKS cluster...${NC}"
CLUSTER_EXISTS=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} 2>/dev/null || echo "NONE")

if [ "${CLUSTER_EXISTS}" = "NONE" ]; then
    echo -e "${YELLOW}Creating EKS cluster...${NC}"
    eksctl create cluster \
        --name ${CLUSTER_NAME} \
        --region ${AWS_REGION} \
        --version ${K8S_VERSION} \
        --nodegroup-name ${NODE_GROUP_NAME} \
        --node-type ${NODE_INSTANCE_TYPE} \
        --nodes ${NODE_COUNT} \
        --with-oidc \
        --enable-ssm
else
    echo "Cluster ${CLUSTER_NAME} already exists"
fi

# Update kubeconfig
echo -e "${YELLOW}Updating kubeconfig...${NC}"
aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${AWS_REGION}

# Test connection
echo -e "${YELLOW}Testing cluster connection...${NC}"
kubectl cluster-info

# Create OIDC provider for Workload Identity (if not exists)
echo -e "${YELLOW}Setting up OIDC provider...${NC}"
OIDC_ID=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} \
    --query 'cluster.identity.oidc.issuer' --output text | cut -d '/' -f 5)

if ! aws iam list-open-id-connect-providers | grep -q ${OIDC_ID}; then
    eksctl utils associate-iam-oidc-provider \
        --cluster=${CLUSTER_NAME} \
        --region=${AWS_REGION} \
        --approve
fi

# Create IAM role for service account
echo -e "${YELLOW}Creating IAM role for service account...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_NAME="${APP_NAME}-eks-role"

# Create trust policy
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/oidc.eks.${AWS_REGION}.amazonaws.com/id/${OIDC_ID}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.${AWS_REGION}.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:cloud-artifact-extractor:cloud-artifact-extractor"
        }
      }
    }
  ]
}
EOF

# Create role if it doesn't exist
if ! aws iam get-role --role-name ${ROLE_NAME} 2>/dev/null; then
    aws iam create-role \
        --role-name ${ROLE_NAME} \
        --assume-role-policy-document file:///tmp/trust-policy.json
fi

# Attach policies
aws iam attach-role-policy \
    --role-name ${ROLE_NAME} \
    --policy-arn arn:aws:iam::aws:policy/EC2ReadOnlyAccess 2>/dev/null || true

aws iam attach-role-policy \
    --role-name ${ROLE_NAME} \
    --policy-arn arn:aws:iam::aws:policy/IAMReadOnlyAccess 2>/dev/null || true

# Apply Kubernetes manifests
echo -e "${YELLOW}Applying Kubernetes manifests...${NC}"
kubectl apply -f deploy/kubernetes/manifests/namespace.yaml
kubectl apply -f deploy/kubernetes/manifests/rbac.yaml
kubectl apply -f deploy/kubernetes/manifests/configmap.yaml
kubectl apply -f deploy/kubernetes/manifests/secret.yaml

# Update service account annotation for IRSA
kubectl annotate serviceaccount cloud-artifact-extractor \
    -n cloud-artifact-extractor \
    eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME} \
    --overwrite

# Apply deployment manifests
kubectl apply -f deploy/kubernetes/manifests/deployment.yaml
kubectl apply -f deploy/kubernetes/manifests/service.yaml
kubectl apply -f deploy/kubernetes/manifests/hpa.yaml
kubectl apply -f deploy/kubernetes/manifests/pdb.yaml

# Wait for deployment
echo -e "${YELLOW}Waiting for deployment to be ready...${NC}"
kubectl rollout status deployment/cloud-artifact-extractor -n cloud-artifact-extractor

echo -e "${GREEN}✓ EKS Kubernetes deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Get service details: kubectl get svc -n cloud-artifact-extractor"
echo "2. Port forward: kubectl port-forward svc/cloud-artifact-extractor 8000:8000 -n cloud-artifact-extractor"
echo "3. View logs: kubectl logs -f deployment/cloud-artifact-extractor -n cloud-artifact-extractor"
echo "4. Apply Ingress: kubectl apply -f deploy/kubernetes/manifests/ingress.yaml"
echo "5. Apply networking: kubectl apply -f deploy/kubernetes/manifests/networkpolicy.yaml"
