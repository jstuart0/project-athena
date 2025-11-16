# Sprint 1: High-Priority Gaps Implementation Plan

## Overview

This plan addresses the 2 remaining high-priority gaps identified in the System Reconciliation Report, bringing Project Athena from 90% to near-100% completion for MVP requirements.

**Total Estimated Time:** 3-5 hours
**Priority:** High (improves production readiness)
**Dependencies:** Existing LLM Router, Orchestrator, Admin API, Session Manager

**Note:** Phase 3 (Admin UI Authentication) was found to be already complete during codebase research and has been removed from this plan.

## Current State Analysis

### Gap 1: Conversation History
**Status:** Partially implemented (50%)
- ✅ Session manager exists (orchestrator/session_manager.py)
- ✅ `conversation_history` field in OrchestratorState (orchestrator/main.py:104)
- ✅ History loaded from session (orchestrator/main.py:860-869)
- ❌ History NOT used in LLM prompts (orchestrator/main.py:556-561 has TODO)

**Impact:** Each query is treated as standalone, no context retention across turns

### Gap 2: Performance Metrics Persistence
**Status:** Partially implemented (40%)
- ✅ Database fields exist (`avg_tokens_per_sec`, `avg_latency_ms` in llm_backends table)
- ✅ LLM Router logs duration (llm_router.py:193-199)
- ❌ Metrics NOT persisted to database
- ❌ No endpoint to report metrics back to Admin API

**Impact:** No historical performance data for optimization decisions

### Gap 3: Admin UI Authentication
**Status:** ✅ **COMPLETE** (100%)
- ✅ Admin API has OIDC integration (app/auth/oidc.py)
- ✅ Backend routes use `get_current_user` (llm_backends.py:92)
- ✅ Permission checks in place (`has_permission()`)
- ✅ Frontend integrated with OIDC (confirmed via codebase research)
- ✅ Admin routes protected in UI with login/logout flow
- ✅ Role-based access control (viewer/support/operator/owner)
- ✅ Comprehensive audit logging with HMAC signatures

**Impact:** No action needed - already production-ready

**Research:** See `thoughts/shared/research/2025-11-15-admin-ui-authentication.md` for complete implementation details.

## Desired End State

After completing this plan:

1. ✅ **Conversation History Working**
   - Multi-turn conversations maintain context
   - LLM receives formatted conversation history
   - Configurable history length (default: 10 messages)

2. ✅ **Performance Metrics Persisted**
   - `avg_tokens_per_sec` and `avg_latency_ms` populated in database
   - Rolling average over last 100 requests
   - Admin UI shows performance trends

3. ✅ **Admin UI Already Secured** (no action needed)
   - OIDC login already implemented and working
   - Protected routes already enforced
   - User permissions already active

### Verification

```bash
# Test conversation history
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "My name is Jay", "session_id": "test-123"}'

curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is my name?", "session_id": "test-123"}'
# Should respond: "Your name is Jay"

# Test performance metrics
curl http://localhost:8080/api/llm-backends | jq '.[] | {model_name, avg_tokens_per_sec, avg_latency_ms}'
# Should show non-null values
```

**Note:** Admin UI authentication verification not needed - already confirmed working via codebase research.

## What We're NOT Doing

- ❌ Streaming LLM responses (deferred to Sprint 2)
- ❌ Voice assistant features (future roadmap)
- ❌ Grafana dashboards (future enhancement)
- ❌ Multi-user conversation isolation (Phase 2 feature)
- ❌ Advanced metrics (tokens/sec by model tier, percentile latencies)

---

## Phase 1: Conversation History Support

### Overview

Enable LLM context retention across conversation turns by formatting conversation history into prompts. The session manager already loads history; we just need to use it.

**Estimated Time:** 1-2 hours
**Files Modified:** 1
**Complexity:** Low (infrastructure exists, just needs integration)

### Changes Required

#### 1. Update Orchestrator Synthesis Node

**File:** `src/orchestrator/main.py`

**Location:** Lines 513-583 (synthesize_node function)

**Current Code (lines 556-561):**
```python
# TODO: Add conversation history support (requires message formatting)
if state.conversation_history:
    logger.info(f"Note: {len(state.conversation_history)} previous messages available (history support pending)")

# Combine system context with synthesis prompt
full_prompt = system_context + synthesis_prompt
```

**Change to:**
```python
# Format conversation history for LLM context
history_context = ""
if state.conversation_history:
    logger.info(f"Including {len(state.conversation_history)} previous messages in context")

    # Format as conversation log
    history_context = "Previous conversation:\n"
    for msg in state.conversation_history:
        role = msg["role"].capitalize()
        content = msg["content"]
        history_context += f"{role}: {content}\n"
    history_context += "\n"

# Combine system context, history, and synthesis prompt
full_prompt = system_context + history_context + synthesis_prompt
```

**Why This Works:**
- `conversation_history` is already loaded from session manager (line 867)
- Session manager already limits history to `max_llm_history_messages` (line 867)
- Simple string formatting is sufficient for current non-streaming approach

### Testing Strategy

#### Unit Tests

Create `tests/orchestrator/test_conversation_history.py`:

```python
import pytest
from orchestrator.main import synthesize_node, OrchestratorState, IntentCategory, ModelTier

@pytest.mark.asyncio
async def test_conversation_history_formatting():
    """Test that conversation history is included in LLM prompt."""

    # Create state with conversation history
    state = OrchestratorState(
        query="What did I just tell you?",
        intent=IntentCategory.GENERAL_INFO,
        model_tier=ModelTier.SMALL,
        conversation_history=[
            {"role": "user", "content": "My favorite color is blue"},
            {"role": "assistant", "content": "I'll remember that your favorite color is blue."}
        ],
        retrieved_data={}
    )

    # Mock LLM router to capture prompt
    captured_prompt = None

    async def mock_generate(model, prompt, **kwargs):
        nonlocal captured_prompt
        captured_prompt = prompt
        return {"response": "Your favorite color is blue"}

    # Inject mock
    import orchestrator.main
    original_generate = orchestrator.main.llm_router.generate
    orchestrator.main.llm_router.generate = mock_generate

    try:
        result = await synthesize_node(state)

        # Verify history was included in prompt
        assert "Previous conversation:" in captured_prompt
        assert "User: My favorite color is blue" in captured_prompt
        assert "Assistant: I'll remember" in captured_prompt

    finally:
        orchestrator.main.llm_router.generate = original_generate


@pytest.mark.asyncio
async def test_no_history_works():
    """Test that synthesis works without conversation history."""

    state = OrchestratorState(
        query="What is the capital of France?",
        intent=IntentCategory.GENERAL_INFO,
        model_tier=ModelTier.SMALL,
        conversation_history=[],  # Empty history
        retrieved_data={}
    )

    result = await synthesize_node(state)

    # Should complete without error
    assert result.answer is not None
```

#### Integration Tests

Add to `tests/integration/test_orchestrator_flow.py`:

```python
@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """Test that conversation context is maintained across turns."""

    # Turn 1: User provides information
    response1 = await client.post("/query", json={
        "query": "My name is Jay Stuart and I live in Baltimore",
        "session_id": "test-history-123"
    })
    assert response1.status_code == 200

    # Turn 2: Ask about previously provided info
    response2 = await client.post("/query", json={
        "query": "Where do I live?",
        "session_id": "test-history-123"
    })
    assert response2.status_code == 200
    data2 = response2.json()

    # Should remember Baltimore
    assert "baltimore" in data2["answer"].lower()

    # Turn 3: Ask about name
    response3 = await client.post("/query", json={
        "query": "What is my name?",
        "session_id": "test-history-123"
    })
    assert response3.status_code == 200
    data3 = response3.json()

    # Should remember name
    assert "jay" in data3["answer"].lower()
```

### Success Criteria

#### Automated Verification

- [ ] All existing unit tests pass: `pytest tests/orchestrator/`
- [ ] New conversation history unit tests pass: `pytest tests/orchestrator/test_conversation_history.py`
- [ ] Integration tests pass: `pytest tests/integration/test_orchestrator_flow.py::test_multi_turn_conversation`
- [ ] No linting errors: `ruff check src/orchestrator/main.py`
- [ ] Type checking passes: `mypy src/orchestrator/main.py`

#### Manual Verification

- [ ] Start fresh session, say "My name is Jay"
- [ ] In same session, ask "What is my name?" - should respond correctly
- [ ] Check orchestrator logs for "Including X previous messages in context"
- [ ] Test with 15+ turn conversation, verify context window trimming
- [ ] Verify session ID is returned in response and reused correctly

**Implementation Note:** After completing automated verification, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Performance Metrics Persistence

### Overview

Persist LLM performance metrics (`tokens/sec`, `latency`) to database for historical tracking and optimization decisions. Currently metrics are logged but not stored.

**Estimated Time:** 2-3 hours
**Files Modified:** 2-3
**Complexity:** Low-Medium (requires new endpoint + background task)

### Changes Required

#### 1. Add Metrics Reporting Method to LLM Router

**File:** `src/shared/llm_router.py`

**Location:** After line 199 (end of generate method)

**Add new method:**
```python
async def report_metrics(
    self,
    model: str,
    duration: float,
    tokens_generated: int,
    error_occurred: bool = False
) -> None:
    """
    Report performance metrics to Admin API for persistence.

    Args:
        model: Model name
        duration: Request duration in seconds
        tokens_generated: Number of tokens generated
        error_occurred: Whether an error occurred
    """
    try:
        # Calculate tokens per second
        tokens_per_sec = tokens_generated / duration if duration > 0 else 0
        latency_ms = duration * 1000

        # Report to Admin API
        url = f"{self.admin_url}/api/llm-backends/model/{model}/metrics"
        await self.client.post(url, json={
            "duration_ms": latency_ms,
            "tokens_generated": tokens_generated,
            "tokens_per_sec": tokens_per_sec,
            "error_occurred": error_occurred
        }, timeout=5.0)

        logger.debug(
            "reported_metrics",
            model=model,
            tokens_per_sec=tokens_per_sec,
            latency_ms=latency_ms
        )

    except Exception as e:
        # Don't fail request if metrics reporting fails
        logger.warning(
            "failed_to_report_metrics",
            model=model,
            error=str(e)
        )
```

**Update generate method (line 163-199):**
```python
async def generate(...) -> Dict[str, Any]:
    # ... existing code ...

    start_time = time.time()
    error_occurred = False
    result = None

    try:
        # ... existing backend routing ...

    except Exception as e:
        error_occurred = True
        raise

    finally:
        duration = time.time() - start_time
        logger.info(
            "llm_request_completed",
            model=model,
            backend_type=backend_type,
            duration=duration
        )

        # Report metrics (non-blocking)
        if result:
            tokens_generated = result.get("eval_count", 0) or 0
            # Fire and forget - don't await
            asyncio.create_task(
                self.report_metrics(model, duration, tokens_generated, error_occurred)
            )

    return result
```

#### 2. Add Metrics Endpoint to Admin API

**File:** `admin/backend/app/routes/llm_backends.py`

**Location:** After line 319 (end of file)

**Add new endpoint:**
```python
class MetricsReport(BaseModel):
    """Request model for reporting metrics."""
    duration_ms: float = Field(..., description="Request duration in milliseconds")
    tokens_generated: int = Field(..., description="Number of tokens generated")
    tokens_per_sec: float = Field(..., description="Tokens per second")
    error_occurred: bool = Field(default=False, description="Whether an error occurred")


@router.post("/model/{model_name}/metrics", status_code=204)
async def report_metrics(
    model_name: str,
    metrics: MetricsReport,
    db: Session = Depends(get_db)
):
    """
    Report performance metrics for a model (service-to-service, no auth required).

    Updates rolling average of tokens/sec and latency over last 100 requests.
    """
    backend = db.query(LLMBackend).filter(
        LLMBackend.model_name == model_name
    ).first()

    if not backend:
        # Create placeholder backend if doesn't exist
        logger.warning(
            "creating_placeholder_backend_for_metrics",
            model_name=model_name
        )
        backend = LLMBackend(
            model_name=model_name,
            backend_type="ollama",
            endpoint_url="http://localhost:11434",
            enabled=True
        )
        db.add(backend)

    # Update counters
    backend.total_requests += 1
    if metrics.error_occurred:
        backend.total_errors += 1

    # Update rolling averages (weighted average with alpha=0.1 for smoothing)
    alpha = 0.1  # Weight for new observation

    if backend.avg_tokens_per_sec is None:
        backend.avg_tokens_per_sec = metrics.tokens_per_sec
    else:
        backend.avg_tokens_per_sec = (
            alpha * metrics.tokens_per_sec +
            (1 - alpha) * backend.avg_tokens_per_sec
        )

    if backend.avg_latency_ms is None:
        backend.avg_latency_ms = metrics.duration_ms
    else:
        backend.avg_latency_ms = (
            alpha * metrics.duration_ms +
            (1 - alpha) * backend.avg_latency_ms
        )

    db.commit()

    logger.debug(
        "updated_backend_metrics",
        model_name=model_name,
        avg_tokens_per_sec=backend.avg_tokens_per_sec,
        avg_latency_ms=backend.avg_latency_ms,
        total_requests=backend.total_requests
    )

    return None
```

#### 3. Add Missing Import

**File:** `src/shared/llm_router.py`

**Location:** Line 10 (after other imports)

**Add:**
```python
import asyncio
```

### Testing Strategy

#### Unit Tests

Create `tests/llm_router/test_metrics.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from llm_router import LLMRouter

@pytest.mark.asyncio
async def test_metrics_reporting():
    """Test that metrics are reported to Admin API."""

    router = LLMRouter(admin_url="http://test-admin:8080")

    # Mock HTTP client
    mock_post = AsyncMock()
    router.client.post = mock_post

    # Report metrics
    await router.report_metrics(
        model="phi3:mini",
        duration=2.5,
        tokens_generated=100,
        error_occurred=False
    )

    # Verify API call
    assert mock_post.called
    call_args = mock_post.call_args
    assert "phi3:mini" in call_args[0][0]  # URL contains model name

    payload = call_args[1]["json"]
    assert payload["duration_ms"] == 2500
    assert payload["tokens_generated"] == 100
    assert payload["tokens_per_sec"] == 40.0  # 100 / 2.5


@pytest.mark.asyncio
async def test_metrics_reporting_failure_doesnt_crash():
    """Test that metrics reporting failure doesn't crash generate()."""

    router = LLMRouter()

    # Mock generate to fail metrics reporting
    router.client.post = AsyncMock(side_effect=Exception("Network error"))

    # Mock backend response
    async def mock_ollama(*args, **kwargs):
        return {"response": "test", "eval_count": 50}

    router._generate_ollama = mock_ollama
    router._get_backend_config = AsyncMock(return_value={
        "backend_type": "ollama",
        "endpoint_url": "http://localhost:11434",
        "max_tokens": 2048,
        "temperature_default": 0.7,
        "timeout_seconds": 60
    })

    # Should not raise exception
    result = await router.generate(model="phi3:mini", prompt="test")
    assert result["response"] == "test"
```

#### Integration Tests

Add to `tests/integration/test_admin_api.py`:

```python
@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test metrics reporting endpoint."""

    # Create backend
    response = await admin_client.post("/api/llm-backends", json={
        "model_name": "test-model",
        "backend_type": "ollama",
        "endpoint_url": "http://localhost:11434"
    })
    assert response.status_code == 201
    backend_id = response.json()["id"]

    # Report metrics
    for i in range(10):
        response = await admin_client.post(
            "/api/llm-backends/model/test-model/metrics",
            json={
                "duration_ms": 1000 + (i * 100),
                "tokens_generated": 50,
                "tokens_per_sec": 50.0 / ((1000 + i * 100) / 1000),
                "error_occurred": False
            }
        )
        assert response.status_code == 204

    # Check updated metrics
    response = await admin_client.get(f"/api/llm-backends/{backend_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["avg_tokens_per_sec"] is not None
    assert data["avg_latency_ms"] is not None
    assert data["total_requests"] == 10
    assert data["total_errors"] == 0
```

### Success Criteria

#### Automated Verification

- [ ] All existing tests pass: `pytest tests/`
- [ ] New metrics unit tests pass: `pytest tests/llm_router/test_metrics.py`
- [ ] Admin API integration tests pass: `pytest tests/integration/test_admin_api.py::test_metrics_endpoint`
- [ ] No linting errors: `ruff check src/shared/llm_router.py admin/backend/app/routes/llm_backends.py`
- [ ] Type checking passes: `mypy src/shared/ admin/backend/`

#### Manual Verification

- [ ] Start orchestrator and make 10 queries
- [ ] Check database: `SELECT model_name, avg_tokens_per_sec, avg_latency_ms, total_requests FROM llm_backends;`
- [ ] Verify metrics are populated (non-null values)
- [ ] Admin UI shows performance data on backend list
- [ ] Make query with non-existent model, verify placeholder backend created
- [ ] Check logs for "updated_backend_metrics" entries

**Implementation Note:** After completing automated verification, pause for manual confirmation before proceeding to Phase 3.

---


---

## Phase 3: Admin UI Authentication - ALREADY COMPLETE ✅

**Status:** Fully implemented and production-ready

### What's Implemented

After thorough codebase research, **Phase 3 (Admin UI Authentication) is already complete**. No additional work needed.

**Frontend Authentication:**
- ✅ Token storage in localStorage with automatic retrieval
- ✅ Login/Logout UI with user info display
- ✅ Protected content areas with auth state checking
- ✅ Automatic redirect to login on 401 responses
- ✅ Session expiration handling

**Backend Authentication:**
- ✅ Full OIDC/OAuth2 integration with Authentik
- ✅ Login endpoint (`/api/auth/login`)
- ✅ Callback endpoint (`/api/auth/callback`)
- ✅ Logout endpoint (`/api/auth/logout`)
- ✅ Current user endpoint (`/api/auth/me`)

**Protected Routes:**
- ✅ All 16 route files use `Depends(get_current_user)`
- ✅ Role-based access control (viewer/support/operator/owner)
- ✅ Comprehensive audit logging with HMAC signatures

**See:** `thoughts/shared/research/2025-11-15-admin-ui-authentication.md` for complete research findings.

---

## Summary

This plan now covers **2 phases** (down from 3):

- **Phase 1:** Conversation History Support (1-2 hours) ✅ Ready to implement
- **Phase 2:** Performance Metrics Persistence (2-3 hours) ✅ Ready to implement
- **Phase 3:** Admin UI Authentication ~~(4-6 hours)~~ ✅ **ALREADY COMPLETE**

**Updated Total Time:** 3-5 hours (down from 7-11 hours)

**Next Steps:**
1. Implement Phase 1 (Conversation History)
2. Verify Phase 1 success criteria
3. Implement Phase 2 (Performance Metrics)
4. Verify Phase 2 success criteria
5. System ready for production deployment

---

**Plan Created:** November 15, 2025  
**Plan Updated:** November 15, 2025 (Removed Phase 3 - already complete)  
**Status:** Ready for implementation
