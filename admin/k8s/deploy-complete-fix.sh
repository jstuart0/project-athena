#!/bin/bash
#
# Complete Fix for Admin Interface - OIDC Authentication and Settings
# This script fixes all authentication issues and deploys the complete solution
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Athena Admin Interface - Complete Fix${NC}"
echo -e "${GREEN}=========================================${NC}"

# Configuration
REGISTRY="192.168.10.222:30500"
NAMESPACE="athena-admin"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Step 1: Build Docker images with kubectl included
echo -e "${GREEN}Building Docker images with kubectl support...${NC}"

# Build backend with kubectl
cd ../backend
echo "Building backend with kubectl and OIDC settings management..."
docker build --platform linux/amd64 -t athena-admin-backend:fix-${TIMESTAMP} .

# Build frontend
cd ../frontend
echo "Building frontend with OIDC UI..."
docker build --platform linux/amd64 -t athena-admin-frontend:fix-${TIMESTAMP} .

# Step 2: Tag and push images
echo -e "${GREEN}Pushing images to Thor registry...${NC}"
docker tag athena-admin-backend:fix-${TIMESTAMP} ${REGISTRY}/athena-admin-backend:fix-${TIMESTAMP}
docker tag athena-admin-backend:fix-${TIMESTAMP} ${REGISTRY}/athena-admin-backend:latest
docker tag athena-admin-frontend:fix-${TIMESTAMP} ${REGISTRY}/athena-admin-frontend:fix-${TIMESTAMP}
docker tag athena-admin-frontend:fix-${TIMESTAMP} ${REGISTRY}/athena-admin-frontend:latest

docker push ${REGISTRY}/athena-admin-backend:fix-${TIMESTAMP}
docker push ${REGISTRY}/athena-admin-backend:latest
docker push ${REGISTRY}/athena-admin-frontend:fix-${TIMESTAMP}
docker push ${REGISTRY}/athena-admin-frontend:latest

# Step 3: Apply RBAC permissions
echo -e "${GREEN}Applying RBAC permissions...${NC}"
cd ../k8s
kubectl apply -f rbac.yaml

# Step 4: Update deployment with service account
echo -e "${GREEN}Updating deployment configuration...${NC}"
kubectl apply -f deployment.yaml

# Step 5: Force pod restart to pick up all changes
echo -e "${GREEN}Restarting pods with new configuration...${NC}"
kubectl -n ${NAMESPACE} rollout restart deployment/athena-admin-backend
kubectl -n ${NAMESPACE} rollout restart deployment/athena-admin-frontend

# Step 6: Wait for rollout
echo -e "${GREEN}Waiting for deployments to be ready...${NC}"
kubectl -n ${NAMESPACE} rollout status deployment/athena-admin-backend --timeout=300s
kubectl -n ${NAMESPACE} rollout status deployment/athena-admin-frontend --timeout=300s

# Step 7: Verify pod status
echo -e "${GREEN}Verifying pod status...${NC}"
kubectl -n ${NAMESPACE} get pods

# Step 8: Check backend logs for any errors
echo -e "${GREEN}Checking backend logs...${NC}"
kubectl -n ${NAMESPACE} logs deployment/athena-admin-backend --tail=20

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Admin Interface is now available at:"
echo "  • https://athena-admin.xmojo.net"
echo ""
echo "✅ Fixed Issues:"
echo "  • OIDC authentication with real Authentik credentials"
echo "  • Automatic Kubernetes secret updates for OIDC settings"
echo "  • RBAC permissions for backend to manage secrets"
echo "  • kubectl installed in backend container"
echo ""
echo "🔧 Test the Fixed Features:"
echo "  1. Login should work with Authentik SSO"
echo "  2. Navigate to Settings tab"
echo "  3. OIDC settings can be viewed and updated"
echo "  4. Changes will automatically update Kubernetes secrets"
echo ""