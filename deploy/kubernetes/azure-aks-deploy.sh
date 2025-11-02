#!/bin/bash
# Azure AKS Deployment Script
# Create and deploy to Azure AKS cluster

set -e

# Configuration
APP_NAME="cloud-artifact-extractor"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-${APP_NAME}-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
CLUSTER_NAME="${CLUSTER_NAME:-${APP_NAME}-aks-cluster}"
NODE_COUNT="${NODE_COUNT:-2}"
VM_SKU="${VM_SKU:-Standard_B2s}"
K8S_VERSION="${K8S_VERSION:-1.28}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Azure AKS Kubernetes Deployment ===${NC}"

# Validate prerequisites
command -v az >/dev/null 2>&1 || { echo "Azure CLI required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }

# Check Azure login
if ! az account show >/dev/null 2>&1; then
    az login
fi

# Create resource group
echo -e "${YELLOW}Creating resource group...${NC}"
az group create \
    --name ${RESOURCE_GROUP} \
    --location ${LOCATION}

# Create AKS cluster
echo -e "${YELLOW}Creating AKS cluster...${NC}"
az aks create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${CLUSTER_NAME} \
    --kubernetes-version ${K8S_VERSION} \
    --node-count ${NODE_COUNT} \
    --vm-set-type VirtualMachineScaleSets \
    --load-balancer-sku standard \
    --enable-managed-identity \
    --enable-addons monitoring,azure-policy \
    --node-vm-size ${VM_SKU} \
    --network-plugin azure \
    --service-principal-prefix ${APP_NAME} \
    2>/dev/null || echo "Cluster may already exist"

# Get cluster credentials
echo -e "${YELLOW}Getting cluster credentials...${NC}"
az aks get-credentials \
    --resource-group ${RESOURCE_GROUP} \
    --name ${CLUSTER_NAME}

# Test connection
echo -e "${YELLOW}Testing cluster connection...${NC}"
kubectl cluster-info

# Create managed identity for pods
echo -e "${YELLOW}Setting up Managed Identity...${NC}"
IDENTITY_NAME="${APP_NAME}-pod-identity"

az identity create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${IDENTITY_NAME} \
    2>/dev/null || true

IDENTITY_PRINCIPAL=$(az identity show \
    --resource-group ${RESOURCE_GROUP} \
    --name ${IDENTITY_NAME} \
    --query principalId -o tsv)

IDENTITY_CLIENT_ID=$(az identity show \
    --resource-group ${RESOURCE_GROUP} \
    --name ${IDENTITY_NAME} \
    --query clientId -o tsv)

# Grant AKS managed identity to use pod identity
CLUSTER_PRINCIPAL=$(az aks show \
    --resource-group ${RESOURCE_GROUP} \
    --name ${CLUSTER_NAME} \
    --query identity.principalId -o tsv)

az role assignment create \
    --role "Managed Identity Operator" \
    --assignee ${CLUSTER_PRINCIPAL} \
    --scope /subscriptions/$(az account show --query id -o tsv)/resourcegroups/${RESOURCE_GROUP}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/${IDENTITY_NAME} \
    2>/dev/null || true

# Grant permissions to managed identity
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az role assignment create \
    --role "Reader" \
    --assignee ${IDENTITY_PRINCIPAL} \
    --scope /subscriptions/${SUBSCRIPTION_ID} \
    2>/dev/null || true

# Apply Kubernetes manifests
echo -e "${YELLOW}Applying Kubernetes manifests...${NC}"
kubectl apply -f deploy/kubernetes/manifests/namespace.yaml
kubectl apply -f deploy/kubernetes/manifests/rbac.yaml
kubectl apply -f deploy/kubernetes/manifests/configmap.yaml
kubectl apply -f deploy/kubernetes/manifests/secret.yaml

# Apply deployment manifests
kubectl apply -f deploy/kubernetes/manifests/deployment.yaml
kubectl apply -f deploy/kubernetes/manifests/service.yaml
kubectl apply -f deploy/kubernetes/manifests/hpa.yaml
kubectl apply -f deploy/kubernetes/manifests/pdb.yaml

# Wait for deployment
echo -e "${YELLOW}Waiting for deployment to be ready...${NC}"
kubectl rollout status deployment/cloud-artifact-extractor -n cloud-artifact-extractor

echo -e "${GREEN}✓ AKS Kubernetes deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Get service details: kubectl get svc -n cloud-artifact-extractor"
echo "2. Port forward: kubectl port-forward svc/cloud-artifact-extractor 8000:8000 -n cloud-artifact-extractor"
echo "3. View logs: kubectl logs -f deployment/cloud-artifact-extractor -n cloud-artifact-extractor"
echo "4. Apply Ingress: kubectl apply -f deploy/kubernetes/manifests/ingress.yaml"
echo "5. Get external IP: kubectl get svc -n cloud-artifact-extractor"
