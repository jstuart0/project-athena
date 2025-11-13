# Orchestrator and Gateway Implementation Plan

## Overview

This plan details the implementation of the two most critical missing components in Project Athena Phase 1: the **Orchestrator** (LangGraph state machine for request coordination) and the **Gateway** (OpenAI-compatible API entry point). Without these components, the system cannot function end-to-end.

**Created:** 2025-11-13
**Status:** Ready for Implementation
**Estimated Time:** 30-40 hours total (20-25h Orchestrator, 10-15h Gateway)
**Priority:** CRITICAL - These are the primary blockers for Phase 1 completion

## Current State Analysis

### What Exists

**Complete and Working:**
- ✅ 3 RAG Services (Weather, Airports, Sports) - Fully implemented at `src/rag/`
- ✅ Shared utilities (HA client, Ollama client, Cache, Logging) at `src/shared/`
- ✅ Docker Compose deployment configuration at `deployment/mac-studio/`
- ✅ Admin interface (bonus feature) at `admin/`
- ✅ LiteLLM gateway configuration at `src/gateway/config.yaml`

**Missing (Critical Gaps):**
- ❌ Orchestrator implementation (`src/orchestrator/` has only empty files)
- ❌ Gateway service code (`src/gateway/` has only config.yaml)

### Key Discoveries from Research

1. **RAG Services Pattern:** FastAPI microservices with Redis caching, health checks, structured logging
2. **Shared Utilities:** Async clients for HA, Ollama, and Redis with proper lifecycle management
3. **Deployment:** Docker Compose on Mac Studio (services) and Mac mini (data layer)
4. **Configuration:** Environment-based with sensible defaults

## Desired End State

### Success Criteria

**Orchestrator Complete When:**
- ✅ LangGraph state machine with 7 nodes (classify, route_control, route_info, retrieve, synthesize, validate, finalize)
- ✅ FastAPI endpoints: `/query` (POST), `/health` (GET), `/metrics` (GET)
- ✅ Integrates with all 3 RAG services via HTTP
- ✅ Calls Ollama for LLM inference (classification and synthesis)
- ✅ Direct HA API calls for device control
- ✅ Redis caching for conversation state
- ✅ Structured logging with request tracing
- ✅ Proper error handling and fallbacks
- ✅ Docker container starts and passes health checks

**Gateway Complete When:**
- ✅ OpenAI-compatible `/v1/chat/completions` endpoint
- ✅ Routes requests to orchestrator for Athena-specific queries
- ✅ Falls back to direct Ollama for general queries
- ✅ Implements streaming responses
- ✅ API key validation (optional for Phase 1)
- ✅ Request/response logging
- ✅ Prometheus metrics export
- ✅ Health check endpoint
- ✅ Docker container starts and integrates with HA

### Performance Targets

- Control queries (HA direct): ≤3.5s P95
- Knowledge queries (RAG + LLM): ≤5.5s P95
- Gateway overhead: ≤100ms
- Orchestrator routing: ≤200ms

## What We're NOT Doing

**Out of scope for this implementation:**
- ❌ Multi-intent handling (single intent only)
- ❌ Cross-model validation (single model inference)
- ❌ Advanced caching strategies (simple TTL caching only)
- ❌ Guest mode automation (manual mode switching)
- ❌ Voice ID/profiles (no user identification)
- ❌ SMS/email sharing (stubbed endpoints only)
- ❌ Kubernetes deployment (Docker Compose only)
- ❌ Production monitoring/alerting (basic metrics only)

## Implementation Approach

### Architecture Decisions

1. **Gateway Implementation:** Custom FastAPI instead of LiteLLM proxy
   - **Rationale:** LiteLLM is great for model routing but we need custom logic for Athena-specific routing
   - **Approach:** Implement OpenAI-compatible endpoints that route to orchestrator

2. **Orchestrator State Machine:** LangGraph with explicit state management
   - **Rationale:** Clear flow visualization, easier debugging, built-in state persistence
   - **Approach:** Define state schema, implement nodes as async functions

3. **Communication Pattern:** HTTP/REST between services
   - **Rationale:** Simple, debuggable, works with existing RAG services
   - **Approach:** Use httpx.AsyncClient for all service calls

4. **Error Handling:** Graceful degradation with fallbacks
   - **Rationale:** Better user experience than hard failures
   - **Approach:** Try primary path → fallback → error message

## Phase 1: Gateway Implementation (10-15 hours)

### 1.1: Core Gateway Structure

**File: `src/gateway/main.py`**

```python
"""
Project Athena Gateway Service

OpenAI-compatible API that routes requests to the orchestrator for
Athena-specific queries or falls back to Ollama for general queries.
"""

import os
import json
import time
import uuid
from typing import AsyncIterator, Dict, Any, List, Optional
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# Add to Python path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.logging_config import configure_logging
from shared.ollama_client import OllamaClient

# Configure logging
logger = configure_logging("gateway")

# Metrics
request_counter = Counter(
    'gateway_requests_total',
    'Total requests to gateway',
    ['endpoint', 'status']
)
request_duration = Histogram(
    'gateway_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint']
)

# Global clients
orchestrator_client: Optional[httpx.AsyncClient] = None
ollama_client: Optional[OllamaClient] = None

# Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8001")
OLLAMA_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:11434")
API_KEY = os.getenv("GATEWAY_API_KEY", "dummy-key")  # Optional for Phase 1

# Model mapping (OpenAI -> Ollama)
MODEL_MAPPING = {
    "gpt-3.5-turbo": "phi3:mini",
    "gpt-4": "llama3.1:8b",
    "gpt-4-32k": "llama3.1:8b",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global orchestrator_client, ollama_client

    # Startup
    logger.info("Starting Gateway service")
    orchestrator_client = httpx.AsyncClient(
        base_url=ORCHESTRATOR_URL,
        timeout=60.0
    )
    ollama_client = OllamaClient(url=OLLAMA_URL)

    # Check orchestrator health
    try:
        response = await orchestrator_client.get("/health")
        if response.status_code == 200:
            logger.info("Orchestrator is healthy")
        else:
            logger.warning(f"Orchestrator unhealthy: {response.status_code}")
    except Exception as e:
        logger.warning(f"Orchestrator not available: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Gateway service")
    if orchestrator_client:
        await orchestrator_client.aclose()
    if ollama_client:
        await ollama_client.close()

app = FastAPI(
    title="Athena Gateway",
    description="OpenAI-compatible API gateway for Project Athena",
    version="1.0.0",
    lifespan=lifespan
)

# Request/Response models (OpenAI-compatible)
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Optional name")

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model to use")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")
    top_p: float = Field(1.0, ge=0, le=1, description="Top-p sampling")
    n: int = Field(1, ge=1, le=10, description="Number of completions")
    stream: bool = Field(False, description="Stream response")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    max_tokens: Optional[int] = Field(None, description="Max tokens to generate")
    presence_penalty: float = Field(0, ge=-2, le=2)
    frequency_penalty: float = Field(0, ge=-2, le=2)
    user: Optional[str] = Field(None, description="User identifier")

class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Dict[str, int]

# API key validation (optional for Phase 1)
async def validate_api_key(request: Request):
    """Validate API key if configured."""
    if API_KEY == "dummy-key":
        return True  # Skip validation in dev

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    token = auth_header.replace("Bearer ", "")
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True

def is_athena_query(messages: List[ChatMessage]) -> bool:
    """
    Determine if this query should be routed to Athena orchestrator.

    Athena handles:
    - Home automation control (lights, switches, climate)
    - Weather queries
    - Airport/flight information
    - Sports information
    - Location-specific queries (Baltimore context)
    """
    # Get the last user message
    last_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            last_user_msg = msg.content.lower()
            break

    if not last_user_msg:
        return False

    # Athena-specific patterns
    athena_patterns = [
        # Home control
        "turn on", "turn off", "set", "dim", "brighten",
        "lights", "switch", "temperature", "thermostat",
        # Weather
        "weather", "forecast", "rain", "snow", "temperature outside",
        # Airports/flights
        "airport", "flight", "delay", "departure", "arrival",
        "bwi", "dca", "iad", "phl", "jfk", "lga", "ewr",
        # Sports
        "game", "score", "ravens", "orioles", "team",
        # Location context
        "baltimore", "home", "office", "bedroom", "kitchen"
    ]

    return any(pattern in last_user_msg for pattern in athena_patterns)

async def route_to_orchestrator(
    request: ChatCompletionRequest
) -> ChatCompletionResponse:
    """Route request to Athena orchestrator."""
    try:
        # Extract user message
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content

        # Call orchestrator
        with request_duration.labels(endpoint="orchestrator").time():
            response = await orchestrator_client.post(
                "/query",
                json={
                    "query": user_message,
                    "mode": "owner",  # Default to owner mode
                    "room": "unknown",  # Could be enriched later
                    "temperature": request.temperature,
                    "model": MODEL_MAPPING.get(request.model, "phi3:mini")
                }
            )
            response.raise_for_status()

        result = response.json()

        # Format as OpenAI response
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=result.get("answer", "I couldn't process that request.")
                    ),
                    finish_reason="stop"
                )
            ],
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(result.get("answer", "").split()),
                "total_tokens": len(user_message.split()) + len(result.get("answer", "").split())
            }
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"Orchestrator error: {e}")
        raise HTTPException(status_code=502, detail="Orchestrator error")
    except Exception as e:
        logger.error(f"Failed to route to orchestrator: {e}", exc_info=True)
        # Fall back to Ollama
        return await route_to_ollama(request)

async def route_to_ollama(
    request: ChatCompletionRequest
) -> ChatCompletionResponse:
    """Route request directly to Ollama."""
    try:
        # Map model name
        ollama_model = MODEL_MAPPING.get(request.model, request.model)

        # Convert messages format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # Call Ollama
        with request_duration.labels(endpoint="ollama").time():
            response_text = ""
            async for chunk in ollama_client.chat(
                model=ollama_model,
                messages=messages,
                temperature=request.temperature,
                stream=False
            ):
                if chunk.get("done"):
                    response_text = chunk.get("message", {}).get("content", "")
                    break

        # Format as OpenAI response
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response_text
                    ),
                    finish_reason="stop"
                )
            ],
            usage={
                "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
                "completion_tokens": len(response_text.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(response_text.split())
            }
        )

    except Exception as e:
        logger.error(f"Ollama error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="LLM service error")

async def stream_response(request: ChatCompletionRequest) -> AsyncIterator[str]:
    """Stream response from Ollama (orchestrator doesn't support streaming yet)."""
    try:
        # Only Ollama supports streaming for now
        ollama_model = MODEL_MAPPING.get(request.model, request.model)
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # Stream from Ollama
        async for chunk in ollama_client.chat(
            model=ollama_model,
            messages=messages,
            temperature=request.temperature,
            stream=True
        ):
            if not chunk.get("done"):
                # Format as OpenAI streaming chunk
                data = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": chunk.get("message", {}).get("content", "")
                        },
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"

        # Send final chunk
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    _: bool = Depends(validate_api_key)
):
    """
    OpenAI-compatible chat completions endpoint.
    Routes to orchestrator for Athena queries, Ollama for general queries.
    """
    request_counter.labels(endpoint="chat_completions", status="started").inc()

    try:
        # Handle streaming
        if request.stream:
            request_counter.labels(endpoint="chat_completions", status="streaming").inc()
            return StreamingResponse(
                stream_response(request),
                media_type="text/event-stream"
            )

        # Route based on query type
        if is_athena_query(request.messages):
            logger.info("Routing to orchestrator")
            response = await route_to_orchestrator(request)
        else:
            logger.info("Routing to Ollama")
            response = await route_to_ollama(request)

        request_counter.labels(endpoint="chat_completions", status="success").inc()
        return response

    except HTTPException:
        request_counter.labels(endpoint="chat_completions", status="error").inc()
        raise
    except Exception as e:
        request_counter.labels(endpoint="chat_completions", status="error").inc()
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "gateway",
        "version": "1.0.0"
    }

    # Check orchestrator
    try:
        response = await orchestrator_client.get("/health")
        health["orchestrator"] = response.status_code == 200
    except:
        health["orchestrator"] = False

    # Check Ollama
    try:
        models = await ollama_client.list_models()
        health["ollama"] = len(models.get("models", [])) > 0
    except:
        health["ollama"] = False

    # Overall health
    if not health["orchestrator"] and not health["ollama"]:
        health["status"] = "unhealthy"
    elif not health["orchestrator"] or not health["ollama"]:
        health["status"] = "degraded"

    return health

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "athena"},
            {"id": "gpt-4", "object": "model", "owned_by": "athena"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 1.2: Gateway Requirements and Docker Configuration

**File: `src/gateway/requirements.txt`**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
httpx>=0.24.0
pydantic>=2.0.0
prometheus-client>=0.19.0
python-dotenv>=1.0.0
```

**File: `src/gateway/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 1.3: Gateway Testing

**File: `src/gateway/test_gateway.py`**

```python
"""Test suite for gateway service."""

import pytest
import httpx
import asyncio
from unittest.mock import AsyncMock, patch

from main import app, is_athena_query, ChatMessage

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "gateway"

def test_is_athena_query():
    """Test Athena query detection."""
    # Should route to Athena
    athena_messages = [
        ChatMessage(role="user", content="Turn on the office lights"),
        ChatMessage(role="user", content="What's the weather in Baltimore?"),
        ChatMessage(role="user", content="Any delays at BWI airport?"),
        ChatMessage(role="user", content="When is the next Ravens game?"),
    ]

    for msg in athena_messages:
        assert is_athena_query([msg]) == True

    # Should not route to Athena
    general_messages = [
        ChatMessage(role="user", content="What is quantum physics?"),
        ChatMessage(role="user", content="Write a poem about nature"),
        ChatMessage(role="user", content="Explain machine learning"),
    ]

    for msg in general_messages:
        assert is_athena_query([msg]) == False

@pytest.mark.asyncio
async def test_chat_completion_routing():
    """Test request routing logic."""
    # This would need mocking of orchestrator_client and ollama_client
    pass  # Implementation details omitted for brevity
```

## Phase 2: Orchestrator Implementation (20-25 hours)

### 2.1: Core Orchestrator Structure with LangGraph

**File: `src/orchestrator/main.py`**

```python
"""
Project Athena Orchestrator Service

LangGraph-based state machine that coordinates between:
- Intent classification
- Home Assistant control
- RAG services for information retrieval
- LLM synthesis
- Response validation
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Literal
from contextlib import asynccontextmanager
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# Add to Python path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.logging_config import configure_logging
from shared.ha_client import HomeAssistantClient
from shared.ollama_client import OllamaClient
from shared.cache import CacheClient

# Configure logging
logger = configure_logging("orchestrator")

# Metrics
request_counter = Counter(
    'orchestrator_requests_total',
    'Total requests to orchestrator',
    ['intent', 'status']
)
request_duration = Histogram(
    'orchestrator_request_duration_seconds',
    'Request duration in seconds',
    ['intent']
)
node_duration = Histogram(
    'orchestrator_node_duration_seconds',
    'Node execution duration in seconds',
    ['node']
)

# Global clients
ha_client: Optional[HomeAssistantClient] = None
ollama_client: Optional[OllamaClient] = None
cache_client: Optional[CacheClient] = None
rag_clients: Dict[str, httpx.AsyncClient] = {}

# Configuration
WEATHER_SERVICE_URL = os.getenv("RAG_WEATHER_URL", "http://localhost:8010")
AIRPORTS_SERVICE_URL = os.getenv("RAG_AIRPORTS_URL", "http://localhost:8011")
SPORTS_SERVICE_URL = os.getenv("RAG_SPORTS_URL", "http://localhost:8012")
OLLAMA_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:11434")

# Intent categories
class IntentCategory(str, Enum):
    CONTROL = "control"  # Home Assistant control
    WEATHER = "weather"  # Weather information
    AIRPORTS = "airports"  # Airport/flight info
    SPORTS = "sports"  # Sports information
    GENERAL_INFO = "general_info"  # General knowledge
    UNKNOWN = "unknown"  # Unclear intent

# Model tiers
class ModelTier(str, Enum):
    SMALL = "phi3:mini"  # Quick responses
    MEDIUM = "llama3.1:8b"  # Standard queries
    LARGE = "llama3.1:8b"  # Complex reasoning (same as medium for Phase 1)

# Orchestrator state
class OrchestratorState(BaseModel):
    """State that flows through the LangGraph state machine."""

    # Input
    query: str = Field(..., description="User's query")
    mode: Literal["owner", "guest"] = Field("owner", description="User mode")
    room: str = Field("unknown", description="Room/zone identifier")
    temperature: float = Field(0.7, description="LLM temperature")

    # Classification
    intent: Optional[IntentCategory] = None
    confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)

    # Model selection
    model_tier: Optional[ModelTier] = None

    # Retrieved data
    retrieved_data: Dict[str, Any] = Field(default_factory=dict)
    data_source: Optional[str] = None

    # Response
    answer: Optional[str] = None
    citations: List[str] = Field(default_factory=list)

    # Validation
    validation_passed: bool = True
    validation_reason: Optional[str] = None

    # Metadata
    request_id: str = Field(default_factory=lambda: hashlib.md5(str(time.time()).encode()).hexdigest()[:8])
    start_time: float = Field(default_factory=time.time)
    node_timings: Dict[str, float] = Field(default_factory=dict)
    error: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global ha_client, ollama_client, cache_client, rag_clients

    # Startup
    logger.info("Starting Orchestrator service")

    # Initialize clients
    ha_client = HomeAssistantClient()
    ollama_client = OllamaClient(url=OLLAMA_URL)
    cache_client = CacheClient()

    # Initialize RAG service clients
    rag_clients = {
        "weather": httpx.AsyncClient(base_url=WEATHER_SERVICE_URL, timeout=30.0),
        "airports": httpx.AsyncClient(base_url=AIRPORTS_SERVICE_URL, timeout=30.0),
        "sports": httpx.AsyncClient(base_url=SPORTS_SERVICE_URL, timeout=30.0),
    }

    # Check service health
    for name, client in rag_clients.items():
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                logger.info(f"RAG service {name} is healthy")
            else:
                logger.warning(f"RAG service {name} unhealthy: {response.status_code}")
        except Exception as e:
            logger.warning(f"RAG service {name} not available: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Orchestrator service")
    if ha_client:
        await ha_client.close()
    if ollama_client:
        await ollama_client.close()
    if cache_client:
        await cache_client.close()
    for client in rag_clients.values():
        await client.aclose()

app = FastAPI(
    title="Athena Orchestrator",
    description="LangGraph-based request coordination for Project Athena",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# Node Implementations
# ============================================================================

async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """
    Classify user intent using LLM.
    Determines: control vs info, specific category, entities.
    """
    start = time.time()

    try:
        # Build classification prompt
        classification_prompt = f"""Classify the following user query into a category and extract entities.

Categories:
- control: Home automation commands (lights, switches, thermostats, scenes)
- weather: Weather information requests
- airports: Airport or flight information
- sports: Sports scores, games, teams
- general_info: Other information requests
- unknown: Unclear or ambiguous

Query: "{state.query}"

Respond in JSON format:
{{
    "intent": "category_name",
    "confidence": 0.0-1.0,
    "entities": {{
        "device": "optional device name",
        "location": "optional location",
        "team": "optional sports team",
        "airport": "optional airport code"
    }}
}}"""

        # Use small model for classification
        messages = [
            {"role": "system", "content": "You are an intent classifier. Respond only with valid JSON."},
            {"role": "user", "content": classification_prompt}
        ]

        response_text = ""
        async for chunk in ollama_client.chat(
            model=ModelTier.SMALL,
            messages=messages,
            temperature=0.3,  # Lower temperature for consistent classification
            stream=False
        ):
            if chunk.get("done"):
                response_text = chunk.get("message", {}).get("content", "")
                break

        # Parse classification result
        try:
            result = json.loads(response_text)
            state.intent = IntentCategory(result.get("intent", "unknown"))
            state.confidence = float(result.get("confidence", 0.5))
            state.entities = result.get("entities", {})
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse classification: {e}")
            # Fallback to pattern matching
            state.intent = _pattern_based_classification(state.query)
            state.confidence = 0.7

        logger.info(f"Classified query as {state.intent} with confidence {state.confidence}")

    except Exception as e:
        logger.error(f"Classification error: {e}", exc_info=True)
        state.intent = IntentCategory.UNKNOWN
        state.confidence = 0.0
        state.error = f"Classification failed: {str(e)}"

    state.node_timings["classify"] = time.time() - start
    return state

def _pattern_based_classification(query: str) -> IntentCategory:
    """Fallback pattern-based classification."""
    query_lower = query.lower()

    # Control patterns
    control_patterns = [
        "turn on", "turn off", "set", "dim", "brighten",
        "lights", "switch", "temperature", "thermostat", "scene"
    ]
    if any(p in query_lower for p in control_patterns):
        return IntentCategory.CONTROL

    # Weather patterns
    if any(p in query_lower for p in ["weather", "forecast", "rain", "snow", "temperature outside"]):
        return IntentCategory.WEATHER

    # Airport patterns
    if any(p in query_lower for p in ["airport", "flight", "delay", "bwi", "dca", "iad"]):
        return IntentCategory.AIRPORTS

    # Sports patterns
    if any(p in query_lower for p in ["game", "score", "ravens", "orioles", "team"]):
        return IntentCategory.SPORTS

    return IntentCategory.GENERAL_INFO

async def route_control_node(state: OrchestratorState) -> OrchestratorState:
    """
    Handle home automation control commands via Home Assistant API.
    """
    start = time.time()

    try:
        # Extract device and action from entities or query
        device = state.entities.get("device")
        query_lower = state.query.lower()

        # Simple pattern matching for common commands
        if "turn on" in query_lower:
            action = "turn_on"
        elif "turn off" in query_lower:
            action = "turn_off"
        else:
            action = None

        if not device:
            # Try to extract device from query
            if "lights" in query_lower or "light" in query_lower:
                device = "light.office_ceiling"  # Default for demo
            elif "switch" in query_lower:
                device = "switch.office_fan"  # Default for demo

        if device and action:
            # Call Home Assistant service
            domain = device.split(".")[0]
            result = await ha_client.call_service(
                domain=domain,
                service=action,
                service_data={"entity_id": device}
            )

            state.answer = f"Done! I've turned {'on' if action == 'turn_on' else 'off'} the {device.replace('_', ' ').replace('.', ' ')}."
            state.retrieved_data = {"ha_response": result}

        else:
            # Need more information
            state.answer = "I understand you want to control something, but I need more details. Which device would you like to control?"

        logger.info(f"Control command executed: {device} - {action}")

    except Exception as e:
        logger.error(f"Control execution error: {e}", exc_info=True)
        state.answer = "I encountered an error while trying to control that device. Please try again."
        state.error = str(e)

    state.node_timings["route_control"] = time.time() - start
    return state

async def route_info_node(state: OrchestratorState) -> OrchestratorState:
    """
    Select appropriate model tier for information queries.
    """
    start = time.time()

    # Estimate complexity based on query length and intent
    query_length = len(state.query.split())

    if state.intent == IntentCategory.GENERAL_INFO and query_length > 20:
        state.model_tier = ModelTier.LARGE
    elif state.intent in [IntentCategory.WEATHER, IntentCategory.SPORTS]:
        state.model_tier = ModelTier.SMALL
    else:
        state.model_tier = ModelTier.MEDIUM

    logger.info(f"Selected model tier: {state.model_tier}")

    state.node_timings["route_info"] = time.time() - start
    return state

async def retrieve_node(state: OrchestratorState) -> OrchestratorState:
    """
    Retrieve information from appropriate RAG service.
    """
    start = time.time()

    try:
        if state.intent == IntentCategory.WEATHER:
            # Call weather service
            location = state.entities.get("location", "Baltimore, MD")
            client = rag_clients["weather"]

            response = await client.get(
                "/weather/current",
                params={"location": location}
            )
            response.raise_for_status()

            state.retrieved_data = response.json()
            state.data_source = "OpenWeatherMap"
            state.citations.append(f"Weather data from OpenWeatherMap for {location}")

        elif state.intent == IntentCategory.AIRPORTS:
            # Call airports service
            airport = state.entities.get("airport", "BWI")
            client = rag_clients["airports"]

            response = await client.get(f"/airports/{airport}")
            response.raise_for_status()

            state.retrieved_data = response.json()
            state.data_source = "FlightAware"
            state.citations.append(f"Flight data from FlightAware for {airport}")

        elif state.intent == IntentCategory.SPORTS:
            # Call sports service
            team = state.entities.get("team", "Ravens")
            client = rag_clients["sports"]

            # Search for team
            search_response = await client.get(
                "/sports/teams/search",
                params={"query": team}
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            if search_data.get("teams"):
                team_id = search_data["teams"][0]["idTeam"]

                # Get next event
                events_response = await client.get(f"/sports/events/{team_id}/next")
                events_response.raise_for_status()

                state.retrieved_data = events_response.json()
                state.data_source = "TheSportsDB"
                state.citations.append(f"Sports data from TheSportsDB for {team}")

        else:
            # No RAG retrieval needed for general info
            state.retrieved_data = {}
            state.data_source = "LLM knowledge"

        logger.info(f"Retrieved data from {state.data_source}")

    except httpx.HTTPStatusError as e:
        logger.error(f"RAG service error: {e}")
        state.error = f"Failed to retrieve data: {str(e)}"
    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        state.error = f"Retrieval failed: {str(e)}"

    state.node_timings["retrieve"] = time.time() - start
    return state

async def synthesize_node(state: OrchestratorState) -> OrchestratorState:
    """
    Generate natural language response using LLM with retrieved data.
    """
    start = time.time()

    try:
        # Build synthesis prompt with retrieved data
        if state.retrieved_data:
            context = json.dumps(state.retrieved_data, indent=2)
            synthesis_prompt = f"""Answer the following question using the provided context.

Question: {state.query}

Context Data:
{context}

Instructions:
1. Provide a natural, conversational response
2. Include specific details from the context
3. Be concise but informative
4. If the context doesn't contain enough information, say so

Response:"""
        else:
            synthesis_prompt = state.query

        # Use selected model tier
        messages = [
            {"role": "system", "content": "You are Athena, a helpful home assistant. Provide clear, concise answers."},
            {"role": "user", "content": synthesis_prompt}
        ]

        response_text = ""
        async for chunk in ollama_client.chat(
            model=state.model_tier or ModelTier.MEDIUM,
            messages=messages,
            temperature=state.temperature,
            stream=False
        ):
            if chunk.get("done"):
                response_text = chunk.get("message", {}).get("content", "")
                break

        state.answer = response_text

        # Add data attribution
        if state.citations:
            state.answer += f"\n\n_Source: {', '.join(state.citations)}_"

        logger.info(f"Synthesized response using {state.model_tier}")

    except Exception as e:
        logger.error(f"Synthesis error: {e}", exc_info=True)
        state.answer = "I apologize, but I'm having trouble generating a response. Please try again."
        state.error = f"Synthesis failed: {str(e)}"

    state.node_timings["synthesize"] = time.time() - start
    return state

async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """
    Validate the generated response for quality and safety.
    """
    start = time.time()

    # Basic validation for Phase 1
    if not state.answer or len(state.answer) < 10:
        state.validation_passed = False
        state.validation_reason = "Response too short"
    elif len(state.answer) > 2000:
        state.validation_passed = False
        state.validation_reason = "Response too long"
    elif "error" in state.answer.lower() and "sorry" in state.answer.lower():
        state.validation_passed = False
        state.validation_reason = "Response indicates error"
    else:
        state.validation_passed = True

    if not state.validation_passed:
        logger.warning(f"Validation failed: {state.validation_reason}")

    state.node_timings["validate"] = time.time() - start
    return state

async def finalize_node(state: OrchestratorState) -> OrchestratorState:
    """
    Prepare final response with fallbacks for validation failures.
    """
    start = time.time()

    if not state.validation_passed:
        # Provide fallback response
        if state.error:
            state.answer = "I encountered an issue processing your request. Please try rephrasing your question."
        else:
            state.answer = "I'm not confident in my response. Could you please rephrase your question?"

    # Calculate total processing time
    total_time = time.time() - state.start_time
    logger.info(
        f"Request {state.request_id} completed in {total_time:.2f}s",
        extra={
            "request_id": state.request_id,
            "intent": state.intent,
            "total_time": total_time,
            "node_timings": state.node_timings
        }
    )

    # Cache conversation context for follow-ups
    await cache_client.set(
        f"conversation:{state.request_id}",
        {
            "query": state.query,
            "intent": state.intent,
            "answer": state.answer,
            "timestamp": time.time()
        },
        ttl=3600  # 1 hour TTL
    )

    state.node_timings["finalize"] = time.time() - start
    return state

# ============================================================================
# LangGraph State Machine
# ============================================================================

def create_orchestrator_graph() -> StateGraph:
    """Create the LangGraph state machine."""

    # Initialize graph with state schema
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("route_control", route_control_node)
    graph.add_node("route_info", route_info_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("validate", validate_node)
    graph.add_node("finalize", finalize_node)

    # Define edges
    graph.set_entry_point("classify")

    # Conditional routing after classification
    def route_after_classify(state: OrchestratorState) -> str:
        if state.intent == IntentCategory.CONTROL:
            return "route_control"
        elif state.intent == IntentCategory.UNKNOWN:
            return "finalize"  # Skip to finalize for unknown intents
        else:
            return "route_info"

    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "route_control": "route_control",
            "route_info": "route_info",
            "finalize": "finalize"
        }
    )

    # Control path
    graph.add_edge("route_control", "finalize")

    # Info path
    graph.add_edge("route_info", "retrieve")
    graph.add_edge("retrieve", "synthesize")
    graph.add_edge("synthesize", "validate")
    graph.add_edge("validate", "finalize")

    # End
    graph.add_edge("finalize", END)

    return graph.compile()

# Create global graph instance
orchestrator_graph = None

# ============================================================================
# API Endpoints
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="User's query")
    mode: Literal["owner", "guest"] = Field("owner", description="User mode")
    room: str = Field("unknown", description="Room identifier")
    temperature: float = Field(0.7, ge=0, le=2, description="LLM temperature")
    model: Optional[str] = Field(None, description="Preferred model")

class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str = Field(..., description="Generated response")
    intent: str = Field(..., description="Detected intent category")
    confidence: float = Field(..., description="Classification confidence")
    citations: List[str] = Field(default_factory=list, description="Data sources")
    request_id: str = Field(..., description="Request tracking ID")
    processing_time: float = Field(..., description="Total processing time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a user query through the orchestrator state machine.
    """
    global orchestrator_graph

    # Initialize graph if needed
    if orchestrator_graph is None:
        orchestrator_graph = create_orchestrator_graph()

    # Track request
    request_counter.labels(intent="unknown", status="started").inc()

    try:
        # Create initial state
        initial_state = OrchestratorState(
            query=request.query,
            mode=request.mode,
            room=request.room,
            temperature=request.temperature
        )

        # Run through state machine
        with request_duration.labels(intent="processing").time():
            final_state = await orchestrator_graph.ainvoke(initial_state)

        # Track metrics
        request_counter.labels(
            intent=final_state.intent or "unknown",
            status="success"
        ).inc()

        # Build response
        return QueryResponse(
            answer=final_state.answer or "I couldn't process that request.",
            intent=final_state.intent or IntentCategory.UNKNOWN,
            confidence=final_state.confidence,
            citations=final_state.citations,
            request_id=final_state.request_id,
            processing_time=time.time() - final_state.start_time,
            metadata={
                "model_used": final_state.model_tier,
                "data_source": final_state.data_source,
                "validation_passed": final_state.validation_passed,
                "node_timings": final_state.node_timings
            }
        )

    except Exception as e:
        logger.error(f"Query processing error: {e}", exc_info=True)
        request_counter.labels(intent="unknown", status="error").inc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0",
        "components": {}
    }

    # Check Home Assistant
    try:
        ha_healthy = await ha_client.health_check() if ha_client else False
        health["components"]["home_assistant"] = ha_healthy
    except:
        health["components"]["home_assistant"] = False

    # Check Ollama
    try:
        models = await ollama_client.list_models() if ollama_client else {}
        health["components"]["ollama"] = len(models.get("models", [])) > 0
    except:
        health["components"]["ollama"] = False

    # Check Redis
    try:
        await cache_client.client.ping() if cache_client else False
        health["components"]["redis"] = True
    except:
        health["components"]["redis"] = False

    # Check RAG services
    for name, client in rag_clients.items():
        try:
            response = await client.get("/health")
            health["components"][f"rag_{name}"] = response.status_code == 200
        except:
            health["components"][f"rag_{name}"] = False

    # Determine overall health
    critical_components = ["ollama", "redis"]
    if not all(health["components"].get(c, False) for c in critical_components):
        health["status"] = "unhealthy"
    elif not all(health["components"].values()):
        health["status"] = "degraded"

    return health

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

### 2.2: Orchestrator Requirements and Docker Configuration

**File: `src/orchestrator/requirements.txt`**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
langgraph>=0.0.20
langchain>=0.1.0
httpx>=0.24.0
pydantic>=2.0.0
prometheus-client>=0.19.0
python-dotenv>=1.0.0
redis>=5.0.0
```

**File: `src/orchestrator/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8001

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

## Phase 3: Integration Testing (5 hours)

### 3.1: End-to-End Test Suite

**File: `tests/integration/test_orchestrator_gateway.py`**

```python
"""Integration tests for orchestrator and gateway."""

import pytest
import httpx
import asyncio

BASE_GATEWAY_URL = "http://localhost:8000"
BASE_ORCHESTRATOR_URL = "http://localhost:8001"

@pytest.mark.asyncio
async def test_health_endpoints():
    """Test both services are healthy."""
    async with httpx.AsyncClient() as client:
        # Gateway health
        gateway_health = await client.get(f"{BASE_GATEWAY_URL}/health")
        assert gateway_health.status_code == 200
        assert gateway_health.json()["service"] == "gateway"

        # Orchestrator health
        orch_health = await client.get(f"{BASE_ORCHESTRATOR_URL}/health")
        assert orch_health.status_code == 200
        assert orch_health.json()["service"] == "orchestrator"

@pytest.mark.asyncio
async def test_control_query_flow():
    """Test home control query through gateway to orchestrator."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Turn on the office lights"}
                ]
            },
            headers={"Authorization": "Bearer dummy-key"}
        )

        assert response.status_code == 200
        result = response.json()
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "turn" in result["choices"][0]["message"]["content"].lower()

@pytest.mark.asyncio
async def test_weather_query_flow():
    """Test weather query through full stack."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "user", "content": "What's the weather in Baltimore?"}
                ]
            },
            headers={"Authorization": "Bearer dummy-key"}
        )

        assert response.status_code == 200
        result = response.json()
        content = result["choices"][0]["message"]["content"].lower()

        # Should mention Baltimore or weather terms
        assert "baltimore" in content or "weather" in content or "temperature" in content

@pytest.mark.asyncio
async def test_direct_orchestrator_query():
    """Test direct orchestrator query."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_ORCHESTRATOR_URL}/query",
            json={
                "query": "What time is it?",
                "mode": "owner",
                "room": "office"
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert "answer" in result
        assert "intent" in result
        assert "request_id" in result

@pytest.mark.asyncio
async def test_streaming_response():
    """Test streaming response from gateway."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Tell me a joke"}
                ],
                "stream": True
            },
            headers={"Authorization": "Bearer dummy-key"}
        )

        assert response.status_code == 200
        # Check it's an event stream
        assert response.headers["content-type"] == "text/event-stream"

@pytest.mark.asyncio
async def test_latency_requirements():
    """Test that latency meets Phase 1 requirements."""
    import time

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Control query (target: ≤3.5s)
        start = time.time()
        response = await client.post(
            f"{BASE_ORCHESTRATOR_URL}/query",
            json={"query": "turn off bedroom lights"}
        )
        control_time = time.time() - start

        assert response.status_code == 200
        assert control_time <= 3.5, f"Control query took {control_time:.2f}s (target: ≤3.5s)"

        # Knowledge query (target: ≤5.5s)
        start = time.time()
        response = await client.post(
            f"{BASE_ORCHESTRATOR_URL}/query",
            json={"query": "what's the weather forecast for tomorrow?"}
        )
        knowledge_time = time.time() - start

        assert response.status_code == 200
        assert knowledge_time <= 5.5, f"Knowledge query took {knowledge_time:.2f}s (target: ≤5.5s)"
```

### 3.2: Deployment Script

**File: `scripts/deploy_orchestrator_gateway.sh`**

```bash
#!/bin/bash

set -e

echo "Deploying Orchestrator and Gateway services..."

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found, using defaults"
fi

# Build images
echo "Building Docker images..."
docker build -t athena-gateway:latest src/gateway/
docker build -t athena-orchestrator:latest src/orchestrator/

# Stop existing containers
echo "Stopping existing containers..."
docker stop athena-gateway athena-orchestrator 2>/dev/null || true
docker rm athena-gateway athena-orchestrator 2>/dev/null || true

# Start services
echo "Starting services..."

# Start orchestrator first (gateway depends on it)
docker run -d \
    --name athena-orchestrator \
    --restart unless-stopped \
    -p 8001:8001 \
    -e HA_URL="${HA_URL:-https://192.168.10.168:8123}" \
    -e HA_TOKEN="${HA_TOKEN}" \
    -e OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}" \
    -e REDIS_URL="${REDIS_URL:-redis://192.168.10.181:6379}" \
    -e RAG_WEATHER_URL="${RAG_WEATHER_URL:-http://host.docker.internal:8010}" \
    -e RAG_AIRPORTS_URL="${RAG_AIRPORTS_URL:-http://host.docker.internal:8011}" \
    -e RAG_SPORTS_URL="${RAG_SPORTS_URL:-http://host.docker.internal:8012}" \
    athena-orchestrator:latest

# Wait for orchestrator to be ready
echo "Waiting for orchestrator to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8001/health &>/dev/null; then
        echo "Orchestrator is ready"
        break
    fi
    sleep 1
done

# Start gateway
docker run -d \
    --name athena-gateway \
    --restart unless-stopped \
    -p 8000:8000 \
    -e ORCHESTRATOR_SERVICE_URL="${ORCHESTRATOR_SERVICE_URL:-http://host.docker.internal:8001}" \
    -e LLM_SERVICE_URL="${LLM_SERVICE_URL:-http://host.docker.internal:11434}" \
    -e GATEWAY_API_KEY="${GATEWAY_API_KEY:-dummy-key}" \
    athena-gateway:latest

# Wait for gateway to be ready
echo "Waiting for gateway to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health &>/dev/null; then
        echo "Gateway is ready"
        break
    fi
    sleep 1
done

# Run health checks
echo "Running health checks..."
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8001/health | jq .

echo "✅ Orchestrator and Gateway deployed successfully!"
echo ""
echo "Next steps:"
echo "1. Test gateway: curl -X POST http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\":\"gpt-3.5-turbo\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"
echo "2. Test orchestrator: curl -X POST http://localhost:8001/query -H 'Content-Type: application/json' -d '{\"query\":\"What is the weather?\"}'"
echo "3. Configure Home Assistant to use http://192.168.10.167:8000/v1 as OpenAI endpoint"
echo "4. Run integration tests: pytest tests/integration/"
```

## Testing Strategy

### Unit Tests

**Orchestrator:**
- Test each node function independently
- Mock external services (HA, Ollama, RAG services)
- Verify state transitions
- Test error handling paths

**Gateway:**
- Test request routing logic
- Test OpenAI format compatibility
- Test streaming response generation
- Test API key validation

### Integration Tests

1. **End-to-end flows:**
   - Control query → HA action
   - Weather query → RAG → LLM → Response
   - Unknown query → Fallback response

2. **Performance tests:**
   - Measure latency for each query type
   - Verify P95 latency targets
   - Test concurrent request handling

3. **Failure scenarios:**
   - RAG service unavailable
   - Ollama timeout
   - Invalid requests
   - HA unreachable

## Monitoring and Observability

### Metrics (Prometheus)

**Gateway metrics:**
- `gateway_requests_total` - Request count by endpoint and status
- `gateway_request_duration_seconds` - Request latency histogram

**Orchestrator metrics:**
- `orchestrator_requests_total` - Request count by intent and status
- `orchestrator_request_duration_seconds` - Total request latency
- `orchestrator_node_duration_seconds` - Per-node execution time

### Logging

**Structured logging with:**
- Request IDs for tracing
- Intent classification results
- Service call durations
- Error details with stack traces

### Health Checks

Both services expose `/health` endpoints that check:
- Service status
- Dependency availability
- Component health (HA, Ollama, Redis, RAG services)

## Migration Notes

### From Current State

1. **Fix cache client methods:** The RAG services expect `connect()`/`disconnect()` methods that don't exist. Either:
   - Add these methods to `CacheClient` as no-ops
   - Update RAG services to use `close()` instead

2. **Environment variables:** Ensure all required environment variables are set:
   - `HA_TOKEN` - Get from thor cluster
   - API keys for weather, airports, sports

3. **Docker networking:** Use `host.docker.internal` for services running on Mac host

### Deprecation

Once implemented:
- Archive any Jetson-specific code
- Update documentation to reflect new architecture
- Remove references to deprecated components

## Success Criteria

### Automated Verification

- [ ] Gateway health check returns 200
- [ ] Orchestrator health check returns 200
- [ ] OpenAI-compatible endpoint works
- [ ] All 7 orchestrator nodes execute
- [ ] RAG services are called successfully
- [ ] Latency targets met (control ≤3.5s, knowledge ≤5.5s)
- [ ] Docker containers restart on failure
- [ ] Prometheus metrics exported
- [ ] Integration tests pass

### Manual Verification

- [ ] Home Assistant can use gateway as OpenAI conversation agent
- [ ] Voice queries work end-to-end through HA
- [ ] Control commands affect actual devices
- [ ] Weather queries return accurate data
- [ ] Sports queries return team information
- [ ] Error messages are user-friendly
- [ ] Logs show complete request flow

## References

- [Phase 1 Implementation Plan](2025-11-11-phase1-core-services-implementation.md)
- [Implementation Status Research](../research/2025-11-13-implementation-plan-vs-actual-reconciliation.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)

---

**Created:** 2025-11-13
**Status:** Ready for Implementation
**Priority:** CRITICAL - Primary blocker for Phase 1 completion