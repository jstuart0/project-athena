#!/bin/bash

#######################################
# SearXNG Deployment Script for THOR
#######################################
# Deploy SearXNG to THOR cluster with:
# - Mac mini Redis integration
# - Admin UI ingress integration
# - Security hardening
#######################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="athena-admin"
EXPECTED_CONTEXT="thor"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    # Check openssl for secret generation
    if ! command -v openssl &> /dev/null; then
        log_error "openssl not found. Please install openssl."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Verify kubectl context
verify_context() {
    log_info "Verifying Kubernetes context..."

    CURRENT_CONTEXT=$(kubectl config current-context)

    if [ "$CURRENT_CONTEXT" != "$EXPECTED_CONTEXT" ]; then
        log_error "Wrong Kubernetes context: $CURRENT_CONTEXT"
        log_error "Expected: $EXPECTED_CONTEXT"
        log_warning "Switch context with: kubectl config use-context $EXPECTED_CONTEXT"
        exit 1
    fi

    log_success "Context verified: $CURRENT_CONTEXT"
}

# Verify namespace exists
verify_namespace() {
    log_info "Verifying namespace exists..."

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        log_warning "Create namespace with: kubectl create namespace $NAMESPACE"
        exit 1
    fi

    log_success "Namespace verified: $NAMESPACE"
}

# Generate SearXNG secret key
generate_secret_key() {
    log_info "Generating SearXNG secret key..."

    # Check if secret already exists
    if kubectl -n "$NAMESPACE" get secret searxng-secret &> /dev/null; then
        log_warning "Secret 'searxng-secret' already exists"
        read -p "Do you want to regenerate it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing secret"
            return 0
        fi
        log_info "Deleting existing secret..."
        kubectl -n "$NAMESPACE" delete secret searxng-secret
    fi

    # Generate random secret key (32 bytes, base64 encoded)
    SECRET_KEY=$(openssl rand -base64 32)

    # Create secret
    kubectl -n "$NAMESPACE" create secret generic searxng-secret \
        --from-literal=secret-key="$SECRET_KEY"

    log_success "Secret key generated and stored"
}

# Deploy ConfigMap
deploy_configmap() {
    log_info "Deploying SearXNG ConfigMap..."

    kubectl apply -f "$SCRIPT_DIR/searxng-configmap.yaml"

    log_success "ConfigMap deployed"
}

# Deploy Middleware
deploy_middleware() {
    log_info "Deploying Traefik Middleware..."

    kubectl apply -f "$SCRIPT_DIR/searxng-middleware.yaml"

    log_success "Middleware deployed"
}

# Deploy Service
deploy_service() {
    log_info "Deploying SearXNG Service..."

    kubectl apply -f "$SCRIPT_DIR/searxng-service.yaml"

    log_success "Service deployed"
}

# Deploy Deployment
deploy_deployment() {
    log_info "Deploying SearXNG Deployment..."

    kubectl apply -f "$SCRIPT_DIR/searxng-deployment.yaml"

    log_success "Deployment deployed"
}

# Update Ingress
update_ingress() {
    log_info "Updating Admin UI Ingress..."

    kubectl apply -f "$SCRIPT_DIR/deployment.yaml"

    log_success "Ingress updated"
}

# Wait for deployment
wait_for_deployment() {
    log_info "Waiting for SearXNG deployment to be ready..."

    if kubectl -n "$NAMESPACE" rollout status deployment/searxng --timeout=300s; then
        log_success "Deployment is ready"
    else
        log_error "Deployment failed to become ready"
        log_info "Checking pod status..."
        kubectl -n "$NAMESPACE" get pods -l app=searxng
        log_info "Checking pod logs..."
        kubectl -n "$NAMESPACE" logs -l app=searxng --tail=50
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check pods
    log_info "Checking pods..."
    READY_PODS=$(kubectl -n "$NAMESPACE" get pods -l app=searxng -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o "True" | wc -l | tr -d ' ')
    TOTAL_PODS=$(kubectl -n "$NAMESPACE" get pods -l app=searxng --no-headers | wc -l | tr -d ' ')

    if [ "$READY_PODS" -lt 1 ]; then
        log_error "No ready pods found ($READY_PODS/$TOTAL_PODS ready)"
        exit 1
    fi

    log_success "Pods ready: $READY_PODS/$TOTAL_PODS"

    # Check service
    log_info "Checking service..."
    SERVICE_IP=$(kubectl -n "$NAMESPACE" get svc searxng -o jsonpath='{.spec.clusterIP}')
    log_success "Service ClusterIP: $SERVICE_IP"

    # Test health endpoint from within cluster
    log_info "Testing health endpoint..."
    if kubectl -n "$NAMESPACE" run test-searxng-health --rm -i --restart=Never --image=curlimages/curl:latest -- \
        curl -sf http://searxng.athena-admin.svc.cluster.local:8080/healthz > /dev/null 2>&1; then
        log_success "Health check passed"
    else
        log_warning "Health check failed (pod may still be initializing)"
    fi
}

# Display access information
display_access_info() {
    echo ""
    log_info "============================================"
    log_info "  SearXNG Deployment Complete!"
    log_info "============================================"
    echo ""
    log_info "Access URLs:"
    echo "  - Public URL: https://athena-admin.xmojo.net/searxng/"
    echo "  - Internal URL: http://searxng.athena-admin.svc.cluster.local:8080"
    echo ""
    log_info "Configuration:"
    echo "  - Redis: 192.168.10.181:6379/1 (Mac mini)"
    echo "  - Namespace: $NAMESPACE"
    echo "  - Replicas: 2"
    echo ""
    log_info "Useful commands:"
    echo "  - View pods: kubectl -n $NAMESPACE get pods -l app=searxng"
    echo "  - View logs: kubectl -n $NAMESPACE logs -f -l app=searxng"
    echo "  - Describe deployment: kubectl -n $NAMESPACE describe deployment searxng"
    echo "  - Test search: curl 'https://athena-admin.xmojo.net/searxng/?q=test&format=json'"
    echo ""
}

# Main deployment flow
main() {
    log_info "Starting SearXNG deployment to THOR cluster..."
    echo ""

    check_prerequisites
    verify_context
    verify_namespace
    echo ""

    generate_secret_key
    echo ""

    deploy_configmap
    deploy_middleware
    deploy_service
    deploy_deployment
    echo ""

    update_ingress
    echo ""

    wait_for_deployment
    echo ""

    verify_deployment
    echo ""

    display_access_info

    log_success "Deployment completed successfully!"
}

# Run main function
main "$@"
