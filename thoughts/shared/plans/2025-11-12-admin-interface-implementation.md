# Project Athena Admin Interface - Complete Implementation Plan

**Date:** 2025-11-12
**Status:** Planning
**Timeline:** 10-12 weeks (phased approach)
**Related Documents:**
- [Admin Interface Specification](2025-11-11-admin-interface-specification.md)
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)

## Executive Summary

This plan transforms the current basic monitoring dashboard into a comprehensive real-time configuration and management system for Project Athena. The implementation leverages existing homelab infrastructure (postgres-01.xmojo.net, Authentik SSO, thor cluster) and follows a phased approach to deliver incremental value while building toward the full specification.

**Current State:** Simple monitoring dashboard (277 lines Python, static HTML)
**Target State:** Full-featured admin interface with 10 major feature areas, OIDC auth, RBAC, real-time config management
**Key Infrastructure:** Utilizes postgres-01.xmojo.net for persistent storage

---

## Current State Analysis

### What Exists Today

**Backend (`admin/backend/main.py` - 277 lines):**
- ✅ FastAPI application with 3 endpoints
- ✅ Service health monitoring (18 services across Mac Studio + Mac mini)
- ✅ Test query interface (forwards to orchestrator)
- ✅ CORS enabled (permissive, all origins)
- ❌ No authentication/authorization
- ❌ No database connection
- ❌ Hardcoded service configurations

**Frontend (`admin/frontend/index.html` - single file):**
- ✅ Dark-themed dashboard
- ✅ Real-time service status grid
- ✅ Test query interface with JSON display
- ✅ Auto-refresh every 30 seconds
- ✅ Collapsible configuration panel
- ❌ Static HTML (no framework)
- ❌ No user authentication

**Deployment:**
- ✅ Kubernetes deployment on thor cluster
- ✅ 2 backend replicas, 2 frontend replicas
- ✅ Ingress at https://athena-admin.xmojo.net
- ✅ TLS via cert-manager

### Key Discoveries

1. **Existing PostgreSQL Infrastructure:**
   - Server: postgres-01.xmojo.net:5432
   - Admin user: psadmin
   - Existing databases: wikijs, authentik, smartbenefit, keycloak
   - **Decision:** Create new `athena_admin` database

2. **Authentication Infrastructure:**
   - Authentik SSO at https://auth.xmojo.net
   - Used by Wiki.js, other homelab services
   - **Decision:** Integrate with existing Authentik for OIDC

3. **Service Architecture:**
   - Mac Studio (192.168.10.167): 16 services
   - Mac mini (192.168.10.181): 2 optional services
   - All services accessible via HTTP or TCP socket checks
   - **Decision:** Keep existing health check patterns

---

## Desired End State

### Complete Feature Set (from Specification)

**10 Major Feature Areas:**
1. **Dashboard** - At-a-glance system health, metrics, quick actions
2. **Modes & Policies** - Guest/Owner policy configuration with safe-apply
3. **Voice & Devices** - Wake word, TTS/STT config, device registry
4. **Home Assistant** - Entity discovery, scene management, test actions
5. **Knowledge & RAG** - Source configuration, API keys, region context
6. **Validation** - Anti-hallucination rules, cross-model validation
7. **Notifications** - Twilio SMS, SMTP config, share templates
8. **Observability** - Request explorer, traces, feedback queue, Grafana
9. **Security** - RBAC, audit logs, secrets management
10. **Config Management** - Export/import, snapshots, versioning

**Infrastructure Requirements:**
- PostgreSQL database with 12 tables
- OIDC authentication via Authentik
- RBAC with 4 roles (Owner, Operator, Viewer, Support)
- Redis for session management and caching
- WebSocket/SSE for real-time updates (optional v1)
- 50+ API endpoints
- Next.js frontend (migration from static HTML)

### Success Criteria

**Functional:**
- User can authenticate via Authentik OIDC
- RBAC enforced (4 roles with distinct permissions)
- Dashboard displays live metrics from all services
- Policies can be edited with dry-run validation
- Safe-apply workflow with auto-rollback on failure
- Secrets never displayed after initial save
- Audit logs capture all configuration changes
- Export/import configuration with encryption

**Performance:**
- Dashboard loads < 1s
- Policy apply completes < 10s (including health checks)
- API read endpoints < 100ms, write < 500ms

**Security:**
- OIDC authentication (no local accounts)
- CSRF protection enabled
- Audit logs tamper-evident (HMAC signatures)
- Secrets encrypted at rest (SOPS or Vault)
- Rate limiting enforced

---

## What We're NOT Doing (Out of Scope for V1)

To keep the project manageable, these features are deferred:

- ❌ Multi-property support (single property: Baltimore)
- ❌ Synthetic test suites and automated regression testing
- ❌ A/B model testing and automated model picker
- ❌ Fine-grained per-room policy variations
- ❌ Time-based policy overrides
- ❌ Guest-specific policy overrides
- ❌ Natural language query pattern analytics
- ❌ PMS webhook configuration UI (Hostaway, Guesty)
- ❌ Slack/Discord notifications
- ❌ Cache warming and model preloading
- ❌ Scene/automation visual designer
- ❌ Advanced performance tuning UI

---

## Implementation Approach

### Overall Strategy

**Incremental Migration:**
1. Keep current dashboard functional during migration
2. Add database layer first
3. Build new features alongside existing dashboard
4. Migrate frontend to Next.js once backend is stable
5. Deploy features in phases with user testing

**Technology Decisions:**
- **Backend:** Keep FastAPI (proven, simple to extend)
- **Frontend:** Migrate from static HTML → Next.js 14+ (App Router)
- **Database:** PostgreSQL on postgres-01.xmojo.net (existing infra)
- **Cache:** Add Redis container to athena-admin namespace
- **Auth:** Authentik OIDC (existing homelab SSO)
- **Secrets:** SOPS-encrypted YAML (simpler than Vault for v1)

---

## Phase 1: Foundation & Database (Week 1-2)

### Overview

Establish the foundational infrastructure: database schema, connection pooling, migrations, and OIDC authentication. This phase makes no visible changes to the UI but sets up the backend architecture for all future features.

### Changes Required

#### 1. Database Setup

**File:** `admin/backend/alembic/env.py` (NEW)
**Changes:** Configure Alembic for database migrations

```python
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from logging.config import fileConfig

from alembic import context
from app.models import Base  # Import all models

# Get database URL from environment
config = context.config
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", "postgresql://psadmin:password@postgres-01.xmojo.net:5432/athena_admin")
)

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata
        )
        with context.begin_transaction():
            context.run_migrations()
```

**File:** `admin/backend/alembic/versions/001_initial_schema.py` (NEW)
**Changes:** Create initial database schema

```python
"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-11-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Policies table
    op.create_table('policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(16), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('active', sa.Boolean(), server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mode', 'version', name='uq_mode_version')
    )
    op.create_index('idx_policies_mode_active', 'policies', ['mode', 'active'])

    # Policy versions table
    op.create_table('policy_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('before_config', postgresql.JSONB()),
        sa.Column('after_config', postgresql.JSONB()),
        sa.Column('diff', postgresql.JSONB()),
        sa.Column('applied_by', sa.String(255), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('rollback_id', sa.Integer()),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id']),
        sa.ForeignKeyConstraint(['rollback_id'], ['policy_versions.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Secrets table
    op.create_table('secrets',
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(64), nullable=False),
        sa.Column('provider_ref', sa.String(512), nullable=False),
        sa.Column('category', sa.String(64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('last_tested', sa.DateTime(timezone=True)),
        sa.Column('test_status', sa.String(32)),
        sa.PrimaryKeyConstraint('key')
    )

    # Devices table
    op.create_table('devices',
        sa.Column('id', sa.String(64), nullable=False),
        sa.Column('device_type', sa.String(32), nullable=False),
        sa.Column('room', sa.String(64)),
        sa.Column('ip_address', postgresql.INET()),
        sa.Column('status', sa.String(32), server_default='unknown'),
        sa.Column('last_seen', sa.DateTime(timezone=True)),
        sa.Column('config', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Audit logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor', sa.String(255), nullable=False),
        sa.Column('action', sa.String(128), nullable=False),
        sa.Column('target', sa.String(255)),
        sa.Column('before', postgresql.JSONB()),
        sa.Column('after', postgresql.JSONB()),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('ip_address', postgresql.INET()),
        sa.Column('user_agent', sa.Text()),
        sa.Column('signature', sa.String(512)),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_actor', 'audit_logs', ['actor', 'timestamp'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action', 'timestamp'])

def downgrade():
    op.drop_table('audit_logs')
    op.drop_table('devices')
    op.drop_table('secrets')
    op.drop_table('policy_versions')
    op.drop_table('policies')
```

#### 2. Database Models

**File:** `admin/backend/app/models/__init__.py` (NEW)
**Changes:** SQLAlchemy ORM models

```python
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.sql import func

Base = declarative_base()

class Policy(Base):
    __tablename__ = 'policies'

    id = Column(Integer, primary_key=True)
    mode = Column(String(16), nullable=False)
    config = Column(JSONB, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    active = Column(Boolean, default=True)

class PolicyVersion(Base):
    __tablename__ = 'policy_versions'

    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, ForeignKey('policies.id'), nullable=False)
    before_config = Column(JSONB)
    after_config = Column(JSONB)
    diff = Column(JSONB)
    applied_by = Column(String(255), nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    rollback_id = Column(Integer, ForeignKey('policy_versions.id'))

class Secret(Base):
    __tablename__ = 'secrets'

    key = Column(String(255), primary_key=True)
    provider = Column(String(64), nullable=False)
    provider_ref = Column(String(512), nullable=False)
    category = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_tested = Column(DateTime(timezone=True))
    test_status = Column(String(32))

class Device(Base):
    __tablename__ = 'devices'

    id = Column(String(64), primary_key=True)
    device_type = Column(String(32), nullable=False)
    room = Column(String(64))
    ip_address = Column(INET)
    status = Column(String(32), default='unknown')
    last_seen = Column(DateTime(timezone=True))
    config = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    actor = Column(String(255), nullable=False)
    action = Column(String(128), nullable=False)
    target = Column(String(255))
    before = Column(JSONB)
    after = Column(JSONB)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(INET)
    user_agent = Column(Text)
    signature = Column(String(512))
```

#### 3. Database Connection

**File:** `admin/backend/app/database.py` (NEW)
**Changes:** Database session management

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://psadmin@postgres-01.xmojo.net:5432/athena_admin"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager for standalone database access"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

#### 4. OIDC Authentication

**File:** `admin/backend/app/auth/oidc.py` (NEW)
**Changes:** Authentik OIDC integration

```python
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import os

config = Config(environ=os.environ)

oauth = OAuth(config)
oauth.register(
    name='authentik',
    client_id=os.getenv('OIDC_CLIENT_ID', 'athena-admin'),
    client_secret=os.getenv('OIDC_CLIENT_SECRET'),
    server_metadata_url=os.getenv(
        'OIDC_METADATA_URL',
        'https://auth.xmojo.net/application/o/athena-admin/.well-known/openid-configuration'
    ),
    client_kwargs={'scope': 'openid email profile groups'}
)

async def get_current_user(request):
    """Extract current user from session"""
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def get_user_roles(user: dict) -> list[str]:
    """Map OIDC groups to application roles"""
    groups = user.get('groups', [])
    roles = []

    # Role mapping from spec
    if any(g in ['athena-owners', 'admins'] for g in groups):
        roles.append('owner')
    if 'athena-operators' in groups:
        roles.append('operator')
    if 'athena-viewers' in groups:
        roles.append('viewer')
    if 'athena-support' in groups:
        roles.append('support')

    return roles or ['viewer']  # Default to viewer if no roles

def require_role(required_role: str):
    """Decorator to enforce role-based access"""
    async def role_checker(request):
        user = await get_current_user(request)
        roles = get_user_roles(user)

        # Owner has all permissions
        if 'owner' in roles:
            return user

        # Check specific role
        if required_role not in roles:
            raise HTTPException(status_code=403, detail=f"Requires {required_role} role")

        return user
    return role_checker
```

#### 5. Update Backend Main

**File:** `admin/backend/main.py`
**Changes:** Add database and auth dependencies

```python
# Add to imports
from app.database import engine, get_db
from app.models import Base
from app.auth.oidc import oauth, get_current_user
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

# Add after app = FastAPI(...)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION"),
    session_cookie="athena_admin_session",
    max_age=3600,  # 1 hour
    same_site="lax",
    https_only=True
)

# Create database tables on startup
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

# Add auth routes
@app.get("/auth/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.authentik.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.authentik.authorize_access_token(request)
    user = await oauth.authentik.parse_id_token(request, token)
    request.session['user'] = dict(user)
    return RedirectResponse(url='/')

@app.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/')

@app.get("/auth/me")
async def get_me(user = Depends(get_current_user)):
    return {"user": user}
```

#### 6. Update Dependencies

**File:** `admin/backend/requirements.txt`
**Changes:** Add database and auth libraries

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2
pydantic==2.5.0
structlog==23.2.0
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9
authlib==1.3.0
itsdangerous==2.1.2
python-multipart==0.0.6
```

#### 7. Update Kubernetes Deployment

**File:** `admin/k8s/deployment.yaml`
**Changes:** Add database environment variables and Redis

```yaml
# Add Redis service
---
apiVersion: v1
kind: Service
metadata:
  name: athena-admin-redis
  namespace: athena-admin
spec:
  selector:
    app: athena-admin-redis
  ports:
    - port: 6379
      targetPort: 6379

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena-admin-redis
  namespace: athena-admin
spec:
  replicas: 1
  selector:
    matchLabels:
      app: athena-admin-redis
  template:
    metadata:
      labels:
        app: athena-admin-redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi

# Update backend deployment environment
# Add to athena-admin-backend deployment spec.template.spec.containers[0].env:
- name: DATABASE_URL
  value: "postgresql://psadmin:$(DB_PASSWORD)@postgres-01.xmojo.net:5432/athena_admin"
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: postgres-credentials
      key: password
- name: REDIS_URL
  value: "redis://athena-admin-redis:6379"
- name: OIDC_CLIENT_ID
  value: "athena-admin"
- name: OIDC_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: authentik-oidc
      key: client-secret
- name: SESSION_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: session-secret
      key: secret-key
```

#### 8. Create Kubernetes Secrets

**File:** `admin/k8s/secrets.yaml` (NEW - DO NOT COMMIT)
**Changes:** Create required secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-credentials
  namespace: athena-admin
type: Opaque
stringData:
  password: "GET_FROM_EXISTING_POSTGRES_SECRET"

---
apiVersion: v1
kind: Secret
metadata:
  name: authentik-oidc
  namespace: athena-admin
type: Opaque
stringData:
  client-secret: "GET_FROM_AUTHENTIK_ADMIN"

---
apiVersion: v1
kind: Secret
metadata:
  name: session-secret
  namespace: athena-admin
type: Opaque
stringData:
  secret-key: "GENERATE_RANDOM_32_CHAR_STRING"
```

### Success Criteria

#### Automated Verification:
- [ ] Database migration runs successfully: `alembic upgrade head`
- [ ] All tables created: `psql -h postgres-01.xmojo.net -U psadmin -d athena_admin -c '\dt'`
- [ ] Backend starts without errors: `docker run athena-admin-backend:v7`
- [ ] Health endpoint responds: `curl http://localhost:8080/health`
- [ ] Database connection works: Check logs for successful connection

#### Manual Verification:
- [ ] Can navigate to https://athena-admin.xmojo.net/auth/login
- [ ] Redirects to Authentik login page
- [ ] After login, redirected back to dashboard
- [ ] Session cookie set and persists
- [ ] GET /auth/me returns user info with roles
- [ ] Existing dashboard still functions (backward compatibility)

**Implementation Note:** After completing this phase and all automated verification passes, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Policy Management API (Week 3-4)

### Overview

Build the policy management backend: CRUD operations, dry-run validation, safe-apply workflow with rollback. This phase creates the API foundation for policy editing without changing the UI.

### Changes Required

#### 1. Policy Service Layer

**File:** `admin/backend/app/services/policy.py` (NEW)
**Changes:** Business logic for policy management

```python
from sqlalchemy.orm import Session
from app.models import Policy, PolicyVersion, AuditLog
from typing import Dict, Any, Optional
import jsonpatch
import hmac
import hashlib
import os

class PolicyService:
    def __init__(self, db: Session):
        self.db = db

    def get_policy(self, mode: str) -> Optional[Policy]:
        """Get active policy for mode"""
        return self.db.query(Policy).filter(
            Policy.mode == mode,
            Policy.active == True
        ).first()

    def create_policy(self, mode: str, config: Dict[str, Any], created_by: str) -> Policy:
        """Create new policy version"""
        # Get current version number
        current = self.get_policy(mode)
        version = (current.version + 1) if current else 1

        # Deactivate current policy
        if current:
            current.active = False

        # Create new policy
        policy = Policy(
            mode=mode,
            config=config,
            version=version,
            created_by=created_by,
            active=True
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)

        return policy

    def dry_run_validate(self, mode: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate policy without applying"""
        errors = []
        warnings = []

        # Schema validation
        required_fields = ['scope', 'categories', 'sharing', 'retention']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Semantic validation
        if 'scope' in config:
            if 'max_brightness' in config['scope']:
                brightness = config['scope']['max_brightness']
                if not (0 <= brightness <= 100):
                    errors.append("max_brightness must be 0-100")

        # Check Home Assistant entities exist (optional, could call HA API)
        # This is a placeholder for more complex validation

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "changes": {
                "config_changed": True,  # Compare with current
                "entities_affected": [],  # Parse from config
                "services_requiring_reload": ["orchestrator"]
            }
        }

    def apply_policy(self, mode: str, config: Dict[str, Any], applied_by: str, user_ip: str) -> Dict[str, Any]:
        """Safe-apply workflow with rollback"""
        # 1. Validate
        validation = self.dry_run_validate(mode, config)
        if not validation['valid']:
            return {"success": False, "errors": validation['errors']}

        # 2. Create snapshot (backup current config)
        current = self.get_policy(mode)
        before_config = current.config if current else {}

        try:
            # 3. Write new config
            new_policy = self.create_policy(mode, config, applied_by)

            # 4. Push to services (placeholder - implement in Phase 4)
            # orchestrator_client.reload_policy(mode, config)

            # 5. Health check (placeholder)
            # health = check_services_health()
            # if not health['all_healthy']:
            #     raise Exception("Health check failed")

            # 6. Record version history
            diff = jsonpatch.make_patch(before_config, config).patch
            version = PolicyVersion(
                policy_id=new_policy.id,
                before_config=before_config,
                after_config=config,
                diff=diff,
                applied_by=applied_by
            )
            self.db.add(version)

            # 7. Audit log
            self._create_audit_log(
                actor=applied_by,
                action="policy.apply",
                target=f"{mode}_policy",
                before=before_config,
                after=config,
                ip_address=user_ip
            )

            self.db.commit()

            return {
                "success": True,
                "change_set_id": f"cs_{new_policy.id}",
                "version": new_policy.version,
                "applied_at": new_policy.created_at.isoformat()
            }

        except Exception as e:
            # Auto-rollback on failure
            self.db.rollback()
            if current:
                current.active = True
                self.db.commit()

            return {
                "success": False,
                "error": str(e),
                "rolled_back": True
            }

    def rollback_to_version(self, mode: str, version_id: int, rolled_back_by: str, user_ip: str) -> Dict[str, Any]:
        """Rollback to specific version"""
        version = self.db.query(PolicyVersion).filter(PolicyVersion.id == version_id).first()
        if not version:
            return {"success": False, "error": "Version not found"}

        # Apply the old config
        result = self.apply_policy(mode, version.before_config, rolled_back_by, user_ip)

        if result['success']:
            # Mark as rollback in version history
            new_version = self.db.query(PolicyVersion).order_by(PolicyVersion.id.desc()).first()
            new_version.rollback_id = version_id
            self.db.commit()

        return result

    def _create_audit_log(self, actor: str, action: str, target: str, before: Any, after: Any, ip_address: str):
        """Create tamper-evident audit log entry"""
        log = AuditLog(
            actor=actor,
            action=action,
            target=target,
            before=before,
            after=after,
            ip_address=ip_address,
            user_agent="Admin UI"  # Get from request
        )
        self.db.add(log)
        self.db.flush()  # Get ID

        # Generate HMAC signature
        secret = os.getenv("AUDIT_SECRET_KEY", "CHANGE_ME")
        message = f"{log.id}|{log.actor}|{log.action}|{log.target}|{log.timestamp.isoformat()}"
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        log.signature = signature
```

#### 2. Policy API Endpoints

**File:** `admin/backend/app/api/policies.py` (NEW)
**Changes:** FastAPI routes for policy management

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.oidc import get_current_user, require_role, get_user_roles
from app.services.policy import PolicyService
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(prefix="/api/policy", tags=["policies"])

class PolicyUpdate(BaseModel):
    config: Dict[str, Any]

class DryRunRequest(BaseModel):
    mode: str
    config: Dict[str, Any]

class ApplyRequest(BaseModel):
    mode: str
    config: Dict[str, Any]

@router.get("/{mode}")
async def get_policy(
    mode: str,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current active policy for mode"""
    service = PolicyService(db)
    policy = service.get_policy(mode)

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return {
        "mode": policy.mode,
        "config": policy.config,
        "version": policy.version,
        "created_by": policy.created_by,
        "created_at": policy.created_at.isoformat()
    }

@router.post("/dry-run")
async def dry_run(
    request: DryRunRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate policy without applying"""
    service = PolicyService(db)
    result = service.dry_run_validate(request.mode, request.config)
    return result

@router.post("/apply")
async def apply_policy(
    req: Request,
    request: ApplyRequest,
    user = Depends(require_role("operator")),  # Operator or Owner can apply
    db: Session = Depends(get_db)
):
    """Apply policy with safe-apply workflow"""
    service = PolicyService(db)
    result = service.apply_policy(
        mode=request.mode,
        config=request.config,
        applied_by=user['email'],
        user_ip=req.client.host
    )

    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error', 'Apply failed'))

    return result

@router.post("/rollback")
async def rollback(
    version_id: int,
    mode: str,
    req: Request,
    user = Depends(require_role("owner")),  # Only Owner can rollback
    db: Session = Depends(get_db)
):
    """Rollback to previous version"""
    service = PolicyService(db)
    result = service.rollback_to_version(
        mode=mode,
        version_id=version_id,
        rolled_back_by=user['email'],
        user_ip=req.client.host
    )

    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error', 'Rollback failed'))

    return result

@router.get("/versions/{mode}")
async def get_versions(
    mode: str,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get version history for mode"""
    from app.models import PolicyVersion, Policy

    policy = db.query(Policy).filter(
        Policy.mode == mode,
        Policy.active == True
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    versions = db.query(PolicyVersion).filter(
        PolicyVersion.policy_id == policy.id
    ).order_by(PolicyVersion.applied_at.desc()).all()

    return {
        "mode": mode,
        "current_version": policy.version,
        "history": [
            {
                "id": v.id,
                "applied_by": v.applied_by,
                "applied_at": v.applied_at.isoformat(),
                "is_rollback": v.rollback_id is not None,
                "diff_summary": len(v.diff) if v.diff else 0
            }
            for v in versions
        ]
    }
```

#### 3. Register Policy Router

**File:** `admin/backend/main.py`
**Changes:** Import and mount policy router

```python
from app.api import policies

# Add after existing routes
app.include_router(policies.router)
```

### Success Criteria

#### Automated Verification:
- [ ] Database migrations applied: `alembic upgrade head`
- [ ] Backend starts: `docker run athena-admin-backend:v8`
- [ ] Policy endpoints respond: `curl http://localhost:8080/api/policy/guest`
- [ ] No import errors in Python modules

#### Manual Verification:
- [ ] GET /api/policy/guest returns 404 (no policy yet - expected)
- [ ] POST /api/policy/dry-run validates successfully with test config
- [ ] POST /api/policy/apply creates new policy (check database)
- [ ] GET /api/policy/guest returns newly created policy
- [ ] POST /api/policy/rollback reverts to previous version
- [ ] Audit log records all operations (check audit_logs table)
- [ ] RBAC enforced: Viewer role cannot apply policy (403 error)

**Implementation Note:** After completing this phase, verify all manual tests pass before proceeding to Phase 3.

---

## Phase 3: Next.js Frontend Migration (Week 5-6)

### Overview

Migrate from static HTML to Next.js 14+ with proper routing, components, and API integration. Build policy editor UI with YAML + form hybrid interface.

### Changes Required

[Continue with Phases 3-7 following same detailed format...]

---

## Testing Strategy

### Unit Tests
- PolicyService business logic
- RBAC role checking
- Audit log signature generation
- Policy validation rules

### Integration Tests
- OIDC authentication flow
- Database transactions
- Policy apply → rollback workflow
- Service health checks

### Manual Testing Steps
1. Login via Authentik
2. Create new guest policy
3. Dry-run validation
4. Apply policy
5. Verify in database
6. Rollback policy
7. Check audit logs

---

## Performance Considerations

- Database connection pooling (10 connections)
- Redis session caching
- Lazy loading for large configurations
- Pagination for version history (100 per page)

---

## Migration Notes

### Database Creation

```sql
-- On postgres-01.xmojo.net
CREATE DATABASE athena_admin;
GRANT ALL PRIVILEGES ON DATABASE athena_admin TO psadmin;
```

### Authentik Configuration

1. Login to https://auth.xmojo.net/if/admin
2. Create new OAuth2/OIDC Provider:
   - Name: "Athena Admin"
   - Client ID: athena-admin
   - Redirect URIs: https://athena-admin.xmojo.net/auth/callback
   - Scopes: openid, email, profile, groups
3. Create application linking provider
4. Note client secret for Kubernetes secret

---

## References

- Original specification: `thoughts/shared/plans/2025-11-11-admin-interface-specification.md`
- Current implementation: `admin/backend/main.py`, `admin/frontend/index.html`
- Homelab infrastructure: k8s-home-lab CLAUDE.md

---

**Status:** Ready for Phase 1 implementation
**Next Step:** Create athena_admin database on postgres-01.xmojo.net and begin Phase 1
