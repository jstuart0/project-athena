# LLM-Based Routing Implementation Plan

**Date:** 2025-11-16
**Status:** Planning
**Priority:** High
**Target:** Open Source Ready + Default for Production

## Overview

Implement configurable routing logic in the Gateway that supports both keyword-based and LLM-based intent classification, controlled via Admin UI feature flag.

## Current State

**Keyword-Based Routing:**
- Fast (~0ms overhead)
- Requires maintaining extensive keyword lists
- Prone to missing edge cases
- Example failure: "whats the football schedule" didn't match because "schedule" wasn't in keywords

**Problems Solved:**
- ✅ Added web search fallback for all RAG service failures
- ✅ Expanded sports keywords to include ALL professional teams
- ✅ Added comprehensive soccer teams (MLS + international)

## Proposed Solution

### Two Routing Modes (Configurable)

1. **Keyword-Based** (Fast, Low Resource)
   - Current implementation
   - Best for: Resource-constrained environments, sub-second response requirements
   - Latency: ~0ms overhead

2. **LLM-Based** (Intelligent, Flexible)
   - Uses phi3:mini-q8 to classify intent
   - Best for: Production deployments with quality focus
   - Latency: +50-200ms overhead
   - No keyword list maintenance required

### Feature Flag

**Name:** `llm_based_routing`
**Type:** Boolean
**Default:** `true` (enabled for production quality)
**Category:** `routing`
**Display Name:** "Use LLM for Intent Classification"
**Description:** "Use AI to intelligently classify query intent instead of keyword matching. More accurate but adds 50-200ms latency."

## Implementation Steps

### 1. Admin Backend - Add Feature Flag

**File:** `admin/backend/alembic/versions/XXX_add_llm_routing_feature.py`

```python
"""Add LLM-based routing feature flag

Revision ID: XXX
Revises: <previous_revision>
Create Date: 2025-11-16
"""

from alembic import op
from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime

# Migration to add llm_based_routing feature

def upgrade():
    # Insert new feature
    op.execute("""
        INSERT INTO features (name, display_name, description, enabled, category, created_at, updated_at)
        VALUES (
            'llm_based_routing',
            'Use LLM for Intent Classification',
            'Use AI to intelligently classify query intent instead of keyword matching. More accurate but adds 50-200ms latency.',
            true,
            'routing',
            NOW(),
            NOW()
        )
    """)

def downgrade():
    op.execute("DELETE FROM features WHERE name = 'llm_based_routing'")
```

### 2. Gateway - Implement LLM-Based Routing

**File:** `src/gateway/main.py`

**Add LLM classifier function:**

```python
import httpx
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://localhost:8080")

# Feature flag cache
_feature_cache = {}
_cache_expiry = 0
_cache_ttl = 60  # 60 seconds

async def is_feature_enabled(feature_name: str) -> bool:
    """Check if feature is enabled via Admin API with caching."""
    global _feature_cache, _cache_expiry

    now = time.time()
    if now > _cache_expiry:
        # Refresh cache
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ADMIN_API_URL}/api/features")
                if response.status_code == 200:
                    features = response.json()
                    _feature_cache = {f["name"]: f["enabled"] for f in features}
                    _cache_expiry = now + _cache_ttl
        except Exception as e:
            logger.warning(f"Failed to fetch features: {e}")

    return _feature_cache.get(feature_name, False)

async def classify_intent_llm(query: str) -> bool:
    """
    Use LLM to classify if query should route to orchestrator.

    Returns:
        True if orchestrator should handle, False for Ollama
    """
    prompt = f"""Classify this query into ONE category:

Query: "{query}"

Categories:
- athena: Home control, weather, sports, airports, local info (Baltimore context)
- general: General knowledge, math, coding, explanations

Respond with ONLY the category name (athena or general)."""

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "phi3:mini-q8",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent classification
                        "num_predict": 10     # Only need one word response
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            classification = result.get("response", "").strip().lower()

            is_athena = "athena" in classification
            logger.info(f"LLM classified '{query}' as {'athena' if is_athena else 'general'}")
            return is_athena

    except Exception as e:
        logger.error(f"LLM classification failed: {e}, falling back to keyword matching")
        # Fallback to keyword matching
        return is_athena_query_keywords(messages)

def is_athena_query_keywords(messages: List[ChatMessage]) -> bool:
    """
    Keyword-based classification (current implementation).
    Used as fallback when LLM is disabled or fails.
    """
    # Get the last user message
    last_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            last_user_msg = msg.content.lower()
            break

    if not last_user_msg:
        return False

    # ... existing keyword patterns ...
    athena_patterns = [
        # [all the current keywords]
    ]

    return any(pattern in last_user_msg for pattern in athena_patterns)

async def is_athena_query(messages: List[ChatMessage]) -> bool:
    """
    Main routing decision function.
    Uses LLM or keywords based on feature flag.
    """
    # Get the last user message
    last_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            last_user_msg = msg.content
            break

    if not last_user_msg:
        return False

    # Check feature flag
    use_llm = await is_feature_enabled("llm_based_routing")

    if use_llm:
        logger.info("Using LLM-based routing")
        return await classify_intent_llm(last_user_msg)
    else:
        logger.info("Using keyword-based routing")
        return is_athena_query_keywords(messages)
```

### 3. Admin Frontend - Add Feature Toggle

**File:** `admin/frontend/features.html`

Add toggle UI in the Routing section:

```html
<div class="feature-card">
    <div class="feature-header">
        <h3>LLM-Based Intent Classification</h3>
        <label class="toggle">
            <input type="checkbox" id="llm_based_routing" onchange="toggleFeature('llm_based_routing', this.checked)">
            <span class="slider"></span>
        </label>
    </div>
    <p class="feature-description">
        Use AI to intelligently classify query intent instead of keyword matching.
        More accurate but adds 50-200ms latency.
    </p>
    <div class="feature-details">
        <strong>Category:</strong> Routing<br>
        <strong>Impact:</strong> All incoming queries<br>
        <strong>Latency:</strong> +50-200ms when enabled
    </div>
</div>
```

### 4. Documentation Updates

**File:** `docs/ADMIN_CONFIG.md`

Add routing configuration section:

```markdown
## Routing Configuration

### LLM-Based Intent Classification

**Feature:** `llm_based_routing`
**Default:** Enabled

Controls how the Gateway routes incoming queries:

**Enabled (LLM-based):**
- Uses phi3:mini-q8 to classify query intent
- More accurate, handles edge cases better
- Adds 50-200ms latency
- No keyword list maintenance required
- Recommended for production deployments

**Disabled (Keyword-based):**
- Fast pattern matching against keyword lists
- 0ms overhead
- May miss edge cases
- Requires maintaining keyword lists
- Best for resource-constrained environments

**Requirements:**
- Ollama must be running with phi3:mini-q8 model
- Set OLLAMA_URL environment variable
```

## Testing Plan

### Unit Tests

1. Test LLM classification with various queries
2. Test keyword fallback when LLM fails
3. Test feature flag caching
4. Test routing decision with flag enabled/disabled

### Integration Tests

1. End-to-end routing with LLM enabled
2. End-to-end routing with LLM disabled
3. Feature flag toggle via Admin UI
4. Performance testing (latency measurements)

### Test Queries

**Should route to Orchestrator:**
- "what's the football schedule this week?" (previously failed)
- "turn on the lights"
- "what's the weather in Baltimore?"
- "when does the Ravens game start?"
- "what flights are delayed at BWI?"

**Should route to Ollama:**
- "what is quantum computing?"
- "write me a Python function"
- "explain relativity"
- "what is 2+2?"

## Performance Considerations

### Latency Budget

- **Keyword matching:** ~0ms
- **LLM classification:** 50-200ms (measured)
- **Total acceptable latency:** <500ms for voice queries

### Caching Strategy

1. **Feature flag cache:** 60 second TTL
2. **LLM classification:** No caching (each query is unique)
3. **Keyword patterns:** Compiled regex (one-time cost)

### Fallback Strategy

```
LLM Classification
    ↓
  Fails?
    ↓
Keyword Matching
    ↓
  Still uncertain?
    ↓
Default to Ollama (general knowledge)
```

## Open Source Considerations

### Installation Documentation

**Minimal Setup (Keyword-based):**
```bash
# No additional requirements
# Just deploy Gateway
```

**Full Setup (LLM-based - Recommended):**
```bash
# Requires Ollama with phi3:mini-q8
ollama pull phi3:mini-q8

# Set environment variable
export OLLAMA_URL="http://localhost:11434"
```

### Configuration File

**File:** `.env.example`

```bash
# Routing Configuration
ADMIN_API_URL=http://localhost:8080
OLLAMA_URL=http://localhost:11434

# Feature defaults (can be overridden in Admin UI)
DEFAULT_LLM_ROUTING=true
```

## Deployment Steps

1. **Database Migration:**
   ```bash
   cd admin/backend
   alembic upgrade head
   ```

2. **Verify Feature Added:**
   ```bash
   curl http://localhost:8080/api/features | jq '.[] | select(.name=="llm_based_routing")'
   ```

3. **Deploy Updated Gateway:**
   ```bash
   # Kill old Gateway
   pkill -f "uvicorn gateway.main:app"

   # Start new Gateway
   cd src && python3 -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000
   ```

4. **Test Routing:**
   ```bash
   # Test with LLM enabled
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "phi3:mini",
       "messages": [{"role": "user", "content": "whats the football schedule this week?"}]
     }'
   ```

5. **Monitor Performance:**
   ```bash
   # Check Gateway logs for routing decisions
   tail -f ~/dev/project-athena/gateway.log | grep "classified"
   ```

## Success Criteria

- ✅ Feature flag exists in Admin UI
- ✅ Toggle works and persists
- ✅ LLM classification routes correctly
- ✅ Keyword fallback works when LLM disabled
- ✅ Latency < 200ms for LLM classification
- ✅ All test queries route correctly
- ✅ Documentation updated
- ✅ Zero breaking changes for existing deployments

## Rollback Plan

If issues occur:

1. **Disable via Admin UI:**
   - Toggle `llm_based_routing` to OFF
   - System falls back to keyword matching

2. **Database Rollback:**
   ```bash
   cd admin/backend
   alembic downgrade -1
   ```

3. **Code Rollback:**
   ```bash
   git revert <commit_hash>
   ./deploy.sh
   ```

## Future Enhancements

1. **Intent Confidence Scoring:**
   - Return confidence scores with LLM classification
   - Use hybrid approach: LLM for uncertain cases, keywords for obvious ones

2. **Model Selection:**
   - Allow choosing different LLM models via Admin UI
   - Support for faster/smaller models (e.g., phi2)

3. **Analytics:**
   - Track routing decisions
   - Compare accuracy between LLM and keyword methods
   - Show metrics in Admin UI

4. **Learning Mode:**
   - Log misrouted queries
   - Auto-update keyword lists based on LLM classifications

## Related Issues

- User reported: "whats the football schedule" routed to Ollama
- Web search fallback not triggering for RAG failures (FIXED)
- Need comprehensive sports keyword coverage (FIXED)

## References

- [Orchestrator Intent Classifier](../../../src/orchestrator/search_providers/intent_classifier.py)
- [Gateway Routing Logic](../../../src/gateway/main.py:248-290)
- [Admin Features API](../../../admin/backend/app/routes/features.py)
