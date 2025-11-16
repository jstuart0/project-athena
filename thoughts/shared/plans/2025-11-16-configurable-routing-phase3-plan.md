# Configurable Routing System - Phase 3+ Implementation Plan

**Date:** 2025-11-16
**Status:** Phase 2 Complete, Phase 3+ Pending
**Context:** Continuing from successful database population

## Progress Summary

### ✅ Phase 1: Database Schema & Backend API (COMPLETE)
- Created 3 database tables: `intent_patterns`, `intent_routing`, `provider_routing`
- Implemented full REST API (`/api/intent-routing/*` endpoints)
- Added authentication and permission checks
- Migration: `005_configurable_routing.py`

### ✅ Phase 2: Database Population (COMPLETE)
- Created `populate_routing_db.py` script
- Successfully populated:
  - **211 intent patterns** across 11 categories
  - **11 routing configurations** (RAG URLs, web search settings)
  - **14 provider mappings** (Ticketmaster, Eventbrite, DuckDuckGo, Brave)
- Zero errors during population

### ⏳ Phase 3: Orchestrator Integration (PENDING)

This is the core work that needs to be completed.

## Phase 3: Detailed Implementation Plan

### 3.1: Extend AdminConfigClient for Routing

**File:** `/Users/jaystuart/dev/project-athena/src/shared/admin_config.py`

**Current State:**
- Exists for secrets management only
- Has `AdminConfigClient` class with `get_secret()` and `get_config()` methods

**Required Changes:**
Add new methods to `AdminConfigClient`:

```python
async def get_intent_patterns(self) -> Dict[str, List[str]]:
    """
    Fetch intent patterns from Admin API.

    Returns:
        Dict mapping intent_category -> list of keywords
        Falls back to empty dict if API unavailable
    """
    url = f"{self.admin_url}/api/intent-routing/patterns"
    # Fetch and transform data
    # Cache for 60 seconds
    # Log errors but don't raise (graceful degradation)

async def get_intent_routing(self) -> Dict[str, Dict]:
    """
    Fetch intent routing configuration.

    Returns:
        Dict mapping intent_category -> {use_rag, rag_service_url, use_web_search, use_llm}
    """

async def get_provider_routing(self) -> Dict[str, List[str]]:
    """
    Fetch provider routing (ordered by priority).

    Returns:
        Dict mapping intent_category -> ordered list of provider names
    """
```

**Implementation Notes:**
- Use `httpx.AsyncClient` (already in class)
- Add 60-second TTL cache using `time.time()` timestamps
- Graceful fallback: return empty dict if API unavailable (allows hardcoded fallback)
- Log all failures but don't raise exceptions

---

### 3.2: Modify Intent Classifier

**File:** `/Users/jaystuart/dev/project-athena/src/orchestrator/intent_classifier.py`

**Current Hardcoded Data (lines to modify):**
- **Lines 48-102**: `INTENT_KEYWORDS` dictionary
- **Lines 106-111**: `COMPLEX_QUERY_INDICATORS`
- **Lines 114-136**: Action/entity patterns (optional - can keep hardcoded)

**Required Changes:**

#### 3.2.1: Add Database Loading

```python
# Add at top of file (after imports)
from shared.admin_config import get_admin_client
import asyncio

# Global cache
_db_patterns: Optional[Dict[str, List[str]]] = None
_db_patterns_loaded_at: float = 0
_DB_CACHE_TTL = 60  # seconds

async def _load_patterns_from_db() -> Optional[Dict[str, List[str]]]:
    """Load patterns from Admin API with caching."""
    global _db_patterns, _db_patterns_loaded_at

    # Check cache
    if _db_patterns and (time.time() - _db_patterns_loaded_at < _DB_CACHE_TTL):
        return _db_patterns

    # Fetch from API
    try:
        client = get_admin_client()
        patterns = await client.get_intent_patterns()
        if patterns:
            _db_patterns = patterns
            _db_patterns_loaded_at = time.time()
            logger.info("intent_patterns_loaded_from_db", count=len(patterns))
            return patterns
    except Exception as e:
        logger.warning("intent_patterns_db_fetch_failed", error=str(e))

    return None
```

#### 3.2.2: Modify `classify_intent()` Method

```python
async def classify_intent(self, query: str) -> IntentClassification:
    """Classify user intent with database-driven patterns."""

    # Try loading from database first
    db_patterns = await _load_patterns_from_db()
    patterns_to_use = db_patterns if db_patterns else INTENT_KEYWORDS

    # Use patterns_to_use instead of INTENT_KEYWORDS throughout method
    for category, keywords in patterns_to_use.items():
        # ... existing matching logic ...
```

**Key Points:**
- Keep all existing `INTENT_KEYWORDS` as fallback
- Only modify pattern source, not matching logic
- Log which source is being used (DB vs hardcoded)
- Ensure backward compatibility

---

### 3.3: Modify Provider Router

**File:** `/Users/jaystuart/dev/project-athena/src/orchestrator/search_providers/provider_router.py`

**Current Hardcoded Data:**
- **Lines 32-51**: `INTENT_PROVIDER_SETS` dictionary
- **Line 54**: `RAG_INTENTS` set

**Required Changes:**

#### 3.3.1: Add Database Loading

```python
from shared.admin_config import get_admin_client

# Global cache
_db_provider_routing: Optional[Dict[str, List[str]]] = None
_db_routing_config: Optional[Dict[str, Dict]] = None
_db_cache_loaded_at: float = 0
_DB_CACHE_TTL = 60

async def _load_routing_from_db():
    """Load provider routing and RAG config from Admin API."""
    global _db_provider_routing, _db_routing_config, _db_cache_loaded_at

    if time.time() - _db_cache_loaded_at < _DB_CACHE_TTL:
        return

    client = get_admin_client()
    try:
        _db_provider_routing = await client.get_provider_routing()
        _db_routing_config = await client.get_intent_routing()
        _db_cache_loaded_at = time.time()
        logger.info("routing_config_loaded_from_db")
    except Exception as e:
        logger.warning("routing_config_db_fetch_failed", error=str(e))
```

#### 3.3.2: Modify `should_use_rag()` Method

```python
async def should_use_rag(self, intent: str) -> bool:
    """Check if RAG should be used (DB-driven)."""
    await _load_routing_from_db()

    if _db_routing_config and intent in _db_routing_config:
        return _db_routing_config[intent].get("use_rag", False)

    # Fallback to hardcoded
    return intent in RAG_INTENTS
```

#### 3.3.3: Modify `get_search_providers()` Method

```python
async def get_search_providers(self, intent: str) -> List[str]:
    """Get ordered list of providers for intent (DB-driven)."""
    await _load_routing_from_db()

    if _db_provider_routing and intent in _db_provider_routing:
        return _db_provider_routing[intent]

    # Fallback to hardcoded
    for intent_set, providers in INTENT_PROVIDER_SETS.items():
        if intent_set in intent or intent in intent_set:
            return providers

    return INTENT_PROVIDER_SETS.get("general", ["duckduckgo", "brave"])
```

---

### 3.4: Modify Main Orchestrator

**File:** `/Users/jaystuart/dev/project-athena/src/orchestrator/main.py`

**Current Hardcoded Data:**
- **Lines 72-75**: RAG service URLs
  ```python
  RAG_WEATHER_URL = os.getenv("RAG_WEATHER_URL", "http://localhost:8010")
  RAG_AIRPORTS_URL = os.getenv("RAG_AIRPORTS_URL", "http://localhost:8011")
  RAG_SPORTS_URL = os.getenv("RAG_SPORTS_URL", "http://localhost:8012")
  ```

**Required Changes:**

#### 3.4.1: Add Dynamic RAG URL Loading

```python
from shared.admin_config import get_admin_client

async def get_rag_service_url(intent: str) -> Optional[str]:
    """
    Get RAG service URL for intent (DB-driven).

    Args:
        intent: Intent category (e.g., "weather", "sports")

    Returns:
        RAG service URL or None
    """
    try:
        client = get_admin_client()
        routing_config = await client.get_intent_routing()

        if routing_config and intent in routing_config:
            return routing_config[intent].get("rag_service_url")
    except Exception as e:
        logger.warning("rag_url_fetch_failed", intent=intent, error=str(e))

    # Fallback to environment variables / hardcoded
    url_map = {
        "weather": RAG_WEATHER_URL,
        "airports": RAG_AIRPORTS_URL,
        "sports": RAG_SPORTS_URL
    }
    return url_map.get(intent)
```

#### 3.4.2: Modify RAG Query Functions

**Lines 404-516**: `_query_weather_rag()`, `_query_airports_rag()`, `_query_sports_rag()`

Change from:
```python
async def _query_weather_rag(...):
    url = RAG_WEATHER_URL
```

To:
```python
async def _query_weather_rag(...):
    url = await get_rag_service_url("weather")
    if not url:
        logger.error("rag_url_not_configured", intent="weather")
        return None
```

Repeat for airports and sports.

---

## Phase 4: Testing Plan

### 4.1: Unit Tests

Create `/Users/jaystuart/dev/project-athena/src/orchestrator/tests/test_db_routing.py`:

```python
import pytest
from orchestrator.intent_classifier import classify_intent

@pytest.mark.asyncio
async def test_intent_classification_from_db():
    """Test that patterns load from database."""
    # Setup: mock Admin API to return test patterns
    # Test: classification uses DB patterns
    # Assert: correct intent detected

@pytest.mark.asyncio
async def test_fallback_to_hardcoded():
    """Test fallback when database unavailable."""
    # Setup: mock Admin API to fail
    # Test: classification still works
    # Assert: uses hardcoded patterns

@pytest.mark.asyncio
async def test_caching():
    """Test that patterns are cached."""
    # Setup: mock Admin API call counter
    # Test: multiple classifications within 60 seconds
    # Assert: only one API call made
```

### 4.2: Integration Tests

**Test Scenarios:**
1. **Database Available:**
   - Admin API returns custom patterns
   - Orchestrator uses DB patterns
   - Verify via logs: "intent_patterns_loaded_from_db"

2. **Database Unavailable:**
   - Admin API returns 404 or times out
   - Orchestrator falls back to hardcoded
   - Verify via logs: "intent_patterns_db_fetch_failed"

3. **Cache Expiry:**
   - Load patterns at T=0
   - Wait 61 seconds
   - Trigger classification at T=61
   - Verify: new API call made

**Test Commands:**
```bash
# Start orchestrator with Admin API available
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "what's the weather"}]}'

# Check logs
tail -f orchestrator.log | grep "intent_patterns_loaded"

# Simulate Admin API failure
# (stop admin backend or firewall port 8081)

# Test fallback
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "turn on the lights"}]}'

# Verify response still works
```

### 4.3: Performance Testing

**Metrics to Track:**
- API call latency (should be < 100ms with cache)
- Cache hit rate (should be > 95% after warmup)
- Fallback activation rate (should be 0% in normal operation)

---

## Phase 5: Frontend UI (Future Work)

### 5.1: Routing Configuration Page

**Location:** `/Users/jaystuart/dev/project-athena/admin/frontend/`

**Features:**
1. **Intent Patterns Table**
   - Columns: Category, Pattern Type, Keyword, Weight, Enabled
   - Actions: Add, Edit, Delete, Toggle Enabled
   - Filters: By category, by enabled status

2. **Intent Routing Table**
   - Columns: Category, Use RAG, RAG URL, Use Web, Use LLM, Priority
   - Actions: Edit routing config
   - Visual indicators: RAG enabled (green), Web search (blue)

3. **Provider Routing Table**
   - Columns: Category, Providers (ordered chips), Priority
   - Actions: Reorder providers (drag-drop), Add/remove providers

**Tech Stack:**
- HTML + Vanilla JavaScript (matching existing frontend)
- Fetch API for REST calls
- Table sorting/filtering
- Modal dialogs for add/edit

### 5.2: Real-time Testing Panel

**Features:**
- Text input: "Test query"
- Button: "Classify Intent"
- Results display:
  - Detected intent
  - Confidence score
  - Which patterns matched
  - Routing decision (RAG/Web/LLM)
  - Selected providers

**Purpose:** Allow admins to test routing changes immediately

---

## Environment Variables

Add to `/Users/jaystuart/dev/project-athena/.env`:

```bash
# Admin API Configuration
ADMIN_API_URL=http://localhost:8081
CONFIG_CACHE_TTL=60  # seconds

# For production (when admin runs in K8s)
# ADMIN_API_URL=http://athena-admin-backend.athena-admin.svc.cluster.local:8080
```

---

## Deployment Checklist

### Before Deploying to Mac Studio:

1. ✅ Ensure Admin API is accessible at `localhost:8081`
2. ✅ Verify database populated (211 patterns, 11 routing, 14 providers)
3. ⬜ Test orchestrator locally with new code
4. ⬜ Run integration tests
5. ⬜ Check logs for errors
6. ⬜ Deploy to Mac Studio
7. ⬜ Restart orchestrator service
8. ⬜ Monitor logs for "intent_patterns_loaded_from_db"
9. ⬜ Test end-to-end queries

### Rollback Plan:

If database integration causes issues:
1. Revert orchestrator code to previous version
2. Orchestrator will use hardcoded patterns (no database dependency)
3. Admin API remains available for manual configuration

---

## Success Criteria

### Phase 3 Complete When:
- [  ] All 3 orchestrator files modified (intent_classifier, provider_router, main)
- [  ] Database patterns successfully loaded on startup
- [  ] Caching works (60-second TTL, logs show cache hits)
- [  ] Fallback works (manual test with Admin API down)
- [  ] No performance regression (< 5ms overhead)
- [  ] Integration tests pass

### Phase 4 Complete When:
- [  ] Unit tests written and passing
- [  ] Integration tests documented
- [  ] Performance metrics logged
- [  ] End-to-end test scenarios validated

### Phase 5 Complete When:
- [  ] Frontend UI deployed and accessible
- [  ] CRUD operations working for all 3 tables
- [  ] Real-time testing panel functional
- [  ] Documentation updated

---

## Known Issues & Considerations

### 1. RAG_INTENTS Inconsistency

**Issue:** Airports uses RAG (per main.py) but is NOT in `RAG_INTENTS` set (provider_router.py:54)

**Resolution:** When implementing database loading, airports routing config has `use_rag=true` in database, which will override the hardcoded set.

### 2. Async/Sync Mixing

**Current State:** Orchestrator uses FastAPI (async), but some methods may not be async.

**Resolution:** All database loading methods MUST be async. Update calling code if needed:

```python
# If caller is sync:
patterns = asyncio.run(_load_patterns_from_db())

# If caller is already async:
patterns = await _load_patterns_from_db()
```

### 3. Port Forwarding for Local Testing

**For Mac Studio Access:**
```bash
# Forward Admin API from K8s
kubectl -n athena-admin port-forward deployment/athena-admin-backend 8081:8080

# Or use direct Mac Studio access:
ssh -L 8081:localhost:8080 jstuart@192.168.10.167
```

---

## File Change Summary

### Files to Modify:
1. `/Users/jaystuart/dev/project-athena/src/shared/admin_config.py` - Add routing methods
2. `/Users/jaystuart/dev/project-athena/src/orchestrator/intent_classifier.py` - DB pattern loading
3. `/Users/jaystuart/dev/project-athena/src/orchestrator/search_providers/provider_router.py` - DB routing loading
4. `/Users/jaystuart/dev/project-athena/src/orchestrator/main.py` - Dynamic RAG URLs

### Files to Create:
1. `/Users/jaystuart/dev/project-athena/src/orchestrator/tests/test_db_routing.py` - Tests
2. Frontend UI files (TBD in Phase 5)

### Files NOT to Modify:
- Database migration files (already done)
- Backend API routes (already done)
- Models (already done)

---

## Next Steps

**Immediate (Phase 3):**
1. Extend `AdminConfigClient` with routing methods
2. Modify `intent_classifier.py` with database loading + fallback
3. Modify `provider_router.py` with database loading + fallback
4. Modify `main.py` for dynamic RAG URLs
5. Test locally on Mac Studio

**After Phase 3:**
6. Write integration tests
7. Deploy and validate
8. Create frontend UI (Phase 5)

---

**Last Updated:** 2025-11-16
**Author:** Claude Code
**Status:** Phase 2 Complete, Ready for Phase 3 Implementation
