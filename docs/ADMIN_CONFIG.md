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
