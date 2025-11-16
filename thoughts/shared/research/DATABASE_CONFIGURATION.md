# Database Configuration - IMPORTANT

## ⚠️ CRITICAL: Use postgres-01.xmojo.net, NOT localhost

**All admin database operations use the shared PostgreSQL server.**

## Connection Details

**Database Server**: `postgres-01.xmojo.net:5432`
**Database Name**: `athena_admin`
**Admin User**: `psadmin`
**Password**: Stored in thor cluster secrets

```bash
# Get password from thor cluster
kubectl config use-context thor
kubectl -n automation get secret postgres-credentials -o jsonpath='{.data.admin-password}' | base64 -d
```

## Configuration Files

### Admin Backend Database URL

**File**: `admin/backend/app/database.py`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ✅ CORRECT - Uses postgres-01
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin"
)

# ❌ WRONG - Do NOT use localhost
# DATABASE_URL = "postgresql://user:password@localhost:5432/athena_admin"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Alembic Migration Configuration

**File**: `admin/backend/alembic.ini`

```ini
[alembic]
# ✅ CORRECT - Uses postgres-01
sqlalchemy.url = postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin

# ❌ WRONG - Do NOT use localhost
# sqlalchemy.url = postgresql://user:password@localhost:5432/athena_admin
```

**File**: `admin/backend/alembic/env.py`

```python
from sqlalchemy import engine_from_config, pool

# ✅ CORRECT - Override from environment or config
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", "postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin")
)

# ❌ WRONG - Hardcoded localhost
# config.set_main_option("sqlalchemy.url", "postgresql://user:password@localhost:5432/db")
```

## Environment Variables

**File**: `admin/backend/.env` (if using)

```bash
# ✅ CORRECT
DATABASE_URL=postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin

# ❌ WRONG
# DATABASE_URL=postgresql://user:password@localhost:5432/athena_admin
```

**Docker Compose**: `admin/k8s/docker-compose.yml`

```yaml
services:
  backend:
    environment:
      # ✅ CORRECT - postgres-01 is accessible from containers
      DATABASE_URL: postgresql://psadmin:${DB_PASSWORD}@postgres-01.xmojo.net:5432/athena_admin

      # ❌ WRONG - localhost refers to container, not host
      # DATABASE_URL: postgresql://psadmin:password@localhost:5432/athena_admin
```

## Running Migrations

### From Mac Studio

```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin"

# Navigate to admin backend
cd /Users/jaystuart/dev/project-athena/admin/backend

# Create migration
alembic revision --autogenerate -m "Add LLM backend registry"

# Apply migration
alembic upgrade head
```

### From Docker Container

```bash
# Migrations run inside container automatically connect to postgres-01
cd /Users/jaystuart/dev/project-athena/admin/k8s

# Build and run with migrations
./build-and-deploy.sh
```

## Testing Database Connection

### Python Test Script

```python
# test_db_connection.py
from sqlalchemy import create_engine, text

# ✅ CORRECT - postgres-01
DATABASE_URL = "postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin"

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print("✓ Connected to postgres-01!")
        print(f"PostgreSQL version: {result.scalar()}")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Command Line Test

```bash
# Using psql
psql -h postgres-01.xmojo.net -U psadmin -d athena_admin

# Test query
psql -h postgres-01.xmojo.net -U psadmin -d athena_admin -c "SELECT current_database();"
```

## LLM Backend Registry - Database Location

When creating the `llm_backends` table:

```sql
-- This table will be created on postgres-01.xmojo.net
-- Database: athena_admin
-- Schema: public

CREATE TABLE llm_backends (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) UNIQUE NOT NULL,
    backend_type VARCHAR(32) NOT NULL,
    endpoint_url VARCHAR(500) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    -- ... other columns
);
```

## Network Access

**postgres-01.xmojo.net is accessible from**:
- ✅ Mac Studio (192.168.10.167)
- ✅ Mac mini (192.168.10.181)
- ✅ Docker containers (via host networking)
- ✅ Kubernetes pods in thor cluster
- ✅ Any device on 192.168.10.0/24 network

**Firewall**: PostgreSQL port 5432 is open for internal network.

## Troubleshooting

### "Connection refused"

```bash
# Check if postgres-01 is accessible
ping postgres-01.xmojo.net

# Check if PostgreSQL is listening
nc -zv postgres-01.xmojo.net 5432

# Check from Mac Studio
ssh jstuart@192.168.10.167 'psql -h postgres-01.xmojo.net -U psadmin -d athena_admin -c "SELECT 1"'
```

### "Authentication failed"

```bash
# Verify password from kubernetes secret
kubectl config use-context thor
kubectl -n automation get secret postgres-credentials -o jsonpath='{.data.admin-password}' | base64 -d

# Update DATABASE_URL with correct password
export DATABASE_URL="postgresql://psadmin:CORRECT_PASSWORD@postgres-01.xmojo.net:5432/athena_admin"
```

### "Database does not exist"

```bash
# List databases on postgres-01
psql -h postgres-01.xmojo.net -U psadmin -l

# Create athena_admin database if missing
psql -h postgres-01.xmojo.net -U psadmin -c "CREATE DATABASE athena_admin;"
```

## Quick Reference

| Component | Database Host | Port | Database Name |
|-----------|--------------|------|---------------|
| Admin Backend | `postgres-01.xmojo.net` | 5432 | `athena_admin` |
| Alembic Migrations | `postgres-01.xmojo.net` | 5432 | `athena_admin` |
| LLM Backend Registry | `postgres-01.xmojo.net` | 5432 | `athena_admin` |

**Remember**:
- ✅ **ALWAYS** use `postgres-01.xmojo.net`
- ❌ **NEVER** use `localhost` for admin database
- ✅ Connection string format: `postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin`

---

**Last Updated**: 2025-11-15
**Maintained By**: Claude Code
**Related Docs**: `/Users/jaystuart/dev/kubernetes/k8s-home-lab/CLAUDE.md`
