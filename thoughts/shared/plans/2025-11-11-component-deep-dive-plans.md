# Component Deep-Dive Technical Specifications

**Date:** 2025-11-11
**Status:** Planning - Part of Architecture Pivot
**Related:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)
- [Phase 1 Implementation Plan](2025-11-11-phase1-core-services-implementation.md)
- [Full Bootstrap Plan](2025-11-11-full-bootstrap-implementation.md)

---

## Executive Summary

This document provides **detailed technical specifications** for each core component of Project Athena's new architecture. Use this as a reference when implementing individual services.

**Components Covered:**
1. OpenAI-Compatible Gateway (LiteLLM)
2. LangGraph Orchestrator
3. RAG Services Architecture
4. Anti-Hallucination Validators
5. Share Service (Twilio + SMTP)
6. Vector Database (Qdrant)
7. Home Assistant Bridge

---

## Table of Contents

1. [Gateway: OpenAI-Compatible API](#1-gateway-openai-compatible-api)
2. [Orchestrator: LangGraph Flow](#2-orchestrator-langgraph-flow)
3. [RAG Services: Microservice Architecture](#3-rag-services-microservice-architecture)
4. [Validators: Anti-Hallucination System](#4-validators-anti-hallucination-system)
5. [Share Service: SMS and Email](#5-share-service-sms-and-email)
6. [Vector Database: Qdrant Setup](#6-vector-database-qdrant-setup)
7. [HA Bridge: Advanced Device Control](#7-ha-bridge-advanced-device-control)

---

## 1. Gateway: OpenAI-Compatible API

### Purpose

Provide OpenAI API-compatible endpoint for Home Assistant's OpenAI Conversation integration while routing to local Ollama models.

### Technology Choice: LiteLLM

**Why LiteLLM:**
- ✅ Pre-built OpenAI compatibility (no manual spec implementation)
- ✅ Model fallbacks and retries
- ✅ Built-in load balancing
- ✅ Prometheus metrics included
- ✅ Request/response logging
- ✅ Cost tracking (useful for monitoring even with local models)

### Configuration

**File:** `apps/gateway/config.yaml`
```yaml
model_list:
  # Small models (fast, simple queries)
  - model_name: athena-small
    litellm_params:
      model: ollama/phi3:mini-q8
      api_base: http://localhost:11434
      stream: true
      temperature: 0.3
      max_tokens: 500

  # Medium models (complex queries with RAG)
  - model_name: athena-medium
    litellm_params:
      model: ollama/llama3.1:8b-q4
      api_base: http://localhost:11434
      stream: true
      temperature: 0.3
      max_tokens: 1000

  # Large models (deep reasoning, optional)
  - model_name: athena-large
    litellm_params:
      model: ollama/llama3.1:13b-q4
      api_base: http://localhost:11434
      stream: true
      temperature: 0.4
      max_tokens: 1500

  # Default model (routes to medium)
  - model_name: gpt-3.5-turbo
    litellm_params:
      model: ollama/llama3.1:8b-q4
      api_base: http://localhost:11434

router_settings:
  # Round-robin if multiple replicas (future)
  routing_strategy: simple-shuffle

  # Retry on failure
  num_retries: 2
  retry_delay: 1

  # Timeout for Ollama
  timeout: 300  # 5 minutes max

  # Fallback chain
  fallbacks:
    - athena-small  # Try small model if medium fails
    - athena-medium  # Try medium if large fails

general_settings:
  # Master key for authentication
  master_key: ${LITELLM_MASTER_KEY}

  # Logging
  proxy_logging: true
  json_logs: true

  # Metrics
  success_callback: ["prometheus"]
  failure_callback: ["prometheus"]

  # Database for request logs (optional for Phase 1)
  # database_url: postgresql://litellm:password@postgres:5432/litellm

  # Caching (handled by Redis separately)
  cache: false
```

### API Endpoints

**Primary Endpoint:**
```
POST /v1/chat/completions
```

**Request Format (OpenAI-compatible):**
```json
{
  "model": "athena-medium",
  "messages": [
    {"role": "system", "content": "You are a helpful Baltimore property assistant."},
    {"role": "user", "content": "What's the weather in Baltimore?"}
  ],
  "temperature": 0.3,
  "max_tokens": 1000,
  "stream": false
}
```

**Response Format:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1699999999,
  "model": "athena-medium",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The current weather in Baltimore is..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  }
}
```

**Health Endpoint:**
```
GET /health
```

**Metrics Endpoint:**
```
GET /metrics  # Prometheus format
```

### Deployment

**Docker Compose:**
```yaml
services:
  gateway:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: athena-gateway
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      PORT: 8000
      OLLAMA_API_BASE: http://host.docker.internal:11434
    volumes:
      - ./apps/gateway/config.yaml:/app/config.yaml:ro
      - ./logs/gateway:/app/logs
    command: ["--config", "/app/config.yaml", "--port", "8000"]
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Monitoring

**Key Metrics:**
- `litellm_requests_total{model, status}` - Total requests per model
- `litellm_request_duration_seconds{model}` - Request latency histogram
- `litellm_tokens_total{model, type}` - Token usage (prompt, completion)
- `litellm_errors_total{model, error_type}` - Error counts

**Alerting Rules:**
```yaml
groups:
  - name: gateway_alerts
    rules:
      - alert: GatewayHighErrorRate
        expr: rate(litellm_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "Gateway error rate > 10%"

      - alert: GatewayHighLatency
        expr: histogram_quantile(0.95, litellm_request_duration_seconds) > 5
        for: 5m
        annotations:
          summary: "Gateway P95 latency > 5s"
```

---

## 2. Orchestrator: LangGraph Flow

### Purpose

Coordinate query processing through classify → route → retrieve → synthesize → validate → finalize pipeline.

### Technology: LangGraph

**Why LangGraph:**
- ✅ State-based workflow management
- ✅ Conditional routing (if/else logic)
- ✅ Built-in checkpointing and persistence
- ✅ Async execution
- ✅ Easy to visualize and debug

### Graph Structure

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  classify   │  Determine: control vs info vs complex
└──────┬──────┘  Extract: category (weather, airports, sports, etc.)
       │          Attach: room, mode (guest/owner)
       │
       ├───────────────┐
       │               │
       ▼               ▼
┌─────────────┐ ┌──────────────┐
│route_control│ │  route_info  │
│(HA direct)  │ │(model select)│
└──────┬──────┘ └──────┬───────┘
       │               │
       │               ▼
       │        ┌─────────────┐
       │        │  retrieve   │  Call RAG service
       │        └──────┬──────┘  Get data + citations
       │               │
       │               ▼
       │        ┌─────────────┐
       │        │ synthesize  │  LLM generates answer
       │        └──────┬──────┘  Include sources
       │               │
       │               ▼
       │        ┌─────────────┐
       │        │  validate   │  Anti-hallucination
       │        └──────┬──────┘  Policy checks
       │               │
       └───────┬───────┘
               │
               ▼
        ┌─────────────┐
        │  finalize   │  Prepare response
        └──────┬──────┘  Add metadata
               │
               ▼
        ┌─────────────┐
        │     END     │
        └─────────────┘
```

### State Definition

```python
from typing import TypedDict, List, Dict, Optional
from enum import Enum

class QueryCategory(str, Enum):
    CONTROL = "control"
    WEATHER = "weather"
    AIRPORTS = "airports"
    SPORTS = "sports"
    NEWS = "news"
    INFO = "info"
    COMPLEX = "complex"

class ModelTier(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class Mode(str, Enum):
    GUEST = "guest"
    OWNER = "owner"

class OrchestratorState(TypedDict):
    # Input
    query: str
    mode: Mode
    room: str
    device_id: str

    # Classification
    category: QueryCategory
    model_tier: ModelTier
    confidence: float

    # Retrieval
    retrieved_data: Optional[Dict]
    sources: List[Dict]
    retrieval_time_ms: float

    # Synthesis
    answer: str
    citations: List[Dict]
    synthesis_time_ms: float
    model_used: str

    # Validation
    validation_passed: bool
    validation_flags: List[str]

    # Metadata
    request_id: str
    timestamp: str
    latency_breakdown: Dict[str, float]
    error: Optional[str]
```

### Node Implementations

**1. Classify Node**
```python
async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """
    Classify query intent and category.

    Logic:
    1. Pattern matching for control commands (turn on/off, set, etc.)
    2. Keyword extraction for categories (weather, airport, sports)
    3. Confidence scoring
    4. Default to "info" if uncertain
    """
    import time
    start = time.time()

    query_lower = state['query'].lower()

    # Control patterns (high confidence)
    control_patterns = {
        'turn on', 'turn off', 'switch on', 'switch off',
        'set brightness', 'dim', 'brighten',
        'set temperature', 'heat', 'cool',
        'activate', 'deactivate', 'enable', 'disable'
    }

    if any(pattern in query_lower for pattern in control_patterns):
        state['category'] = QueryCategory.CONTROL
        state['confidence'] = 0.95
        state['model_tier'] = ModelTier.SMALL  # Simple routing
        return state

    # Category keywords
    category_keywords = {
        QueryCategory.WEATHER: ['weather', 'temperature', 'forecast', 'rain', 'snow', 'sunny', 'cloudy'],
        QueryCategory.AIRPORTS: ['airport', 'flight', 'gate', 'terminal', 'airline', 'departure', 'arrival', 'delay'],
        QueryCategory.SPORTS: ['game', 'score', 'team', 'match', 'win', 'lose', 'player', 'season'],
        QueryCategory.NEWS: ['news', 'headline', 'article', 'breaking', 'latest'],
    }

    # Find best category match
    best_category = QueryCategory.INFO
    best_score = 0

    for category, keywords in category_keywords.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > best_score:
            best_score = score
            best_category = category

    state['category'] = best_category
    state['confidence'] = min(0.9, 0.5 + (best_score * 0.1))

    # Select model tier based on query complexity
    token_count = len(state['query'].split())
    if token_count < 10:
        state['model_tier'] = ModelTier.SMALL
    elif token_count < 30:
        state['model_tier'] = ModelTier.MEDIUM
    else:
        state['model_tier'] = ModelTier.LARGE

    state['latency_breakdown']['classify'] = (time.time() - start) * 1000
    return state
```

**2. Route Control Node**
```python
async def route_control_node(state: OrchestratorState) -> OrchestratorState:
    """
    Handle control commands via HA API directly.

    For Phase 1: Simple pass-through to HA
    For Phase 2+: Parse entities, validate permissions
    """
    import time
    start = time.time()

    # Parse command (simple extraction for Phase 1)
    command_text = state['query']

    # Call HA client
    from apps.shared.ha_client import HomeAssistantClient

    async with HomeAssistantClient() as ha:
        # For Phase 1: Use HA conversation API
        response = await ha.conversation_process(command_text)
        state['answer'] = response.get('speech', 'Command processed')

    state['model_used'] = 'ha_native'
    state['latency_breakdown']['route_control'] = (time.time() - start) * 1000
    return state
```

**3. Route Info Node**
```python
async def route_info_node(state: OrchestratorState) -> OrchestratorState:
    """
    Route info/complex queries to LLM pipeline.

    Select model tier based on classification.
    """
    # Model tier already set in classify node
    # Just pass through for now
    return state
```

**4. Retrieve Node**
```python
async def retrieve_node(state: OrchestratorState) -> OrchestratorState:
    """
    Retrieve data from appropriate RAG service.
    """
    import time
    import aiohttp
    start = time.time()

    # Map category to RAG service
    rag_service_map = {
        QueryCategory.WEATHER: 'http://localhost:8010',
        QueryCategory.AIRPORTS: 'http://localhost:8011',
        QueryCategory.SPORTS: 'http://localhost:8012',
    }

    service_url = rag_service_map.get(state['category'])

    if service_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{service_url}/query",
                    json={"query": state['query']},
                    timeout=aiohttp.ClientTimeout(total=2.0)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        state['retrieved_data'] = data.get('data', {})
                        state['sources'] = data.get('sources', [])
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            state['retrieved_data'] = {}
            state['sources'] = []
    else:
        # No RAG service for this category
        state['retrieved_data'] = {}
        state['sources'] = []

    state['retrieval_time_ms'] = (time.time() - start) * 1000
    state['latency_breakdown']['retrieve'] = state['retrieval_time_ms']
    return state
```

**5. Synthesize Node**
```python
async def synthesize_node(state: OrchestratorState) -> OrchestratorState:
    """
    Generate answer using LLM + retrieved data.
    """
    import time
    import aiohttp
    start = time.time()

    # Build prompt with context
    prompt = build_synthesis_prompt(
        query=state['query'],
        retrieved_data=state.get('retrieved_data', {}),
        sources=state.get('sources', [])
    )

    # Select model
    model_name = f"athena-{state['model_tier'].value}"

    # Call gateway
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                headers={"Authorization": f"Bearer {os.getenv('LITELLM_MASTER_KEY')}"},
                timeout=aiohttp.ClientTimeout(total=10.0)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    state['answer'] = result['choices'][0]['message']['content']
                    state['model_used'] = model_name
                else:
                    state['answer'] = "I'm having trouble generating a response right now."
    except Exception as e:
        logger.error(f"LLM synthesis failed: {e}")
        state['answer'] = "I encountered an error. Please try again."

    state['synthesis_time_ms'] = (time.time() - start) * 1000
    state['latency_breakdown']['synthesize'] = state['synthesis_time_ms']
    return state

def build_synthesis_prompt(query: str, retrieved_data: dict, sources: list) -> str:
    """Build synthesis prompt with context"""
    if not retrieved_data:
        return query

    # Format context
    context_text = json.dumps(retrieved_data, indent=2)

    # Format sources
    sources_text = "\n".join([
        f"- {src.get('name', 'Unknown')}: {src.get('url', 'N/A')}"
        for src in sources
    ])

    return f"""Answer the following question using ONLY the provided context. Be concise and accurate.

Question: {query}

Context:
{context_text}

Sources:
{sources_text}

Instructions:
1. Answer directly and concisely
2. Include specific details from the context (numbers, names, dates)
3. Mention the source if relevant
4. If the context doesn't contain the answer, say "I don't have that information"
5. Do NOT make up information not in the context

Answer:"""
```

**6. Validate Node**
```python
async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """
    Basic validation (Phase 1: simple checks only)

    Phase 2+ will add:
    - Cross-model validation
    - Policy guard checks
    - Retrieval confidence thresholds
    """
    validation_flags = []

    # Check 1: Answer exists and is not too short
    if not state.get('answer') or len(state['answer']) < 10:
        validation_flags.append('answer_too_short')

    # Check 2: Answer is not just repeating the question
    if state['query'].lower() in state.get('answer', '').lower():
        validation_flags.append('answer_repeats_question')

    # Check 3: If RAG was used, answer should mention data
    if state.get('retrieved_data') and not any(
        keyword in state.get('answer', '').lower()
        for keyword in ['temperature', 'forecast', 'delay', 'score', 'game']
    ):
        validation_flags.append('rag_data_not_used')

    state['validation_flags'] = validation_flags
    state['validation_passed'] = len(validation_flags) == 0

    return state
```

**7. Finalize Node**
```python
async def finalize_node(state: OrchestratorState) -> OrchestratorState:
    """
    Prepare final response with metadata.
    """
    # If validation failed, use fallback answer
    if not state['validation_passed']:
        state['answer'] = "I'm not confident in my answer. Could you rephrase your question?"

    # Build citations from sources
    if state.get('sources'):
        state['citations'] = [
            {
                'source': src.get('name', 'Unknown'),
                'url': src.get('url'),
                'freshness': src.get('freshness', 'unknown')
            }
            for src in state['sources']
        ]

    # Calculate total latency
    total_latency = sum(state.get('latency_breakdown', {}).values())
    state['latency_breakdown']['total'] = total_latency

    return state
```

### API Endpoints

**Primary Endpoint:**
```
POST /query
```

**Request:**
```json
{
  "query": "what's the weather in Baltimore?",
  "mode": "guest",
  "room": "office",
  "device_id": "jarvis-office-01"
}
```

**Response:**
```json
{
  "answer": "The current weather in Baltimore is 72°F and sunny with a high of 75°F today.",
  "category": "weather",
  "model_tier": "small",
  "model_used": "athena-small",
  "validation_passed": true,
  "citations": [
    {
      "source": "OpenWeatherMap",
      "url": "https://openweathermap.org/",
      "freshness": "<1h"
    }
  ],
  "metadata": {
    "request_id": "req_abc123",
    "latency_breakdown": {
      "classify": 15,
      "retrieve": 450,
      "synthesize": 1200,
      "total": 1665
    }
  }
}
```

---

## 3. RAG Services: Microservice Architecture

### Design Pattern

Each RAG category is a **separate microservice** with:
- FastAPI HTTP API
- Redis caching layer
- Prometheus metrics
- Health checks
- Error handling

### Service Template

**Structure:**
```
apps/rag/<category>/
  main.py           # FastAPI app
  handler.py        # Category-specific logic
  cache.py          # Redis caching
  models.py         # Pydantic models
  Dockerfile
  requirements.txt
  README.md
```

### Example: Weather Service

**File:** `apps/rag/weather/main.py`
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
import aiohttp
import os
import json
from datetime import datetime, timedelta
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Prometheus metrics
weather_requests_total = Counter('weather_requests_total', 'Total weather requests', ['status'])
weather_request_duration = Histogram('weather_request_duration_seconds', 'Weather request duration')
weather_cache_hits = Counter('weather_cache_hits_total', 'Weather cache hits')
weather_cache_misses = Counter('weather_cache_misses_total', 'Weather cache misses')

app = FastAPI(title="Weather RAG Service", version="1.0.0")

# Redis client
redis_client = None

@app.on_event("startup")
async def startup():
    global redis_client
    redis_url = os.getenv('REDIS_URL', 'redis://192.168.10.29:6379/0')
    redis_client = redis.from_url(redis_url, decode_responses=True)

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()

class WeatherQuery(BaseModel):
    query: str
    location: str = "Baltimore, MD"

class WeatherSource(BaseModel):
    name: str
    url: str
    freshness: str

class WeatherResponse(BaseModel):
    data: Dict
    sources: List[WeatherSource]
    cached: bool
    retrieved_at: str

@app.post("/query", response_model=WeatherResponse)
@weather_request_duration.time()
async def get_weather(request: WeatherQuery):
    """Get weather data with caching"""
    try:
        # Extract location (default to Baltimore)
        location = request.location

        # Check cache
        cache_key = f"weather:{location.lower().replace(' ', '_')}"
        cached_data = await redis_client.get(cache_key)

        if cached_data:
            weather_cache_hits.inc()
            weather_requests_total.labels(status='success_cached').inc()

            return WeatherResponse(
                data=json.loads(cached_data),
                sources=[
                    WeatherSource(
                        name="OpenWeatherMap",
                        url="https://openweathermap.org",
                        freshness="<48h"
                    )
                ],
                cached=True,
                retrieved_at=datetime.utcnow().isoformat()
            )

        # Cache miss - fetch from API
        weather_cache_misses.inc()

        api_key = os.getenv('OPENWEATHER_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY not configured")

        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': location,
            'appid': api_key,
            'units': 'imperial'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5.0)) as response:
                if response.status != 200:
                    weather_requests_total.labels(status='error_api').inc()
                    raise HTTPException(status_code=response.status, detail="Weather API error")

                data = await response.json()

                # Cache for 48 hours
                await redis_client.setex(
                    cache_key,
                    timedelta(hours=48),
                    json.dumps(data)
                )

                weather_requests_total.labels(status='success_fresh').inc()

                return WeatherResponse(
                    data=data,
                    sources=[
                        WeatherSource(
                            name="OpenWeatherMap",
                            url="https://openweathermap.org",
                            freshness="real-time"
                        )
                    ],
                    cached=False,
                    retrieved_at=datetime.utcnow().isoformat()
                )

    except HTTPException:
        raise
    except Exception as e:
        weather_requests_total.labels(status='error').inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check Redis
    try:
        await redis_client.ping()
        redis_healthy = True
    except:
        redis_healthy = False

    # Check OpenWeatherMap API key
    api_key_configured = bool(os.getenv('OPENWEATHER_API_KEY'))

    return {
        "status": "healthy" if (redis_healthy and api_key_configured) else "degraded",
        "service": "weather-rag",
        "redis": redis_healthy,
        "api_key_configured": api_key_configured
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Caching Strategy

**Cache Keys:**
```
weather:<location>          TTL: 48 hours
airports:<airport_code>     TTL: 1 hour
sports:<team>_<date>        TTL: 15 minutes (live games), 24 hours (past games)
news:<category>             TTL: 1 hour
```

**Cache Invalidation:**
- Manual: `redis-cli DEL <key>`
- Automatic: TTL expiration
- Force refresh: `?force_refresh=true` query parameter

---

## 4. Validators: Anti-Hallucination System

### Purpose

Prevent LLM from generating false information, especially in high-stakes categories (airports, flights, sports scores).

### Validation Strategies (Phase 1: Basic)

**1. Policy Guard**
- Block unsafe queries (security, privacy, illegal)
- Guest mode restrictions (no access to cameras, locks)
- Rate limiting

**2. Retrieval Confidence**
- Require retrieval success for RAG categories
- Check if answer uses retrieved data
- Flag generic/vague responses

**3. Answer Quality**
- Minimum length checks
- Not repeating question
- Contains expected keywords for category

### Implementation (Expand in Phase 2+)

**File:** `apps/validators/main.py`
```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Athena Validators", version="1.0.0")

class ValidationRequest(BaseModel):
    query: str
    answer: str
    category: str
    retrieved_data: Dict
    mode: str  # guest or owner

class ValidationResult(BaseModel):
    passed: bool
    flags: List[str]
    confidence: float

@app.post("/validate", response_model=ValidationResult)
async def validate_answer(request: ValidationRequest):
    """Validate answer quality and safety"""
    flags = []

    # Policy guard (Phase 1: basic)
    if request.mode == "guest":
        unsafe_keywords = ['password', 'unlock', 'disable', 'security code', 'camera']
        if any(kw in request.query.lower() for kw in unsafe_keywords):
            flags.append('unsafe_query_guest_mode')

    # Retrieval validation (RAG categories)
    if request.category in ['weather', 'airports', 'sports']:
        if not request.retrieved_data:
            flags.append('missing_retrieval_data')

    # Answer quality
    if len(request.answer) < 10:
        flags.append('answer_too_short')

    if request.query.lower() in request.answer.lower():
        flags.append('answer_repeats_question')

    # Calculate confidence
    confidence = 1.0 - (len(flags) * 0.2)

    return ValidationResult(
        passed=len(flags) == 0,
        flags=flags,
        confidence=max(0.0, confidence)
    )
```

---

## 5. Share Service: SMS and Email

### Purpose

Enable guests to receive directions, recipes, recommendations via SMS or email.

### Technology Stack

- **SMS:** Twilio API
- **Email:** SMTP (Gmail, SendGrid, etc.)

### Implementation (Stub for Phase 1)

**File:** `apps/share/main.py`
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Share Service", version="1.0.0")

# Twilio client
twilio_client = None
if os.getenv('TWILIO_ACCOUNT_SID') and os.getenv('TWILIO_AUTH_TOKEN'):
    twilio_client = Client(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )

class SMSRequest(BaseModel):
    to: str  # Phone number
    message: str

class EmailRequest(BaseModel):
    to: str  # Email address
    subject: str
    body: str

@app.post("/sms")
async def send_sms(request: SMSRequest):
    """Send SMS via Twilio"""
    if not twilio_client:
        raise HTTPException(status_code=503, detail="Twilio not configured")

    try:
        message = twilio_client.messages.create(
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            to=request.to,
            body=request.message
        )
        return {"status": "sent", "sid": message.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/email")
async def send_email(request: EmailRequest):
    """Send email via SMTP"""
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    if not all([smtp_user, smtp_password]):
        raise HTTPException(status_code=503, detail="SMTP not configured")

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = request.to
        msg['Subject'] = request.subject
        msg.attach(MIMEText(request.body, 'plain'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "twilio_configured": twilio_client is not None,
        "smtp_configured": bool(os.getenv('SMTP_USER'))
    }
```

---

## 6. Vector Database: Qdrant Setup

### Purpose

Store embeddings for property context, FAQs, and future RAG expansion.

### Deployment on Mac mini

**Docker Compose:**
```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_storage:/qdrant/storage
    environment:
      QDRANT__SERVICE__GRPC_PORT: 6334
      QDRANT__LOG_LEVEL: INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  qdrant_storage:
    driver: local
```

### Collection Schema

**Collection Name:** `athena_knowledge`

**Vector Config:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

client = QdrantClient(url="http://192.168.10.29:6333")

# Create collection
client.create_collection(
    collection_name="athena_knowledge",
    vectors_config=VectorParams(
        size=384,  # sentence-transformers/all-MiniLM-L6-v2
        distance=Distance.COSINE
    )
)

# Add property context (Baltimore)
property_context = [
    {
        "id": str(uuid.uuid4()),
        "text": "The property is located at 912 South Clinton St, Baltimore, MD 21224",
        "category": "property_info",
        "metadata": {"type": "address"}
    },
    {
        "id": str(uuid.uuid4()),
        "text": "Nearby airports: Baltimore/Washington International (BWI) - 15 minutes, Philadelphia (PHL) - 90 minutes",
        "category": "property_info",
        "metadata": {"type": "transportation"}
    },
    # ... more context points
]

# Insert vectors (using sentence-transformers)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

points = []
for item in property_context:
    embedding = model.encode(item['text'])
    points.append(
        PointStruct(
            id=item['id'],
            vector=embedding.tolist(),
            payload={
                "text": item['text'],
                "category": item['category'],
                **item.get('metadata', {})
            }
        )
    )

client.upsert(collection_name="athena_knowledge", points=points)
```

---

## 7. HA Bridge: Advanced Device Control

### Purpose

Provide advanced Home Assistant device control beyond basic conversation API (for Phase 2+).

### Features (Phase 2+)

- Multi-step scenes (e.g., "movie night")
- Complex automations
- State queries with filtering
- Bulk operations

### Simple Implementation (Phase 1)

Use existing `apps/shared/ha_client.py` for basic operations.

---

## Summary

This document provides technical specifications for all core components. Use these as reference when implementing each service.

**Next Steps:**
1. Implement services following these specs
2. Test each component independently
3. Integrate via orchestrator
4. Deploy to Mac Studio/mini
5. Test end-to-end voice flow

**Related:**
- [Phase 1 Implementation](2025-11-11-phase1-core-services-implementation.md) - Step-by-step deployment
- [Full Bootstrap](2025-11-11-full-bootstrap-implementation.md) - From zero to working system
