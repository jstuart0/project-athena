# SearXNG THOR Cluster Deployment Implementation Plan

## Overview

This plan covers the deployment of SearXNG to the THOR Kubernetes cluster, reusing existing homelab infrastructure (Mac mini Redis) and integrating with the Athena Admin UI for easy access.

**Key Goals:**
- Deploy SearXNG to THOR cluster (192.168.10.222:6443)
- Reuse Mac mini Redis (192.168.10.181:6379) for search result caching
- Integrate SearXNG UI into Admin UI (athena-admin.xmojo.net/searxng)
- Follow existing Project Athena deployment patterns
- Maintain privacy-first architecture (100% local processing)

## Current State Analysis

### Existing THOR Infrastructure

**Athena Admin Namespace:**
- **Frontend**: athena-admin-frontend (2 replicas, port 80)
- **Backend**: athena-admin-backend (2 replicas, port 8080)
- **Redis**: redis:6379 in athena-admin namespace (for sessions)
- **Ingress**: athena-admin.xmojo.net with path-based routing
- **TLS**: cert-manager with Let's Encrypt

**Homelab Infrastructure:**
- **PostgreSQL**: postgres-01.xmojo.net:5432 (wikijs, authentik databases)
- **Mac mini Redis**: 192.168.10.181:6379 (used by Qdrant, Athena services)
- **Private Registry**: 192.168.10.222:30500

**Admin UI Ingress Routes** (`admin/k8s/deployment.yaml:184-235`):
```yaml
paths:
  - /api → athena-admin-backend:8080
  - /auth → athena-admin-backend:8080
  - /settings → athena-admin-backend:8080
  - /health → athena-admin-backend:8080
  - /status → athena-admin-backend:8080
  - /test-query → athena-admin-backend:8080
  - / → athena-admin-frontend:80
```

### Infrastructure Reuse Strategy

**What We're Reusing:**
1. ✅ **Mac mini Redis** (192.168.10.181:6379) - For SearXNG search result caching
2. ✅ **Traefik Ingress** - Existing ingress controller
3. ✅ **cert-manager** - Automatic TLS certificate management
4. ✅ **Private Registry** - For custom images if needed
5. ✅ **Admin UI Ingress** - Add `/searxng` path for UI integration

**What We're NOT Using:**
- ❌ PostgreSQL (SearXNG doesn't need a database)
- ❌ Separate Redis deployment (using Mac mini Redis)
- ❌ Separate ingress (integrating into admin ingress)

### Key Discoveries

1. **Redis Access**: SearXNG in THOR can access Mac mini Redis at `192.168.10.181:6379` (no network restrictions)
2. **Admin UI Pattern**: Path-based routing allows easy integration (`/searxng` → searxng service)
3. **Resource Availability**: THOR cluster has capacity for SearXNG (512MB RAM, 1 CPU)
4. **Platform**: Must build for `linux/amd64` (x86_64 cluster)
5. **Namespace**: Deploy to `athena-admin` namespace for easier integration

## Desired End State

### Success Criteria

**Deployment Complete:**
1. ✅ SearXNG running in `athena-admin` namespace on THOR
2. ✅ Using Mac mini Redis (192.168.10.181:6379) for caching
3. ✅ Accessible via https://athena-admin.xmojo.net/searxng
4. ✅ Health checks passing
5. ✅ Admin UI has link to SearXNG in navigation

**Verification:**
1. SearXNG UI loads at https://athena-admin.xmojo.net/searxng
2. Search queries return results
3. Redis caching works (check cache hit performance)
4. Resource usage within limits (< 512MB RAM, < 1 CPU)
5. TLS certificate valid

## What We're NOT Doing

- ❌ Deploying separate Redis for SearXNG
- ❌ Creating separate ingress domain
- ❌ Public internet exposure
- ❌ User tracking or analytics
- ❌ Rate limiting (private instance)
- ❌ Custom search engine implementations
- ❌ Caddy reverse proxy
- ❌ Docker Compose deployment (THOR only for now)

## Implementation Approach

**Single-Track THOR Deployment:**

1. **Phase 1:** Create Kubernetes manifests for SearXNG
2. **Phase 2:** Deploy to THOR and integrate with Mac mini Redis
3. **Phase 3:** Integrate UI into Admin ingress and add navigation link

---

## Phase 1: Create Kubernetes Manifests

### Overview
Create production-ready Kubernetes manifests for SearXNG deployment to THOR cluster, configured to use Mac mini Redis.

### Changes Required

#### 1. SearXNG ConfigMap

**File**: `admin/k8s/searxng-configmap.yaml`

**Changes**: Create ConfigMap with SearXNG settings optimized for privacy and performance

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: searxng-config
  namespace: athena-admin
  labels:
    app: searxng
    component: search
data:
  settings.yml: |
    # SearXNG Configuration for Project Athena
    # Privacy-focused, self-hosted metasearch engine

    use_default_settings: true

    general:
      debug: false
      instance_name: "Athena Search"
      privacypolicy_url: false
      donation_url: false
      contact_url: false
      enable_metrics: false

    brand:
      new_issue_url: false
      docs_url: false
      public_instances: false
      wiki_url: false
      issue_url: false

    search:
      safe_search: 0  # No filtering (private instance)
      autocomplete: ""  # Disable autocomplete
      default_lang: "en"
      max_page: 3  # Limit to 3 pages for performance
      formats:
        - html
        - json

    server:
      port: 8080
      bind_address: "0.0.0.0"
      secret_key: "__SECRET_KEY__"  # Will be replaced from secret
      limiter: false  # No rate limiting for private instance
      image_proxy: false  # Disable image proxy for performance
      http_protocol_version: "1.1"
      base_url: "https://athena-admin.xmojo.net/searxng/"

    # Redis connection to Mac mini
    redis:
      url: redis://192.168.10.181:6379/1  # Database 1 (db 0 is for Qdrant)

    ui:
      static_use_hash: true
      default_locale: "en"
      theme_args:
        simple_style: auto
      results_on_new_tab: false
      advanced_search: true
      query_in_title: true
      infinite_scroll: false
      center_alignment: false
      cache_url: "https://web.archive.org/web/"

    # Search engines configuration
    engines:
      - name: google
        engine: google
        shortcut: go
        use_mobile_ui: false
        disabled: false

      - name: duckduckgo
        engine: duckduckgo
        shortcut: ddg
        disabled: false

      - name: brave
        engine: brave
        shortcut: br
        disabled: false
        time_range_support: true

      - name: wikipedia
        engine: wikipedia
        shortcut: wp
        disabled: false
        categories: [general]

      - name: wikidata
        engine: wikidata
        shortcut: wd
        disabled: false

      - name: github
        engine: github
        shortcut: gh
        disabled: false

      - name: stackoverflow
        engine: stackoverflow
        shortcut: so
        disabled: false

    enabled_plugins:
      - 'Hash plugin'
      - 'Self Information'
      - 'Tracker URL remover'
      - 'Open Access DOI rewrite'

    disabled_plugins:
      - 'Hostnames plugin'  # Reduce processing overhead
```

#### 2. SearXNG Secret

**File**: `admin/k8s/searxng-secret.yaml`

**Changes**: Create secret for SearXNG secret key

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: searxng-secret
  namespace: athena-admin
  labels:
    app: searxng
type: Opaque
stringData:
  secret-key: "REPLACE_WITH_GENERATED_SECRET"  # Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 3. SearXNG Deployment

**File**: `admin/k8s/searxng-deployment.yaml`

**Changes**: Create deployment manifest following Athena Admin patterns

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: searxng
  namespace: athena-admin
  labels:
    app: searxng
    component: search
spec:
  replicas: 1  # Single instance for now
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: searxng
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: searxng
        component: search
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 977  # SearXNG user/group
        runAsNonRoot: true
        runAsUser: 977
      initContainers:
      # Init container to inject secret key into settings.yml
      - name: config-init
        image: busybox:latest
        command:
        - sh
        - -c
        - |
          SECRET_KEY=$(cat /tmp/secrets/secret-key)
          sed "s|__SECRET_KEY__|$SECRET_KEY|g" /tmp/config/settings.yml > /etc/searxng/settings.yml
          chmod 644 /etc/searxng/settings.yml
        volumeMounts:
        - name: config-template
          mountPath: /tmp/config
          readOnly: true
        - name: secrets
          mountPath: /tmp/secrets
          readOnly: true
        - name: config
          mountPath: /etc/searxng
      containers:
      - name: searxng
        image: searxng/searxng:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        env:
        - name: INSTANCE_NAME
          value: "Athena Search"
        - name: BASE_URL
          value: "https://athena-admin.xmojo.net/searxng/"
        - name: BIND_ADDRESS
          value: "0.0.0.0:8080"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        startupProbe:
          httpGet:
            path: /healthz
            port: 8080
            scheme: HTTP
          failureThreshold: 60
          periodSeconds: 10
          timeoutSeconds: 30
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 15
          periodSeconds: 20
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 5
          periodSeconds: 10
          failureThreshold: 3
        securityContext:
          runAsNonRoot: true
          runAsUser: 977
          privileged: false
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
            add:
              - SETGID
              - SETUID
          seccompProfile:
            type: RuntimeDefault
        volumeMounts:
        - name: config
          mountPath: /etc/searxng
          readOnly: true
        - name: cache
          mountPath: /var/cache/searxng
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config-template
        configMap:
          name: searxng-config
      - name: secrets
        secret:
          secretName: searxng-secret
      - name: config
        emptyDir: {}
      - name: cache
        emptyDir:
          sizeLimit: 500Mi
      - name: tmp
        emptyDir:
          sizeLimit: 100Mi
```

#### 4. SearXNG Service

**File**: `admin/k8s/searxng-service.yaml`

**Changes**: Create ClusterIP service for internal access

```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: searxng
  namespace: athena-admin
  labels:
    app: searxng
    component: search
spec:
  type: ClusterIP
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: searxng
```

#### 5. Update Admin Ingress

**File**: `admin/k8s/deployment.yaml` (UPDATE EXISTING)

**Changes**: Add `/searxng` path to existing ingress

```yaml
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: athena-admin-ingress
  namespace: athena-admin
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-production
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
    # Strip /searxng prefix when forwarding to service
    traefik.ingress.kubernetes.io/router.middlewares: athena-admin-searxng-strip@kubernetescrd
spec:
  ingressClassName: traefik
  tls:
  - hosts:
    - athena-admin.xmojo.net
    secretName: athena-admin-tls
  rules:
  - host: athena-admin.xmojo.net
    http:
      paths:
      # NEW: SearXNG path (must be before / to match first)
      - path: /searxng
        pathType: Prefix
        backend:
          service:
            name: searxng
            port:
              number: 8080
      # Existing paths...
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: athena-admin-backend
            port:
              number: 8080
      - path: /auth
        pathType: Prefix
        backend:
          service:
            name: athena-admin-backend
            port:
              number: 8080
      - path: /settings
        pathType: Prefix
        backend:
          service:
            name: athena-admin-backend
            port:
              number: 8080
      - path: /health
        pathType: Prefix
        backend:
          service:
            name: athena-admin-backend
            port:
              number: 8080
      - path: /status
        pathType: Prefix
        backend:
          service:
            name: athena-admin-backend
            port:
              number: 8080
      - path: /test-query
        pathType: Prefix
        backend:
          service:
            name: athena-admin-backend
            port:
              number: 8080
      - path: /
        pathType: Prefix
        backend:
          service:
            name: athena-admin-frontend
            port:
              number: 80
---
# Middleware to strip /searxng prefix
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: searxng-strip
  namespace: athena-admin
spec:
  stripPrefix:
    prefixes:
      - /searxng
```

#### 6. Deployment Script

**File**: `admin/k8s/deploy-searxng.sh`

**Changes**: Create automated deployment script

```bash
#!/bin/bash
set -e

# SearXNG THOR Deployment Script
# Deploys SearXNG to athena-admin namespace on THOR cluster

echo "======================================"
echo "SearXNG THOR Deployment"
echo "======================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prerequisites check
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"
command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}kubectl not found${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}python3 not found${NC}"; exit 1; }

# Verify context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "Current context: ${CURRENT_CONTEXT}"

if [[ "${CURRENT_CONTEXT}" != "thor" ]]; then
    echo -e "${YELLOW}Switching to thor context...${NC}"
    kubectl config use-context thor || { echo -e "${RED}Failed to switch context${NC}"; exit 1; }
fi

# Verify namespace exists
echo -e "${YELLOW}[2/7] Verifying athena-admin namespace...${NC}"
if ! kubectl get namespace athena-admin &>/dev/null; then
    echo -e "${RED}Namespace athena-admin does not exist${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Namespace exists${NC}"

# Generate secret key
echo -e "${YELLOW}[3/7] Generating secret key...${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Generated secret key: ${SECRET_KEY:0:10}..."

# Update secret manifest
echo -e "${YELLOW}[4/7] Creating secret...${NC}"
sed "s/REPLACE_WITH_GENERATED_SECRET/${SECRET_KEY}/g" "${SCRIPT_DIR}/searxng-secret.yaml" | kubectl apply -f -

# Apply ConfigMap
echo -e "${YELLOW}[5/7] Applying configuration...${NC}"
kubectl apply -f "${SCRIPT_DIR}/searxng-configmap.yaml"

# Apply deployment and service
echo -e "${YELLOW}[6/7] Deploying SearXNG...${NC}"
kubectl apply -f "${SCRIPT_DIR}/searxng-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/searxng-service.yaml"

# Update ingress
echo -e "${YELLOW}[7/7] Updating ingress...${NC}"
kubectl apply -f "${SCRIPT_DIR}/deployment.yaml"  # Contains updated ingress

# Wait for deployment
echo -e "${YELLOW}Waiting for deployment to be ready...${NC}"
kubectl -n athena-admin rollout status deployment/searxng --timeout=300s

# Verify pods
echo -e "${YELLOW}Verifying pods...${NC}"
kubectl -n athena-admin get pods -l app=searxng

# Test Redis connectivity
echo -e "${YELLOW}Testing Redis connectivity...${NC}"
POD_NAME=$(kubectl -n athena-admin get pods -l app=searxng -o jsonpath='{.items[0].metadata.name}')
if kubectl -n athena-admin exec ${POD_NAME} -- sh -c "nc -zv 192.168.10.181 6379" &>/dev/null; then
    echo -e "${GREEN}✓ Redis connectivity OK${NC}"
else
    echo -e "${RED}✗ Redis connectivity FAILED${NC}"
    echo "Check Mac mini Redis is running: ssh jstuart@192.168.10.181 'docker ps | grep redis'"
fi

# Test service
echo -e "${YELLOW}Testing service...${NC}"
kubectl -n athena-admin port-forward svc/searxng 8080:8080 &
PF_PID=$!
sleep 5

if curl -f http://localhost:8080/healthz &>/dev/null; then
    echo -e "${GREEN}✓ SearXNG is healthy!${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    kill $PF_PID || true
    exit 1
fi

kill $PF_PID || true

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo "Namespace: athena-admin"
echo "Service: searxng.athena-admin.svc.cluster.local:8080"
echo "URL: https://athena-admin.xmojo.net/searxng"
echo ""
echo "View logs: kubectl -n athena-admin logs -f deployment/searxng"
echo "View status: kubectl -n athena-admin get all -l app=searxng"
echo ""
echo -e "${YELLOW}Note: SearXNG UI will be accessible once DNS/ingress propagates${NC}"
```

### Success Criteria

#### Automated Verification
- [ ] All manifests validate: `kubectl apply --dry-run=client -f admin/k8s/searxng-*.yaml`
- [ ] Deployment script is executable: `chmod +x admin/k8s/deploy-searxng.sh`
- [ ] ConfigMap has valid YAML: `kubectl create --dry-run=client -f admin/k8s/searxng-configmap.yaml -o yaml | kubectl apply --dry-run=client -f -`
- [ ] Secret key generation works: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

#### Manual Verification
- [ ] All manifest files created in `admin/k8s/`
- [ ] Ingress updated with `/searxng` path
- [ ] Middleware created for path stripping
- [ ] ConfigMap references Mac mini Redis (192.168.10.181:6379)
- [ ] Security context follows best practices

**Implementation Note:** After completing this phase and all automated verification passes, pause here for manual review of manifests before proceeding to Phase 2 deployment.

---

## Phase 2: Deploy to THOR and Validate

### Overview
Deploy SearXNG to THOR cluster and verify integration with Mac mini Redis and existing infrastructure.

### Changes Required

#### 1. Execute Deployment

**Action:** Run deployment script

```bash
cd /Users/jaystuart/dev/project-athena/admin/k8s
chmod +x deploy-searxng.sh
./deploy-searxng.sh
```

**Expected Outcome:**
- Secret created in athena-admin namespace
- ConfigMap applied
- Deployment running with 1 replica
- Service created
- Ingress updated
- Pod reaches ready state

#### 2. Verify Mac mini Redis Connection

**Action:** Test Redis connectivity from SearXNG pod

```bash
# Get pod name
POD_NAME=$(kubectl -n athena-admin get pods -l app=searxng -o jsonpath='{.items[0].metadata.name}')

# Test Redis connection
kubectl -n athena-admin exec ${POD_NAME} -- sh -c "nc -zv 192.168.10.181 6379"

# Expected: Connection to 192.168.10.181 6379 port [tcp/redis] succeeded!
```

#### 3. Test Search Functionality

**Action:** Verify search queries work via port-forward

```bash
# Port forward to local machine
kubectl -n athena-admin port-forward svc/searxng 8080:8080 &
PF_PID=$!

# Health check
curl http://localhost:8080/healthz

# Search query test
curl "http://localhost:8080/search?q=kubernetes&format=json" | jq '.results | length'

# Expected: > 0 results

# Kill port forward
kill $PF_PID
```

#### 4. Verify Ingress Access

**Action:** Test HTTPS access via ingress

```bash
# Test health endpoint through ingress
curl -k https://athena-admin.xmojo.net/searxng/healthz

# Test search through ingress
curl -k "https://athena-admin.xmojo.net/searxng/search?q=test&format=json" | jq '.results | length'

# Open in browser
open https://athena-admin.xmojo.net/searxng
```

**Expected:**
- HTTPS certificate valid (Let's Encrypt)
- Health check returns 200
- Search UI loads correctly
- Search queries return results

#### 5. Monitor Resource Usage

**Action:** Check CPU and memory consumption

```bash
# Get resource usage
kubectl -n athena-admin top pod -l app=searxng

# Expected:
# NAME                       CPU(cores)   MEMORY(bytes)
# searxng-xxx                50-200m      150-350Mi

# View resource limits
kubectl -n athena-admin describe deployment searxng | grep -A 5 "Limits:"
```

#### 6. Test Cache Performance

**Action:** Verify Redis caching works

```bash
# First query (cache miss)
time curl -s "https://athena-admin.xmojo.net/searxng/search?q=artificial+intelligence&format=json" | jq '.results | length'

# Second query (cache hit - should be faster)
time curl -s "https://athena-admin.xmojo.net/searxng/search?q=artificial+intelligence&format=json" | jq '.results | length'

# Check Redis for cached keys (from Mac mini)
ssh jstuart@192.168.10.181 "docker exec mac-mini-redis redis-cli -n 1 KEYS 'searxng:*'"

# Expected: Keys present for cached searches
```

### Success Criteria

#### Automated Verification
- [ ] Deployment is ready: `kubectl -n athena-admin get deployment searxng -o jsonpath='{.status.conditions[?(@.type=="Available")].status}'` returns "True"
- [ ] Pod is running: `kubectl -n athena-admin get pods -l app=searxng -o jsonpath='{.items[0].status.phase}'` returns "Running"
- [ ] Health check passes: `curl -f -k https://athena-admin.xmojo.net/searxng/healthz`
- [ ] Search returns results: `curl -k "https://athena-admin.xmojo.net/searxng/search?q=test&format=json" | jq -e '.results | length > 0'`
- [ ] Redis connection works: `kubectl -n athena-admin exec deployment/searxng -- nc -zv 192.168.10.181 6379`
- [ ] Memory usage acceptable: `kubectl -n athena-admin top pod -l app=searxng | awk 'NR==2 {print $3}' | grep -E '^[0-9]+Mi$' | sed 's/Mi//' | awk '$1 < 512'`

#### Manual Verification
- [ ] SearXNG UI loads at https://athena-admin.xmojo.net/searxng
- [ ] Search quality is good (relevant results from multiple engines)
- [ ] Response time acceptable (<3s first query, <1s cached)
- [ ] No errors in pod logs: `kubectl -n athena-admin logs -l app=searxng --tail=50`
- [ ] TLS certificate valid in browser
- [ ] No resource warnings or throttling

**Implementation Note:** After completing this phase and all automated verification passes, pause here for manual confirmation that SearXNG is working correctly before proceeding to Phase 3.

---

## Phase 3: Admin UI Integration

### Overview
Add navigation link to SearXNG in the Athena Admin UI frontend for easy access.

### Changes Required

#### 1. Update Admin Frontend Navigation

**File**: `admin/frontend/index.html` (UPDATE EXISTING)

**Changes**: Add SearXNG link to navigation menu

```html
<!-- Locate the navigation section and add SearXNG link -->
<nav class="sidebar">
  <ul>
    <li><a href="/">Dashboard</a></li>
    <li><a href="/settings">Settings</a></li>
    <li><a href="/status">System Status</a></li>
    <!-- NEW: SearXNG Link -->
    <li>
      <a href="/searxng" target="_blank" rel="noopener noreferrer">
        <span class="icon">🔍</span>
        Web Search
      </a>
    </li>
  </ul>
</nav>
```

#### 2. Add SearXNG Card to Dashboard

**File**: `admin/frontend/app.js` (UPDATE EXISTING)

**Changes**: Add SearXNG status card to dashboard

```javascript
// Add to dashboard components
const searchCard = {
  title: 'Web Search',
  icon: '🔍',
  status: 'active',
  description: 'Privacy-focused metasearch powered by SearXNG',
  link: '/searxng',
  linkText: 'Open Search',
  external: true
};

// Add to dashboard render function
function renderDashboard() {
  const cards = [
    // ... existing cards
    searchCard
  ];

  // Render cards...
}
```

#### 3. Update Backend Health Check

**File**: `admin/backend/app/routes/status.py` (UPDATE EXISTING)

**Changes**: Add SearXNG service health check

```python
from typing import Dict, Any
import httpx

async def check_searxng_health() -> Dict[str, Any]:
    """Check SearXNG service health"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://searxng.athena-admin.svc.cluster.local:8080/healthz",
                timeout=5.0
            )
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds()
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Add to /status endpoint
@router.get("/status")
async def get_system_status():
    """Get system-wide status"""

    # Existing checks...

    # NEW: SearXNG check
    searxng_health = await check_searxng_health()

    return {
        "services": {
            # ... existing services
            "searxng": searxng_health
        }
    }
```

#### 4. Rebuild and Deploy Frontend

**Action:** Build updated frontend and deploy

```bash
cd /Users/jaystuart/dev/project-athena/admin/frontend

# Build Docker image for x86_64
docker buildx build --platform linux/amd64 \
  -t 192.168.10.222:30500/athena-admin-frontend:latest \
  --push .

# Restart frontend deployment to pull new image
kubectl -n athena-admin rollout restart deployment/athena-admin-frontend

# Wait for rollout
kubectl -n athena-admin rollout status deployment/athena-admin-frontend
```

#### 5. Rebuild and Deploy Backend

**Action:** Build updated backend and deploy

```bash
cd /Users/jaystuart/dev/project-athena/admin/backend

# Build Docker image for x86_64
docker buildx build --platform linux/amd64 \
  -t 192.168.10.222:30500/athena-admin-backend:latest \
  --push .

# Restart backend deployment
kubectl -n athena-admin rollout restart deployment/athena-admin-backend

# Wait for rollout
kubectl -n athena-admin rollout status deployment/athena-admin-backend
```

### Success Criteria

#### Automated Verification
- [ ] Frontend image builds: `docker buildx build --platform linux/amd64 -t test-frontend --load admin/frontend/`
- [ ] Backend image builds: `docker buildx build --platform linux/amd64 -t test-backend --load admin/backend/`
- [ ] Frontend deployment ready: `kubectl -n athena-admin get deployment athena-admin-frontend -o jsonpath='{.status.readyReplicas}'` equals replicas
- [ ] Backend deployment ready: `kubectl -n athena-admin get deployment athena-admin-backend -o jsonpath='{.status.readyReplicas}'` equals replicas
- [ ] Status endpoint includes SearXNG: `curl -k https://athena-admin.xmojo.net/api/status | jq -e '.services.searxng'`

#### Manual Verification
- [ ] Admin UI loads at https://athena-admin.xmojo.net
- [ ] Navigation menu shows "Web Search" link with 🔍 icon
- [ ] Clicking link opens SearXNG in new tab
- [ ] Dashboard shows SearXNG status card
- [ ] Status page shows SearXNG service health
- [ ] Link works correctly (opens SearXNG at /searxng path)
- [ ] No JavaScript errors in console

**Implementation Note:** After completing this phase, SearXNG is fully integrated into the Athena Admin UI.

---

## Testing Strategy

### Unit Tests

**Kubernetes Manifest Validation:**
```bash
# Validate all manifests
kubectl apply --dry-run=client -f admin/k8s/searxng-*.yaml

# Check for common issues
kubeval admin/k8s/searxng-*.yaml || echo "kubeval not installed, skipping"
```

**ConfigMap Validation:**
```bash
# Extract and validate YAML
kubectl create configmap test --from-file=admin/k8s/searxng-configmap.yaml --dry-run=client -o yaml
```

### Integration Tests

**End-to-End Search Test:**
```bash
#!/bin/bash
# Test complete search flow

# 1. Health check
curl -f -k https://athena-admin.xmojo.net/searxng/healthz || exit 1

# 2. Perform search
RESULTS=$(curl -k "https://athena-admin.xmojo.net/searxng/search?q=kubernetes&format=json" | jq '.results | length')
if [ "$RESULTS" -gt 0 ]; then
    echo "✓ Search returned $RESULTS results"
else
    echo "✗ Search failed"
    exit 1
fi

# 3. Test cache
START=$(date +%s%N)
curl -s -k "https://athena-admin.xmojo.net/searxng/search?q=kubernetes&format=json" > /dev/null
END=$(date +%s%N)
CACHED_TIME=$(( (END - START) / 1000000 ))  # Convert to ms

echo "✓ Cached query took ${CACHED_TIME}ms"
```

**Redis Cache Test:**
```bash
# Verify caching in Mac mini Redis
ssh jstuart@192.168.10.181 'docker exec mac-mini-redis redis-cli -n 1 KEYS "searxng:*" | wc -l'
# Expected: > 0 if searches have been performed
```

### Manual Testing Steps

1. **UI Access Test:**
   - Navigate to https://athena-admin.xmojo.net
   - Click "Web Search" in navigation
   - Verify SearXNG UI loads in new tab
   - Perform search query
   - Verify results displayed

2. **Search Quality Test:**
   - Search: "artificial intelligence latest news"
   - Verify results from Google, DuckDuckGo, Brave
   - Check result relevance
   - Verify pagination works

3. **Admin Integration:**
   - Check dashboard shows SearXNG card
   - Verify status page shows SearXNG health
   - Test that clicking dashboard card opens SearXNG

4. **Performance Test:**
   - Perform same search 3 times
   - Verify second and third are faster (cache hit)
   - Monitor resource usage during searches

5. **Error Handling:**
   - Disconnect Mac mini Redis temporarily
   - Verify SearXNG shows appropriate error
   - Reconnect Redis and verify recovery

## Performance Considerations

**Response Time Targets:**
- Health check: <100ms
- First search query: <3 seconds
- Cached query: <500ms
- UI page load: <2 seconds

**Resource Limits:**
- SearXNG pod: 512MB RAM max, 1 CPU
- Expected usage: 150-300MB RAM, 0.1-0.3 CPU
- Burst capacity: Up to 1 CPU for concurrent searches

**Caching Strategy:**
- Cache location: Mac mini Redis database 1 (192.168.10.181:6379/1)
- Cache TTL: Managed by SearXNG (typically 1 hour)
- Cache policy: allkeys-lru (evict least recently used)
- Cache key format: `searxng:*`

**Search Engine Selection:**
- Primary: Google, DuckDuckGo, Brave
- Specialized: Wikipedia, GitHub, Stack Overflow
- Limit: 3 pages per search (max_page: 3)
- Concurrent engine queries: Default SearXNG behavior

## Migration Notes

**N/A** - This is a new deployment with no migration required.

**Infrastructure Dependencies:**
1. **Mac mini Redis** must be running and accessible at 192.168.10.181:6379
2. **THOR cluster** must have athena-admin namespace deployed
3. **Traefik ingress** must be configured with cert-manager
4. **DNS** athena-admin.xmojo.net must resolve to cluster load balancer

## Security Considerations

**Network Security:**
- SearXNG only accessible via HTTPS through ingress (no direct pod access)
- Redis connection is internal network only (192.168.10.0/24)
- No public internet exposure

**Pod Security:**
- Read-only root filesystem
- Run as non-root user (UID 977)
- Minimal capabilities (drop ALL, add SETGID/SETUID only)
- SeccompProfile: RuntimeDefault
- No service account token mounted

**Data Privacy:**
- No user tracking enabled
- No search analytics or metrics
- Search history not persisted (cache only)
- All processing local (no external services)

## References

- **SearXNG Official Docs:** https://docs.searxng.org/
- **GitHub Repository:** https://github.com/searxng/searxng
- **Kubernetes Security Best Practices:** https://www.peppoj.net/2024/05/securely-deploy-searxng-on-kubernetes/
- **Project Athena CLAUDE.md:** `/Users/jaystuart/dev/project-athena/CLAUDE.md`
- **Admin Deployment:** `/Users/jaystuart/dev/project-athena/admin/k8s/deployment.yaml`
- **Homelab Infrastructure:** `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`
- **Mac mini Redis:** Deployed via docker-compose at 192.168.10.181:6379
