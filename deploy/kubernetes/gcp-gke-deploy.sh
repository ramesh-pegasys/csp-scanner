#!/bin/bash
# Google Cloud GKE Deployment Script
# Create and deploy to GCP GKE cluster

set -e

# Configuration
APP_NAME="cloud-artifact-extractor"
GCP_PROJECT_ID="${GCP_PROJECT_ID}"
GCP_REGION="${GCP_REGION:-us-central1}"
GCP_ZONE="${GCP_ZONE:-us-central1-a}"
CLUSTER_NAME="${CLUSTER_NAME:-${APP_NAME}-gke-cluster}"
NODE_COUNT="${NODE_COUNT:-2}"
MACHINE_TYPE="${MACHINE_TYPE:-n1-standard-2}"
K8S_VERSION="${K8S_VERSION:-1.28}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Google GKE Kubernetes Deployment ===${NC}"

# Validate prerequisites
command -v gcloud >/dev/null 2>&1 || { echo "Google Cloud SDK required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }

if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    exit 1
fi

# Set GCP project
gcloud config set project ${GCP_PROJECT_ID}

# Enable APIs
echo -e "${YELLOW}Enabling GCP APIs...${NC}"
gcloud services enable \
    container.googleapis.com \
    compute.googleapis.com \
    cloudresourcemanager.googleapis.com

# Create GKE cluster
echo -e "${YELLOW}Creating GKE cluster...${NC}"
gcloud container clusters create ${CLUSTER_NAME} \
    --region ${GCP_REGION} \
    --num-nodes ${NODE_COUNT} \
    --machine-type ${MACHINE_TYPE} \
    --cluster-version ${K8S_VERSION} \
    --enable-ip-alias \
    --enable-stackdriver-kubernetes \
    --addons HorizontalPodAutoscaling,HttpLoadBalancing \
    --workload-pool=${GCP_PROJECT_ID}.svc.id.goog \
    --enable-shielded-nodes \
    2>/dev/null || echo "Cluster may already exist"

# Get cluster credentials
echo -e "${YELLOW}Getting cluster credentials...${NC}"
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${GCP_REGION}

# Test connection
echo -e "${YELLOW}Testing cluster connection...${NC}"
kubectl cluster-info

# Create service account for Workload Identity
echo -e "${YELLOW}Setting up Workload Identity...${NC}"
GSA_NAME="${APP_NAME}"
KSA_NAME="cloud-artifact-extractor"
KSA_NAMESPACE="cloud-artifact-extractor"

# Create Google Service Account
gcloud iam service-accounts create ${GSA_NAME} \
    --display-name="${APP_NAME} Service Account" \
    --project=${GCP_PROJECT_ID} 2>/dev/null || true

# Grant roles to GSA
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member=serviceAccount:${GSA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/compute.instanceAdmin.v1 2>/dev/null || true

gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
    --member=serviceAccount:${GSA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/iam.securityReviewer 2>/dev/null || true

# Bind KSA to GSA
gcloud iam service-accounts add-iam-policy-binding \
    ${GSA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${GCP_PROJECT_ID}.svc.id.goog[${KSA_NAMESPACE}/${KSA_NAME}]" \
    --project=${GCP_PROJECT_ID} 2>/dev/null || true

# Apply Kubernetes manifests
echo -e "${YELLOW}Applying Kubernetes manifests...${NC}"
kubectl apply -f deploy/kubernetes/manifests/namespace.yaml
kubectl apply -f deploy/kubernetes/manifests/rbac.yaml
kubectl apply -f deploy/kubernetes/manifests/configmap.yaml
kubectl apply -f deploy/kubernetes/manifests/secret.yaml

# Annotate service account for Workload Identity
kubectl annotate serviceaccount cloud-artifact-extractor \
    -n cloud-artifact-extractor \
    iam.gke.io/gcp-service-account=${GSA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
    --overwrite

# Apply deployment manifests
kubectl apply -f deploy/kubernetes/manifests/deployment.yaml
kubectl apply -f deploy/kubernetes/manifests/service.yaml
kubectl apply -f deploy/kubernetes/manifests/hpa.yaml
kubectl apply -f deploy/kubernetes/manifests/pdb.yaml

# Wait for deployment
echo -e "${YELLOW}Waiting for deployment to be ready...${NC}"
kubectl rollout status deployment/cloud-artifact-extractor -n cloud-artifact-extractor

echo -e "${GREEN}✓ GKE Kubernetes deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Get service details: kubectl get svc -n cloud-artifact-extractor"
echo "2. Port forward: kubectl port-forward svc/cloud-artifact-extractor 8000:8000 -n cloud-artifact-extractor"
echo "3. View logs: kubectl logs -f deployment/cloud-artifact-extractor -n cloud-artifact-extractor"
echo "4. Apply Ingress: kubectl apply -f deploy/kubernetes/manifests/ingress.yaml"
echo "5. Get external IP: kubectl get svc -n cloud-artifact-extractor"
