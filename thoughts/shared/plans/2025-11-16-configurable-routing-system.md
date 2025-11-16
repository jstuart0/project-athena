# Configurable Routing System Implementation Plan

**Date:** 2025-11-16
**Status:** Planning
**Priority:** High
**Estimated Effort:** 3-4 days

## Overview

Make the entire Project Athena routing system configurable through the admin web interface instead of hardcoded in Python files.

## Current State Analysis

### Routing Layers (All Exist, Some Configurable)

#### 1. LLM Backend Routing ✅ **ALREADY CONFIGURABLE**
- **File:** `src/shared/llm_router.py`
- **Purpose:** Routes LLM requests to Ollama, MLX, or Auto backends
- **Current State:** Fully configurable via admin API
- **Admin API:** `/api/llm-backends`
- **Frontend UI:** LLM Backend Management tab (added 2025-11-16)
- **No work needed** - this is done

#### 2. Intent Classification ❌ **HARDCODED**
- **File:** `src/orchestrator/intent_classifier.py`
- **Purpose:** "Coordinator LLM" - classifies query intent to determine routing
- **Categories:** CONTROL, WEATHER, SPORTS, AIRPORTS, TRANSIT, EMERGENCY, FOOD, EVENTS, LOCATION, GENERAL_INFO, UNKNOWN
- **Hardcoded Elements:**
  - Control patterns (lines 49-58): `["turn on", "turn off", "dim", "brighten", ...]`
  - Info patterns (lines 62-103): Weather keywords, sports terms, airport codes, etc.
  - Complex indicators (lines 106-111): `["explain", "why", "how does", ...]`
  - Entity patterns: Rooms, devices, actions, colors, teams, airports

#### 3. Search Provider Routing ❌ **HARDCODED**
- **File:** `src/orchestrator/search_providers/provider_router.py`
- **Purpose:** Routes web search queries to appropriate providers
- **Hardcoded Elements:**
  - Intent-to-provider mapping (lines 32-51):
    - `event_search` → Ticketmaster, Eventbrite, DuckDuckGo, Brave
    - `general` → DuckDuckGo, Brave
    - `news` → Brave, DuckDuckGo
    - `local_business` → Brave, DuckDuckGo
  - RAG intent list (line 54): `RAG_INTENTS = {"weather", "sports"}`

## Implementation Plan

### Phase 1: Database Schema & Backend API

#### Step 1.1: Create Intent Patterns Table

```sql
CREATE TABLE intent_patterns (
    id SERIAL PRIMARY KEY,
    intent_category VARCHAR(50) NOT NULL,  -- e.g., "control", "weather", "sports"
    pattern_type VARCHAR(50) NOT NULL,     -- e.g., "basic", "dimming", "temperature"
    keyword VARCHAR(100) NOT NULL,         -- e.g., "turn on", "dim", "ravens"
    confidence_weight FLOAT DEFAULT 1.0,   -- Higher weight = more confident match
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(intent_category, pattern_type, keyword)
);

-- Example data:
-- intent_category='control', pattern_type='basic', keyword='turn on', confidence_weight=1.0
-- intent_category='weather', pattern_type='general', keyword='temperature', confidence_weight=1.0
-- intent_category='sports', pattern_type='team', keyword='ravens', confidence_weight=1.2
```

#### Step 1.2: Create Intent Routing Table

```sql
CREATE TABLE intent_routing (
    id SERIAL PRIMARY KEY,
    intent_category VARCHAR(50) NOT NULL UNIQUE,
    use_rag BOOLEAN DEFAULT FALSE,         -- True = route to RAG service
    rag_service_url VARCHAR(255),          -- e.g., "http://localhost:8010"
    use_web_search BOOLEAN DEFAULT FALSE,  -- True = route to web search
    use_llm BOOLEAN DEFAULT TRUE,          -- True = route to LLM
    priority INTEGER DEFAULT 100,          -- Higher priority = checked first
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Example data:
-- intent_category='weather', use_rag=TRUE, rag_service_url='http://localhost:8010'
-- intent_category='sports', use_rag=TRUE, rag_service_url='http://localhost:8017'
-- intent_category='general', use_llm=TRUE
```

#### Step 1.3: Create Provider Routing Table

```sql
CREATE TABLE provider_routing (
    id SERIAL PRIMARY KEY,
    intent_category VARCHAR(50) NOT NULL,
    provider_name VARCHAR(50) NOT NULL,    -- e.g., "duckduckgo", "brave", "ticketmaster"
    priority INTEGER NOT NULL,             -- Order to try providers (1 = first)
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(intent_category, provider_name)
);

-- Example data:
-- intent_category='event_search', provider_name='ticketmaster', priority=1
-- intent_category='event_search', provider_name='eventbrite', priority=2
-- intent_category='general', provider_name='duckduckgo', priority=1
```

#### Step 1.4: Create Alembic Migration

**File:** `admin/backend/alembic/versions/004_configurable_routing.py`

```python
"""Add configurable routing tables

Revision ID: 004_configurable_routing
Revises: 003_intent_validation_multiintent
Create Date: 2025-11-16
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create intent_patterns table
    op.create_table(
        'intent_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('intent_category', sa.String(50), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('keyword', sa.String(100), nullable=False),
        sa.Column('confidence_weight', sa.Float(), default=1.0),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('intent_category', 'pattern_type', 'keyword')
    )

    # Create intent_routing table
    op.create_table(
        'intent_routing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('intent_category', sa.String(50), nullable=False, unique=True),
        sa.Column('use_rag', sa.Boolean(), default=False),
        sa.Column('rag_service_url', sa.String(255)),
        sa.Column('use_web_search', sa.Boolean(), default=False),
        sa.Column('use_llm', sa.Boolean(), default=True),
        sa.Column('priority', sa.Integer(), default=100),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create provider_routing table
    op.create_table(
        'provider_routing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('intent_category', sa.String(50), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('intent_category', 'provider_name')
    )

def downgrade():
    op.drop_table('provider_routing')
    op.drop_table('intent_routing')
    op.drop_table('intent_patterns')
```

#### Step 1.5: Create SQLAlchemy Models

**File:** `admin/backend/app/models.py` (add to existing file)

```python
class IntentPattern(Base):
    """Intent classification patterns."""
    __tablename__ = "intent_patterns"

    id = Column(Integer, primary_key=True, index=True)
    intent_category = Column(String(50), nullable=False)
    pattern_type = Column(String(50), nullable=False)
    keyword = Column(String(100), nullable=False)
    confidence_weight = Column(Float, default=1.0)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint('intent_category', 'pattern_type', 'keyword'),)


class IntentRouting(Base):
    """Intent routing configuration."""
    __tablename__ = "intent_routing"

    id = Column(Integer, primary_key=True, index=True)
    intent_category = Column(String(50), nullable=False, unique=True)
    use_rag = Column(Boolean, default=False)
    rag_service_url = Column(String(255), nullable=True)
    use_web_search = Column(Boolean, default=False)
    use_llm = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProviderRouting(Base):
    """Search provider routing configuration."""
    __tablename__ = "provider_routing"

    id = Column(Integer, primary_key=True, index=True)
    intent_category = Column(String(50), nullable=False)
    provider_name = Column(String(50), nullable=False)
    priority = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint('intent_category', 'provider_name'),)
```

#### Step 1.6: Create Backend API Routes

**File:** `admin/backend/app/routes/intent_routing.py` (new file)

```python
"""
Intent and Routing Configuration API

Provides endpoints for managing:
- Intent classification patterns
- Intent routing rules
- Search provider routing
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import structlog

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, IntentPattern, IntentRouting, ProviderRouting

logger = structlog.get_logger()
router = APIRouter(prefix="/api/routing", tags=["routing"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class IntentPatternCreate(BaseModel):
    intent_category: str
    pattern_type: str
    keyword: str
    confidence_weight: float = 1.0
    enabled: bool = True


class IntentPatternUpdate(BaseModel):
    pattern_type: Optional[str] = None
    keyword: Optional[str] = None
    confidence_weight: Optional[float] = None
    enabled: Optional[bool] = None


class IntentPatternResponse(BaseModel):
    id: int
    intent_category: str
    pattern_type: str
    keyword: str
    confidence_weight: float
    enabled: bool

    class Config:
        from_attributes = True


class IntentRoutingCreate(BaseModel):
    intent_category: str
    use_rag: bool = False
    rag_service_url: Optional[str] = None
    use_web_search: bool = False
    use_llm: bool = True
    priority: int = 100
    enabled: bool = True


class IntentRoutingUpdate(BaseModel):
    use_rag: Optional[bool] = None
    rag_service_url: Optional[str] = None
    use_web_search: Optional[bool] = None
    use_llm: Optional[bool] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class IntentRoutingResponse(BaseModel):
    id: int
    intent_category: str
    use_rag: bool
    rag_service_url: Optional[str]
    use_web_search: bool
    use_llm: bool
    priority: int
    enabled: bool

    class Config:
        from_attributes = True


class ProviderRoutingCreate(BaseModel):
    intent_category: str
    provider_name: str
    priority: int
    enabled: bool = True


class ProviderRoutingUpdate(BaseModel):
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class ProviderRoutingResponse(BaseModel):
    id: int
    intent_category: str
    provider_name: str
    priority: int
    enabled: bool

    class Config:
        from_attributes = True


# ============================================================================
# INTENT PATTERNS ENDPOINTS
# ============================================================================

@router.get("/intent-patterns", response_model=List[IntentPatternResponse])
async def list_intent_patterns(
    intent_category: Optional[str] = Query(None),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all intent patterns, optionally filtered."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(IntentPattern)

    if intent_category:
        query = query.filter(IntentPattern.intent_category == intent_category)

    if enabled_only:
        query = query.filter(IntentPattern.enabled == True)

    patterns = query.order_by(IntentPattern.intent_category, IntentPattern.pattern_type).all()
    return patterns


@router.post("/intent-patterns", response_model=IntentPatternResponse, status_code=201)
async def create_intent_pattern(
    pattern_data: IntentPatternCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new intent pattern."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check for duplicate
    existing = db.query(IntentPattern).filter(
        IntentPattern.intent_category == pattern_data.intent_category,
        IntentPattern.pattern_type == pattern_data.pattern_type,
        IntentPattern.keyword == pattern_data.keyword
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Pattern already exists")

    pattern = IntentPattern(**pattern_data.dict())
    db.add(pattern)
    db.commit()
    db.refresh(pattern)

    logger.info("intent_pattern_created", pattern_id=pattern.id, user=current_user.username)
    return pattern


@router.put("/intent-patterns/{pattern_id}", response_model=IntentPatternResponse)
async def update_intent_pattern(
    pattern_id: int,
    pattern_data: IntentPatternUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update intent pattern."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    pattern = db.query(IntentPattern).filter(IntentPattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Update fields
    update_data = pattern_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pattern, key, value)

    db.commit()
    db.refresh(pattern)

    logger.info("intent_pattern_updated", pattern_id=pattern.id, user=current_user.username)
    return pattern


@router.delete("/intent-patterns/{pattern_id}", status_code=204)
async def delete_intent_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete intent pattern."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    pattern = db.query(IntentPattern).filter(IntentPattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    db.delete(pattern)
    db.commit()

    logger.info("intent_pattern_deleted", pattern_id=pattern_id, user=current_user.username)
    return None


# ============================================================================
# INTENT ROUTING ENDPOINTS
# ============================================================================

@router.get("/intent-routing", response_model=List[IntentRoutingResponse])
async def list_intent_routing(
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all intent routing rules."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(IntentRouting)

    if enabled_only:
        query = query.filter(IntentRouting.enabled == True)

    rules = query.order_by(IntentRouting.priority.desc()).all()
    return rules


@router.post("/intent-routing", response_model=IntentRoutingResponse, status_code=201)
async def create_intent_routing(
    routing_data: IntentRoutingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new intent routing rule."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check for duplicate
    existing = db.query(IntentRouting).filter(
        IntentRouting.intent_category == routing_data.intent_category
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Routing rule already exists for this intent")

    routing = IntentRouting(**routing_data.dict())
    db.add(routing)
    db.commit()
    db.refresh(routing)

    logger.info("intent_routing_created", routing_id=routing.id, user=current_user.username)
    return routing


@router.put("/intent-routing/{routing_id}", response_model=IntentRoutingResponse)
async def update_intent_routing(
    routing_id: int,
    routing_data: IntentRoutingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update intent routing rule."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    routing = db.query(IntentRouting).filter(IntentRouting.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing rule not found")

    # Update fields
    update_data = routing_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(routing, key, value)

    db.commit()
    db.refresh(routing)

    logger.info("intent_routing_updated", routing_id=routing.id, user=current_user.username)
    return routing


@router.delete("/intent-routing/{routing_id}", status_code=204)
async def delete_intent_routing(
    routing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete intent routing rule."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    routing = db.query(IntentRouting).filter(IntentRouting.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing rule not found")

    db.delete(routing)
    db.commit()

    logger.info("intent_routing_deleted", routing_id=routing_id, user=current_user.username)
    return None


# ============================================================================
# PROVIDER ROUTING ENDPOINTS
# ============================================================================

@router.get("/provider-routing", response_model=List[ProviderRoutingResponse])
async def list_provider_routing(
    intent_category: Optional[str] = Query(None),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all provider routing rules."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(ProviderRouting)

    if intent_category:
        query = query.filter(ProviderRouting.intent_category == intent_category)

    if enabled_only:
        query = query.filter(ProviderRouting.enabled == True)

    rules = query.order_by(ProviderRouting.intent_category, ProviderRouting.priority).all()
    return rules


@router.post("/provider-routing", response_model=ProviderRoutingResponse, status_code=201)
async def create_provider_routing(
    routing_data: ProviderRoutingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new provider routing rule."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check for duplicate
    existing = db.query(ProviderRouting).filter(
        ProviderRouting.intent_category == routing_data.intent_category,
        ProviderRouting.provider_name == routing_data.provider_name
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Provider routing already exists")

    routing = ProviderRouting(**routing_data.dict())
    db.add(routing)
    db.commit()
    db.refresh(routing)

    logger.info("provider_routing_created", routing_id=routing.id, user=current_user.username)
    return routing


@router.put("/provider-routing/{routing_id}", response_model=ProviderRoutingResponse)
async def update_provider_routing(
    routing_id: int,
    routing_data: ProviderRoutingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update provider routing rule."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    routing = db.query(ProviderRouting).filter(ProviderRouting.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing rule not found")

    # Update fields
    update_data = routing_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(routing, key, value)

    db.commit()
    db.refresh(routing)

    logger.info("provider_routing_updated", routing_id=routing.id, user=current_user.username)
    return routing


@router.delete("/provider-routing/{routing_id}", status_code=204)
async def delete_provider_routing(
    routing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete provider routing rule."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    routing = db.query(ProviderRouting).filter(ProviderRouting.id == routing_id).first()
    if not routing:
        raise HTTPException(status_code=404, detail="Routing rule not found")

    db.delete(routing)
    db.commit()

    logger.info("provider_routing_deleted", routing_id=routing_id, user=current_user.username)
    return None
```

#### Step 1.7: Register Router in Main App

**File:** `admin/backend/main.py` (modify existing)

```python
# Add to imports
from app.routes import (
    ...,
    intent_routing  # NEW
)

# Add to router registration
app.include_router(intent_routing.router)  # NEW
```

### Phase 2: Migrate Hardcoded Patterns to Database

#### Step 2.1: Create Migration Script

**File:** `admin/backend/scripts/migrate_intent_patterns.py`

This script will:
1. Read hardcoded patterns from `intent_classifier.py`
2. Insert them into the database
3. Provide summary of what was migrated

#### Step 2.2: Create Migration Script for Provider Routing

**File:** `admin/backend/scripts/migrate_provider_routing.py`

This script will:
1. Read hardcoded mappings from `provider_router.py`
2. Insert them into the database
3. Provide summary of what was migrated

### Phase 3: Update Orchestrator to Use Database Config

#### Step 3.1: Modify Intent Classifier

**File:** `src/orchestrator/intent_classifier.py`

Changes needed:
1. Add `admin_api_url` parameter to `__init__`
2. Replace hardcoded patterns with `_load_patterns_from_db()` method
3. Add caching (TTL 60 seconds) to avoid DB calls on every request
4. Keep fallback to hardcoded patterns if database unavailable

#### Step 3.2: Modify Provider Router

**File:** `src/orchestrator/search_providers/provider_router.py`

Changes needed:
1. Add `admin_api_url` parameter to `__init__`
2. Replace hardcoded mappings with `_load_routing_from_db()` method
3. Add caching (TTL 60 seconds)
4. Keep fallback to hardcoded mappings if database unavailable

### Phase 4: Frontend UI

#### Step 4.1: Add Intent Routing Tab to Admin UI

**Location:** `admin/frontend/index.html` + `admin/frontend/app.js`

**UI Components:**

1. **Intent Patterns Management**
   - List all patterns by intent category
   - Add/edit/delete patterns
   - Bulk enable/disable
   - Import from current hardcoded patterns
   - Export to JSON

2. **Intent Routing Rules**
   - List all intent categories
   - Configure routing per intent:
     - Use RAG? (checkbox + RAG service URL)
     - Use Web Search? (checkbox)
     - Use LLM? (checkbox)
     - Priority (number)
   - Visual flow diagram showing routing path

3. **Provider Routing**
   - Matrix view: Intents (rows) × Providers (columns)
   - Drag-and-drop to reorder provider priority
   - Enable/disable providers per intent

#### Step 4.2: Add Navigation

**File:** `admin/frontend/index.html`

Add to sidebar:
```html
<button onclick="showTab('intent-routing')" class="sidebar-item ...">
    <span class="text-lg">🧭</span>
    <span>Intent Routing</span>
</button>
```

## Success Criteria

- [ ] All intent patterns configurable via UI
- [ ] All intent routing rules configurable via UI
- [ ] All provider routing configurable via UI
- [ ] Changes take effect within 60 seconds (cache TTL)
- [ ] Fallback to hardcoded config if database unavailable
- [ ] Migration scripts successfully import all existing patterns
- [ ] Frontend UI is intuitive and allows bulk operations
- [ ] Performance impact < 10ms per request (due to caching)

## Migration Path

1. **Week 1:**
   - Implement database schema and models
   - Create backend API endpoints
   - Write migration scripts

2. **Week 2:**
   - Update orchestrator to use database config
   - Add caching and fallback logic
   - Test with hardcoded and database configs side-by-side

3. **Week 3:**
   - Build frontend UI
   - Run migration scripts to populate database
   - Test end-to-end routing configuration

4. **Week 4:**
   - User acceptance testing
   - Performance testing
   - Documentation
   - Deploy to production

## Risks & Mitigation

**Risk:** Database unavailable causes routing failures
**Mitigation:** Keep fallback to hardcoded patterns, implement robust caching

**Risk:** Cache invalidation issues
**Mitigation:** Short TTL (60s), manual cache clear endpoint

**Risk:** Complex UI for provider routing
**Mitigation:** Start with simple list view, iterate to matrix/drag-drop

**Risk:** Performance degradation
**Mitigation:** Aggressive caching, async DB calls, monitoring

## Open Questions

1. Should we support versioning of routing configs?
2. Should we allow A/B testing of different routing strategies?
3. How do we handle conflicts between user-configured and default patterns?
4. Should we provide analytics on routing effectiveness?

## Related Files

- `src/orchestrator/intent_classifier.py` - Intent classification logic
- `src/orchestrator/search_providers/provider_router.py` - Provider routing logic
- `src/shared/llm_router.py` - LLM backend routing (already configurable)
- `admin/backend/app/routes/llm_backends.py` - LLM backend API (reference implementation)
- `admin/frontend/app.js` - Frontend logic (add intent routing UI here)
