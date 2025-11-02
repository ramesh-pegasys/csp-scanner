#!/bin/bash
# Undeploy and cleanup Cloud Artifact Extractor from Google Cloud Run
# Usage: bash deploy/gcp/cloudrun-undeploy.sh

set -e

APP_NAME="cloud-artifact-extractor"
GCP_PROJECT_ID="${GCP_PROJECT_ID}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_ACCOUNT="${APP_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# Secret names
CONFIG_SECRET="${APP_NAME}-config-${APP_NAME}"
AWS_ACCESS_KEY_ID_SECRET="${APP_NAME}-aws-access-key-id"
AWS_SECRET_ACCESS_KEY_SECRET="${APP_NAME}-aws-secret-access-key"
AWS_SESSION_TOKEN_SECRET="${APP_NAME}-aws-session-token"
AZURE_TENANT_ID_SECRET="${APP_NAME}-azure-tenant-id"
AZURE_CLIENT_ID_SECRET="${APP_NAME}-azure-client-id"
AZURE_CLIENT_SECRET_SECRET="${APP_NAME}-azure-client-secret"
JWT_SECRET_KEY_SECRET="${APP_NAME}-jwt-secret-key"
JWT_ALGORITHM_SECRET="${APP_NAME}-jwt-algorithm"
JWT_EXPIRE_DAYS_SECRET="${APP_NAME}-jwt-expire-days"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Cloud Run Undeploy & Cleanup ===${NC}"

if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    exit 1
fi

echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project ${GCP_PROJECT_ID}

echo -e "${YELLOW}Deleting Cloud Run service...${NC}"
gcloud run services delete ${APP_NAME} --region=${GCP_REGION} --platform=managed --quiet || true

echo -e "${YELLOW}Deleting Artifact Registry repository...${NC}"
gcloud artifacts repositories delete ${APP_NAME} --location=${GCP_REGION} --quiet || true

echo -e "${YELLOW}Deleting service account...${NC}"
gcloud iam service-accounts delete ${SERVICE_ACCOUNT} --quiet || true

echo -e "${YELLOW}Deleting secrets...${NC}"
for secret in "$CONFIG_SECRET" "$AWS_ACCESS_KEY_ID_SECRET" "$AWS_SECRET_ACCESS_KEY_SECRET" "$AWS_SESSION_TOKEN_SECRET" "$AZURE_TENANT_ID_SECRET" "$AZURE_CLIENT_ID_SECRET" "$AZURE_CLIENT_SECRET_SECRET" "$JWT_SECRET_KEY_SECRET" "$JWT_ALGORITHM_SECRET" "$JWT_EXPIRE_DAYS_SECRET"; do
    gcloud secrets delete "$secret" --quiet --project="$GCP_PROJECT_ID" || true
done

echo -e "${YELLOW}Deleting Cloud Scheduler job...${NC}"
JOB_NAME="${APP_NAME}-scheduler"
gcloud scheduler jobs delete "$JOB_NAME" --location=${GCP_REGION} --quiet || true

echo -e "${YELLOW}Deleting Cloud Logging sink...${NC}"
gcloud logging sinks delete ${APP_NAME}-errors --quiet --project=${GCP_PROJECT_ID} || true

echo -e "${GREEN}✓ Cloud Run undeploy and cleanup complete!${NC}"
