#!/bin/bash
# Google Cloud Run Deployment Script
# Deploy Cloud Artifact Extractor to Cloud Run

set -e

# Configuration
APP_NAME="cloud-artifact-extractor"
GCP_PROJECT_ID="${GCP_PROJECT_ID}"
GCP_REGION="${GCP_REGION:-us-central1}"
IMAGE_NAME="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${APP_NAME}/${APP_NAME}"
SERVICE_ACCOUNT="${APP_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Google Cloud Run Deployment ===${NC}"

# Validate prerequisites
echo "Checking prerequisites..."
command -v gcloud >/dev/null 2>&1 || { echo "Google Cloud SDK is required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required"; exit 1; }

if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    exit 1
fi

# Set GCP project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project ${GCP_PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}Enabling required GCP APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    compute.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudtasks.googleapis.com \
    logging.googleapis.com

# Create Artifact Registry repository
echo -e "${YELLOW}Setting up Artifact Registry...${NC}"
gcloud artifacts repositories create ${APP_NAME} \
    --repository-format=docker \
    --location=${GCP_REGION} \
    --project=${GCP_PROJECT_ID} 2>/dev/null || true

# Configure Docker for Artifact Registry
echo -e "${YELLOW}Configuring Docker authentication...${NC}"
gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev

# Build and push Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:latest -f Dockerfile .

echo -e "${YELLOW}Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_NAME}:latest

# Create service account if it doesn't exist
echo -e "${YELLOW}Setting up service account...${NC}"
gcloud iam service-accounts create ${APP_NAME} \
    --display-name="Cloud Artifact Extractor Service Account" \
    --project=${GCP_PROJECT_ID} 2>/dev/null || true

# Grant necessary roles
echo "Granting IAM roles..."
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member=serviceAccount:${SERVICE_ACCOUNT} \
    --role=roles/compute.instanceAdmin.v1 \
    --condition=None 2>/dev/null || true

gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member=serviceAccount:${SERVICE_ACCOUNT} \
    --role=roles/iam.securityReviewer \
    --condition=None 2>/dev/null || true

gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member=serviceAccount:${SERVICE_ACCOUNT} \
    --role=roles/logging.logWriter \
    --condition=None 2>/dev/null || true

# Create Cloud Run service
echo -e "${YELLOW}Creating Cloud Run service...${NC}"

gcloud run deploy ${APP_NAME} \
    --image=${IMAGE_NAME}:latest \
    --platform=managed \
    --region=${GCP_REGION} \
    --allow-unauthenticated \
    --port=8000 \
    --memory=2Gi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=100 \
    --timeout=3600 \
    --set-env-vars="ENABLED_PROVIDERS=[\"aws\",\"azure\",\"gcp\"],DEBUG=false,CONFIG_FILE=/app/config/production.yaml" \
    --service-account=${SERVICE_ACCOUNT} \
    --project=${GCP_PROJECT_ID}

# Get service URL
SERVICE_URL=$(gcloud run services describe ${APP_NAME} \
    --platform=managed \
    --region=${GCP_REGION} \
    --format='value(status.url)' \
    --project=${GCP_PROJECT_ID})

# Create Cloud Scheduler job for periodic extractions (optional)
echo -e "${YELLOW}Setting up Cloud Scheduler for periodic extractions...${NC}"

JOB_NAME="${APP_NAME}-scheduler"

gcloud scheduler jobs create http ${JOB_NAME} \
    --location=${GCP_REGION} \
    --schedule="0 */6 * * *" \
    --uri="${SERVICE_URL}/api/v1/extraction/extract" \
    --http-method=POST \
    --oidc-service-account-email=${SERVICE_ACCOUNT} \
    --oidc-token-audience=${SERVICE_URL} \
    --project=${GCP_PROJECT_ID} \
    --message-body='{"provider":"all","extract_type":"full"}' 2>/dev/null || true

# Create Cloud Logging sink for monitoring
echo -e "${YELLOW}Setting up monitoring...${NC}"

gcloud logging sinks create ${APP_NAME}-errors \
    logging.googleapis.com/projects/${GCP_PROJECT_ID}/logs/cloud-artifact-extractor-errors \
    --log-filter='resource.type="cloud_run_revision" AND jsonPayload.level="ERROR"' \
    --project=${GCP_PROJECT_ID} 2>/dev/null || true

echo -e "${GREEN}✓ Cloud Run deployment complete!${NC}"
echo ""
echo "Service Details:"
echo "URL: ${SERVICE_URL}"
echo "Service Account: ${SERVICE_ACCOUNT}"
echo ""
echo "Next steps:"
echo "1. View logs: gcloud run logs read ${APP_NAME} --region=${GCP_REGION} --limit=50"
echo "2. View service: gcloud run services describe ${APP_NAME} --region=${GCP_REGION}"
echo "3. Test endpoint: curl ${SERVICE_URL}/api/v1/health/ready"
echo "4. Configure environment: gcloud run services update ${APP_NAME} --region=${GCP_REGION} --set-env-vars KEY=value"
echo "5. Set up Cloud Monitoring alerts: gcloud monitoring policies create --policy=<policy.yaml>"
