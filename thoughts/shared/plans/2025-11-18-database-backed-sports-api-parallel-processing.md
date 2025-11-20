# Database-Backed Sports API Keys with Parallel Processing

**Date:** 2025-11-18
**Status:** In progress — code merged, DB migration pending (needs direct access to postgres-01 / 192.168.10.30 or .31)
**Priority:** High
**Related Issues:** TheSportsDB API reliability issues, team_id data corruption

## Executive Summary

**Current state (2025-11-18):**
- Code is landed: ExternalAPIKey model + Alembic `012_add_external_api_keys.py`, admin API routes + UI tab, and sports RAG refactor to fetch keys from admin and do parallel provider search.
- Blocker: Admin DB migration not yet applied; this environment cannot reach the DB (`psycopg2 OperationalError: Operation not permitted` to 192.168.10.30/.31). Run Alembic from a host with DB reachability:
  - `cd /Users/jaystuart/dev/project-athena/admin/backend && source .venv/bin/activate && DATABASE_URL="postgresql://psadmin:Ibucej1!@192.168.10.30:5432/athena_admin" alembic upgrade head` (try .31 if .30 fails).
- After migration: seed external API keys via Admin UI/API (`thesportsdb`, `api-football`, optional `espn`), restart sports RAG on 8012 with `ADMIN_API_URL` set, and recheck `/health` + `/sports/teams/search`.

This plan implements database-backed external API key management with admin UI integration, and refactors the Sports RAG service to use parallel processing across three sports APIs (TheSportsDB, ESPN, API-Football.com) for improved reliability and redundancy.

### Problem Statement

**Current Issues:**
1. **TheSportsDB API Unreliability:**
   - 500 Internal Server Errors
   - Data corruption: `team_id` returns wrong team's events (Bolton Wanderers instead of Ravens)
   - Empty event arrays for valid teams
   - Discovered in `src/orchestrator/rag_validator.py:87-119` with team mismatch detection

2. **API Key Management:**
   - API keys currently stored in `.env` file (not scalable)
   - No admin UI for managing external API credentials
   - Credential rotation requires code changes and redeployment

**Solution:**
- Database-backed external API key storage with encryption
- Admin UI for managing API credentials
- Parallel processing across three sports APIs with priority-based fallback
- Improved redundancy and reliability for sports queries

### Success Criteria

**Phase 1 - Database Schema (Automated):**
- ExternalAPIKey model created in `admin/backend/app/models.py`
- Migration `012_add_external_api_keys.py` successfully applied
- API-Football.com key migrated from `.env` to database
- All columns indexed correctly

**Phase 2 - API Routes (Automated):**
- CRUD endpoints for external API keys functional
- Authentication/authorization enforced
- API keys returned in encrypted format
- Audit logging for all key operations

**Phase 3 - Sports RAG Refactor (Automated):**
- Sports RAG fetches API keys from admin database (not `.env`)
- Parallel processing with `asyncio.gather()` implemented
- Priority-based fallback (return first successful result)
- Response validation prevents bad data from reaching user
- < 500ms P95 latency (parallel processing should be faster than sequential)

**Phase 4 - Admin UI (Manual verification):**
- UI form for adding/editing external API keys
- Secure display of sensitive credentials (masked by default)
- Enable/disable toggle for individual APIs
- Visual indicators for API health status

**Phase 5 - Testing (Manual):**
- Sports queries work with any combination of APIs
- Fallback triggers correctly when APIs fail
- No regressions in existing functionality
- API key rotation doesn't require service restart

## Architecture Design

### Database Schema

**New Table: `external_api_keys`**

```sql
CREATE TABLE external_api_keys (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) NOT NULL,           -- e.g., 'api-football', 'thesportsdb', 'espn'
    api_name VARCHAR(255) NOT NULL,              -- Human-readable: 'API-Football.com'
    api_key_encrypted TEXT NOT NULL,             -- Application-level encryption
    endpoint_url TEXT NOT NULL,                  -- Base URL for API
    enabled BOOLEAN NOT NULL DEFAULT true,       -- Enable/disable without deletion
    description TEXT,                            -- Admin notes
    rate_limit_per_minute INTEGER,               -- Optional rate limiting
    created_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE,          -- Track usage
    UNIQUE(service_name)
);

CREATE INDEX idx_external_api_keys_service_name ON external_api_keys(service_name);
CREATE INDEX idx_external_api_keys_enabled ON external_api_keys(enabled);
CREATE INDEX idx_external_api_keys_last_used ON external_api_keys(last_used);
```

**Design Rationale:**
- `service_name`: Unique identifier for code lookups (e.g., `api-football`)
- `api_name`: Human-readable display name for admin UI
- `api_key_encrypted`: Encrypted at application level (not database level)
- `enabled`: Soft disable for testing/debugging without data loss
- `last_used`: Track API usage patterns for monitoring

**Follows Existing Patterns:**
- Similar to `Secret` model in `admin/backend/app/models.py:125-150`
- Uses same encryption approach as existing secrets management
- Audit trail pattern matches `LLMBackend` model (lines 60-95)

### API Routes

**New File: `admin/backend/app/routes/external_api_keys.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/external-api-keys", tags=["external-api-keys"])

class ExternalAPIKeyCreate(BaseModel):
    """Request model for creating external API key."""
    service_name: str = Field(..., description="Unique service identifier")
    api_name: str = Field(..., description="Human-readable API name")
    api_key: str = Field(..., description="API key (will be encrypted)")
    endpoint_url: str = Field(..., description="Base API endpoint URL")
    enabled: bool = Field(default=True, description="Enable/disable API")
    description: Optional[str] = Field(None, description="Admin notes")
    rate_limit_per_minute: Optional[int] = Field(None, description="Rate limit")

class ExternalAPIKeyResponse(BaseModel):
    """Response model for external API key."""
    id: int
    service_name: str
    api_name: str
    api_key_masked: str  # Only show last 4 characters
    endpoint_url: str
    enabled: bool
    description: Optional[str]
    rate_limit_per_minute: Optional[int]
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime]

@router.post("/", response_model=ExternalAPIKeyResponse)
async def create_external_api_key(
    key_data: ExternalAPIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new external API key with encryption."""
    # Check for duplicate service_name
    existing = db.query(ExternalAPIKey).filter_by(service_name=key_data.service_name).first()
    if existing:
        raise HTTPException(400, f"API key for '{key_data.service_name}' already exists")

    # Encrypt API key
    encrypted_key = encrypt_value(key_data.api_key)

    # Create record
    new_key = ExternalAPIKey(
        service_name=key_data.service_name,
        api_name=key_data.api_name,
        api_key_encrypted=encrypted_key,
        endpoint_url=key_data.endpoint_url,
        enabled=key_data.enabled,
        description=key_data.description,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        created_by_id=current_user.id
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    # Audit log
    log_audit(db, current_user.id, "external_api_key_created", new_key.id)

    return to_response(new_key)

@router.get("/", response_model=List[ExternalAPIKeyResponse])
async def list_external_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all external API keys (masked)."""
    keys = db.query(ExternalAPIKey).order_by(ExternalAPIKey.service_name).all()
    return [to_response(key) for key in keys]

@router.get("/{service_name}", response_model=ExternalAPIKeyResponse)
async def get_external_api_key(
    service_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific API key by service_name."""
    key = db.query(ExternalAPIKey).filter_by(service_name=service_name).first()
    if not key:
        raise HTTPException(404, f"API key '{service_name}' not found")
    return to_response(key)

@router.put("/{service_name}", response_model=ExternalAPIKeyResponse)
async def update_external_api_key(
    service_name: str,
    key_data: ExternalAPIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update existing API key."""
    key = db.query(ExternalAPIKey).filter_by(service_name=service_name).first()
    if not key:
        raise HTTPException(404, f"API key '{service_name}' not found")

    # Update fields
    key.api_name = key_data.api_name
    if key_data.api_key:  # Only update if provided
        key.api_key_encrypted = encrypt_value(key_data.api_key)
    key.endpoint_url = key_data.endpoint_url
    key.enabled = key_data.enabled
    key.description = key_data.description
    key.rate_limit_per_minute = key_data.rate_limit_per_minute

    db.commit()
    db.refresh(key)

    # Audit log
    log_audit(db, current_user.id, "external_api_key_updated", key.id)

    return to_response(key)

@router.delete("/{service_name}")
async def delete_external_api_key(
    service_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete API key."""
    key = db.query(ExternalAPIKey).filter_by(service_name=service_name).first()
    if not key:
        raise HTTPException(404, f"API key '{service_name}' not found")

    # Audit log before deletion
    log_audit(db, current_user.id, "external_api_key_deleted", key.id)

    db.delete(key)
    db.commit()

    return {"message": f"API key '{service_name}' deleted"}

# Public endpoint for services (no authentication required)
@router.get("/public/{service_name}/key", include_in_schema=False)
async def get_api_key_for_service(
    service_name: str,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint for services to fetch API keys.
    NOT exposed in public schema.
    """
    key = db.query(ExternalAPIKey).filter_by(
        service_name=service_name,
        enabled=True
    ).first()

    if not key:
        raise HTTPException(404, f"Enabled API key '{service_name}' not found")

    # Update last_used timestamp
    key.last_used = datetime.utcnow()
    db.commit()

    # Decrypt and return
    return {
        "api_key": decrypt_value(key.api_key_encrypted),
        "endpoint_url": key.endpoint_url,
        "rate_limit_per_minute": key.rate_limit_per_minute
    }
```

**Design Rationale:**
- Follows existing pattern from `admin/backend/app/routes/llm_backends.py`
- Public endpoint for services (no auth) to fetch keys
- Masked keys in list responses (security)
- Audit logging for all operations
- Soft delete via `enabled` flag

### Sports RAG Parallel Processing

**Refactored: `src/rag/sports/main.py`**

**Key Changes:**

1. **Remove `.env` API keys:**
```python
# OLD (lines 31-36)
THESPORTSDB_API_KEY = os.getenv("THESPORTSDB_API_KEY", "3")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")

# NEW
# API keys now fetched from admin database
admin_api_url = os.getenv("ADMIN_API_URL", "https://athena-admin.xmojo.net")
```

2. **Fetch API keys from database:**
```python
async def get_api_key(service_name: str) -> Optional[Dict[str, Any]]:
    """Fetch API key from admin database."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{admin_api_url}/api/external-api-keys/public/{service_name}/key",
                timeout=5.0
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch API key for {service_name}: {e}")
        return None

async def initialize_api_configs():
    """Load API configurations from database on startup."""
    global api_football_config, thesportsdb_config, espn_config

    # Fetch API-Football.com credentials
    api_football_config = await get_api_key("api-football")

    # TheSportsDB (free tier, no key needed)
    thesportsdb_config = {
        "endpoint_url": "https://www.thesportsdb.com/api/v1/json/3",
        "api_key": None
    }

    # ESPN (no key needed)
    espn_config = {
        "endpoint_url": "https://site.api.espn.com/apis/site/v2/sports",
        "api_key": None
    }

    logger.info(f"API configs loaded: api_football={bool(api_football_config)}, "
                f"thesportsdb=True, espn=True")
```

3. **Parallel team search across all APIs:**
```python
async def search_teams_parallel(query: str) -> List[Dict[str, Any]]:
    """
    Search for teams across all three APIs in parallel.
    Returns first successful result.
    """
    async def search_thesportsdb(query: str):
        """Search TheSportsDB API."""
        try:
            url = f"{thesportsdb_config['endpoint_url']}/searchteams.php"
            response = await http_client.get(url, params={"t": query}, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            teams = data.get("teams", []) or []
            return {"source": "thesportsdb", "teams": teams, "error": None}
        except Exception as e:
            logger.warning(f"TheSportsDB search failed: {e}")
            return {"source": "thesportsdb", "teams": [], "error": str(e)}

    async def search_espn(query: str):
        """Search ESPN API."""
        try:
            # ESPN requires sport-specific searches
            # Search NFL, NBA, MLB, NHL
            searches = []
            for sport in ["football/nfl", "basketball/nba", "baseball/mlb", "hockey/nhl"]:
                url = f"{espn_config['endpoint_url']}/{sport}/teams"
                searches.append(http_client.get(url, timeout=5.0))

            responses = await asyncio.gather(*searches, return_exceptions=True)
            all_teams = []
            for resp in responses:
                if isinstance(resp, httpx.Response):
                    data = resp.json()
                    teams = data.get("teams", [])
                    # Filter by query match
                    matching = [t for t in teams if query.lower() in t.get("displayName", "").lower()]
                    all_teams.extend(matching)

            return {"source": "espn", "teams": all_teams, "error": None}
        except Exception as e:
            logger.warning(f"ESPN search failed: {e}")
            return {"source": "espn", "teams": [], "error": str(e)}

    async def search_api_football(query: str):
        """Search API-Football.com."""
        if not api_football_config:
            return {"source": "api-football", "teams": [], "error": "No API key configured"}

        try:
            url = f"{api_football_config['endpoint_url']}/teams"
            headers = {"X-RapidAPI-Key": api_football_config['api_key']}
            response = await http_client.get(
                url,
                headers=headers,
                params={"search": query},
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            teams = data.get("response", [])
            return {"source": "api-football", "teams": teams, "error": None}
        except Exception as e:
            logger.warning(f"API-Football search failed: {e}")
            return {"source": "api-football", "teams": [], "error": str(e)}

    # Execute all searches in parallel
    logger.info(f"Searching teams in parallel across 3 APIs: {query}")
    results = await asyncio.gather(
        search_thesportsdb(query),
        search_espn(query),
        search_api_football(query),
        return_exceptions=True
    )

    # Return first successful result with data
    for result in results:
        if isinstance(result, dict) and result.get("teams") and len(result["teams"]) > 0:
            logger.info(f"Using teams from {result['source']}: {len(result['teams'])} results")
            return result["teams"]

    # All failed or empty
    logger.warning(f"All APIs failed or returned empty for: {query}")
    return []
```

4. **Update endpoints to use parallel processing:**
```python
@app.get("/sports/teams/search")
async def search_teams(query: str = Query(..., description="Team name to search")):
    """Search for teams by name (parallel across all APIs)."""
    try:
        teams = await search_teams_parallel(query)
        return {"query": query, "teams": teams, "count": len(teams)}
    except Exception as e:
        logger.error(f"Team search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Team search failed")
```

**Performance Targets:**
- Parallel execution should reduce P95 latency from ~800ms to <500ms
- First successful API wins (no need to wait for slower APIs)
- Fallback chain: TheSportsDB → ESPN → API-Football.com

**Error Handling:**
- Each API search has independent timeout (5 seconds)
- Exceptions caught per-API (don't fail entire request)
- Return first successful result with data
- Log which API provided the data for monitoring

### Admin UI Integration

**New Component: `admin/frontend/external-api-keys.html`**

**Features:**
- List all external API keys in table format
- Add/Edit forms with validation
- Masked API key display (show/hide toggle)
- Enable/disable toggle for each API
- Visual indicators for API health (last_used timestamp)
- Delete confirmation dialog

**UI Mockup:**
```
+----------------------------------------------------------+
| External API Keys                                [+ Add] |
+----------------------------------------------------------+
| Service       | API Name           | Enabled | Last Used |
|---------------|--------------------|---------+-----------|
| api-football  | API-Football.com   | ✓       | 2 min ago |
|               | http://v3.footb... |         |           |
|               | Key: ********1a    | [Edit]  | [Delete]  |
+----------------------------------------------------------+
| thesportsdb   | TheSportsDB        | ✓       | 5 min ago |
|               | https://thespor... |         |           |
|               | Key: Free Tier     | [Edit]  | [Delete]  |
+----------------------------------------------------------+
| espn          | ESPN API           | ✓       | Never     |
|               | https://site.ap... |         |           |
|               | Key: (No key)      | [Edit]  | [Disable] |
+----------------------------------------------------------+
```

**Edit Form:**
```
+----------------------------------------------------------+
| Edit API Key: api-football                               |
+----------------------------------------------------------+
| Service Name:    api-football                  (readonly)|
| API Name:        [API-Football.com                    ]  |
| Endpoint URL:    [https://v3.football.api-sports.io   ]  |
| API Key:         [••••••••••••••••••••••1a] [Show]       |
| Rate Limit:      [60] requests/minute                    |
| Description:     [Commercial sports API for football]    |
| Enabled:         [✓] Enable this API                     |
+----------------------------------------------------------+
|                                      [Cancel]  [Save]    |
+----------------------------------------------------------+
```

## Implementation Plan

### Phase 1: Database Schema & Migration

**Files to Create:**
1. `admin/backend/app/models.py` - Add `ExternalAPIKey` model
2. `admin/backend/alembic/versions/012_add_external_api_keys.py` - Migration

**Steps:**

1. **Add model to `models.py`** (after line 150):
```python
class ExternalAPIKey(Base):
    """External API key storage with encryption."""
    __tablename__ = 'external_api_keys'

    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False, unique=True, index=True)
    api_name = Column(String(255), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    endpoint_url = Column(Text, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    description = Column(Text)
    rate_limit_per_minute = Column(Integer)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_used = Column(DateTime(timezone=True), index=True)

    creator = relationship('User', foreign_keys=[created_by_id])

    __table_args__ = (
        Index('idx_external_api_keys_service_name', 'service_name'),
        Index('idx_external_api_keys_enabled', 'enabled'),
        Index('idx_external_api_keys_last_used', 'last_used'),
    )
```

2. **Create migration `012_add_external_api_keys.py`:**
```python
"""Add external API keys table

Revision ID: 012
Revises: 011
Create Date: 2025-11-18
"""

from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'

def upgrade():
    op.create_table('external_api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(255), nullable=False),
        sa.Column('api_name', sa.String(255), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('endpoint_url', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text()),
        sa.Column('rate_limit_per_minute', sa.Integer()),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_name')
    )

    op.create_index('idx_external_api_keys_service_name', 'external_api_keys', ['service_name'])
    op.create_index('idx_external_api_keys_enabled', 'external_api_keys', ['enabled'])
    op.create_index('idx_external_api_keys_last_used', 'external_api_keys', ['last_used'])

def downgrade():
    op.drop_index('idx_external_api_keys_last_used')
    op.drop_index('idx_external_api_keys_enabled')
    op.drop_index('idx_external_api_keys_service_name')
    op.drop_table('external_api_keys')
```

3. **Run migration:**
```bash
cd /Users/jaystuart/dev/project-athena/admin/k8s
./build-and-deploy.sh

# Verify migration applied
kubectl -n athena-admin exec deployment/athena-admin-backend -- alembic current
# Should show: 012 (head)
```

4. **Seed initial API key:**
```bash
# Via kubectl port-forward
kubectl -n athena-admin port-forward deployment/athena-admin-backend 8080:8080

# Create API-Football.com key
curl -X POST http://localhost:8080/api/external-api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "api-football",
    "api_name": "API-Football.com",
    "api_key": "351232a8c06ccb67df0102eb5628131a",
    "endpoint_url": "https://v3.football.api-sports.io",
    "enabled": true,
    "description": "Commercial sports API for football/soccer data",
    "rate_limit_per_minute": 60
  }'
```

**Success Criteria:**
- [ ] Migration applied successfully (alembic current shows `012`)
- [ ] `external_api_keys` table exists in database
- [ ] API-Football.com key created and encrypted
- [ ] All indexes created
- [ ] Foreign key to `users` table enforced

### Phase 2: API Routes

**Files to Create:**
1. `admin/backend/app/routes/external_api_keys.py` - CRUD endpoints
2. `admin/backend/app/main.py` - Register router

**Steps:**

1. **Create `external_api_keys.py`** (see Architecture Design above)

2. **Register router in `main.py`:**
```python
from app.routes import external_api_keys

app.include_router(external_api_keys.router)
```

3. **Deploy updated backend:**
```bash
cd /Users/jaystuart/dev/project-athena/admin/k8s
./build-and-deploy.sh
```

4. **Test endpoints:**
```bash
# List all keys
curl http://localhost:8080/api/external-api-keys | jq

# Get specific key
curl http://localhost:8080/api/external-api-keys/api-football | jq

# Update key
curl -X PUT http://localhost:8080/api/external-api-keys/api-football \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, ...}'

# Public endpoint (for services)
curl http://localhost:8080/api/external-api-keys/public/api-football/key | jq
```

**Success Criteria:**
- [ ] All CRUD endpoints work (create, read, update, delete)
- [ ] Public endpoint returns decrypted key
- [ ] Audit logs created for all operations
- [ ] API keys masked in list responses
- [ ] `last_used` timestamp updates on fetch

### Phase 3: Sports RAG Refactor

**Files to Modify:**
1. `src/rag/sports/main.py` - Complete refactor

**Steps:**

1. **Backup existing file:**
```bash
ssh jstuart@192.168.10.167 'cp ~/dev/project-athena/src/rag/sports/main.py ~/dev/project-athena/src/rag/sports/main.py.backup-$(date +%Y%m%d-%H%M%S)'
```

2. **Implement parallel processing** (see Architecture Design above)

3. **Remove `.env` dependencies:**
```bash
# Remove from .env file on Mac Studio
ssh jstuart@192.168.10.167 "sed -i '' '/API_FOOTBALL/d' ~/dev/project-athena/.env"
```

4. **Deploy updated Sports RAG:**
```bash
# Sync updated code
rsync -av /Users/jaystuart/dev/project-athena/src/rag/sports/ \
  jstuart@192.168.10.167:~/dev/project-athena/src/rag/sports/

# Restart service
ssh jstuart@192.168.10.167 'pkill -f "python3 main.py.*sports"; \
  cd ~/dev/project-athena && set -a && source .env && set +a && \
  cd ~/dev/project-athena/src/rag/sports && nohup python3 main.py > sports.log 2>&1 &'
```

5. **Test parallel processing:**
```bash
# Test team search
curl "http://192.168.10.167:8011/sports/teams/search?query=Ravens" | jq

# Check logs for parallel execution
ssh jstuart@192.168.10.167 'tail -50 ~/dev/project-athena/src/rag/sports/sports.log | grep -E "(parallel|source|API)"'
```

**Success Criteria:**
- [ ] Sports RAG fetches API keys from database (not `.env`)
- [ ] Parallel queries execute across all 3 APIs
- [ ] First successful result returned
- [ ] Logs show which API provided data
- [ ] Fallback works when APIs fail
- [ ] Latency < 500ms for P95

### Phase 4: Admin UI

**Files to Create:**
1. `admin/frontend/external-api-keys.html` - UI component
2. `admin/frontend/crud-extensions.js` - CRUD functions

**Steps:**

1. **Create UI component** (see Architecture Design above)

2. **Add to navigation:**
```javascript
// In admin/frontend/app.js
const navItems = [
  { label: 'Features', href: '#features', icon: 'toggle-on' },
  { label: 'LLM Backends', href: '#llm-backends', icon: 'server' },
  { label: 'External API Keys', href: '#external-api-keys', icon: 'key' },  // NEW
  { label: 'Secrets', href: '#secrets', icon: 'lock' }
];
```

3. **Deploy frontend:**
```bash
cd /Users/jaystuart/dev/project-athena/admin/k8s
./build-and-deploy.sh

# Wait for rollout
kubectl -n athena-admin rollout status deployment/athena-admin-frontend
```

4. **Manual UI testing:**
- Navigate to https://athena-admin.xmojo.net/#external-api-keys
- Verify table displays API keys
- Test add/edit/delete operations
- Verify show/hide API key toggle works
- Test enable/disable toggle

**Success Criteria:**
- [ ] UI displays all external API keys
- [ ] Add form creates new keys
- [ ] Edit form updates existing keys
- [ ] Delete confirmation works
- [ ] API keys masked by default
- [ ] Show/hide toggle reveals full key
- [ ] Enable/disable toggle updates database
- [ ] Visual indicators for API health

### Phase 5: Testing & Validation

**Test Cases:**

**1. API Key Management:**
```bash
# Create new API key
curl -X POST http://localhost:8080/api/external-api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "test-api",
    "api_name": "Test API",
    "api_key": "test-key-123",
    "endpoint_url": "https://api.example.com",
    "enabled": true
  }'

# Verify it's encrypted in database
kubectl -n athena-admin exec deployment/athena-admin-backend -- \
  psql $DATABASE_URL -c "SELECT service_name, api_key_encrypted FROM external_api_keys WHERE service_name='test-api';"

# Verify decryption works
curl http://localhost:8080/api/external-api-keys/public/test-api/key | jq
```

**2. Parallel Processing:**
```bash
# Test with all APIs enabled
curl "http://192.168.10.167:8011/sports/teams/search?query=Ravens" | jq

# Disable API-Football.com
curl -X PUT http://localhost:8080/api/external-api-keys/api-football \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Test fallback to ESPN/TheSportsDB
curl "http://192.168.10.167:8011/sports/teams/search?query=Ravens" | jq

# Verify logs show fallback
ssh jstuart@192.168.10.167 'tail -50 ~/dev/project-athena/src/rag/sports/sports.log | grep -E "(source|fallback)"'
```

**3. End-to-End Sports Queries:**
```bash
# Via Gateway (full stack)
curl -X POST http://192.168.10.167:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3:mini",
    "messages": [{"role": "user", "content": "When do the Ravens play next?"}],
    "stream": false
  }' | jq -r '.choices[0].message.content'

# Should return actual schedule data (not "check sports websites")
```

**4. Performance Testing:**
```bash
# Measure latency with 10 concurrent requests
for i in {1..10}; do
  (time curl -s "http://192.168.10.167:8011/sports/teams/search?query=Ravens") &
done
wait

# P95 latency should be < 500ms
```

**Success Criteria:**
- [ ] All test cases pass
- [ ] API keys encrypted in database
- [ ] Decryption works correctly
- [ ] Parallel processing works with all APIs
- [ ] Fallback works when APIs disabled
- [ ] No regressions in existing queries
- [ ] Performance targets met (< 500ms P95)

## Rollback Plan

**If Issues Arise:**

1. **Revert Sports RAG to backup:**
```bash
ssh jstuart@192.168.10.167 'cp ~/dev/project-athena/src/rag/sports/main.py.backup-* \
  ~/dev/project-athena/src/rag/sports/main.py && \
  pkill -f "python3 main.py.*sports" && \
  cd ~/dev/project-athena/src/rag/sports && python3 main.py &'
```

2. **Restore `.env` API keys:**
```bash
ssh jstuart@192.168.10.167 'echo "API_FOOTBALL_KEY=351232a8c06ccb67df0102eb5628131a" >> ~/dev/project-athena/.env'
```

3. **Rollback database migration:**
```bash
kubectl -n athena-admin exec deployment/athena-admin-backend -- alembic downgrade -1
```

4. **Rollback admin backend:**
```bash
kubectl -n athena-admin rollout undo deployment/athena-admin-backend
```

## Timeline

**Phase 1 (Database):** 1 hour
**Phase 2 (API Routes):** 2 hours
**Phase 3 (Sports RAG):** 3 hours
**Phase 4 (Admin UI):** 2 hours
**Phase 5 (Testing):** 2 hours

**Total Estimated Time:** 10 hours

## Risk Mitigation

**Risk 1: API-Football.com Rate Limiting**
- **Mitigation:** Implement rate limit tracking in database
- **Fallback:** Disable API-Football.com, use ESPN/TheSportsDB only

**Risk 2: Parallel Processing Slower Than Sequential**
- **Mitigation:** Add metrics to compare latency
- **Fallback:** Add feature flag to disable parallel processing

**Risk 3: Database Encryption Performance**
- **Mitigation:** Cache decrypted keys in memory (60s TTL)
- **Fallback:** Store keys in plaintext (not recommended)

**Risk 4: Migration Breaks Admin Backend**
- **Mitigation:** Test migration in local environment first
- **Fallback:** Rollback migration via `alembic downgrade`

## Monitoring & Observability

**Metrics to Track:**

1. **API Performance:**
   - Response time per API (TheSportsDB, ESPN, API-Football.com)
   - Success/failure rate per API
   - Which API provided data (source attribution)

2. **Database Operations:**
   - API key fetch latency
   - Encryption/decryption time
   - Cache hit rate for API keys

3. **User Impact:**
   - Sports query success rate
   - End-to-end latency for sports queries
   - Fallback trigger frequency

**Logging:**
```python
logger.info(f"API key fetched: {service_name}, cache_hit={cache_hit}")
logger.info(f"Parallel search: query={query}, results=[{sources}], latency={elapsed}ms")
logger.warning(f"API failed: {source}, error={error}, falling back to next API")
```

## Future Enhancements

**Post-MVP:**
1. API health monitoring dashboard
2. Automatic API key rotation
3. Rate limit enforcement at application level
4. A/B testing framework for comparing API quality
5. Smart routing based on query type (use best API for specific sports)
6. Cost tracking for paid APIs
7. API response caching to reduce API calls
8. Historical API performance analytics

## References

**Code Patterns:**
- Secret management: `admin/backend/app/models.py:125-150`
- LLM Backend routes: `admin/backend/app/routes/llm_backends.py`
- Migration example: `admin/backend/alembic/versions/93bea4659785_add_llm_backend_registry.py`
- Sports validation: `src/orchestrator/rag_validator.py:36-178`

**Documentation:**
- Admin config: `docs/ADMIN_CONFIG.md`
- Sports RAG current implementation: `src/rag/sports/main.py`

**API Documentation:**
- TheSportsDB: https://www.thesportsdb.com/api.php
- ESPN: https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c
- API-Football.com: https://www.api-football.com/documentation-v3

---

**Status:** Ready for implementation
**Next Steps:** Begin Phase 1 (Database Schema & Migration)
**Expected Completion:** 2025-11-19 (1 day)
