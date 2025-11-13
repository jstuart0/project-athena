#!/bin/bash
#
# Deploy Admin Interface with OIDC Settings Update
# Builds AMD64 images and deploys to Thor cluster
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Athena Admin Interface - OIDC Update${NC}"
echo -e "${GREEN}=========================================${NC}"

# Configuration
REGISTRY="192.168.10.222:30500"
NAMESPACE="athena-admin"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Step 1: Build Docker images with OIDC updates
echo -e "${GREEN}Building Docker images (AMD64 architecture)...${NC}"

# Build backend
cd ../backend
echo "Building backend with OIDC settings API..."
docker build --platform linux/amd64 -t athena-admin-backend:oidc-${TIMESTAMP} .

# Build frontend
cd ../frontend
echo "Building frontend with OIDC settings UI..."
docker build --platform linux/amd64 -t athena-admin-frontend:oidc-${TIMESTAMP} .

# Step 2: Tag images for registry
echo -e "${GREEN}Tagging images for Thor registry...${NC}"
docker tag athena-admin-backend:oidc-${TIMESTAMP} ${REGISTRY}/athena-admin-backend:oidc-${TIMESTAMP}
docker tag athena-admin-backend:oidc-${TIMESTAMP} ${REGISTRY}/athena-admin-backend:latest
docker tag athena-admin-frontend:oidc-${TIMESTAMP} ${REGISTRY}/athena-admin-frontend:oidc-${TIMESTAMP}
docker tag athena-admin-frontend:oidc-${TIMESTAMP} ${REGISTRY}/athena-admin-frontend:latest

# Step 3: Push to registry
echo -e "${GREEN}Pushing images to Thor registry...${NC}"
docker push ${REGISTRY}/athena-admin-backend:oidc-${TIMESTAMP}
docker push ${REGISTRY}/athena-admin-backend:latest
docker push ${REGISTRY}/athena-admin-frontend:oidc-${TIMESTAMP}
docker push ${REGISTRY}/athena-admin-frontend:latest

# Step 4: Update deployment
echo -e "${GREEN}Updating Kubernetes deployment...${NC}"
cd ../k8s

# Force pod restart to pick up new images
kubectl -n ${NAMESPACE} rollout restart deployment/athena-admin-backend
kubectl -n ${NAMESPACE} rollout restart deployment/athena-admin-frontend

# Step 5: Wait for rollout
echo -e "${GREEN}Waiting for deployment to complete...${NC}"
kubectl -n ${NAMESPACE} rollout status deployment/athena-admin-backend --timeout=300s
kubectl -n ${NAMESPACE} rollout status deployment/athena-admin-frontend --timeout=300s

# Step 6: Verify pods
echo -e "${GREEN}Verifying pod status...${NC}"
kubectl -n ${NAMESPACE} get pods

# Step 7: Show ingress URL
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Admin Interface with OIDC Settings available at:"
echo "  • https://athena-admin.xmojo.net"
echo ""
echo "OIDC Settings Features:"
echo "  • View current OIDC configuration"
echo "  • Test OIDC provider connection"
echo "  • Update OIDC settings (admin only)"
echo ""
echo "To test the new OIDC settings:"
echo "  1. Login to the admin interface"
echo "  2. Navigate to Settings tab"
echo "  3. View/update OIDC Authentication Settings"
echo ""