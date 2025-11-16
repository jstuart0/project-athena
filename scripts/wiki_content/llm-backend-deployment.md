# LLM Backend System - Deployment Guide

> **Last Updated:** November 15, 2025
> **Status:** Production Ready
> **Audience:** DevOps Engineers and System Administrators

## Overview

This guide covers production deployment of the LLM Backend System across different environments. You'll learn how to deploy the Admin API, configure backends, deploy to Kubernetes, and monitor system health.

**Quick Links:**
- [Overview](./llm-backend-overview) - System overview
- [Configuration Guide](./llm-backend-config) - Backend configuration
- [Admin API Reference](./llm-backend-admin-api) - API documentation

## Deployment Architecture

```
┌──────────────────────────────────────────────────┐
│         Kubernetes Cluster (thor)                │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────────┐    ┌──────────────────┐   │
│  │  Admin Backend  │    │  Orchestrator     │   │
│  │  Port: 8080     │◄───│  Port: 8001       │   │
│  │  (LLM API)      │    │  (Uses LLMRouter) │   │
│  └────────┬────────┘    └──────────────────┘   │
│           │                                      │
│           ▼                                      │
│  ┌─────────────────┐                            │
│  │  PostgreSQL     │                            │
│  │  llm_backends   │                            │
│  └─────────────────┘                            │
└──────────────────────────────────────────────────┘
                     │
        ┌────────────┴─────────────┐
        ▼                          ▼
┌───────────────┐          ┌───────────────┐
│  Ollama       │          │  MLX Server   │
│  Port: 11434  │          │  Port: 8080   │
│  (Metal GPU)  │          │  (Mac Studio) │
└───────────────┘          └───────────────┘
```

## Prerequisites

### Infrastructure Requirements

**1. Kubernetes Cluster:**
- Cluster: `thor` (192.168.10.222:6443)
- kubectl access configured
- Namespace: `athena` or `athena-admin`

**2. Database:**
- PostgreSQL 13+ (postgres-01.xmojo.net:5432)
- Database created
- Migration tool: Alembic

**3. LLM Backends (at least one):**
- Ollama server (recommended)
- MLX server (optional, Apple Silicon only)

**4. Credentials:**
```bash
# Admin API credentials
kubectl -n automation get secret admin-api-credentials

# Database credentials
kubectl -n automation get secret postgres-credentials
```

---

## Phase 1: Database Setup

### Step 1: Verify PostgreSQL Connection

```bash
# Get database credentials
PGHOST=$(kubectl -n automation get secret postgres-credentials -o jsonpath='{.data.host}' | base64 -d)
PGUSER=$(kubectl -n automation get secret postgres-credentials -o jsonpath='{.data.user}' | base64 -d)
PGPASS=$(kubectl -n automation get secret postgres-credentials -o jsonpath='{.data.password}' | base64 -d)

# Test connection
PGPASSWORD=$PGPASS psql -h $PGHOST -U $PGUSER -d athena -c "SELECT version();"
```

### Step 2: Run Database Migrations

**Using Alembic:**

```bash
# Navigate to admin backend directory
cd /Users/jaystuart/dev/project-athena/admin/backend

# Set database URL
export DATABASE_URL="postgresql://$PGUSER:$PGPASS@$PGHOST:5432/athena"

# Run migrations
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 93bea4659785, add_llm_backend_registry
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

### Step 3: Verify Tables Created

```bash
PGPASSWORD=$PGPASS psql -h $PGHOST -U $PGUSER -d athena -c "\dt"
```

**Expected Output:**
```
             List of relations
 Schema |        Name         | Type  |  Owner
--------+---------------------+-------+---------
 public | llm_backends        | table | psadmin
 public | admin_users         | table | psadmin
 public | config_audit_log    | table | psadmin
```

---

## Phase 2: Deploy Admin API

### Kubernetes Deployment

**Deployment Manifest:** `admin/k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena-admin-backend
  namespace: athena-admin
spec:
  replicas: 2
  selector:
    matchLabels:
      app: athena-admin-backend
  template:
    metadata:
      labels:
        app: athena-admin-backend
    spec:
      containers:
      - name: backend
        image: 192.168.10.222:30500/athena-admin-backend:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: connection-string
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: admin-jwt-secret
              key: secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: athena-admin-backend
  namespace: athena-admin
spec:
  selector:
    app: athena-admin-backend
  ports:
  - protocol: TCP
    port: 8080
    targetPort: 8080
```

**Deploy to Kubernetes:**

```bash
# Apply deployment
kubectl apply -f admin/k8s/deployment.yaml

# Wait for rollout
kubectl -n athena-admin rollout status deployment/athena-admin-backend

# Verify pods running
kubectl -n athena-admin get pods -l app=athena-admin-backend
```

**Expected Output:**
```
NAME                                     READY   STATUS    RESTARTS   AGE
athena-admin-backend-7d4f5c8b9d-abc12    1/1     Running   0          30s
athena-admin-backend-7d4f5c8b9d-def34    1/1     Running   0          30s
```

### Verify Deployment

```bash
# Port forward to access locally
kubectl -n athena-admin port-forward svc/athena-admin-backend 8080:8080 &

# Test health endpoint
curl http://localhost:8080/health

# Test API endpoints
curl http://localhost:8080/api/llm-backends
```

---

## Phase 3: Deploy LLM Backends

### Option A: Deploy Ollama (Recommended)

**1. Install Ollama on Target Server:**

```bash
# Mac Studio (192.168.10.167)
ssh jstuart@192.168.10.167

# Install Ollama
brew install ollama

# Start Ollama service
brew services start ollama

# Verify service running
curl http://localhost:11434/api/tags
```

**2. Pull Models:**

```bash
# Pull phi3:mini (fast classification)
ollama pull phi3:mini

# Pull llama3.1:8b (response synthesis)
ollama pull llama3.1:8b

# Verify models pulled
ollama list
```

**3. Configure Ollama in Admin API:**

```bash
# Get API token
export TOKEN=$(kubectl -n automation get secret admin-api-credentials -o jsonpath='{.data.api-token}' | base64 -d)

# Create Ollama backend for phi3:mini
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "ollama",
    "endpoint_url": "http://192.168.10.167:11434",
    "enabled": true,
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "timeout_seconds": 60,
    "description": "Phi-3 Mini on Mac Studio Ollama"
  }'
```

### Option B: Deploy MLX (Apple Silicon)

**1. Install MLX on Mac Studio:**

```bash
ssh jstuart@192.168.10.167

# Install mlx-lm
pip3 install mlx-lm

# Verify installation
python3 -c "import mlx; print(mlx.__version__)"
```

**2. Convert Models to MLX Format:**

```bash
# Create models directory
mkdir -p ~/models/mlx

# Convert phi3:mini
mlx_lm.convert \
  --hf-path microsoft/Phi-3-mini-4k-instruct \
  --mlx-path ~/models/mlx/phi3-mini

# Convert llama3.1:8b (optional)
mlx_lm.convert \
  --hf-path meta-llama/Meta-Llama-3.1-8B-Instruct \
  --mlx-path ~/models/mlx/llama3.1-8b
```

**3. Create Systemd Service (Linux) or Launch Agent (macOS):**

**macOS Launch Agent:** `~/Library/LaunchAgents/com.athena.mlx.phi3.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.athena.mlx.phi3</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3</string>
        <string>-m</string>
        <string>mlx_lm.server</string>
        <string>--model</string>
        <string>/Users/jstuart/models/mlx/phi3-mini</string>
        <string>--port</string>
        <string>8080</string>
        <string>--host</string>
        <string>0.0.0.0</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/mlx-phi3.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mlx-phi3.err</string>
</dict>
</plist>
```

**Load Launch Agent:**

```bash
launchctl load ~/Library/LaunchAgents/com.athena.mlx.phi3.plist
launchctl start com.athena.mlx.phi3

# Verify service running
curl http://localhost:8080/v1/models
```

**4. Configure MLX in Admin API:**

```bash
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "mlx",
    "endpoint_url": "http://192.168.10.167:8080",
    "enabled": true,
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "timeout_seconds": 60,
    "description": "Phi-3 Mini on MLX (2.3x faster)"
  }'
```

---

## Phase 4: Deploy Orchestrator with LLMRouter

### Step 1: Build Orchestrator Image

```bash
cd /Users/jaystuart/dev/project-athena/src

# Build Docker image
docker build -t athena-orchestrator:latest -f orchestrator/Dockerfile .

# Tag for registry
docker tag athena-orchestrator:latest 192.168.10.222:30500/athena-orchestrator:latest

# Push to registry
docker push 192.168.10.222:30500/athena-orchestrator:latest
```

### Step 2: Deploy to Kubernetes

**Deployment Manifest:** `manifests/orchestrator/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena-orchestrator
  namespace: athena
spec:
  replicas: 2
  selector:
    matchLabels:
      app: athena-orchestrator
  template:
    metadata:
      labels:
        app: athena-orchestrator
    spec:
      containers:
      - name: orchestrator
        image: 192.168.10.222:30500/athena-orchestrator:latest
        ports:
        - containerPort: 8001
        env:
        - name: ADMIN_API_URL
          value: "http://athena-admin-backend.athena-admin.svc.cluster.local:8080"
        - name: REDIS_URL
          value: "redis://redis.athena.svc.cluster.local:6379"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: athena-orchestrator
  namespace: athena
spec:
  selector:
    app: athena-orchestrator
  ports:
  - protocol: TCP
    port: 8001
    targetPort: 8001
```

**Deploy:**

```bash
kubectl apply -f manifests/orchestrator/deployment.yaml

# Wait for rollout
kubectl -n athena rollout status deployment/athena-orchestrator

# Verify pods
kubectl -n athena get pods -l app=athena-orchestrator
```

### Step 3: Verify Integration

```bash
# Port forward orchestrator
kubectl -n athena port-forward svc/athena-orchestrator 8001:8001 &

# Test health endpoint
curl http://localhost:8001/health | jq

# Test query endpoint (uses LLMRouter)
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the weather in Baltimore?",
    "mode": "owner"
  }' | jq
```

**Expected Health Response:**
```json
{
  "status": "healthy",
  "components": {
    "llm_router": "healthy",
    "redis": "healthy"
  }
}
```

---

## Phase 5: Monitoring and Observability

### Structured Logging

**Log Events to Monitor:**

1. **LLM Routing Decisions:**
```json
{
  "event": "routing_llm_request",
  "model": "phi3:mini",
  "backend_type": "mlx",
  "endpoint": "http://192.168.10.167:8080"
}
```

2. **Request Completion:**
```json
{
  "event": "llm_request_completed",
  "model": "phi3:mini",
  "backend_type": "mlx",
  "duration": 2.98
}
```

3. **Fallback Events (Auto mode):**
```json
{
  "event": "mlx_failed_falling_back_to_ollama",
  "error": "Connection refused"
}
```

**View Logs:**

```bash
# Orchestrator logs
kubectl -n athena logs -f deployment/athena-orchestrator | grep routing_llm

# Admin backend logs
kubectl -n athena-admin logs -f deployment/athena-admin-backend
```

### Performance Metrics

**Track Backend Performance:**

```bash
# Get performance stats for all backends
curl -X GET http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | {
    model: .model_name,
    backend: .backend_type,
    tokens_per_sec: .avg_tokens_per_sec,
    latency_ms: .avg_latency_ms,
    requests: .total_requests,
    errors: .total_errors
  }'
```

**Expected Output:**
```json
{
  "model": "phi3:mini",
  "backend": "mlx",
  "tokens_per_sec": 33.4,
  "latency_ms": 2980.0,
  "requests": 142,
  "errors": 1
}
```

### Health Checks

**Endpoint Health Checks:**

```bash
# Admin API health
curl http://localhost:8080/health

# Orchestrator health
curl http://localhost:8001/health

# Ollama health
curl http://192.168.10.167:11434/api/tags

# MLX health
curl http://192.168.10.167:8080/v1/models
```

---

## Rollback Procedures

### Rollback Database Migration

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 003
```

### Rollback Kubernetes Deployment

```bash
# Rollback orchestrator deployment
kubectl -n athena rollout undo deployment/athena-orchestrator

# Rollback admin backend
kubectl -n athena-admin rollout undo deployment/athena-admin-backend

# Check rollout history
kubectl -n athena rollout history deployment/athena-orchestrator
```

### Restore Database Backup

```bash
# Restore from backup
PGPASSWORD=$PGPASS pg_restore \
  -h $PGHOST \
  -U $PGUSER \
  -d athena \
  --clean \
  athena_backup_20251115.dump
```

---

## Production Checklist

**Before Production Deployment:**

- [ ] Database migrations applied successfully
- [ ] Admin API deployed and healthy
- [ ] At least one LLM backend (Ollama) running
- [ ] Backend configurations created for all models
- [ ] Orchestrator deployed and using LLMRouter
- [ ] Health checks passing
- [ ] Logging configured and monitored
- [ ] Backups configured (database + configurations)
- [ ] Rollback procedures tested
- [ ] Documentation updated

**Post-Deployment Verification:**

- [ ] Test query end-to-end
- [ ] Verify correct backend routing
- [ ] Check performance metrics
- [ ] Monitor error rates
- [ ] Verify fallback behavior (if using Auto mode)

---

## Troubleshooting

### Issue: Orchestrator Can't Reach Admin API

**Symptom:** Orchestrator logs show "Connection refused" to Admin API.

**Solution:**
```bash
# Verify Admin API service exists
kubectl -n athena-admin get svc athena-admin-backend

# Check service endpoints
kubectl -n athena-admin get endpoints athena-admin-backend

# Verify ADMIN_API_URL environment variable
kubectl -n athena get deployment athena-orchestrator -o yaml | grep ADMIN_API_URL
```

### Issue: Backend Configuration Not Taking Effect

**Symptom:** Router using old configuration after update.

**Cause:** Configuration cache (60-second TTL).

**Solution:**
```bash
# Wait 60 seconds, or restart orchestrator
kubectl -n athena rollout restart deployment/athena-orchestrator
```

### Issue: MLX Server Not Accessible

**Symptom:** Auto mode not falling back, getting timeouts.

**Solution:**
```bash
# Check MLX server status
ssh jstuart@192.168.10.167 'curl http://localhost:8080/v1/models'

# Check Launch Agent status (macOS)
ssh jstuart@192.168.10.167 'launchctl list | grep mlx'

# Restart MLX server
ssh jstuart@192.168.10.167 'launchctl stop com.athena.mlx.phi3 && launchctl start com.athena.mlx.phi3'
```

---

## Next Steps

- **[Configuration Guide](./llm-backend-config)** - Configure backends
- **[Admin API Reference](./llm-backend-admin-api)** - API usage
- **[Router Technical Docs](./llm-backend-router)** - Router internals
- **[Overview](./llm-backend-overview)** - Back to system overview

---

**Last Updated:** November 15, 2025
**Maintained By:** Jay Stuart
