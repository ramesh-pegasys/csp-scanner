#!/bin/bash
# Azure Container Apps Deployment Script
# Deploy Cloud Artifact Extractor to Azure Container Apps

set -e

# Configuration
APP_NAME="cloud-artifact-extractor"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-$APP_NAME-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
REGISTRY_NAME="${AZURE_CONTAINER_REGISTRY_NAME:-${APP_NAME}acr}"
REGISTRY_SKU="${AZURE_CONTAINER_REGISTRY_SKU:-Basic}"
CONTAINER_APP_ENV="${APP_NAME}-env"
CONTAINER_APP_NAME="${APP_NAME}-app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Azure Container Apps Deployment ===${NC}"

# Validate prerequisites
echo "Checking prerequisites..."
command -v az >/dev/null 2>&1 || { echo "Azure CLI is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }

# Check if logged in to Azure
if ! az account show >/dev/null 2>&1; then
    echo "Logging into Azure..."
    az login
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Using subscription: $SUBSCRIPTION_ID"

# Create resource group
echo -e "${YELLOW}Creating resource group...${NC}"
az group create \
    --name ${RESOURCE_GROUP} \
    --location ${LOCATION}

# Create container registry
echo -e "${YELLOW}Creating Azure Container Registry...${NC}"
REGISTRY_URL="${REGISTRY_NAME}.azurecr.io"

az acr create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${REGISTRY_NAME} \
    --sku ${REGISTRY_SKU} \
    --location ${LOCATION} 2>/dev/null || true

# Build and push Docker image
echo -e "${YELLOW}Building and pushing Docker image...${NC}"

# Get ACR credentials
REGISTRY_USERNAME=$(az acr credential show --name ${REGISTRY_NAME} --query "username" -o tsv)
REGISTRY_PASSWORD=$(az acr credential show --name ${REGISTRY_NAME} --query "passwords[0].value" -o tsv)

# Build image
docker build -t ${REGISTRY_URL}/${APP_NAME}:latest -f Dockerfile .

# Login to registry
echo ${REGISTRY_PASSWORD} | docker login ${REGISTRY_URL} -u ${REGISTRY_USERNAME} --password-stdin

# Push image
docker push ${REGISTRY_URL}/${APP_NAME}:latest

# Create Log Analytics workspace
echo -e "${YELLOW}Creating Log Analytics workspace...${NC}"
WORKSPACE_NAME="${APP_NAME}-workspace"

WORKSPACE=$(az monitor log-analytics workspace create \
    --resource-group ${RESOURCE_GROUP} \
    --workspace-name ${WORKSPACE_NAME} \
    --location ${LOCATION} \
    --query id -o tsv 2>/dev/null || \
    az monitor log-analytics workspace show \
        --resource-group ${RESOURCE_GROUP} \
        --workspace-name ${WORKSPACE_NAME} \
        --query id -o tsv)

WORKSPACE_ID=$(echo $WORKSPACE | cut -d'/' -f9)
WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
    --resource-group ${RESOURCE_GROUP} \
    --workspace-name ${WORKSPACE_NAME} \
    --query primarySharedKey -o tsv)

# Create Container App Environment
echo -e "${YELLOW}Creating Container App environment...${NC}"

az containerapp env create \
    --name ${CONTAINER_APP_ENV} \
    --resource-group ${RESOURCE_GROUP} \
    --logs-workspace-id ${WORKSPACE_ID} \
    --logs-workspace-key ${WORKSPACE_KEY} \
    --location ${LOCATION} 2>/dev/null || true

# Create managed identity
echo -e "${YELLOW}Creating managed identity...${NC}"
IDENTITY_NAME="${APP_NAME}-identity"

az identity create \
    --name ${IDENTITY_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --location ${LOCATION} 2>/dev/null || true

IDENTITY_PRINCIPAL=$(az identity show \
    --resource-group ${RESOURCE_GROUP} \
    --name ${IDENTITY_NAME} \
    --query principalId -o tsv)

# Grant identity access to container registry
echo -e "${YELLOW}Granting managed identity access to registry...${NC}"

REGISTRY_RESOURCE_ID=$(az acr show \
    --name ${REGISTRY_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --query id -o tsv)

az role assignment create \
    --assignee ${IDENTITY_PRINCIPAL} \
    --role "AcrPull" \
    --scope ${REGISTRY_RESOURCE_ID} 2>/dev/null || true

# Create Container App
echo -e "${YELLOW}Creating Container App...${NC}"

az containerapp create \
    --name ${CONTAINER_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --environment ${CONTAINER_APP_ENV} \
    --image ${REGISTRY_URL}/${APP_NAME}:latest \
    --target-port 8000 \
    --ingress 'external' \
    --query properties.configuration.ingress.fqdn -o tsv \
    --cpu 1.0 --memory 2Gi \
    --min-replicas 2 \
    --max-replicas 10 \
    --registry-server ${REGISTRY_URL} \
    --registry-username ${REGISTRY_USERNAME} \
    --registry-password ${REGISTRY_PASSWORD} \
    --env-vars \
        ENABLED_PROVIDERS='["aws","azure","gcp"]' \
        DEBUG=false \
        CONFIG_FILE=/app/config/production.yaml \
    --secrets \
        jwt-secret=your-jwt-secret-key \
        scanner-endpoint=https://your-scanner-endpoint.com

# Update scaling rules
echo -e "${YELLOW}Configuring auto-scaling...${NC}"

az containerapp update \
    --name ${CONTAINER_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --min-replicas 2 \
    --max-replicas 10 \
    --set-env-vars CPU_TARGET=70 MEMORY_TARGET=80

# Get the FQDN
FQDN=$(az containerapp show \
    --name ${CONTAINER_APP_NAME} \
    --resource-group ${RESOURCE_GROUP} \
    --query properties.configuration.ingress.fqdn -o tsv)

echo -e "${GREEN}✓ Azure Container Apps deployment complete!${NC}"
echo ""
echo "Application URL: https://${FQDN}"
echo ""
echo "Next steps:"
echo "1. View logs: az containerapp logs show --name ${CONTAINER_APP_NAME} --resource-group ${RESOURCE_GROUP} --follow"
echo "2. View details: az containerapp show --name ${CONTAINER_APP_NAME} --resource-group ${RESOURCE_GROUP}"
echo "3. Test the endpoint: curl https://${FQDN}/api/v1/health/ready"
echo "4. Configure monitoring in Azure Portal"
