# Phase 1: Core Services Implementation Plan - Mac Studio & Mac mini Deployment

**Date:** 2025-11-11
**Status:** Planning - Part of Architecture Pivot
**Related:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)
- [Full Bootstrap Plan](2025-11-11-full-bootstrap-implementation.md)
- [Component Deep-Dive Plans](2025-11-11-component-deep-dive-plans.md)

---

## Executive Summary

This plan provides **detailed implementation steps** for Phase 1 of the new Project Athena architecture: deploying core services on Mac Studio M4/64GB and Mac mini M4/16GB.

**Phase 1 Goal:** Transform the existing Jetson-based implementation into a production-ready system running on Mac hardware with LangGraph orchestration, advanced RAG, and dual Home Assistant pipelines.

**Timeline:** 4-6 weeks (given existing codebase to migrate)

**Key Deliverables:**
1. Mac Studio running gateway, orchestrator, LLMs, RAG services
2. Mac mini running vector DB, cache, monitoring
3. HA Assist Pipelines (Control + Knowledge) configured
4. End-to-end voice query working through HA Voice devices
5. Docker Compose deployment with Metal acceleration

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Desired End State](#2-desired-end-state)
3. [What We're NOT Doing](#3-what-were-not-doing)
4. [Implementation Phases](#4-implementation-phases)
5. [Testing Strategy](#5-testing-strategy)
6. [Performance Targets](#6-performance-targets)
7. [Migration from Jetson](#7-migration-from-jetson)
8. [References](#8-references)

---

## 1. Current State Analysis

### What Exists (Jetson-based)

**Fully functional voice assistant at:** `/Users/jaystuart/dev/project-athena/src/jetson/`

**Working Components:**
- ✅ Home Assistant REST API client (`ha_client.py`)
- ✅ Intent classification (43 versions, currently using facade)
- ✅ 10+ RAG handlers:
  - Weather (OpenWeatherMap)
  - Airports (7 airports: PHL, BWI, EWR, LGA, JFK, IAD, DCA)
  - Flights (FlightAware)
  - Events (Eventbrite, Ticketmaster)
  - Streaming (TMDB)
  - News (NewsAPI)
  - Stocks (Alpha Vantage)
  - Sports (TheSportsDB)
  - Web Search (DuckDuckGo)
- ✅ Ollama integration (`ollama_proxy.py`)
- ✅ Function calling orchestration (`function_calling.py`)
- ✅ Caching system (`caching.py`)
- ✅ Context management (`context_manager.py`)
- ✅ Performance metrics (`metrics.py`)
- ✅ Validation guardrails (`validation.py`)
- ✅ Configuration management (`config/`)
- ✅ Extensive test suite (1000+ query benchmarks)

**Currently Running:**
- Jetson Orin Nano @ 192.168.10.62
- Services: Ollama proxy (port 11434), Ollama (port 11435)
- Home Assistant @ 192.168.10.168 (Proxmox VM)

### What's Missing for Phase 1

**Infrastructure:**
- ❌ Docker containerization (no Dockerfiles exist)
- ❌ Docker Compose orchestration
- ❌ apps/ directory structure (production organization)
- ❌ Environment-based configuration
- ❌ Health check endpoints
- ❌ Prometheus metrics exporters
- ❌ Graceful shutdown handlers

**Architecture Components:**
- ❌ OpenAI-compatible gateway (LiteLLM or custom)
- ❌ LangGraph orchestrator (classify → route → retrieve → validate → share)
- ❌ Wyoming protocol integration (no implementation exists)
- ❌ HA Assist Pipeline configuration
- ❌ Multi-zone audio routing
- ❌ Vector database (Qdrant/Weaviate/Chroma)
- ❌ Redis cache/job queue
- ❌ Share service (Twilio SMS + SMTP email)

**Hardware:**
- ❌ Mac Studio M4/64GB (needs purchase/delivery)
- ❌ Mac mini M4/16GB (needs purchase/delivery)
- ❌ HA Voice preview devices (needs ordering)

### Key Discoveries from Codebase

1. **Mature RAG handlers exist:** All 10+ handlers are production-ready with caching, error handling, API integration
2. **Intent classification is sophisticated:** 43 versions of evolution, currently using facade system with high accuracy
3. **HA integration pattern established:** REST API client with function calling works well
4. **Performance is good:** 2.5-5s total response time on Jetson hardware
5. **Testing is comprehensive:** 1000+ query benchmark suite, multi-version comparisons
6. **Baltimore property context embedded:** Facade system has "912 South Clinton St, Baltimore, MD 21224" hardcoded

---

## 2. Desired End State

### Phase 1 Complete When:

**Mac Studio (192.168.10.20) Running:**
```
apps/
  gateway/           → OpenAI-compatible API (port 8000)
  orchestrator/      → LangGraph (port 8001)
  rag-weather/       → Weather service (port 8010)
  rag-airports/      → Airport service (port 8011)
  rag-sports/        → Sports service (port 8012)
  [... other RAG services ...]
  validators/        → Anti-hallucination (port 8020)
  share/             → Twilio SMS + email (port 8021)
  ollama/            → LLM inference (port 11434)
```

**Mac mini (192.168.10.181) Running:**
```
services/
  qdrant/            → Vector DB (port 6333)
  redis/             → Cache + job queue (port 6379)
  prometheus-export/ → Metrics exporter (port 9090)
```

**Home Assistant (192.168.10.168) Configured:**
- ✅ Faster-Whisper add-on (Wyoming STT)
- ✅ Piper TTS add-on (Wyoming TTS)
- ✅ Assist Pipeline 1: **CONTROL** (HA native agent)
- ✅ Assist Pipeline 2: **KNOWLEDGE** (OpenAI Conversation → 192.168.10.20:8000)

**End-to-End Voice Flow Working:**
1. User says "Jarvis, what's the weather in Baltimore?"
2. HA Voice device captures audio
3. Wyoming Whisper transcribes → "what's the weather in Baltimore?"
4. HA routes to KNOWLEDGE pipeline
5. OpenAI Conversation calls Mac Studio gateway (192.168.10.20:8000)
6. LangGraph orchestrator:
   - Classifies as "info/weather"
   - Routes to rag-weather service
   - Retrieves from OpenWeatherMap
   - Synthesizes answer with sources
   - Validates (no hallucinations)
7. Returns to HA → Piper TTS → HA Voice device speaks answer
8. **Total time:** ≤5.5s (pre-optimization target)

### Success Criteria (Automated):

- [ ] `curl http://192.168.10.20:8000/v1/chat/completions` returns valid OpenAI-compatible response
- [ ] `curl http://192.168.10.20:8001/health` returns healthy status
- [ ] `curl http://192.168.10.181:6333/healthz` returns Qdrant healthy
- [ ] `redis-cli -h 192.168.10.181 PING` returns PONG
- [ ] HA Assist Pipeline test returns answer (HA UI → Settings → Voice Assistants → Test Pipeline)
- [ ] Prometheus scrapes all service metrics successfully
- [ ] Docker containers start cleanly: `docker compose up -d`
- [ ] All services pass health checks: `docker compose ps`

### Success Criteria (Manual):

- [ ] Voice query "what's the weather" returns accurate Baltimore weather
- [ ] Voice query "turn on office lights" controls HA device via Control pipeline
- [ ] Voice query "what time is it" returns current time
- [ ] Complex query uses medium/large model (visible in logs)
- [ ] RAG query includes citations in response
- [ ] Failed query triggers proper error response (not crash)
- [ ] Latency ≤5.5s for knowledge queries (pre-optimization)
- [ ] Latency ≤3.5s for control queries

---

## 3. What We're NOT Doing

**Explicitly out of scope for Phase 1:**

1. ❌ **Performance optimization:** Accepting higher latency (5.5s) initially
2. ❌ **All 10 RAG sources:** Starting with weather, airports, sports only
3. ❌ **Guest mode automation:** Manual mode switching OK for Phase 1
4. ❌ **Admin interface:** CLI/environment variables acceptable
5. ❌ **Cross-model validation:** Single model inference for speed
6. ❌ **Voice ID/profiles:** No user identification
7. ❌ **SMS/email sharing:** Stubbed out, not fully functional
8. ❌ **Full 10 zones:** Testing with 1-2 HA Voice devices
9. ❌ **Kubernetes deployment:** Docker Compose only
10. ❌ **Production monitoring:** Basic Prometheus, no alerting

**Deferred to Phase 2:**
- Full RAG source coverage
- Performance tuning (≤4.0s target)
- Guest mode calendar integration
- Share service completion
- Occupancy-based routing
- Property context enrichment

**Deferred to Phase 3:**
- Admin interface
- Cross-model validation
- Voice identification
- Learning from feedback
- Full 10-zone deployment

---

## 4. Implementation Phases

### Phase 1.1: Repository Restructuring (Week 1)

**Goal:** Transform research code into production structure

#### Step 1.1.1: Create Directory Structure

**Create:**
```bash
mkdir -p apps/gateway
mkdir -p apps/orchestrator
mkdir -p apps/rag/weather
mkdir -p apps/rag/airports
mkdir -p apps/rag/sports
mkdir -p apps/validators
mkdir -p apps/share
mkdir -p deploy/docker
mkdir -p deploy/compose
mkdir -p config/env
mkdir -p config/prompts
mkdir -p logs
mkdir -p data/models
```

#### Step 1.1.2: Extract and Refactor Core Components

**Migrate HA Client:**
```bash
# Source: src/jetson/ha_client.py → apps/shared/ha_client.py
# Changes:
# - Add environment-based configuration
# - Add health check method
# - Add Prometheus metrics
# - Add async/await support
# - Add connection pooling
```

**File:** `apps/shared/ha_client.py`
```python
import os
import aiohttp
from prometheus_client import Counter, Histogram

# Metrics
ha_requests_total = Counter('ha_requests_total', 'Total HA API requests', ['method', 'status'])
ha_request_duration = Histogram('ha_request_duration_seconds', 'HA API request duration')

class HomeAssistantClient:
    def __init__(self):
        self.base_url = os.getenv('HA_URL', 'https://192.168.10.168:8123')
        self.token = os.getenv('HA_TOKEN')
        if not self.token:
            raise ValueError("HA_TOKEN environment variable required")

        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if HA is reachable"""
        try:
            async with self.session.get(f'{self.base_url}/api/') as response:
                return response.status == 200
        except Exception:
            return False

    # ... migrate other methods from src/jetson/ha_client.py ...
```

**Migrate RAG Handlers:**

Extract these from `src/jetson/facade/handlers/`:
- `weather.py` → `apps/rag/weather/handler.py`
- `airports.py` → `apps/rag/airports/handler.py`
- `sports.py` → `apps/rag/sports/handler.py`

**Changes needed:**
- Wrap in FastAPI application
- Add `/health` endpoint
- Add Prometheus metrics
- Use environment variables for API keys
- Add async/await support
- Add caching layer (Redis)

**Migrate Intent Classifier:**

```bash
# Source: src/jetson/facade/airbnb_intent_classifier.py (v43)
# Destination: apps/orchestrator/classifier.py
# Changes:
# - Remove Baltimore-specific hardcoding
# - Make configurable via environment
# - Add telemetry
```

#### Step 1.1.3: Configuration Management

**Create:** `config/env/.env.example`
```bash
# Home Assistant
HA_URL=https://192.168.10.168:8123
HA_TOKEN=your_ha_token_here

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_SMALL_MODEL=phi3:mini-q8
OLLAMA_MEDIUM_MODEL=llama3.1:8b-q4
OLLAMA_LARGE_MODEL=llama3.1:13b-q4

# Vector DB
QDRANT_URL=http://192.168.10.181:6333
QDRANT_COLLECTION=athena_knowledge

# Redis
REDIS_URL=redis://192.168.10.181:6379/0

# RAG API Keys
OPENWEATHER_API_KEY=your_key_here
FLIGHTAWARE_API_KEY=your_key_here
THESPORTSDB_API_KEY=your_key_here

# Feature Flags
ENABLE_CROSS_MODEL_VALIDATION=false
ENABLE_GUEST_MODE=false
ENABLE_SHARE_SERVICE=false

# Latency Budgets
MAX_CONTROL_LATENCY_MS=3500
MAX_KNOWLEDGE_LATENCY_MS=5500

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### Step 1.1.4: Success Criteria

**Automated Verification:**
- [ ] Directory structure created: `ls -la apps/ deploy/ config/`
- [ ] Core files exist: `find apps/ -name "*.py" | wc -l` returns >10
- [ ] Configuration template exists: `test -f config/env/.env.example`
- [ ] Python imports work: `python -c "from apps.shared.ha_client import HomeAssistantClient"`

**Manual Verification:**
- [ ] All source files have proper headers (docstrings, imports organized)
- [ ] Configuration values make sense (no hardcoded Jetson IPs)
- [ ] TODOs marked for incomplete migrations

---

### Phase 1.2: OpenAI-Compatible Gateway (Week 1-2)

**Goal:** Create API gateway that HA OpenAI Conversation can call

#### Step 1.2.1: Choose Gateway Implementation

**Option A: LiteLLM (Recommended)**
- ✅ Pre-built OpenAI compatibility
- ✅ Model routing built-in
- ✅ Prometheus metrics included
- ✅ Caching support
- ❌ Additional dependency

**Option B: Custom FastAPI**
- ✅ Full control
- ✅ Simpler deployment
- ✅ Direct Ollama integration
- ❌ Must implement OpenAI spec manually

**Decision:** Use **LiteLLM** for Phase 1 (faster, battle-tested)

#### Step 1.2.2: Install and Configure LiteLLM

**File:** `apps/gateway/config.yaml`
```yaml
model_list:
  - model_name: athena-small
    litellm_params:
      model: ollama/phi3:mini-q8
      api_base: http://localhost:11434

  - model_name: athena-medium
    litellm_params:
      model: ollama/llama3.1:8b-q4
      api_base: http://localhost:11434

  - model_name: athena-large
    litellm_params:
      model: ollama/llama3.1:13b-q4
      api_base: http://localhost:11434

router_settings:
  routing_strategy: simple-shuffle
  num_retries: 2
  timeout: 300

general_settings:
  master_key: ${LITELLM_MASTER_KEY}
  proxy_logging: true
  success_callback: ["prometheus"]
```

**File:** `apps/gateway/Dockerfile`
```dockerfile
FROM ghcr.io/berriai/litellm:main-latest

WORKDIR /app

COPY config.yaml /app/config.yaml

ENV PORT=8000
ENV DATABASE_URL=postgresql://litellm:password@postgres:5432/litellm

EXPOSE 8000

CMD ["--config", "/app/config.yaml", "--port", "8000"]
```

**File:** `apps/gateway/docker-compose.gateway.yml`
```yaml
version: '3.8'

services:
  litellm:
    build: ./apps/gateway
    container_name: athena-gateway
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      OLLAMA_API_BASE: http://host.docker.internal:11434
    volumes:
      - ./logs:/app/logs
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Step 1.2.3: Test Gateway

**Test script:** `scripts/test_gateway.sh`
```bash
#!/bin/bash

echo "Testing OpenAI-compatible gateway..."

# Test 1: Health check
echo "1. Health check:"
curl -f http://localhost:8000/health || exit 1

# Test 2: Simple completion
echo "2. Simple completion:"
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -d '{
    "model": "athena-small",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "temperature": 0.7
  }'

# Test 3: Model routing
echo "3. Model routing (medium):"
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -d '{
    "model": "athena-medium",
    "messages": [{"role": "user", "content": "Explain quantum physics briefly"}],
    "temperature": 0.7
  }'

echo "Gateway tests complete!"
```

#### Step 1.2.4: Success Criteria

**Automated Verification:**
- [ ] Gateway starts: `docker compose up -d gateway`
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] OpenAI spec compatibility: `scripts/test_gateway.sh`
- [ ] Metrics endpoint works: `curl http://localhost:8000/metrics`
- [ ] All 3 models respond: test script passes for small/medium/large

**Manual Verification:**
- [ ] Response format matches OpenAI spec
- [ ] Latency acceptable (≤3s for simple query)
- [ ] Error handling works (try invalid API key, timeout)
- [ ] Logs show request details

---

### Phase 1.3: LangGraph Orchestrator (Week 2-3)

**Goal:** Build classify → route → retrieve → validate → finalize flow

#### Step 1.3.1: Setup LangGraph Project

**File:** `apps/orchestrator/requirements.txt`
```
langgraph==0.0.20
langchain==0.1.0
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.0
aiohttp==3.9.1
redis==5.0.1
prometheus-client==0.19.0
```

**File:** `apps/orchestrator/main.py`
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
import os
import logging

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

app = FastAPI(title="Athena Orchestrator", version="1.0.0")

# State definition
class OrchestratorState(BaseModel):
    query: str
    mode: str = "guest"  # guest or owner
    room: str = "unknown"
    category: str = None  # weather, control, info, complex
    model_tier: str = None  # small, medium, large
    retrieved_data: dict = {}
    answer: str = None
    citations: list = []
    validation_passed: bool = True
    metadata: dict = {}

# Build graph
def build_orchestrator_graph():
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("route_control", route_control_node)
    graph.add_node("route_info", route_info_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("validate", validate_node)
    graph.add_node("finalize", finalize_node)

    # Add edges
    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        classify_router,
        {
            "control": "route_control",
            "info": "route_info",
            "complex": "route_info"
        }
    )

    graph.add_edge("route_control", "finalize")
    graph.add_edge("route_info", "retrieve")
    graph.add_edge("retrieve", "synthesize")
    graph.add_edge("synthesize", "validate")
    graph.add_edge("validate", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()

# Node implementations (simplified for Phase 1)
async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """Classify intent: control vs info vs complex"""
    # Migrate logic from src/jetson/facade/airbnb_intent_classifier.py
    query_lower = state.query.lower()

    # Simple pattern matching for Phase 1
    control_patterns = ['turn on', 'turn off', 'set', 'brightness', 'dim', 'brighten']
    if any(p in query_lower for p in control_patterns):
        state.category = "control"
    elif 'weather' in query_lower:
        state.category = "weather"
    elif 'airport' in query_lower or 'flight' in query_lower:
        state.category = "airports"
    elif 'score' in query_lower or 'game' in query_lower:
        state.category = "sports"
    else:
        state.category = "info"  # Generic info query

    logger.info(f"Classified query '{state.query}' as: {state.category}")
    return state

def classify_router(state: OrchestratorState) -> str:
    """Route based on classification"""
    if state.category == "control":
        return "control"
    else:
        return "info"

async def route_control_node(state: OrchestratorState) -> OrchestratorState:
    """Handle control commands via HA API"""
    # TODO: Call HA client directly
    state.answer = f"Control command handled: {state.query}"
    state.metadata['handler'] = 'ha_direct'
    return state

async def route_info_node(state: OrchestratorState) -> OrchestratorState:
    """Select model tier for info queries"""
    # Simple heuristic for Phase 1
    token_estimate = len(state.query.split())

    if token_estimate < 10:
        state.model_tier = "small"
    elif token_estimate < 30:
        state.model_tier = "medium"
    else:
        state.model_tier = "large"

    logger.info(f"Selected model tier: {state.model_tier}")
    return state

async def retrieve_node(state: OrchestratorState) -> OrchestratorState:
    """Retrieve data from RAG sources"""
    # Call appropriate RAG service based on category
    rag_service_url = get_rag_service_url(state.category)

    if rag_service_url:
        # Make HTTP request to RAG service
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{rag_service_url}/query",
                json={"query": state.query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    state.retrieved_data = data
                    logger.info(f"Retrieved data from {state.category} service")

    return state

async def synthesize_node(state: OrchestratorState) -> OrchestratorState:
    """Generate answer using LLM + retrieved data"""
    # Call gateway with model tier and context
    model_name = f"athena-{state.model_tier}"

    # Build prompt with retrieved data
    prompt = build_synthesis_prompt(state.query, state.retrieved_data)

    # Call LiteLLM gateway
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            headers={"Authorization": f"Bearer {os.getenv('LITELLM_MASTER_KEY')}"}
        ) as response:
            if response.status == 200:
                result = await response.json()
                state.answer = result['choices'][0]['message']['content']
                state.metadata['model_used'] = model_name

    return state

async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """Basic validation (expand in later phases)"""
    # For Phase 1: simple checks only
    if not state.answer or len(state.answer) < 10:
        state.validation_passed = False
        logger.warning("Validation failed: answer too short")
    else:
        state.validation_passed = True

    return state

async def finalize_node(state: OrchestratorState) -> OrchestratorState:
    """Prepare final response"""
    if not state.validation_passed:
        state.answer = "I'm not confident in my answer. Could you rephrase your question?"

    return state

def get_rag_service_url(category: str) -> str:
    """Get RAG service URL based on category"""
    services = {
        'weather': 'http://localhost:8010',
        'airports': 'http://localhost:8011',
        'sports': 'http://localhost:8012'
    }
    return services.get(category)

def build_synthesis_prompt(query: str, retrieved_data: dict) -> str:
    """Build prompt for synthesis"""
    if not retrieved_data:
        return query

    return f"""Answer the following question using the provided context:

Question: {query}

Context:
{retrieved_data}

Provide a concise, accurate answer with specific details from the context."""

# API endpoint
@app.post("/query")
async def process_query(request: dict):
    """Process voice query through orchestrator"""
    query = request.get('query', '')
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    # Initialize state
    state = OrchestratorState(
        query=query,
        mode=request.get('mode', 'guest'),
        room=request.get('room', 'unknown')
    )

    # Run graph
    graph = build_orchestrator_graph()
    result = await graph.ainvoke(state)

    # Return response
    return {
        "answer": result.answer,
        "category": result.category,
        "model_tier": result.model_tier,
        "validation_passed": result.validation_passed,
        "citations": result.citations,
        "metadata": result.metadata
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

#### Step 1.3.2: Dockerfile for Orchestrator

**File:** `apps/orchestrator/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["python", "main.py"]
```

#### Step 1.3.3: Success Criteria

**Automated Verification:**
- [ ] Orchestrator starts: `docker compose up -d orchestrator`
- [ ] Health check passes: `curl http://localhost:8001/health`
- [ ] Classification works: `curl -X POST http://localhost:8001/query -d '{"query":"turn on lights"}' -H "Content-Type: application/json"` returns category="control"
- [ ] Weather query routed correctly: Test with "what's the weather"
- [ ] Model tier selection works: Simple query uses "small", complex uses "medium"

**Manual Verification:**
- [ ] Control queries return expected response
- [ ] Info queries attempt retrieval (even if RAG services not ready)
- [ ] Validation catches bad responses
- [ ] Logs show graph execution flow

---

### Phase 1.4: RAG Services (Week 3-4)

**Goal:** Deploy weather, airports, sports microservices

#### Step 1.4.1: Create RAG Service Template

**File:** `apps/rag/weather/main.py`
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import aiohttp
import json
from datetime import datetime, timedelta
import redis.asyncio as redis

app = FastAPI(title="Weather RAG Service", version="1.0.0")

# Initialize Redis cache
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://192.168.10.181:6379/0'))

class WeatherQuery(BaseModel):
    query: str
    location: str = "Baltimore, MD"  # Default to Baltimore

class WeatherResponse(BaseModel):
    data: dict
    source: str
    cached: bool
    freshness: str

@app.post("/query", response_model=WeatherResponse)
async def get_weather(request: WeatherQuery):
    """Get weather data with caching"""

    # Check cache first
    cache_key = f"weather:{request.location}"
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        return WeatherResponse(
            data=json.loads(cached_data),
            source="OpenWeatherMap",
            cached=True,
            freshness="<48h"
        )

    # Fetch from API
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY not configured")

    url = f"https://api.openweathermap.org/data/2.5/weather?q={request.location}&appid={api_key}&units=imperial"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise HTTPException(status_code=response.status, detail="Weather API error")

            data = await response.json()

            # Cache for 48 hours
            await redis_client.setex(
                cache_key,
                timedelta(hours=48),
                json.dumps(data)
            )

            return WeatherResponse(
                data=data,
                source="OpenWeatherMap",
                cached=False,
                freshness="real-time"
            )

@app.get("/health")
async def health_check():
    # Check Redis connection
    try:
        await redis_client.ping()
        redis_healthy = True
    except:
        redis_healthy = False

    return {
        "status": "healthy" if redis_healthy else "degraded",
        "service": "weather-rag",
        "redis": redis_healthy
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

**File:** `apps/rag/weather/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8010

CMD ["python", "main.py"]
```

**File:** `apps/rag/weather/requirements.txt`
```
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.0
aiohttp==3.9.1
redis==5.0.1
```

#### Step 1.4.2: Replicate for Airports and Sports

**Create similar services:**
- `apps/rag/airports/main.py` (port 8011) - Migrate from `src/jetson/facade/handlers/airports.py`
- `apps/rag/sports/main.py` (port 8012) - Migrate from `src/jetson/facade/handlers/sports.py`

**Changes needed:**
- Extract API logic from facade handlers
- Add Redis caching
- Add health checks
- Add Prometheus metrics
- Make API keys configurable

#### Step 1.4.3: Docker Compose for RAG Services

**File:** `deploy/compose/docker-compose.rag.yml`
```yaml
version: '3.8'

services:
  rag-weather:
    build: ./apps/rag/weather
    container_name: athena-rag-weather
    restart: unless-stopped
    ports:
      - "8010:8010"
    environment:
      OPENWEATHER_API_KEY: ${OPENWEATHER_API_KEY}
      REDIS_URL: redis://192.168.10.181:6379/0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  rag-airports:
    build: ./apps/rag/airports
    container_name: athena-rag-airports
    restart: unless-stopped
    ports:
      - "8011:8011"
    environment:
      FLIGHTAWARE_API_KEY: ${FLIGHTAWARE_API_KEY}
      REDIS_URL: redis://192.168.10.181:6379/0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8011/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  rag-sports:
    build: ./apps/rag/sports
    container_name: athena-rag-sports
    restart: unless-stopped
    ports:
      - "8012:8012"
    environment:
      THESPORTSDB_API_KEY: ${THESPORTSDB_API_KEY}
      REDIS_URL: redis://192.168.10.181:6379/0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8012/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Step 1.4.4: Success Criteria

**Automated Verification:**
- [ ] All RAG services start: `docker compose -f deploy/compose/docker-compose.rag.yml up -d`
- [ ] Health checks pass for all 3 services
- [ ] Weather query returns data: `curl -X POST http://localhost:8010/query -d '{"query":"weather","location":"Baltimore"}' -H "Content-Type: application/json"`
- [ ] Airport query returns data
- [ ] Sports query returns data
- [ ] Redis caching works (second query shows `cached: true`)

**Manual Verification:**
- [ ] Weather data is accurate for Baltimore
- [ ] Airport data includes all 7 airports (PHL, BWI, etc.)
- [ ] Sports data returns recent games
- [ ] Cached responses are faster (≤50ms vs ≤1s)
- [ ] Error handling works (invalid location, API timeout)

---

### Phase 1.5: Mac mini Services (Week 4)

**Goal:** Deploy Qdrant vector DB and Redis on Mac mini

#### Step 1.5.1: Setup Docker on Mac mini

```bash
# SSH to Mac mini
ssh jstuart@192.168.10.181

# Install Docker Desktop for Mac or use Homebrew
brew install docker docker-compose

# Start Docker daemon
open /Applications/Docker.app
```

#### Step 1.5.2: Deploy Qdrant

**File:** `deploy/mac-mini/docker-compose.yml`
```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_storage:/qdrant/storage
    environment:
      QDRANT__SERVICE__GRPC_PORT: 6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  qdrant_storage:
  redis_data:
```

#### Step 1.5.3: Initialize Qdrant Collection

**Script:** `scripts/init_qdrant.py`
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://192.168.10.181:6333")

# Create collection for knowledge vectors
client.create_collection(
    collection_name="athena_knowledge",
    vectors_config=VectorParams(
        size=384,  # sentence-transformers/all-MiniLM-L6-v2 dimension
        distance=Distance.COSINE
    )
)

print("Qdrant collection 'athena_knowledge' created successfully")
```

#### Step 1.5.4: Success Criteria

**Automated Verification:**
- [ ] Services start on Mac mini: `docker compose up -d`
- [ ] Qdrant health check: `curl http://192.168.10.181:6333/healthz`
- [ ] Redis health check: `redis-cli -h 192.168.10.181 PING`
- [ ] Qdrant collection created: `python scripts/init_qdrant.py`
- [ ] Redis memory limit enforced: `redis-cli -h 192.168.10.181 INFO memory | grep maxmemory`

**Manual Verification:**
- [ ] Qdrant web UI accessible: http://192.168.10.181:6333/dashboard
- [ ] Redis accepts connections from Mac Studio
- [ ] Storage volumes persist after restart

---

### Phase 1.6: Home Assistant Configuration (Week 4-5)

**Goal:** Setup HA Assist Pipelines with Wyoming STT/TTS

#### Step 1.6.1: Install Wyoming Add-ons

**In Home Assistant UI:**
1. Navigate to Settings → Add-ons
2. Add repository: https://github.com/rhasspy/hassio-addons
3. Install **Faster Whisper** add-on
4. Install **Piper** add-on

**Configure Faster Whisper:**
```yaml
# Configuration
language: en
model: tiny-en
beam_size: 1
```

**Configure Piper:**
```yaml
# Configuration
voice: en_US-lessac-medium
```

#### Step 1.6.2: Create Assist Pipelines

**Pipeline 1: CONTROL (Local)**
```yaml
# In HA UI: Settings → Voice Assistants → Add Pipeline
name: "Control Pipeline"
conversation_agent: "Home Assistant"
speech_to_text: "Faster Whisper"
text_to_speech: "Piper"
wake_word: "jarvis"
```

**Pipeline 2: KNOWLEDGE (LLM)**
```yaml
# First configure OpenAI Conversation integration
# Settings → Integrations → Add Integration → OpenAI Conversation

# Configuration:
api_key: "dummy-key"  # LiteLLM doesn't validate
base_url: "http://192.168.10.20:8000/v1"
model: "athena-medium"

# Then create pipeline
name: "Knowledge Pipeline"
conversation_agent: "OpenAI Conversation"
speech_to_text: "Faster Whisper"
text_to_speech: "Piper"
wake_word: "athena"
```

#### Step 1.6.3: Test Pipelines via HA UI

**Test Control Pipeline:**
1. Settings → Voice Assistants → Control Pipeline
2. Click "Test"
3. Say: "Turn on office lights"
4. Verify: HA processes command locally

**Test Knowledge Pipeline:**
1. Settings → Voice Assistants → Knowledge Pipeline
2. Click "Test"
3. Say: "What's the weather in Baltimore?"
4. Verify: Gateway receives request, orchestrator processes, returns answer

#### Step 1.6.4: Success Criteria

**Automated Verification:**
- [ ] Wyoming add-ons running: Check HA add-ons page
- [ ] STT works: Test transcription in HA
- [ ] TTS works: Test speech synthesis in HA
- [ ] OpenAI integration configured: Check integrations page
- [ ] Both pipelines created: Check voice assistants page

**Manual Verification:**
- [ ] Control pipeline responds to "turn on lights" command
- [ ] Knowledge pipeline calls Mac Studio gateway
- [ ] Gateway logs show incoming requests from HA
- [ ] Orchestrator logs show query processing
- [ ] End-to-end latency ≤5.5s for knowledge queries
- [ ] End-to-end latency ≤3.5s for control queries

---

### Phase 1.7: Integration and Testing (Week 5-6)

**Goal:** End-to-end voice queries working

#### Step 1.7.1: Deploy All Services

**Master Docker Compose:**
**File:** `deploy/compose/docker-compose.yml`
```yaml
version: '3.8'

services:
  gateway:
    extends:
      file: docker-compose.gateway.yml
      service: litellm

  orchestrator:
    build: ../../apps/orchestrator
    container_name: athena-orchestrator
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      LITELLM_URL: http://gateway:8000
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      REDIS_URL: redis://192.168.10.181:6379/0
      QDRANT_URL: http://192.168.10.181:6333
    depends_on:
      - gateway
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  rag-weather:
    extends:
      file: docker-compose.rag.yml
      service: rag-weather

  rag-airports:
    extends:
      file: docker-compose.rag.yml
      service: rag-airports

  rag-sports:
    extends:
      file: docker-compose.rag.yml
      service: rag-sports

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

volumes:
  ollama_data:
```

**Deploy script:** `scripts/deploy_phase1.sh`
```bash
#!/bin/bash
set -e

echo "Deploying Project Athena Phase 1..."

# Check environment
if [ ! -f config/env/.env ]; then
    echo "Error: config/env/.env not found. Copy from .env.example"
    exit 1
fi

# Load environment
source config/env/.env

# Deploy Mac mini services
echo "1. Deploying Mac mini services (Qdrant + Redis)..."
ssh jstuart@192.168.10.181 "cd ~/athena/mac-mini && docker compose up -d"

# Initialize Qdrant collection
echo "2. Initializing Qdrant collection..."
python scripts/init_qdrant.py

# Pull Ollama models
echo "3. Pulling Ollama models..."
ollama pull phi3:mini-q8
ollama pull llama3.1:8b-q4
# ollama pull llama3.1:13b-q4  # Optional, large

# Build Docker images
echo "4. Building Docker images..."
docker compose -f deploy/compose/docker-compose.yml build

# Start all services
echo "5. Starting all services..."
docker compose -f deploy/compose/docker-compose.yml up -d

# Wait for health checks
echo "6. Waiting for services to be healthy..."
sleep 30

# Run health checks
echo "7. Running health checks..."
curl -f http://localhost:8000/health || { echo "Gateway unhealthy"; exit 1; }
curl -f http://localhost:8001/health || { echo "Orchestrator unhealthy"; exit 1; }
curl -f http://localhost:8010/health || { echo "Weather RAG unhealthy"; exit 1; }
curl -f http://localhost:8011/health || { echo "Airports RAG unhealthy"; exit 1; }
curl -f http://localhost:8012/health || { echo "Sports RAG unhealthy"; exit 1; }

echo "✅ Phase 1 deployment complete!"
echo "Next steps:"
echo "1. Configure HA Assist Pipelines (see docs/HA_INTEGRATION.md)"
echo "2. Test voice queries via HA Voice device"
echo "3. Run integration tests: ./scripts/run_integration_tests.sh"
```

#### Step 1.7.2: Integration Test Suite

**File:** `tests/integration/test_phase1.py`
```python
import pytest
import aiohttp
import asyncio

BASE_GATEWAY_URL = "http://localhost:8000"
BASE_ORCHESTRATOR_URL = "http://localhost:8001"

@pytest.mark.asyncio
async def test_gateway_health():
    """Test gateway health endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_GATEWAY_URL}/health") as response:
            assert response.status == 200

@pytest.mark.asyncio
async def test_gateway_completion():
    """Test OpenAI-compatible completion"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "athena-small",
                "messages": [{"role": "user", "content": "What is 2+2?"}]
            },
            headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}"}
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert 'choices' in data
            assert len(data['choices']) > 0

@pytest.mark.asyncio
async def test_orchestrator_classify():
    """Test orchestrator classification"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_ORCHESTRATOR_URL}/query",
            json={"query": "turn on office lights"}
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data['category'] == 'control'

@pytest.mark.asyncio
async def test_orchestrator_weather():
    """Test weather query end-to-end"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_ORCHESTRATOR_URL}/query",
            json={"query": "what's the weather in Baltimore"}
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data['category'] == 'weather'
            assert 'Baltimore' in data['answer'] or 'temperature' in data['answer'].lower()

@pytest.mark.asyncio
async def test_latency_targets():
    """Test latency meets Phase 1 targets"""
    import time

    async with aiohttp.ClientSession() as session:
        # Control query (target: ≤3.5s)
        start = time.time()
        async with session.post(
            f"{BASE_ORCHESTRATOR_URL}/query",
            json={"query": "turn on lights"}
        ) as response:
            control_latency = time.time() - start
            assert response.status == 200

        assert control_latency <= 3.5, f"Control latency {control_latency}s exceeds 3.5s target"

        # Knowledge query (target: ≤5.5s)
        start = time.time()
        async with session.post(
            f"{BASE_ORCHESTRATOR_URL}/query",
            json={"query": "what's the weather"}
        ) as response:
            knowledge_latency = time.time() - start
            assert response.status == 200

        assert knowledge_latency <= 5.5, f"Knowledge latency {knowledge_latency}s exceeds 5.5s target"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### Step 1.7.3: Success Criteria

**Automated Verification:**
- [ ] Deployment script runs without errors: `./scripts/deploy_phase1.sh`
- [ ] All services healthy: `docker compose ps`
- [ ] Integration tests pass: `pytest tests/integration/test_phase1.py`
- [ ] Latency targets met (control ≤3.5s, knowledge ≤5.5s)

**Manual Verification:**
- [ ] Voice query "what's the weather" via HA Voice device returns accurate answer
- [ ] Voice query "turn on office lights" controls HA device
- [ ] Logs show complete request flow (STT → HA → Gateway → Orchestrator → RAG → Response → TTS)
- [ ] No crashes or errors in any service logs
- [ ] Prometheus metrics collected from all services

---

## 5. Testing Strategy

### Unit Tests

**Per-component testing:**
- Gateway: OpenAI spec compliance, model routing
- Orchestrator: Classification accuracy, graph execution
- RAG services: API integration, caching, error handling
- HA client: API methods, connection pooling

### Integration Tests

**End-to-end scenarios:**
1. Control query (lights, scenes, climate)
2. Weather query
3. Airport query
4. Sports query
5. Generic info query
6. Error handling (invalid query, timeout, API failure)

### Performance Tests

**Latency benchmarking:**
```bash
# scripts/benchmark_latency.sh
for i in {1..100}; do
    time curl -X POST http://localhost:8001/query \
        -d '{"query":"what'\''s the weather"}' \
        -H "Content-Type: application/json"
done | grep "real" | awk '{print $2}' | sort -n
```

**Target metrics:**
- P50: ≤4.0s
- P95: ≤5.5s
- P99: ≤7.0s

### Manual Voice Tests

**Voice device testing:**
1. Say "Jarvis, turn on office lights" (Control pipeline)
2. Say "Athena, what's the weather in Baltimore?" (Knowledge pipeline)
3. Say "Athena, when is the next Ravens game?" (Sports RAG)
4. Say "Athena, any delays at BWI airport?" (Airport RAG)
5. Say "Athena, what time is it?" (Simple info)

---

## 6. Performance Targets

### Phase 1 Latency Targets (Pre-Optimization)

| Query Type | P50 | P95 | P99 |
|------------|-----|-----|-----|
| Control (HA native) | ≤2.5s | ≤3.5s | ≤4.5s |
| Info (simple, small model) | ≤3.0s | ≤4.5s | ≤6.0s |
| Knowledge (RAG, medium model) | ≤4.0s | ≤5.5s | ≤7.0s |
| Complex (large model) | ≤5.0s | ≤7.0s | ≤9.0s |

**Component Breakdown:**
- STT (Whisper): ≤0.8s
- Classification: ≤0.1s
- RAG retrieval: ≤0.5s
- LLM inference: ≤2.0s (small), ≤3.5s (medium)
- Synthesis: ≤0.5s
- TTS (Piper): ≤0.8s
- Network overhead: ≤0.3s

### Success Rate Targets

- Control queries: ≥90% success rate
- Info queries: ≥85% success rate with high-confidence retrieval
- Overall system uptime: ≥99% (excluding planned maintenance)

---

## 7. Migration from Jetson

### Code Migration Checklist

**From `src/jetson/` to `apps/`:**

- [ ] `ha_client.py` → `apps/shared/ha_client.py` (with async, health checks, metrics)
- [ ] `facade/airbnb_intent_classifier.py` (v43) → `apps/orchestrator/classifier.py`
- [ ] `facade/handlers/weather.py` → `apps/rag/weather/handler.py`
- [ ] `facade/handlers/airports.py` → `apps/rag/airports/handler.py`
- [ ] `facade/handlers/sports.py` → `apps/rag/sports/handler.py`
- [ ] `caching.py` → Redis integration in each service
- [ ] `context_manager.py` → Orchestrator state management
- [ ] `metrics.py` → Prometheus metrics in each service
- [ ] `validation.py` → Orchestrator validation node

**Configuration Migration:**
- [ ] `config/ha_config.py` → Environment variables in `.env`
- [ ] `config/zones.yaml` → Keep for Phase 2 (multi-zone)
- [ ] `.env.example` → Update with Phase 1 requirements

**Test Migration:**
- [ ] Facade benchmarks → New integration test suite
- [ ] Intent classifier tests → Orchestrator classification tests

### Deprecation Plan

**Archive old implementation:**
```bash
mkdir -p deprecated/jetson-implementation
mv src/jetson/* deprecated/jetson-implementation/
mv athena-lite/ deprecated/athena-lite/
```

**Update README:**
```markdown
# Project Athena

**Current Implementation:** Mac Studio M4 + Mac mini M4 architecture (Phase 1 complete)

**Deprecated:** Jetson-based implementation archived in `deprecated/`
```

---

## 8. References

**Related Plans:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md) - Overall architecture
- [Component Deep-Dive Plans](2025-11-11-component-deep-dive-plans.md) - Technical specs for each component
- [Full Bootstrap Plan](2025-11-11-full-bootstrap-implementation.md) - Step-by-step from zero
- [Guest Mode & Quality Tracking](2025-11-11-guest-mode-and-quality-tracking.md) - Guest mode features (Phase 2)
- [Admin Interface Specification](2025-11-11-admin-interface-specification.md) - Web UI (Phase 3)
- [Kubernetes Deployment Strategy](2025-11-11-kubernetes-deployment-strategy.md) - K8s deployment (future)
- [Haystack RAG Eval DVC Integration](2025-11-11-haystack-rageval-dvc-integration.md) - Production RAG (future)

**Existing Code:**
- `/Users/jaystuart/dev/project-athena/src/jetson/` - Current Jetson implementation
- `/Users/jaystuart/dev/project-athena/tests/` - Existing test suite

**External Documentation:**
- LangGraph: https://langchain-ai.github.io/langgraph/
- LiteLLM: https://docs.litellm.ai/
- Home Assistant Voice: https://www.home-assistant.io/voice_control/
- Wyoming Protocol: https://github.com/rhasspy/wyoming

---

**Timeline:** 4-6 weeks
**Last Updated:** 2025-11-11
**Status:** Ready for implementation
