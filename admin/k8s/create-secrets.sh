#!/bin/bash
#
# Create Kubernetes secrets for Athena Admin Interface
#
# This script creates all necessary secrets for the admin interface:
# - Database credentials
# - Authentik OIDC configuration
# - Session and JWT secrets
#

set -e

# Colors for output
RED='\033[0.31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating Kubernetes secrets for Athena Admin...${NC}"

# Ensure we're on the correct context
CURRENT_CONTEXT=$(kubectl config current-context)
if [ "$CURRENT_CONTEXT" != "thor" ]; then
    echo -e "${YELLOW}Switching to thor context...${NC}"
    kubectl config use-context thor
fi

# Ensure namespace exists
kubectl get namespace athena-admin > /dev/null 2>&1 || kubectl create namespace athena-admin

echo -e "${GREEN}1. Creating database credentials secret...${NC}"

# Using postgres-01.xmojo.net for all Athena databases
DB_HOST="postgres-01.xmojo.net"
DB_USER="psadmin"
DB_PASS="Ibucej1!"
DB_NAME="athena_admin"

# Create database URL (URL-encoding the password for special characters)
DB_PASS_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${DB_PASS}'))")
DATABASE_URL="postgresql://${DB_USER}:${DB_PASS_ENCODED}@${DB_HOST}:5432/${DB_NAME}"

kubectl -n athena-admin create secret generic athena-admin-db \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --from-literal=DB_HOST="$DB_HOST" \
    --from-literal=DB_USER="$DB_USER" \
    --from-literal=DB_PASSWORD="$DB_PASS" \
    --from-literal=DB_NAME="$DB_NAME" \
    --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}2. Creating session and JWT secrets...${NC}"

# Generate secure secrets
SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

kubectl -n athena-admin create secret generic athena-admin-secrets \
    --from-literal=SESSION_SECRET_KEY="$SESSION_SECRET" \
    --from-literal=JWT_SECRET="$JWT_SECRET" \
    --dry-run=client -o yaml | kubectl apply -f -

echo -e "${YELLOW}3. Creating placeholder for Authentik OIDC credentials...${NC}"
echo -e "${YELLOW}   NOTE: You must update this secret after configuring Authentik!${NC}"

# Create placeholder secret (will need to be updated after Authentik setup)
kubectl -n athena-admin create secret generic athena-admin-oidc \
    --from-literal=OIDC_CLIENT_ID="PLACEHOLDER_UPDATE_AFTER_AUTHENTIK_SETUP" \
    --from-literal=OIDC_CLIENT_SECRET="PLACEHOLDER_UPDATE_AFTER_AUTHENTIK_SETUP" \
    --from-literal=OIDC_ISSUER="https://auth.xmojo.net/application/o/athena-admin/" \
    --from-literal=OIDC_REDIRECT_URI="https://athena-admin.xmojo.net/auth/callback" \
    --from-literal=OIDC_SCOPES="openid profile email" \
    --from-literal=FRONTEND_URL="https://athena-admin.xmojo.net" \
    --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✓ All secrets created successfully!${NC}"
echo ""
echo -e "${YELLOW}⚠ IMPORTANT: Next steps:${NC}"
echo "1. Configure Authentik provider for athena-admin application"
echo "2. Update the OIDC secret with real credentials:"
echo "   kubectl -n athena-admin edit secret athena-admin-oidc"
echo "3. Update OIDC_CLIENT_ID and OIDC_CLIENT_SECRET with values from Authentik"
echo ""
echo -e "${GREEN}To view secrets:${NC}"
echo "  kubectl -n athena-admin get secrets"
echo ""
