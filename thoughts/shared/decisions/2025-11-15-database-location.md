# Database Location for Project Athena

**Date:** 2025-11-15
**Decision:** Always use homelab PostgreSQL server for Admin Panel database

## Context

Project Athena's Admin Panel uses PostgreSQL for configuration and analytics storage. The database is NOT local to the Mac Studio - it's hosted on the homelab infrastructure server.

## Database Connection Details

**Host:** `postgres-01.xmojo.net` (192.168.10.xxx - resolve via DNS)
**Port:** `5432`
**Database:** `athena_admin`
**User:** `athena_admin`
**Password:** Stored in Kubernetes secrets

**Connection String:**
```
postgresql://athena_admin:<password>@postgres-01.xmojo.net:5432/athena_admin
```

## Important Reminders

### ⚠️ ALWAYS use postgres-01.xmojo.net

**When running migrations:**
```bash
# ✅ CORRECT - Uses homelab PostgreSQL server
psql postgresql://athena_admin:athena_admin@postgres-01.xmojo.net:5432/athena_admin < migration.sql

# ❌ WRONG - Uses localhost (doesn't exist)
psql postgresql://athena_admin:athena_admin@localhost:5432/athena_admin < migration.sql
```

**When configuring services:**
```bash
# .env file for admin backend
ADMIN_DB_HOST=postgres-01.xmojo.net  # NOT localhost
ADMIN_DB_PORT=5432
ADMIN_DB_NAME=athena_admin
ADMIN_DB_USER=athena_admin
ADMIN_DB_PASSWORD=<from-secrets>
```

**When writing Python code:**
```python
# Database URL in admin backend
DATABASE_URL = "postgresql://athena_admin:<password>@postgres-01.xmojo.net:5432/athena_admin"

# Config loader in orchestrator
ADMIN_DB_HOST = "postgres-01.xmojo.net"  # NOT localhost
```

## Why This Matters

1. **Centralized Infrastructure** - postgres-01.xmojo.net is the homelab's central database server
2. **Shared Across Services** - Multiple services use this database (Admin Panel, future services)
3. **Persistent Storage** - Data persists across Mac Studio restarts
4. **Backup Integration** - Homelab backup strategy covers postgres-01.xmojo.net
5. **High Availability** - Future HA setup will be on homelab infrastructure

## Related Infrastructure

**From `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`:**

> **Primary Database Server: postgres-01.xmojo.net:5432**
>
> **Databases:**
> - `wikijs` - Wiki.js documentation
> - `authentik` - Authentik SSO
> - `smartbenefit` - Smart Benefit Wallet (application)
> - `keycloak` - Keycloak OAuth2 (if deployed here)
> - **`athena_admin` - Project Athena Admin Panel** ← Our database
>
> **Admin User:** `psadmin`
> **Password:** Check `automation` namespace secrets or Vaultwarden

## Getting Database Password

```bash
# From thor cluster
kubectl config use-context thor
kubectl -n automation get secret postgres-credentials -o jsonpath='{.data.admin-password}' | base64 -d
```

## Verifying Connection

```bash
# Test connection from Mac Studio
ssh jstuart@192.168.10.167 "psql postgresql://athena_admin:athena_admin@postgres-01.xmojo.net:5432/athena_admin -c '\dt'"

# Should return list of tables including:
# - conversation_settings
# - clarification_settings
# - etc.
```

## Future Considerations

- **Multi-region:** If deploying Project Athena in other locations, each location should have its own postgres instance
- **Read replicas:** For high-traffic deployments, consider postgres-01 as primary with read replicas
- **Connection pooling:** Admin backend should use connection pooling (pgbouncer or asyncpg pool)

---

**Last Updated:** 2025-11-15
**Related Files:**
- `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md` - Homelab infrastructure documentation
- `admin/backend/.env` - Database connection configuration
- `src/orchestrator/config_loader.py` - Orchestrator config loading
