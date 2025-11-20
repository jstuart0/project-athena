# SearXNG Web Search Integration Implementation Plan

## Overview

This plan covers the deployment of SearXNG, a privacy-respecting metasearch engine, as part of Project Athena's RAG (Retrieval Augmented Generation) capabilities. SearXNG will provide real-time web search functionality for voice queries that require current information beyond the local knowledge base.

**Key Goals:**
- Deploy SearXNG with both Docker and Kubernetes configurations for open-source portability
- Integrate with Project Athena's orchestrator for intelligent routing
- Maintain privacy-first architecture (all processing local)
- Provide documentation for community deployment

## Current State Analysis

### Project Athena RAG Architecture

**Current Components (Mac Studio & Mac mini):**
- **Qdrant** (192.168.10.181:6333) - Vector database for local knowledge
- **Redis** (192.168.10.181:6379) - Caching layer
- **Orchestrator** (192.168.10.167:8001) - Intent routing and coordination
- **Gateway** (192.168.10.167:8000) - Entry point API

**Missing Capability:**
- Real-time web search for queries requiring current information (weather, news, sports, etc.)
- Fallback mechanism when local RAG returns low-confidence results

### Existing Deployment Patterns

**Docker Deployment Pattern** (`deployment/mac-mini/docker-compose.yml`):
```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
    networks:
      - athena
```

**Kubernetes Deployment Pattern** (`admin/k8s/deployment.yaml`):
- Private registry: `192.168.10.222:30500/`
- Platform: `linux/amd64` for Thor cluster (x86_64)
- Ingress class: `traefik`
- TLS: `cert-manager.io/cluster-issuer: letsencrypt-production`
- Health probes on all services
- Resource limits defined

### Key Discoveries

1. **Deployment Target:** Mac mini (192.168.10.181) is the ideal location alongside Qdrant/Redis
2. **Network Access:** SearXNG will be accessed via `http://192.168.10.181:8080` from orchestrator
3. **Configuration Management:** Following existing pattern of volume-mounted configs
4. **Resource Constraints:** Mac mini has 16GB RAM, must set reasonable limits
5. **Privacy:** SearXNG runs 100% locally, never sends user data to external services

## Desired End State

### Success Criteria

**Deployment Artifacts Created:**
1. ✅ Docker Compose configuration ready for Mac mini deployment
2. ✅ Kubernetes manifests ready for Thor cluster deployment
3. ✅ Deployment documentation for open-source use
4. ✅ Integration code in orchestrator for web search routing

**Verification:**
1. SearXNG responds to web search queries at http://192.168.10.181:8080
2. Orchestrator can route voice queries to SearXNG when appropriate
3. Redis caching reduces redundant external search calls
4. Installation works on both Docker Compose and Kubernetes environments

## What We're NOT Doing

- ❌ Public internet exposure of SearXNG (remains local network only)
- ❌ User tracking or analytics (privacy-first)
- ❌ Custom search engine implementations (using upstream SearXNG)
- ❌ Caddy reverse proxy (not needed for internal use)
- ❌ Rate limiting (private instance, not needed)
- ❌ Immediate orchestrator integration (deployment first, integration separate phase)

## Implementation Approach

**Two-Track Deployment Strategy:**

1. **Docker Compose (Primary):** Deploy to Mac mini for immediate use
2. **Kubernetes (Alternative):** Provide manifests for Thor cluster or community deployments

**Phased Implementation:**

1. **Phase 1:** Create deployment configurations (Docker + K8s)
2. **Phase 2:** Deploy to Mac mini and validate
3. **Phase 3:** Document for open-source use

---

## Phase 1: Create Deployment Configurations

### Overview
Create production-ready SearXNG deployment configurations following Project Athena patterns for both Docker Compose and Kubernetes environments.

### Changes Required

#### 1. Docker Compose Configuration

**File**: `deployment/searxng/docker-compose.yml`

**Changes**: Create new Docker Compose file for SearXNG with Redis/Valkey cache

```yaml
version: '3.8'

networks:
  athena:
    driver: bridge

volumes:
  searxng-data:
  valkey-data:

services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./searxng-config:/etc/searxng:rw
      - searxng-data:/var/cache/searxng:rw
    environment:
      - BASE_URL=http://192.168.10.181:8080
      - INSTANCE_NAME=Athena Search
    networks:
      - athena
    depends_on:
      - valkey
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M
          cpu: '1.0'
        reservations:
          memory: 128M
          cpu: '0.1'
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  valkey:
    image: valkey/valkey:8-alpine
    container_name: searxng-valkey
    restart: unless-stopped
    command: >
      valkey-server
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --save 30 1
    volumes:
      - valkey-data:/data
    networks:
      - athena
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 64M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### 2. SearXNG Settings Configuration

**File**: `deployment/searxng/searxng-config/settings.yml`

**Changes**: Create SearXNG configuration optimized for privacy and performance

```yaml
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
  secret_key: "CHANGE_THIS_SECRET_KEY"  # Will be generated during deployment
  limiter: false  # No rate limiting for private instance
  image_proxy: false  # Disable image proxy for performance
  http_protocol_version: "1.1"

redis:
  url: redis://valkey:6379/0

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

#### 3. Kubernetes Deployment Manifests

**File**: `deployment/searxng/k8s/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: searxng
  labels:
    app: searxng
    project: athena
```

**File**: `deployment/searxng/k8s/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: searxng-config
  namespace: searxng
data:
  settings.yml: |
    # (Same settings.yml content as above)
```

**File**: `deployment/searxng/k8s/secret.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: searxng-secret
  namespace: searxng
type: Opaque
stringData:
  secret-key: "REPLACE_WITH_GENERATED_SECRET"  # Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**File**: `deployment/searxng/k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: searxng
  namespace: searxng
  labels:
    app: searxng
spec:
  replicas: 1
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
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 977
      containers:
      - name: searxng
        image: searxng/searxng:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        env:
        - name: BASE_URL
          value: "https://searxng.athena.local"  # Update with actual domain
        - name: INSTANCE_NAME
          value: "Athena Search"
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
          runAsNonRoot: false
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
        - name: searxng-config
          mountPath: /etc/searxng
          readOnly: false
        - name: cache
          mountPath: /var/cache/searxng
      volumes:
      - name: searxng-config
        configMap:
          name: searxng-config
      - name: cache
        emptyDir:
          sizeLimit: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: valkey
  namespace: searxng
  labels:
    app: valkey
spec:
  replicas: 1
  selector:
    matchLabels:
      app: valkey
  template:
    metadata:
      labels:
        app: valkey
    spec:
      containers:
      - name: valkey
        image: valkey/valkey:8-alpine
        args:
          - valkey-server
          - --appendonly
          - "yes"
          - --maxmemory
          - "256mb"
          - --maxmemory-policy
          - allkeys-lru
          - --save
          - "30"
          - "1"
        ports:
        - containerPort: 6379
          name: redis
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
              - valkey-cli
              - ping
          initialDelaySeconds: 10
          periodSeconds: 10
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        emptyDir:
          sizeLimit: 500Mi
```

**File**: `deployment/searxng/k8s/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: searxng
  namespace: searxng
  labels:
    app: searxng
spec:
  type: ClusterIP
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: searxng
---
apiVersion: v1
kind: Service
metadata:
  name: valkey
  namespace: searxng
  labels:
    app: valkey
spec:
  type: ClusterIP
  ports:
  - port: 6379
    targetPort: 6379
    protocol: TCP
    name: redis
  selector:
    app: valkey
```

**File**: `deployment/searxng/k8s/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: searxng
  namespace: searxng
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-production
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  ingressClassName: traefik
  rules:
  - host: searxng.xmojo.net
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: searxng
            port:
              number: 8080
  tls:
  - hosts:
    - searxng.xmojo.net
    secretName: searxng-tls
```

#### 4. Deployment Scripts

**File**: `deployment/searxng/deploy-docker.sh`

```bash
#!/bin/bash
set -e

# SearXNG Docker Deployment Script for Project Athena
# Deploys to Mac mini at 192.168.10.181

echo "======================================"
echo "SearXNG Docker Deployment"
echo "======================================"

# Configuration
MAC_MINI_IP="192.168.10.181"
MAC_MINI_USER="jstuart"
DEPLOY_DIR="~/athena/searxng"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Generate secret key
echo -e "${YELLOW}[1/6] Generating secret key...${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Generated secret key: ${SECRET_KEY:0:10}..."

# Step 2: Update settings.yml with secret key
echo -e "${YELLOW}[2/6] Updating configuration...${NC}"
sed "s/CHANGE_THIS_SECRET_KEY/${SECRET_KEY}/g" searxng-config/settings.yml > searxng-config/settings.yml.tmp
mv searxng-config/settings.yml.tmp searxng-config/settings.yml

# Step 3: Create deployment directory on Mac mini
echo -e "${YELLOW}[3/6] Creating deployment directory on Mac mini...${NC}"
ssh ${MAC_MINI_USER}@${MAC_MINI_IP} "mkdir -p ${DEPLOY_DIR}/searxng-config"

# Step 4: Copy files to Mac mini
echo -e "${YELLOW}[4/6] Copying deployment files...${NC}"
scp docker-compose.yml ${MAC_MINI_USER}@${MAC_MINI_IP}:${DEPLOY_DIR}/
scp -r searxng-config/* ${MAC_MINI_USER}@${MAC_MINI_IP}:${DEPLOY_DIR}/searxng-config/

# Step 5: Deploy containers
echo -e "${YELLOW}[5/6] Deploying SearXNG containers...${NC}"
ssh ${MAC_MINI_USER}@${MAC_MINI_IP} "cd ${DEPLOY_DIR} && docker compose down || true && docker compose up -d"

# Step 6: Wait for health check
echo -e "${YELLOW}[6/6] Waiting for SearXNG to become healthy...${NC}"
for i in {1..30}; do
    if curl -f http://${MAC_MINI_IP}:8080/healthz &>/dev/null; then
        echo -e "${GREEN}✓ SearXNG is healthy and ready!${NC}"
        echo ""
        echo "======================================"
        echo "Deployment Complete!"
        echo "======================================"
        echo "SearXNG URL: http://${MAC_MINI_IP}:8080"
        echo "Search endpoint: http://${MAC_MINI_IP}:8080/search?q=test"
        echo ""
        break
    fi
    echo "Waiting for health check... ($i/30)"
    sleep 2
done

# Verify deployment
echo "Checking service status..."
ssh ${MAC_MINI_USER}@${MAC_MINI_IP} "cd ${DEPLOY_DIR} && docker compose ps"
```

**File**: `deployment/searxng/deploy-k8s.sh`

```bash
#!/bin/bash
set -e

# SearXNG Kubernetes Deployment Script for Project Athena
# Deploys to Thor cluster

echo "======================================"
echo "SearXNG Kubernetes Deployment"
echo "======================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Prerequisites check
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}kubectl not found${NC}"; exit 1; }

# Verify context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "Current context: ${CURRENT_CONTEXT}"

if [[ "${CURRENT_CONTEXT}" != "thor" ]]; then
    echo -e "${YELLOW}Switching to thor context...${NC}"
    kubectl config use-context thor || { echo -e "${RED}Failed to switch context${NC}"; exit 1; }
fi

# Step 1: Generate secret key
echo -e "${YELLOW}[1/6] Generating secret key...${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Step 2: Update secret manifest
echo -e "${YELLOW}[2/6] Creating secret...${NC}"
sed "s/REPLACE_WITH_GENERATED_SECRET/${SECRET_KEY}/g" k8s/secret.yaml > k8s/secret.yaml.tmp
mv k8s/secret.yaml.tmp k8s/secret.yaml

# Step 3: Apply manifests
echo -e "${YELLOW}[3/6] Applying Kubernetes manifests...${NC}"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Step 4: Wait for deployment
echo -e "${YELLOW}[4/6] Waiting for deployment to be ready...${NC}"
kubectl -n searxng rollout status deployment/searxng --timeout=300s

# Step 5: Verify pods
echo -e "${YELLOW}[5/6] Verifying pods...${NC}"
kubectl -n searxng get pods

# Step 6: Test service
echo -e "${YELLOW}[6/6] Testing service...${NC}"
kubectl -n searxng port-forward svc/searxng 8080:8080 &
PF_PID=$!
sleep 5

if curl -f http://localhost:8080/healthz &>/dev/null; then
    echo -e "${GREEN}✓ SearXNG is healthy!${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    kill $PF_PID
    exit 1
fi

kill $PF_PID

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo "Namespace: searxng"
echo "Service: searxng.searxng.svc.cluster.local:8080"
echo "Ingress: https://searxng.xmojo.net (if DNS configured)"
echo ""
echo "View logs: kubectl -n searxng logs -f deployment/searxng"
echo "View status: kubectl -n searxng get all"
```

#### 5. Documentation

**File**: `deployment/searxng/README.md`

```markdown
# SearXNG Deployment for Project Athena

SearXNG is a privacy-respecting metasearch engine that aggregates results from multiple search engines without tracking users.

## Overview

This deployment provides two installation methods:

1. **Docker Compose** - Recommended for single-server deployments (Mac mini, standalone)
2. **Kubernetes** - For cluster deployments (Thor, production environments)

## Prerequisites

### Docker Compose
- Docker and Docker Compose installed
- 1GB RAM minimum, 2GB recommended
- Network access to search engines (Google, DuckDuckGo, etc.)

### Kubernetes
- kubectl configured with cluster access
- cert-manager for TLS (optional, for HTTPS)
- Ingress controller (Traefik, Nginx, etc.)

## Quick Start

### Docker Compose Deployment

**Deploy to Mac mini (192.168.10.181):**

```bash
cd deployment/searxng
chmod +x deploy-docker.sh
./deploy-docker.sh
```

**Verify deployment:**
```bash
curl http://192.168.10.181:8080/healthz
curl "http://192.168.10.181:8080/search?q=test&format=json"
```

**Manual deployment:**
```bash
# Generate secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > secret.txt

# Update settings.yml with secret key

# Deploy
docker compose up -d

# Check status
docker compose ps
docker compose logs -f searxng
```

### Kubernetes Deployment

**Deploy to Thor cluster:**

```bash
cd deployment/searxng
chmod +x deploy-k8s.sh
./deploy-k8s.sh
```

**Verify deployment:**
```bash
kubectl -n searxng get all
kubectl -n searxng logs -f deployment/searxng
kubectl -n searxng port-forward svc/searxng 8080:8080
curl http://localhost:8080/healthz
```

## Configuration

### Customizing Search Engines

Edit `searxng-config/settings.yml` to enable/disable search engines:

```yaml
engines:
  - name: google
    disabled: false  # Set to true to disable

  - name: bing
    engine: bing
    disabled: true  # Enable by setting to false
```

### Resource Limits

**Docker Compose** - Edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 512M  # Adjust based on available RAM
      cpu: '1.0'
```

**Kubernetes** - Edit `k8s/deployment.yaml`:
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"  # Adjust based on cluster capacity
    cpu: "1000m"
```

## API Usage

### Search Query
```bash
curl "http://192.168.10.181:8080/search?q=project+athena&format=json" | jq
```

### Response Format
```json
{
  "query": "project athena",
  "results": [
    {
      "title": "Result title",
      "url": "https://example.com",
      "content": "Result snippet",
      "engine": "google"
    }
  ]
}
```

## Integration with Project Athena Orchestrator

### Python Example

```python
import httpx

SEARXNG_URL = "http://192.168.10.181:8080"

async def web_search(query: str, num_results: int = 5):
    """Search the web using SearXNG"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json"},
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        return data["results"][:num_results]
```

## Troubleshooting

### Health Check Fails

```bash
# Check logs
docker compose logs searxng

# Verify Redis connection
docker compose logs valkey
docker compose exec searxng curl http://valkey:6379
```

### Search Returns No Results

1. Check internet connectivity
2. Verify search engines are enabled in settings.yml
3. Check SearXNG logs for API errors

### High Memory Usage

- Reduce `maxmemory` for Valkey/Redis
- Decrease `max_page` in settings.yml
- Disable unused search engines

## Maintenance

### Update SearXNG

```bash
# Docker Compose
docker compose pull
docker compose up -d

# Kubernetes
kubectl -n searxng set image deployment/searxng searxng=searxng/searxng:latest
kubectl -n searxng rollout status deployment/searxng
```

### View Logs

```bash
# Docker Compose
docker compose logs -f searxng

# Kubernetes
kubectl -n searxng logs -f deployment/searxng
```

### Backup Configuration

```bash
# Docker Compose
tar -czf searxng-backup-$(date +%Y%m%d).tar.gz searxng-config/

# Kubernetes
kubectl -n searxng get configmap searxng-config -o yaml > searxng-config-backup.yaml
```

## Security Considerations

1. **Private Network Only** - SearXNG is not exposed to the internet
2. **No User Tracking** - Instance configured with tracking disabled
3. **Rate Limiting Disabled** - Safe for private instances
4. **Secret Key** - Generated uniquely per deployment
5. **Read-only Root Filesystem** - Kubernetes deployment uses read-only containers

## Performance Tuning

### Cache Configuration

Redis/Valkey caches search results for faster repeated queries:

```yaml
# settings.yml
redis:
  url: redis://valkey:6379/0

# Adjust cache size in docker-compose.yml
command: >
  valkey-server
  --maxmemory 512mb  # Increase for larger cache
```

### Search Engine Selection

For faster results, disable slow or redundant engines:

```yaml
engines:
  - name: slow_engine
    disabled: true  # Disable for better performance
```

## Resources

- **Official Documentation:** https://docs.searxng.org/
- **GitHub Repository:** https://github.com/searxng/searxng
- **Docker Hub:** https://hub.docker.com/r/searxng/searxng
- **Project Athena Wiki:** https://wiki.xmojo.net/homelab/projects/project-athena
```

### Success Criteria

#### Automated Verification
- [ ] Docker Compose file validates: `docker compose config`
- [ ] Kubernetes manifests validate: `kubectl apply --dry-run=client -f k8s/`
- [ ] Deployment scripts are executable: `chmod +x deploy-*.sh && ./deploy-docker.sh --dry-run`
- [ ] Settings.yml passes YAML validation: `yamllint searxng-config/settings.yml`

#### Manual Verification
- [ ] All configuration files created in `deployment/searxng/`
- [ ] Secret key generation works correctly
- [ ] Documentation is complete and accurate
- [ ] Deployment scripts have error handling

**Implementation Note:** After completing this phase and all automated verification passes, pause here for manual review of configurations before proceeding to Phase 2 deployment.

---

## Phase 2: Deploy to Mac mini and Validate

### Overview
Deploy SearXNG to Mac mini (192.168.10.181) using Docker Compose and verify full functionality.

### Changes Required

#### 1. Deploy SearXNG Stack

**Action:** Execute Docker deployment script from Mac Studio

```bash
# On Mac Studio (192.168.10.167)
cd /Users/jaystuart/dev/project-athena/deployment/searxng
./deploy-docker.sh
```

**Expected Outcome:**
- SearXNG container running on Mac mini
- Valkey/Redis cache running
- Health checks passing
- Service accessible at http://192.168.10.181:8080

#### 2. Verify Search Functionality

**Action:** Test search queries via API

```bash
# Basic health check
curl http://192.168.10.181:8080/healthz

# Search query test
curl "http://192.168.10.181:8080/search?q=artificial+intelligence&format=json" | jq '.results[0]'

# Multiple format test
curl "http://192.168.10.181:8080/search?q=project+athena&format=html" | head -20
```

**Expected Results:**
- Health endpoint returns 200 OK
- JSON format returns structured results
- HTML format returns rendered page
- Results from multiple search engines (Google, DuckDuckGo, etc.)

#### 3. Monitor Resource Usage

**Action:** Check memory and CPU usage on Mac mini

```bash
# SSH to Mac mini
ssh jstuart@192.168.10.181

# Check container resource usage
docker stats searxng searxng-valkey --no-stream

# Expected:
# searxng: <300MB RAM, <50% CPU
# valkey: <100MB RAM, <10% CPU
```

#### 4. Test Cache Performance

**Action:** Verify Redis caching works

```bash
# First query (cache miss)
time curl -s "http://192.168.10.181:8080/search?q=kubernetes&format=json" | jq '.results | length'

# Second query (cache hit - should be faster)
time curl -s "http://192.168.10.181:8080/search?q=kubernetes&format=json" | jq '.results | length'

# Check Redis for cached keys
ssh jstuart@192.168.10.181 "docker exec searxng-valkey valkey-cli KEYS '*'"
```

**Expected:**
- Second query significantly faster
- Redis contains cached search results
- Cache TTL properly configured

### Success Criteria

#### Automated Verification
- [ ] Health check passes: `curl -f http://192.168.10.181:8080/healthz`
- [ ] Search returns results: `curl "http://192.168.10.181:8080/search?q=test&format=json" | jq '.results | length'`
- [ ] Containers running: `ssh jstuart@192.168.10.181 "docker ps | grep searxng"`
- [ ] Redis connection works: `ssh jstuart@192.168.10.181 "docker exec searxng-valkey valkey-cli PING"`
- [ ] Memory usage acceptable: `ssh jstuart@192.168.10.181 "docker stats --no-stream | grep searxng | awk '{print \\$4}' | cut -d'M' -f1"` < 600

#### Manual Verification
- [ ] Search results quality is good (relevant, diverse sources)
- [ ] Response time is acceptable (<3 seconds for first query, <1s for cached)
- [ ] UI accessible and functional (if browsing directly)
- [ ] No errors in container logs
- [ ] Mac mini system resources not overloaded

**Implementation Note:** After completing this phase and all automated verification passes, pause here for manual confirmation that SearXNG is working correctly before proceeding to Phase 3.

---

## Phase 3: Documentation for Open Source Use

### Overview
Create comprehensive documentation and verification scripts for community deployments.

### Changes Required

#### 1. Add Kubernetes Deployment Guide

**File**: `deployment/searxng/KUBERNETES.md`

**Changes**: Create detailed Kubernetes deployment documentation

```markdown
# SearXNG Kubernetes Deployment Guide

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- cert-manager (optional, for TLS)
- Ingress controller (Traefik, Nginx, etc.)

## Installation Steps

### 1. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Generate Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update `k8s/secret.yaml` with the generated key.

### 3. Apply Configuration

```bash
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
```

### 4. Deploy Services

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### 5. (Optional) Configure Ingress

Update `k8s/ingress.yaml` with your domain, then:

```bash
kubectl apply -f k8s/ingress.yaml
```

## Verification

```bash
# Check pod status
kubectl -n searxng get pods

# View logs
kubectl -n searxng logs -f deployment/searxng

# Port forward for testing
kubectl -n searxng port-forward svc/searxng 8080:8080

# Test search
curl "http://localhost:8080/search?q=test&format=json"
```

## Scaling

```bash
# Scale up for high availability
kubectl -n searxng scale deployment/searxng --replicas=3

# Verify
kubectl -n searxng get pods -l app=searxng
```

## Monitoring

```bash
# Resource usage
kubectl -n searxng top pods

# Events
kubectl -n searxng get events --sort-by='.lastTimestamp'
```

## Troubleshooting

### Pod CrashLoopBackOff

```bash
kubectl -n searxng describe pod -l app=searxng
kubectl -n searxng logs -l app=searxng --previous
```

### No Search Results

1. Check internet connectivity from pods
2. Verify ConfigMap is correctly mounted
3. Check for DNS resolution issues

## Uninstall

```bash
kubectl delete namespace searxng
```
```

#### 2. Create Testing Script

**File**: `deployment/searxng/test-deployment.sh`

```bash
#!/bin/bash
set -e

# SearXNG Deployment Test Script
# Tests both Docker and Kubernetes deployments

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    echo -n "Testing $name... "

    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$response_code" -eq "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response_code)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected HTTP $expected_code, got $response_code)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test search functionality
test_search() {
    local url=$1
    local query="artificial intelligence"

    echo -n "Testing search query... "

    results=$(curl -s "${url}/search?q=${query}&format=json" | jq -r '.results | length')

    if [ "$results" -gt 0 ]; then
        echo -e "${GREEN}✓ PASS${NC} ($results results returned)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (No results returned)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Main test execution
echo "======================================"
echo "SearXNG Deployment Test Suite"
echo "======================================"
echo ""

# Check for deployment type
if [ "$1" == "docker" ]; then
    BASE_URL="http://192.168.10.181:8080"
    echo "Testing Docker deployment at $BASE_URL"
elif [ "$1" == "k8s" ]; then
    BASE_URL="http://localhost:8080"
    echo "Testing Kubernetes deployment (port-forward required)"
    echo "Run: kubectl -n searxng port-forward svc/searxng 8080:8080"
else
    BASE_URL="${1:-http://localhost:8080}"
    echo "Testing deployment at $BASE_URL"
fi

echo ""

# Run tests
test_endpoint "Health check" "$BASE_URL/healthz"
test_endpoint "Homepage" "$BASE_URL/"
test_search "$BASE_URL"

# Summary
echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Check logs for details.${NC}"
    exit 1
fi
```

#### 3. Add Project Integration Example

**File**: `deployment/searxng/INTEGRATION.md`

```markdown
# SearXNG Integration with Project Athena

## Overview

This guide covers integrating SearXNG web search into the Project Athena orchestrator for intelligent query routing.

## Architecture

```
Voice Query → Gateway → Orchestrator → Intent Classifier
                                          ↓
                                    [Route Decision]
                                          ↓
                        ┌─────────────────┼─────────────────┐
                        ↓                 ↓                 ↓
                   Local RAG         Web Search        Home Assistant
                  (Qdrant)          (SearXNG)         (Device Control)
```

## When to Use Web Search

**Ideal queries for SearXNG:**
- Real-time information (weather, news, sports scores)
- Current events ("what happened today in...")
- Fact-checking ("what is the current price of...")
- General knowledge beyond local docs
- Fallback when local RAG confidence is low

**NOT ideal for:**
- Personal information queries
- Device control commands
- Information in local knowledge base
- Privacy-sensitive queries

## Python Integration

### Basic Search Function

```python
import httpx
from typing import List, Dict, Any

SEARXNG_URL = "http://192.168.10.181:8080"

async def web_search(
    query: str,
    num_results: int = 5,
    timeout: float = 10.0
) -> List[Dict[str, Any]]:
    """
    Perform web search using SearXNG

    Args:
        query: Search query string
        num_results: Maximum number of results to return
        timeout: Request timeout in seconds

    Returns:
        List of search results with title, url, content
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SEARXNG_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": "en"
                },
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Return top N results
            return results[:num_results]

        except httpx.HTTPError as e:
            print(f"Web search error: {e}")
            return []
```

### Orchestrator Integration

```python
from enum import Enum
from typing import Optional

class IntentType(Enum):
    DEVICE_CONTROL = "device_control"
    WEB_SEARCH = "web_search"
    LOCAL_KNOWLEDGE = "local_knowledge"
    UNKNOWN = "unknown"

class Orchestrator:
    def __init__(self):
        self.searxng_url = "http://192.168.10.181:8080"
        self.qdrant_url = "http://192.168.10.181:6333"
        self.ha_url = "https://192.168.10.168:8123"

    async def classify_intent(self, query: str) -> IntentType:
        """Classify query intent for routing"""

        # Keywords indicating web search
        web_search_keywords = [
            "what is", "who is", "when did", "where is",
            "current", "latest", "today", "news",
            "weather", "score", "price"
        ]

        query_lower = query.lower()

        # Check for device control
        if any(word in query_lower for word in ["turn on", "turn off", "dim", "set"]):
            return IntentType.DEVICE_CONTROL

        # Check for web search indicators
        if any(keyword in query_lower for keyword in web_search_keywords):
            return IntentType.WEB_SEARCH

        # Default to local knowledge
        return IntentType.LOCAL_KNOWLEDGE

    async def handle_query(self, query: str) -> Dict[str, Any]:
        """Route query to appropriate handler"""

        intent = await self.classify_intent(query)

        if intent == IntentType.WEB_SEARCH:
            results = await web_search(query)
            return {
                "type": "web_search",
                "results": results,
                "answer": self._summarize_results(results)
            }

        elif intent == IntentType.DEVICE_CONTROL:
            # Route to Home Assistant
            pass

        else:
            # Query local RAG
            pass

    def _summarize_results(self, results: List[Dict]) -> str:
        """Summarize web search results for voice response"""
        if not results:
            return "I couldn't find any information on that."

        top_result = results[0]
        return f"According to {top_result.get('engine', 'the web')}, {top_result.get('content', '')}"
```

### Caching Strategy

```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(
    host='192.168.10.181',
    port=6379,
    decode_responses=True
)

async def cached_web_search(query: str, ttl: int = 3600) -> List[Dict]:
    """Web search with Redis caching"""

    cache_key = f"search:{query}"

    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Perform search
    results = await web_search(query)

    # Cache results
    redis_client.setex(
        cache_key,
        ttl,  # 1 hour default
        json.dumps(results)
    )

    return results
```

## Testing Integration

```python
import asyncio

async def test_integration():
    """Test SearXNG integration"""

    test_queries = [
        "what is the weather today",
        "latest news about AI",
        "who won the super bowl",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        results = await web_search(query, num_results=3)

        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   {result['url']}")
            print(f"   {result['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_integration())
```

## Performance Considerations

1. **Timeout Management**: Set reasonable timeouts (10s) to prevent voice response delays
2. **Caching**: Cache frequently asked queries (weather, news) for faster responses
3. **Result Limiting**: Return only top 3-5 results to reduce processing time
4. **Fallback**: Have a fallback response if web search fails

## Next Steps

1. Implement intent classification in orchestrator
2. Add web search route handler
3. Create result summarization for voice responses
4. Add monitoring/logging for search usage
```

#### 4. Update Main Project Documentation

**File**: Update `/Users/jaystuart/dev/project-athena/CLAUDE.md`

**Changes**: Add SearXNG to architecture documentation

```markdown
**RAG Components (Mac mini 192.168.10.181):**
- **Qdrant** (6333) - Vector database for local knowledge
- **Redis** (6379) - Caching layer
- **SearXNG** (8080) - Web search metasearch engine (NEW)
```

### Success Criteria

#### Automated Verification
- [ ] Test script runs successfully: `./test-deployment.sh docker`
- [ ] README renders correctly: `mdcat README.md` (if mdcat installed)
- [ ] Integration examples have no syntax errors: `python3 -m py_compile INTEGRATION.md` (extract code blocks first)
- [ ] All markdown files lint cleanly: `markdownlint *.md`

#### Manual Verification
- [ ] Documentation is clear and easy to follow for new users
- [ ] Code examples are accurate and tested
- [ ] Kubernetes deployment works on a clean test cluster
- [ ] Integration guide matches actual orchestrator architecture
- [ ] Troubleshooting section covers common issues

**Implementation Note:** After completing this phase, the SearXNG deployment is production-ready for both Docker and Kubernetes environments.

---

## Testing Strategy

### Unit Tests

**Docker Compose Configuration Test:**
```bash
# Validate docker-compose.yml
docker compose config

# Check for required images
docker pull searxng/searxng:latest
docker pull valkey/valkey:8-alpine
```

**Kubernetes Manifest Test:**
```bash
# Dry-run apply all manifests
kubectl apply --dry-run=client -f k8s/

# Validate with kubeval (if available)
kubeval k8s/*.yaml
```

### Integration Tests

**End-to-End Search Test:**
```bash
# Test complete search flow
query="kubernetes tutorial"
response=$(curl -s "http://192.168.10.181:8080/search?q=${query}&format=json")
echo "$response" | jq '.results | length'  # Should return > 0
```

**Cache Performance Test:**
```bash
# Measure cache hit performance
time curl -s "http://192.168.10.181:8080/search?q=test" > /dev/null  # Cache miss
time curl -s "http://192.168.10.181:8080/search?q=test" > /dev/null  # Cache hit (faster)
```

### Manual Testing Steps

1. **Search Quality Test:**
   - Search for "artificial intelligence news"
   - Verify results from multiple engines (Google, DuckDuckGo, etc.)
   - Check result relevance and diversity

2. **UI Accessibility:**
   - Browse to http://192.168.10.181:8080
   - Test search interface
   - Verify no JavaScript errors in console

3. **Resource Monitoring:**
   - Monitor CPU/memory during search bursts
   - Verify no memory leaks over 24 hours
   - Check disk usage for cache growth

4. **Error Handling:**
   - Test with network disconnected
   - Test with malformed queries
   - Verify graceful degradation

## Performance Considerations

**Response Time Targets:**
- Health check: <100ms
- Cached query: <500ms
- Uncached query: <3 seconds
- UI page load: <2 seconds

**Resource Limits:**
- SearXNG: 512MB RAM max, 1 CPU
- Valkey: 256MB RAM max, 0.5 CPU
- Total: <800MB RAM footprint on Mac mini

**Caching Strategy:**
- Cache TTL: 1 hour (3600s)
- Cache policy: allkeys-lru (evict least recently used)
- Max cache size: 256MB

**Search Engine Selection:**
- Enable: Google, DuckDuckGo, Brave, Wikipedia
- Disable: Bing, Yahoo (redundant with Google)
- Limit: 3 pages per search (max_page: 3)

## Migration Notes

**N/A** - This is a new deployment, no migration required.

## References

- **SearXNG Official Docs:** https://docs.searxng.org/
- **GitHub Repository:** https://github.com/searxng/searxng
- **Docker Compose Reference:** https://github.com/searxng/searxng-docker
- **Kubernetes Deployment Guide:** https://www.peppoj.net/2024/05/securely-deploy-searxng-on-kubernetes/
- **Project Athena CLAUDE.md:** `/Users/jaystuart/dev/project-athena/CLAUDE.md`
- **Homelab Infrastructure:** `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`
