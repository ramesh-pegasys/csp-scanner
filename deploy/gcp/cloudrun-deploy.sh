#!/bin/bash
# Ensure running from project root
cd "$(dirname "$0")/../../"

# Parse arguments
WITH_SECRETS=false
for arg in "$@"; do
    if [ "$arg" = "--withSecrets" ]; then
        WITH_SECRETS=true
    fi
done
# Google Cloud Run Deployment Script
# Deploy Cloud Artifact Extractor to Cloud Run

set -e

# Configuration
APP_NAME="cloud-artifact-extractor"
GCP_PROJECT_ID="${GCP_PROJECT_ID}"
GCP_REGION="${GCP_REGION:-us-central1}"
IMAGE_NAME="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${APP_NAME}/${APP_NAME}"
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
echo -e "${YELLOW}Building Docker image for linux/amd64...${NC}"
docker build --platform linux/amd64 --build-arg TARGETPLATFORM=linux/amd64 -t ${IMAGE_NAME}:latest -f Dockerfile .

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


# Secret management if --withSecrets is passed
if [ "$WITH_SECRETS" = true ]; then
    echo -e "${YELLOW}Creating/updating secrets...${NC}"

    # Helper to create/update secret and disable previous versions
    create_or_update_secret() {
        local secret_name="$1"
        local secret_value="$2"
        local tmpfile=$(mktemp)
        echo -n "$secret_value" > "$tmpfile"
        if gcloud secrets describe "$secret_name" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
            gcloud secrets versions add "$secret_name" --data-file="$tmpfile" --project="$GCP_PROJECT_ID"
        else
            gcloud secrets create "$secret_name" --data-file="$tmpfile" --replication-policy="automatic" --project="$GCP_PROJECT_ID"
        fi
        rm "$tmpfile"
        # Disable all previous versions except latest
        latest_version=$(gcloud secrets versions list "$secret_name" --project="$GCP_PROJECT_ID" --format="value(name)" | head -n 1 | awk -F/ '{print $NF}')
        for version in $(gcloud secrets versions list "$secret_name" --project="$GCP_PROJECT_ID" --format="value(name)" | awk -F/ '{print $NF}'); do
            if [ "$version" != "$latest_version" ]; then
                gcloud secrets versions disable "$secret_name" --version="$version" --project="$GCP_PROJECT_ID" || true
            fi
        done
    }

    # Upload config file as secret
    if [ -f "app/config/production.yaml" ]; then
        create_or_update_secret "$CONFIG_SECRET" "$(cat app/config/production.yaml)"
    else
        echo -e "${RED}Error: app/config/production.yaml not found${NC}"
        exit 1
    fi

    # Create/update secrets for AWS, AZURE, JWT
    [ -n "$AWS_ACCESS_KEY_ID" ] && create_or_update_secret "$AWS_ACCESS_KEY_ID_SECRET" "$AWS_ACCESS_KEY_ID"
    [ -n "$AWS_SECRET_ACCESS_KEY" ] && create_or_update_secret "$AWS_SECRET_ACCESS_KEY_SECRET" "$AWS_SECRET_ACCESS_KEY"
    [ -n "$AWS_SESSION_TOKEN" ] && create_or_update_secret "$AWS_SESSION_TOKEN_SECRET" "$AWS_SESSION_TOKEN"
    [ -n "$AZURE_TENANT_ID" ] && create_or_update_secret "$AZURE_TENANT_ID_SECRET" "$AZURE_TENANT_ID"
    [ -n "$AZURE_CLIENT_ID" ] && create_or_update_secret "$AZURE_CLIENT_ID_SECRET" "$AZURE_CLIENT_ID"
    [ -n "$AZURE_CLIENT_SECRET" ] && create_or_update_secret "$AZURE_CLIENT_SECRET_SECRET" "$AZURE_CLIENT_SECRET"
    [ -n "$JWT_SECRET_KEY" ] && create_or_update_secret "$JWT_SECRET_KEY_SECRET" "$JWT_SECRET_KEY"
    [ -n "$JWT_ALGORITHM" ] && create_or_update_secret "$JWT_ALGORITHM_SECRET" "$JWT_ALGORITHM"
    [ -n "$JWT_EXPIRE_DAYS" ] && create_or_update_secret "$JWT_EXPIRE_DAYS_SECRET" "$JWT_EXPIRE_DAYS"
fi

# Deploy Cloud Run with secrets mounted
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
        --service-account=${SERVICE_ACCOUNT} \
        --project=${GCP_PROJECT_ID} \
        --set-secrets="CONFIG_FILE=${CONFIG_SECRET}:latest,AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID_SECRET}:latest,AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY_SECRET}:latest,AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN_SECRET}:latest,AZURE_TENANT_ID=${AZURE_TENANT_ID_SECRET}:latest,AZURE_CLIENT_ID=${AZURE_CLIENT_ID_SECRET}:latest,AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET_SECRET}:latest,JWT_SECRET_KEY=${JWT_SECRET_KEY_SECRET}:latest,JWT_ALGORITHM=${JWT_ALGORITHM_SECRET}:latest,JWT_EXPIRE_DAYS=${JWT_EXPIRE_DAYS_SECRET}:latest" \
        --set-env-vars="ENVIRONMENT=production,DEBUG=false,MAX_CONCURRENT_EXTRACTORS=20,BATCH_SIZE=200,BATCH_DELAY_SECONDS=0.1,TRANSPORT_TYPE=null,TRANSPORT_TIMEOUT_SECONDS=60,TRANSPORT_MAX_RETRIES=5,SCANNER_ENDPOINT_URL=${SCANNER_ENDPOINT_URL:-}" 

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
