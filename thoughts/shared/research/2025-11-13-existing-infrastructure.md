# Existing Infrastructure and Deployments
**Date:** 2025-11-13
**Author:** Assistant
**Status:** Reference Document

## Purpose
Document what infrastructure and deployment artifacts already exist to prevent recreating them.

## Admin Interface - Already Exists!

### Location: `/admin` directory

**Backend (`/admin/backend/`):**
- `main.py` - FastAPI application entry point
- `app/` - Application modules (auth, routes, models, database)
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container definition
- `alembic/` - Database migrations (if needed)
- `alembic.ini` - Alembic configuration

**Frontend (`/admin/frontend/`):**
- `index.html` - Main HTML page
- `app.js` - Frontend JavaScript application
- `Dockerfile` - Nginx-based container
- `nginx.conf` - Nginx configuration (created if missing)

### Kubernetes Manifests (`/admin/k8s/`)

**Existing Files:**
1. **deployment.yaml** - Complete K8s deployment containing:
   - Namespace: `athena-admin`
   - Backend Deployment (2 replicas)
   - Backend Service (ClusterIP)
   - Frontend Deployment (2 replicas)
   - Frontend Service (ClusterIP)
   - Ingress (athena-admin.xmojo.net)

2. **create-secrets.sh** - Script to create all required secrets:
   - `athena-admin-db` - Database credentials
   - `athena-admin-secrets` - Session and JWT secrets
   - `athena-admin-oidc` - Authentik OIDC configuration

3. **postgres.yaml** - PostgreSQL deployment (if needed locally)
4. **redis.yaml** - Redis deployment (if needed locally)
5. **README.md** - Documentation for the K8s deployment

**Registry:** Images push to `192.168.10.222:30500` (Thor cluster registry)

### Key Configuration Points

**Database:**
- Uses `postgres-01.xmojo.net` (192.168.10.30)
- Database: `athena_admin`
- User: `psadmin`
- Password: `Ibucej1!` (needs URL encoding: `Ibucej1%21`)

**Ingress:**
- URL: `https://athena-admin.xmojo.net`
- TLS: cert-manager with letsencrypt-production
- Traefik ingress controller

**Environment Variables Set in deployment.yaml:**
- `MAC_STUDIO_IP`: 192.168.10.167
- `MAC_MINI_IP`: 192.168.10.181
- `PORT`: 8080
- `REDIS_URL`: redis://redis:6379
- Plus secrets from K8s secrets

## Gateway and Orchestrator Services

### Deployment Location: Mac Studio (192.168.10.167)

**NOT in Kubernetes!** These run as Python processes on Mac Studio.

**Gateway:**
- Port: 8000
- OpenAI-compatible API
- Code: `/src/gateway/`
- No Dockerfile needed for Mac Studio deployment

**Orchestrator:**
- Port: 8001
- LangGraph state machine
- Code: `/src/orchestrator/`
- Includes intent classification, validation, multi-intent handling

**Deployment Script:**
- `/scripts/deploy_to_mac_studio.sh` - Deploys gateway and orchestrator

## RAG Services

### Deployment Location: Mac Studio (192.168.10.167)

**Running Services:**
- Weather (Port 8010)
- Airports (Port 8011)
- Sports (Port 8012)
- Additional services can be added (8013-8017)

**Code Structure:**
- `/src/rag/base_rag_service.py` - Base class for all RAG services
- `/src/rag/service.py` - Generic service runner

**Deployment:**
- Services run as Python processes
- Configuration loaded from database
- No Docker containers on Mac Studio

## Database Schema

### Already Created via Migration Script

**Script:** `/scripts/run_migrations.py`

**Tables Created:**
- `intent_categories`
- `intent_patterns`
- `intent_entities`
- `validation_rules`
- `multi_intent_config`
- `intent_chain_rules`
- `rag_services`
- `rag_service_params`
- `rag_response_templates`
- `query_logs`

**Admin Tables:**
- `admin_users`
- `admin_sessions`
- `config_audit_log`

**Initial Data:** Seeded with categories, patterns, and service configurations

## What Should NOT Be Created Again

1. **Admin Interface Code** - Already exists in `/admin/`
2. **Kubernetes Manifests** - Already in `/admin/k8s/`
3. **Database Tables** - Already created via migration
4. **RAG Service Framework** - Already implemented
5. **Gateway/Orchestrator** - Already deployed on Mac Studio

## Deployment Commands

### To Deploy Admin to Thor (from machine with kubectl access):
```bash
cd admin/k8s
chmod +x build-and-deploy.sh
./build-and-deploy.sh
```

### To Deploy Services on Mac Studio:
```bash
# Gateway and Orchestrator
./scripts/deploy_to_mac_studio.sh

# RAG Services
./scripts/deploy_rag_services.sh
```

### To Run Database Migrations:
```bash
# From Mac Studio (has network access)
python3 scripts/run_migrations.py
```

## Common Mistakes to Avoid

1. **Don't deploy admin interface on Mac Studio** - It belongs on Thor K8s
2. **Don't containerize Mac Studio services** - They run as Python processes
3. **Don't recreate database tables** - Migration script already ran
4. **Don't forget to URL-encode the database password** (`Ibucej1%21`)
5. **Don't create new manifests** - Update existing ones in `/admin/k8s/`

## Service Locations Summary

| Service | Location | Port | Deployment Method |
|---------|----------|------|-------------------|
| Admin Backend | Thor K8s | 8080 | Kubernetes |
| Admin Frontend | Thor K8s | 80 | Kubernetes |
| Gateway | Mac Studio | 8000 | Python process |
| Orchestrator | Mac Studio | 8001 | Python process |
| RAG Services | Mac Studio | 8010-8017 | Python processes |
| Ollama | Mac Studio | 11434 | Existing |
| Redis | Mac mini | 6379 | Docker |
| Qdrant | Mac mini | 6333 | Docker |
| PostgreSQL | postgres-01.xmojo.net | 5432 | Existing |

## Notes for Future

- Admin interface manifests already exist - just need to build images and deploy
- All database configuration is already seeded
- RAG services are database-configurable (no code changes needed)
- Gateway and orchestrator are NOT containerized on Mac Studio
- Everything is already built, just needs proper deployment commands