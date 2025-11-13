# Architecture Decision: Admin App as Primary Configuration Interface

**Date:** 2025-01-13
**Status:** Accepted
**Decision By:** Jay Stuart
**Tags:** architecture, admin-interface, configuration, ui

---

## Context

Project Athena has multiple configuration surfaces:
- Service-level configuration files (YAML, .env)
- Home Assistant integrations
- RAG service settings
- Guest mode policies
- Quality tracking parameters
- API credentials

Without a unified configuration interface, managing these settings requires:
- SSH access to servers
- Direct file editing
- Service restarts
- Multiple sources of truth
- Risk of configuration drift

The admin interface (`admin/` directory) already exists with:
- FastAPI backend with Authentik OIDC authentication
- PostgreSQL database for persistent storage
- Frontend UI with configuration management
- API endpoints for various system controls

## Decision

**All Project Athena features must be configurable and manageable through the Admin App web interface.**

This means:
1. **No configuration-only files**: All settings must be editable via admin UI
2. **Database-backed configuration**: Settings stored in PostgreSQL, not just YAML files
3. **API-first design**: Services pull config from admin backend APIs
4. **Live updates**: Configuration changes apply without service restarts when possible
5. **Audit trail**: All config changes logged with user/timestamp

## Consequences

### Positive

- **Single source of truth**: All configuration in one place (PostgreSQL)
- **User-friendly**: Non-technical users can manage system via web UI
- **Audit trail**: Full history of who changed what and when
- **Validation**: UI can enforce valid configuration before saving
- **Access control**: Authentik OIDC provides role-based access
- **Remote management**: No need for SSH access to change settings
- **Consistency**: Prevents configuration drift across services

### Negative

- **Additional development work**: Every new feature needs admin UI implementation
- **Complexity**: Services must poll or receive webhooks for config updates
- **Dependency**: Services depend on admin backend availability
- **Migration effort**: Existing YAML configs must be migrated to database

### Neutral

- Configuration files (YAML, .env) can exist as **defaults only**
- Services should support both database-backed config (preferred) and file-based fallback
- Admin app becomes a critical system component

## Implementation Principles

### For All New Features

When implementing any new Project Athena feature, you MUST:

1. **Design the data model first**:
   - Add SQLAlchemy models to `admin/backend/app/models.py`
   - Create Alembic migrations for schema changes
   - Define validation rules and constraints

2. **Create admin backend APIs**:
   - Add REST endpoints to `admin/backend/app/routes/`
   - Implement CRUD operations (Create, Read, Update, Delete)
   - Add authentication/authorization checks
   - Include audit logging

3. **Build the admin frontend UI**:
   - Add configuration pages to `admin/frontend/`
   - Create forms with validation
   - Display current settings and history
   - Show real-time status

4. **Enable services to consume config**:
   - Services query admin backend API on startup
   - Implement config refresh mechanism (polling or webhooks)
   - Support graceful fallback to file-based config
   - Log configuration source (database vs file)

### Configuration Hierarchy

Services should check configuration in this order:

1. **Database (via Admin API)** - Primary source
2. **Environment variables** - Override for specific deployments
3. **YAML/config files** - Default fallback values
4. **Hardcoded defaults** - Last resort

### Examples

**Guest Mode Configuration (Phase 2):**
- ❌ BAD: Edit `config/security_modes.yaml` via SSH
- ✅ GOOD: Admin UI → Guest Mode Settings → Edit allowlist/denylist → Save

**RAG Service API Keys (Phase 2):**
- ❌ BAD: Update `.env` file and restart service
- ✅ GOOD: Admin UI → API Credentials → Edit key → Services auto-reload

**Performance Tuning (Phase 2):**
- ❌ BAD: Modify `config/performance.yaml` and redeploy
- ✅ GOOD: Admin UI → Performance Settings → Adjust cache TTL → Apply live

**Airbnb Calendar URL (Phase 2):**
- ❌ BAD: SSH to Mac Studio, edit `.env`, restart mode service
- ✅ GOOD: Admin UI → Guest Mode → Calendar Settings → Paste URL → Save

## Impact on Phase 2 Planning

Every Phase 2 feature must include:

### Additional Implementation Tasks

1. **Database Schema**:
   - Design tables/models for feature configuration
   - Create Alembic migration
   - Define relationships and constraints

2. **Admin Backend**:
   - Create API endpoints for feature management
   - Implement configuration validation
   - Add audit logging
   - Handle config updates

3. **Admin Frontend**:
   - Create configuration UI pages
   - Build forms with proper validation
   - Show real-time status/health
   - Display configuration history

4. **Service Integration**:
   - Services call admin API for config
   - Implement config refresh (polling every 60s or webhook)
   - Handle config update gracefully
   - Log configuration changes

### Success Criteria Updates

For every Phase 2 feature, success criteria must include:

#### Automated Verification:
- [ ] Database migration applies cleanly: `cd admin/backend && alembic upgrade head`
- [ ] Admin backend API responds: `curl http://localhost:5000/api/{feature}`
- [ ] Configuration can be retrieved: `curl http://localhost:5000/api/{feature}/config`
- [ ] Configuration can be updated: `curl -X PUT ...`

#### Manual Verification:
- [ ] Feature configuration is accessible in admin UI
- [ ] Configuration changes are saved to database
- [ ] Services reflect updated configuration (within 60s)
- [ ] Audit log shows configuration changes
- [ ] Invalid configuration is rejected with clear errors

## Architectural Components

### Admin Backend (`admin/backend/`)

**Already exists:**
- FastAPI application with OIDC authentication
- PostgreSQL database with Alembic migrations
- SQLAlchemy models
- API route structure
- Audit logging framework

**Phase 2 additions needed:**
- Guest mode configuration endpoints
- RAG service management endpoints
- Quality tracking configuration endpoints
- Performance tuning endpoints
- Airbnb calendar connector endpoints

### Admin Frontend (`admin/frontend/`)

**Already exists:**
- Web UI with navigation
- Authentication flow
- Basic configuration pages

**Phase 2 additions needed:**
- Guest mode configuration UI
- RAG service management UI (enable/disable, API keys)
- Quality tracking dashboard
- Performance metrics dashboard
- Calendar integration setup UI

### Service Configuration Clients

**Pattern to follow:**

```python
# Every service should have a config client
from shared.admin_client import AdminConfigClient

class ServiceConfig:
    def __init__(self):
        self.admin_client = AdminConfigClient(
            base_url=os.getenv("ADMIN_API_URL", "http://localhost:5000")
        )
        self.config = {}
        self.load_config()

    async def load_config(self):
        """Load config from admin API with file fallback"""
        try:
            # Try admin API first
            self.config = await self.admin_client.get_config("service_name")
            logger.info("Loaded config from admin API")
        except Exception as e:
            # Fallback to file
            logger.warning(f"Admin API unavailable: {e}, using file config")
            self.config = self._load_from_file()

    async def refresh_config(self):
        """Periodically refresh config from admin API"""
        while True:
            await asyncio.sleep(60)  # Check every 60 seconds
            await self.load_config()
```

## References

- **Admin Interface Implementation**: `thoughts/shared/plans/2025-11-12-admin-interface-implementation.md`
- **Admin Backend Code**: `admin/backend/`
- **Admin Frontend Code**: `admin/frontend/`
- **Current Admin Routes**: `admin/backend/app/routes/`
- **Existing Models**: `admin/backend/app/models.py`

## Review and Updates

This decision should be reviewed:
- When adding any new configurable feature
- If configuration complexity becomes unmanageable
- If admin app becomes a performance bottleneck

**Last Updated:** 2025-01-13
**Next Review:** After Phase 2 implementation
