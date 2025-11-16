#!/bin/bash
#
# Build and Deploy Admin Interface to Thor Kubernetes Cluster
#
# This script:
# 1. Builds Docker images for admin backend and frontend
# 2. Pushes them to Thor's registry
# 3. Creates secrets
# 4. Deploys to Thor cluster
#
# Prerequisites:
# - kubectl configured with thor context
# - Docker running locally
# - Access to Thor cluster registry (192.168.10.222:30500)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="192.168.10.222:30500"
BACKEND_IMAGE="athena-admin-backend"
FRONTEND_IMAGE="athena-admin-frontend"
VERSION="v1.0.0"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Athena Admin Interface Deployment${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check kubectl context
CURRENT_CONTEXT=$(kubectl config current-context)
if [ "$CURRENT_CONTEXT" != "thor" ]; then
    echo -e "${YELLOW}Switching to thor context...${NC}"
    kubectl config use-context thor
fi

# Verify cluster access
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Thor cluster${NC}"
    echo -e "${RED}Please ensure you have access to 192.168.10.222:6443${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"

# Step 1: Build Docker images
echo ""
echo -e "${GREEN}Step 1: Building Docker images...${NC}"

# Build backend
echo "Building admin backend..."
cd ../backend
docker build --platform linux/amd64 -t ${BACKEND_IMAGE}:${VERSION} -t ${BACKEND_IMAGE}:latest .

# Build frontend
echo "Building admin frontend with sidebar layout..."
cd ../frontend

# Verify required files exist
if [ ! -f index.html ]; then
    echo -e "${RED}Error: index.html not found${NC}"
    exit 1
fi

if [ ! -f app.js ]; then
    echo -e "${RED}Error: app.js not found${NC}"
    exit 1
fi

# Create nginx.conf if it doesn't exist or update it for the new layout
cat > nginx.conf << 'EOF'
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/javascript application/json;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files $uri $uri/ /index.html;
        # Ensure proper MIME types
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
    }

    # API proxy to backend
    location /api {
        proxy_pass http://athena-admin-backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check
    location /health {
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
EOF

docker build --platform linux/amd64 -t ${FRONTEND_IMAGE}:${VERSION} -t ${FRONTEND_IMAGE}:latest .

echo -e "${GREEN}✓ Docker images built${NC}"

# Step 2: Tag and push images
echo ""
echo -e "${GREEN}Step 2: Pushing images to Thor registry...${NC}"

# Tag images for registry
docker tag ${BACKEND_IMAGE}:latest ${REGISTRY}/${BACKEND_IMAGE}:latest
docker tag ${BACKEND_IMAGE}:${VERSION} ${REGISTRY}/${BACKEND_IMAGE}:${VERSION}
docker tag ${FRONTEND_IMAGE}:latest ${REGISTRY}/${FRONTEND_IMAGE}:latest
docker tag ${FRONTEND_IMAGE}:${VERSION} ${REGISTRY}/${FRONTEND_IMAGE}:${VERSION}

# Push images
echo "Pushing backend image..."
docker push ${REGISTRY}/${BACKEND_IMAGE}:latest
docker push ${REGISTRY}/${BACKEND_IMAGE}:${VERSION}

echo "Pushing frontend image..."
docker push ${REGISTRY}/${FRONTEND_IMAGE}:latest
docker push ${REGISTRY}/${FRONTEND_IMAGE}:${VERSION}

echo -e "${GREEN}✓ Images pushed to registry${NC}"

# Step 3: Create secrets
echo ""
echo -e "${GREEN}Step 3: Creating Kubernetes secrets...${NC}"

cd ../k8s
./create-secrets.sh

echo -e "${GREEN}✓ Secrets created${NC}"

# Step 4: Apply deployment manifests
echo ""
echo -e "${GREEN}Step 4: Deploying to Thor cluster...${NC}"

# Apply the deployment manifest
kubectl apply -f deployment.yaml

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl -n athena-admin rollout status deployment/athena-admin-backend --timeout=300s
kubectl -n athena-admin rollout status deployment/athena-admin-frontend --timeout=300s

echo -e "${GREEN}✓ Deployments ready${NC}"

# Step 5: Verify deployment
echo ""
echo -e "${GREEN}Step 5: Verifying deployment...${NC}"

# Check pods
echo "Pods in athena-admin namespace:"
kubectl -n athena-admin get pods

# Check services
echo ""
echo "Services:"
kubectl -n athena-admin get svc

# Check ingress
echo ""
echo "Ingress:"
kubectl -n athena-admin get ingress

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Admin Interface URLs:"
echo "  • Frontend: https://athena-admin.xmojo.net"
echo "  • Backend API: https://athena-admin.xmojo.net/api"
echo ""
echo "To check deployment status:"
echo "  kubectl -n athena-admin get pods"
echo "  kubectl -n athena-admin logs deployment/athena-admin-backend"
echo ""
echo -e "${YELLOW}⚠ Note: If using Authentik OIDC:${NC}"
echo "1. Configure Authentik provider for athena-admin"
echo "2. Update the OIDC secret with real credentials:"
echo "   kubectl -n athena-admin edit secret athena-admin-oidc"
echo ""