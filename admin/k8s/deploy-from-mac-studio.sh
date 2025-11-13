#!/bin/bash
#
# Deploy Admin Interface from Mac Studio
# This script should be run from Mac Studio which has kubectl access to Thor
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deploy Athena Admin from Mac Studio${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check if we're on Mac Studio
if [[ $(hostname) != *"Mac-Studio"* ]]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be Mac Studio${NC}"
    echo -e "${YELLOW}Hostname: $(hostname)${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Copy build script to Mac Studio
echo -e "${GREEN}Step 1: Setting up deployment directory...${NC}"
DEPLOY_DIR="$HOME/athena-admin-deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

# Step 2: Copy entire admin directory
echo -e "${GREEN}Step 2: Copying admin files from local to Mac Studio...${NC}"
echo "This will copy the admin directory to Mac Studio for building"

# Create tar archive of admin directory (excluding node_modules if any)
cd /Users/jaystuart/dev/project-athena
tar czf /tmp/admin-deploy.tar.gz \
    --exclude='node_modules' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    admin/

# Copy to Mac Studio
scp /tmp/admin-deploy.tar.gz jstuart@192.168.10.167:~/athena-admin-deploy/
rm /tmp/admin-deploy.tar.gz

# Extract on Mac Studio and run build
ssh jstuart@192.168.10.167 << 'REMOTE_SCRIPT'
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd ~/athena-admin-deploy

# Extract the archive
echo -e "${GREEN}Extracting admin files...${NC}"
tar xzf admin-deploy.tar.gz
rm admin-deploy.tar.gz

# Navigate to k8s directory
cd admin/k8s

# Make scripts executable
chmod +x build-and-deploy.sh
chmod +x create-secrets.sh

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Starting deployment to Thor cluster${NC}"
echo -e "${GREEN}=========================================${NC}"

# Run the build and deploy script
./build-and-deploy.sh

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment initiated from Mac Studio!${NC}"
echo -e "${GREEN}=========================================${NC}"

# Cleanup
cd ~
rm -rf ~/athena-admin-deploy

REMOTE_SCRIPT

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Admin interface deployment complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Access the admin interface at:"
echo "  • https://athena-admin.xmojo.net"
echo ""
echo "To check deployment status from Mac Studio:"
echo "  ssh jstuart@192.168.10.167"
echo "  kubectl -n athena-admin get pods"
echo ""