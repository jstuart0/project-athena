# Admin Configuration Management

This document explains how Project Athena services fetch configuration and secrets from the centralized admin interface.

## Overview

Instead of storing secrets in environment variables scattered across different machines, all sensitive configuration is:

1. **Stored encrypted** in the admin database
2. **Fetched on-demand** by services using a secure API
3. **Audited automatically** when accessed or modified
4. **Managed via UI** at https://athena-admin.xmojo.net

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Interface                           │
│  https://athena-admin.xmojo.net                             │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   Secrets    │         │   Users /    │                │
│  │  Management  │         │     RBAC     │                │
│  └──────────────┘         └──────────────┘                │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────────────────────┐                      │
│  │   PostgreSQL (Encrypted)         │                      │
│  │   - home-assistant                │                      │
│  │   - openweathermap-api-key       │                      │
│  │   - other-secrets...             │                      │
│  └──────────────────────────────────┘                      │
└─────────────────────┬────────────────────────────────────────┘
                      │
                      │ HTTP + X-API-Key
                      ▼
         ┌────────────────────────────┐
         │   Project Athena Services  │
         │                            │
         │  - Orchestrator (8001)     │
         │  - Gateway (8000)          │
         │  - RAG Services (8010+)    │
         └────────────────────────────┘
```

## Setup

### 1. Admin API Deployment

The admin API is deployed in the thor Kubernetes cluster:

```bash
kubectl -n athena-admin get pods
kubectl -n athena-admin get svc
```

**Access:** https://athena-admin.xmojo.net

### 2. Service API Key

Generate a secure service API key and add it to:

**Thor Cluster (for admin backend):**
```bash
kubectl -n athena-admin create secret generic service-api-key \
  --from-literal=SERVICE_API_KEY=$(openssl rand -hex 32)
```

**Mac Studio (for services):**
```bash
# Add to ~/dev/project-athena/.env
SERVICE_API_KEY=<same-key-as-above>
ADMIN_API_URL=https://athena-admin.xmojo.net  # Or http://localhost:8080 for local
```

### 3. Store Secrets in Admin

**Via Admin UI:**
1. Log in to https://athena-admin.xmojo.net
2. Navigate to **Secrets** → **Add Secret**
3. Fill in:
   - **Service Name:** `home-assistant`
   - **Value:** Your HA long-lived token
   - **Description:** Home Assistant access token

**Via API:**
```bash
# Get your admin JWT token from the UI first
curl -X POST https://athena-admin.xmojo.net/api/secrets \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "home-assistant",
    "value": "your-ha-token",
    "description": "Home Assistant long-lived access token"
  }'
```

## Usage in Services

### Python Services

```python
from shared.admin_config import get_secret, get_config

# Fetch a secret
ha_token = await get_secret("home-assistant")

# Fetch configuration (falls back to env vars)
timeout = await get_config("REQUEST_TIMEOUT", default=30)
```

### Full Example

```python
from fastapi import FastAPI
from shared.admin_config import AdminConfigClient

app = FastAPI()
admin_client = None

@app.on_event("startup")
async def startup():
    """Initialize admin client on startup."""
    global admin_client
    admin_client = AdminConfigClient(
        admin_url="https://athena-admin.xmojo.net",
        api_key=os.getenv("SERVICE_API_KEY")
    )

    # Fetch Home Assistant token
    ha_token = await admin_client.get_secret("home-assistant")
    if not ha_token:
        raise ValueError("Home Assistant token not configured")

    # Store for use in requests
    app.state.ha_token = ha_token

@app.on_event("shutdown")
async def shutdown():
    """Clean up admin client."""
    if admin_client:
        await admin_client.close()
```

## Available Secrets

| Service Name | Description | Used By |
|---|---|---|
| `home-assistant` | HA long-lived access token | Orchestrator, Gateway |
| `openweathermap-api-key` | Weather API key | Weather RAG service |
| `ticketmaster-api-key` | Ticketmaster API key | Events RAG service |
| *(add more as needed)* | | |

## Security

### Encryption

- **At Rest:** Secrets are encrypted using Fernet (symmetric encryption) before storing in PostgreSQL
- **In Transit:** HTTPS with TLS 1.2+ for all API calls
- **API Key:** Service-to-service authentication uses HMAC-verified API keys

### Audit Logging

All secret access is logged:
- Who accessed the secret (service name)
- When it was accessed
- IP address of requester

View audit logs in the admin UI under **Audit**.

### RBAC

User permissions:
- **owner**: Full access (read, write, manage secrets, manage users)
- **operator**: Read/write access (cannot manage secrets)
- **viewer**: Read-only access
- **support**: Read-only + audit log access

## Migration from Environment Variables

To migrate secrets from `.env` files to the admin database:

1. **Identify secrets** in your `.env` file:
   ```bash
   grep -E "TOKEN|KEY|PASSWORD|SECRET" ~/dev/project-athena/.env
   ```

2. **Add to admin database** via UI or API (see Setup section)

3. **Update service code** to use `get_secret()` instead of `os.getenv()`

4. **Remove from `.env`** once confirmed working

5. **Update deployment scripts** to no longer inject environment variables

## Troubleshooting

### Service can't fetch secrets

**Check service API key:**
```bash
# On Mac Studio
grep SERVICE_API_KEY ~/dev/project-athena/.env
```

**Check admin API accessibility:**
```bash
curl -H "X-API-Key: YOUR_SERVICE_API_KEY" \
  https://athena-admin.xmojo.net/api/secrets/service/home-assistant
```

Expected response:
```json
{
  "id": 1,
  "service_name": "home-assistant",
  "value": "your-token-here",
  "description": "Home Assistant access token"
}
```

### Secret not found (404)

The secret hasn't been created in the admin database. Add it via the admin UI.

### Authentication failed (401)

The SERVICE_API_KEY is incorrect or missing. Verify it matches between:
- Admin backend Kubernetes secret
- Service `.env` file

## Best Practices

1. **Never commit secrets** to git - use admin database instead
2. **Rotate secrets regularly** - use the admin UI to update values
3. **Use descriptive names** - `home-assistant` not `ha_token`
4. **Add descriptions** - explain what each secret is for
5. **Monitor audit logs** - review who's accessing secrets

## Future Enhancements

- [ ] Automatic secret rotation
- [ ] Secret versioning and rollback
- [ ] Integration with HashiCorp Vault
- [ ] Secret expiration and alerts
- [ ] Multi-environment support (dev, staging, prod)

---

# Database-Driven LLM Backend Configuration

## Overview

Project Athena services (Gateway, Orchestrator, RAG) now fetch LLM backend configuration from the admin database instead of environment variables. This enables:

1. **Live Configuration Updates** - Changes in Admin UI propagate to services within 60 seconds
2. **No Service Restarts** - Configuration updates don't require redeploying services
3. **Centralized Management** - Single source of truth for all LLM backend settings
4. **Performance Tracking** - Database tracks metrics (latency, tokens/sec, request counts)
5. **Priority-Based Selection** - Configure backend priorities for intelligent routing

## What's Configurable

### LLM Backends

Each LLM backend configuration includes:

| Field | Description | Example |
|---|---|---|
| `model_name` | Model identifier (unique) | `phi3:mini`, `llama3.1:8b-q4` |
| `backend_type` | Backend type | `ollama`, `mlx`, `auto` |
| `endpoint_url` | Backend service URL | `http://192.168.10.167:11434` |
| `enabled` | Whether backend is active | `true` / `false` |
| `priority` | Routing priority (lower = higher) | `100`, `200` |
| `max_tokens` | Maximum tokens to generate | `2048`, `4096` |
| `temperature_default` | Default temperature | `0.7` |
| `timeout_seconds` | Request timeout | `60`, `90` |
| `description` | Human-readable description | "Fast classification" |

### Feature Flags

System features can be toggled on/off via the admin UI:

- **RAG Services** - Enable/disable specific RAG services (weather, sports, airports)
- **Caching** - Redis caching on/off
- **MLX Backend** - Use MLX for inference
- **Response Streaming** - Stream responses to clients
- **Performance Features** - Various optimizations

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Admin Interface                       │
│  https://athena-admin.xmojo.net                         │
│                                                          │
│  ┌──────────────┐         ┌──────────────┐            │
│  │ LLM Backends │         │   Features   │            │
│  │  Management  │         │    Flags     │            │
│  └──────────────┘         └──────────────┘            │
│           │                                             │
│           ▼                                             │
│  ┌──────────────────────────────────┐                  │
│  │   PostgreSQL (admin database)    │                  │
│  │   - llm_backends table           │                  │
│  │   - features table               │                  │
│  │   - llm_performance_metrics      │                  │
│  └──────────────────────────────────┘                  │
└─────────────────────┬────────────────────────────────────┘
                      │
                      │ HTTP (no auth for services)
                      │ 60-second cache TTL
                      ▼
         ┌────────────────────────────┐
         │   Project Athena Services  │
         │                            │
         │  - Gateway (8000)          │
         │  - Orchestrator (8001)     │
         │  - RAG Services (8010+)    │
         │                            │
         │  Uses: AdminConfigClient   │
         │  Cache: 60 seconds         │
         └────────────────────────────┘
```

## Using the Admin UI

### Managing LLM Backends

**View Backends:**
1. Log in to https://athena-admin.xmojo.net
2. Navigate to **AI Configuration** → **LLM Backends**
3. See list of all configured backends with performance metrics

**Add New Backend:**
1. Click **Add Backend**
2. Fill in configuration:
   - Model Name: `qwen2:7b` (example)
   - Backend Type: `ollama`
   - Endpoint URL: `http://192.168.10.167:11434`
   - Priority: `150`
   - Max Tokens: `2048`
   - Description: "Qwen 2 7B for general queries"
3. Click **Save**
4. Backend will be available to services within 60 seconds

**Edit Backend:**
1. Click **Edit** on existing backend
2. Modify fields (endpoint URL, priority, enabled status, etc.)
3. Click **Save**
4. Changes propagate within 60 seconds (cache TTL)

**Disable Backend:**
1. Click **Toggle** button on backend row
2. Backend becomes unavailable immediately (on next cache refresh)
3. Services will skip disabled backends

**Delete Backend:**
1. Click **Delete** on backend row
2. Confirm deletion
3. Backend removed from database and services

### Managing Feature Flags

**Toggle Feature:**
1. Navigate to **AI Configuration** → **Feature Flags**
2. Find feature (e.g., "RAG Weather Service")
3. Click **Toggle** switch
4. Change propagates within 60 seconds

**View Feature Impact:**
1. Navigate to **What-If Analysis**
2. See latency impact of each feature
3. Compare scenarios (all optimizations, no RAG, no caching, etc.)

## How Services Consume Configuration

### Python Services (Gateway, Orchestrator)

Services use the `AdminConfigClient` to fetch configuration:

```python
from shared.admin_config import get_admin_client

# Get admin client singleton
admin_client = get_admin_client()

# Fetch LLM backends (cached for 60 seconds)
backends = await admin_client.get_llm_backends()

# Result: List of enabled backends sorted by priority
# [
#   {"model_name": "phi3:mini", "backend_type": "ollama",
#    "endpoint_url": "http://192.168.10.167:11434", ...},
#   {"model_name": "llama3.1:8b-q4", "backend_type": "ollama", ...}
# ]

# Check if feature is enabled
redis_enabled = await admin_client.is_feature_enabled("redis_caching")
```

### LLMRouter Integration

The `LLMRouter` singleton automatically fetches backend configuration from the database:

```python
from shared.llm_router import get_llm_router

# Get router singleton (pre-configured with admin API)
router = get_llm_router()

# Router automatically queries database for backend config
response = await router.generate(
    model="phi3:mini",
    prompt="What is the weather?",
    max_tokens=200
)

# Router fetches backend config from:
# GET https://athena-admin.xmojo.net/api/llm-backends/model/phi3:mini
```

## Cache TTL and Propagation Time

**Configuration Changes:**
- **Cache Duration:** 60 seconds
- **Propagation Time:** Up to 60 seconds after saving changes
- **Cache Location:** In-memory cache within each service instance

**How It Works:**
1. Admin makes change in UI → Saved to PostgreSQL
2. Service has cached config for up to 60 seconds
3. After cache expires, service fetches new config from database
4. New requests use updated configuration

**Force Immediate Update:**
- Restart service to clear cache immediately
- Wait 60 seconds for natural cache expiration

## API Reference

### Public Endpoints (No Authentication)

These endpoints are used by services and don't require authentication:

**List All LLM Backends:**
```bash
GET https://athena-admin.xmojo.net/api/llm-backends/public?enabled_only=true

Response:
[
  {
    "id": 1,
    "model_name": "phi3:mini",
    "backend_type": "ollama",
    "endpoint_url": "http://192.168.10.167:11434",
    "enabled": true,
    "priority": 100,
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "timeout_seconds": 60,
    "description": "Phi-3 Mini (Q4) - Fast classification",
    "avg_tokens_per_sec": 45.2,
    "avg_latency_ms": 1250.0,
    "total_requests": 1543,
    "total_errors": 12
  }
]
```

**Get Backend for Specific Model:**
```bash
GET https://athena-admin.xmojo.net/api/llm-backends/model/{model_name}

Example: GET /api/llm-backends/model/phi3:mini

Response: (same as list, single object)
```

**List Feature Flags:**
```bash
GET https://athena-admin.xmojo.net/api/features/public?enabled_only=false

Response:
[
  {
    "id": 1,
    "name": "redis_caching",
    "display_name": "Redis Caching",
    "description": "Cache LLM responses in Redis",
    "category": "performance",
    "enabled": true,
    "avg_latency_ms": 15.0,
    "priority": 10
  }
]
```

### Authenticated Endpoints (Admin Only)

**Create Backend:**
```bash
POST https://athena-admin.xmojo.net/api/llm-backends
Authorization: Bearer YOUR_ADMIN_TOKEN
Content-Type: application/json

{
  "model_name": "qwen2:7b",
  "backend_type": "ollama",
  "endpoint_url": "http://192.168.10.167:11434",
  "enabled": true,
  "priority": 150,
  "max_tokens": 2048,
  "temperature_default": 0.7,
  "timeout_seconds": 60,
  "description": "Qwen 2 7B for general queries"
}
```

**Update Backend:**
```bash
PUT https://athena-admin.xmojo.net/api/llm-backends/{backend_id}
Authorization: Bearer YOUR_ADMIN_TOKEN
Content-Type: application/json

{
  "enabled": false,
  "priority": 200
}
```

**Delete Backend:**
```bash
DELETE https://athena-admin.xmojo.net/api/llm-backends/{backend_id}
Authorization: Bearer YOUR_ADMIN_TOKEN
```

## Verification Steps

### Confirm Services Use Database Configs

**1. Check Gateway Logs:**
```bash
docker logs athena-gateway 2>&1 | grep -i "llm_backends_loaded_from_db"

Expected output:
{"event": "llm_backends_loaded_from_db", "count": 2,
 "backends": ["phi3:mini", "llama3.1:8b-q4"]}
```

**2. Check Orchestrator Logs:**
```bash
docker logs athena-orchestrator 2>&1 | grep -i "LLM Router initialized"

Expected output:
{"event": "LLM Router initialized with admin API: https://athena-admin.xmojo.net"}
```

**3. Query Admin API:**
```bash
curl -s https://athena-admin.xmojo.net/api/llm-backends/public | jq

# Should return list of configured backends
```

**4. Test Configuration Change:**
1. Log in to admin UI
2. Change priority of `phi3:mini` from 100 to 50
3. Wait 60 seconds (cache TTL)
4. Send test request to Gateway
5. Check logs to confirm new priority used

## Troubleshooting

### Service Not Using Database Configs

**Symptom:** Service still uses .env variables instead of database configuration.

**Check:**
```bash
# View service logs for admin client initialization
docker logs athena-gateway 2>&1 | grep -i "admin"

# Expected to see:
# "Admin config client initialized"
# "llm_backends_loaded_from_db"
```

**Fix:**
1. Verify `ADMIN_API_URL` environment variable points to admin backend
2. Check admin backend is accessible: `curl https://athena-admin.xmojo.net/health`
3. Restart service to clear cache: `docker restart athena-gateway`
4. Check service logs for connection errors

### Configuration Changes Not Propagating

**Symptom:** Changed backend priority in UI but service still uses old value.

**Cause:** Cache TTL (60 seconds) has not expired yet.

**Fix:**
- **Wait 60 seconds** for cache to expire naturally
- **OR** restart service: `docker restart athena-gateway`

### Backend Not Found (404)

**Symptom:** Service logs show "backend_not_found" for model.

**Cause:** Model not configured in database.

**Fix:**
1. Log in to admin UI
2. Navigate to **LLM Backends**
3. Add backend for the model
4. Ensure `enabled` is set to `true`
5. Wait 60 seconds or restart service

### Database Connection Failed

**Symptom:** Logs show "llm_backends_db_error" or "admin_api_connection_failed".

**Fix:**
```bash
# Check admin backend is running
kubectl -n athena-admin get pods

# Check admin backend logs
kubectl -n athena-admin logs -f deployment/athena-admin-backend

# Verify database is accessible
psql -h postgres-01.xmojo.net -U psadmin -d athena_admin -c "SELECT COUNT(*) FROM llm_backends;"
```

### Service Falls Back to Environment Variables

**Symptom:** Logs show "using environment variable fallback" or similar.

**Behavior:** This is intentional - services gracefully fall back to .env if database unavailable.

**When This Happens:**
- Admin API is unreachable
- Database query fails
- Network connectivity issues

**Fix:**
- Ensure admin backend is healthy
- Check network connectivity between services
- Verify `ADMIN_API_URL` is correct

## Best Practices

1. **Always use Admin UI for configuration changes** - Don't modify database directly
2. **Set appropriate priorities** - Lower = higher priority (100, 200, 300, etc.)
3. **Add descriptions** - Help operators understand backend purpose
4. **Monitor performance metrics** - Check avg_latency_ms and tokens_per_sec
5. **Test before disabling** - Ensure other backends can handle load
6. **Use feature flags** - Toggle features instead of removing backends
7. **Document backend purposes** - Add clear descriptions in Admin UI

## Performance Tracking

The system automatically tracks performance metrics for each backend:

| Metric | Description | Populated By |
|---|---|---|
| `avg_tokens_per_sec` | Average token generation speed | Performance metrics aggregation |
| `avg_latency_ms` | Average request latency | Performance metrics aggregation |
| `total_requests` | Total requests processed | Incremented on each request |
| `total_errors` | Total errors encountered | Incremented on failures |

**View Metrics:**
1. Navigate to **AI Configuration** → **LLM Backends**
2. See real-time metrics in backend list
3. Click backend for detailed performance history

**Performance Metrics API:**
```bash
# Get recent metrics for a model
GET https://athena-admin.xmojo.net/api/llm-backends/metrics?model=phi3:mini&limit=100

# Response: List of recent request metrics
```

## Database Schema

### llm_backends Table

```sql
CREATE TABLE llm_backends (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) UNIQUE NOT NULL,
    backend_type VARCHAR(50) NOT NULL,  -- ollama, mlx, auto
    endpoint_url VARCHAR(500) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100,
    max_tokens INTEGER DEFAULT 2048,
    temperature_default FLOAT DEFAULT 0.7,
    timeout_seconds INTEGER DEFAULT 60,
    description TEXT,

    -- Performance tracking
    avg_tokens_per_sec FLOAT,
    avg_latency_ms FLOAT,
    total_requests INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,

    -- Audit
    created_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Initial Seed Data

Migration `010_seed_initial_configs.py` seeds:

```sql
INSERT INTO llm_backends VALUES
    ('phi3:mini', 'ollama', 'http://192.168.10.167:11434', true, 100, 2048, 0.7, 60,
     'Phi-3 Mini (Q4) - Fast classification and quick responses'),
    ('llama3.1:8b-q4', 'ollama', 'http://192.168.10.167:11434', true, 200, 4096, 0.7, 90,
     'Llama 3.1 8B (Q4) - Complex reasoning and detailed responses');
```

## Future Enhancements

- [ ] A/B testing support for backend comparisons
- [ ] Cost tracking per backend (if using paid APIs)
- [ ] Automatic backend health checks and failover
- [ ] Backend load balancing across multiple endpoints
- [ ] Historical performance trend charts
- [ ] Alerting for backend failures or degraded performance
- [ ] Multi-region backend support
