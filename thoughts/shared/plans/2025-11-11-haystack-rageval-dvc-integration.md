# Haystack, Open-RAG-Eval, and DVC Integration Plan

**Date:** 2025-11-11
**Status:** Planning
**Related Plans:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)
- [Guest Mode & Quality Tracking](2025-11-11-guest-mode-and-quality-tracking.md)
- [Admin Interface Specification](2025-11-11-admin-interface-specification.md)
- [Kubernetes Deployment Strategy](2025-11-11-kubernetes-deployment-strategy.md)

---

## Executive Summary

This plan integrates three production-grade tools into Project Athena to enhance RAG capabilities, quality monitoring, and version governance:

1. **Haystack** - Production RAG backbone replacing ad-hoc retrieval logic
2. **Open-RAG-Eval** - Continuous quality & hallucination monitoring
3. **DVC** - Model/data/config version control and audit trails

**Key Design Principles:**
- **Zero/low hot-path overhead:** When disabled, core system behaves exactly as before
- **Modular:** Each tool runs as its own service with thin adapter
- **Configurable:** Toggle via env flags, Admin UI, or per-request policy
- **Portable:** Docker Compose + Kubernetes Helm; GPU optional

---

## Table of Contents

1. [Design Goals](#1-design-goals)
2. [Haystack - Production RAG Backbone](#2-haystack---production-rag-backbone)
3. [Open-RAG-Eval - Quality & Hallucination Monitoring](#3-open-rag-eval---quality--hallucination-monitoring)
4. [DVC - Model/Data/Version Governance](#4-dvc---modeldataversion-governance)
5. [Architecture Integration](#5-architecture-integration)
6. [Packaging (Docker & K8s)](#6-packaging-docker--k8s)
7. [Observability & Performance](#7-observability--performance)
8. [Security & Privacy](#8-security--privacy)
9. [Rollout Plan](#9-rollout-plan)
10. [Implementation Timeline](#10-implementation-timeline)

---

## 1. Design Goals

### Core Principles

**1. Zero Impact When Disabled**
- Feature flags for each tool: `ATHENA_FEATURE_HAYSTACK`, `ATHENA_FEATURE_RAGEVAL`, `ATHENA_FEATURE_DVC`
- Legacy code paths remain active when features disabled
- No runtime dependencies on new services unless explicitly enabled

**2. Modular Service Architecture**
- Each tool runs as independent service
- Thin adapter layer in Orchestrator/LangGraph
- Services can be deployed/scaled independently
- Clean API boundaries

**3. Comprehensive Configuration**
- Environment variable toggles
- Admin UI runtime configuration
- Per-request policy overrides (guest vs owner mode)
- Category-specific settings (weather, news, airports, etc.)

**4. Deployment Portability**
- Docker Compose for Baltimore production
- Kubernetes Helm charts for open-source
- GPU optional for all services
- Works on Mac Studio M4, cloud, or bare-metal

### Integration Points

```
┌─────────────────────────────────────────────────────────┐
│                    Voice Devices                        │
│                (Wyoming Protocol)                        │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              Home Assistant                             │
│         (Device Control + Info Intents)                 │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              LangGraph Orchestrator                     │
│    (Classify → Route → Retrieve → Validate → Share)    │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  RAG Node    │  │  Eval Sink   │  │ Policy Edge  │ │
│  │   (HTTP)     │  │   (async)    │  │ (guest/own)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘ │
└─────────┼──────────────────┼────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────┐  ┌──────────────────┐
│ athena-haystack │  │ athena-rageval   │
│ (Retriever →    │  │ (Quality         │
│  Ranker →       │  │  Monitoring)     │
│  Generator)     │  │                  │
└─────────┬───────┘  └──────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│  Vector DB (Qdrant/Chroma)              │
│  + Ollama/LLM Gateway                   │
│  + Tool Connectors (Weather/News/etc)   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  DVC (Git + Remote Storage)             │
│  - Prompt templates                     │
│  - Pipeline configs                     │
│  - Eval datasets                        │
│  - Model version tags                   │
└─────────────────────────────────────────┘
```

---

## 2. Haystack - Production RAG Backbone

### 2.1 Purpose

Replace ad-hoc RAG pipeline with **Haystack pipelines** (retriever → ranker → generator), keeping local LLMs (Ollama/LLM Gateway) and vector DB (Qdrant/Chroma) but gaining:

- **Pluggable retrievers:** Dense (embeddings), sparse (BM25), hybrid
- **Flexible components:** Query rewriter, filters, cross-encoder ranker
- **Observability hooks:** Built-in metrics, tracing, logging
- **Easy A/B configs:** Different pipelines per category (weather/news/airports/sports/recipes/media)

### 2.2 Integration Points

**Where Haystack Plugs In:**

1. **LangGraph "Complex/Info Path" node** calls **Haystack API** instead of bespoke RAG code
2. **Home Assistant "Info intents"** route to LangGraph → Haystack for retrieval/generation

**Request Flow:**
```
User: "What's the weather forecast for Baltimore?"
  ↓
STT (Faster-Whisper)
  ↓
Intent Router (Weather/Info)
  ↓
LangGraph Info Node
  ↓
POST /v1/rag/query to athena-haystack
  {
    "query": "weather forecast Baltimore",
    "category": "weather",
    "mode": "guest",
    "top_k": 8,
    "rerank": false
  }
  ↓
Haystack Pipeline:
  1. QueryRewriter (optional)
  2. DenseRetriever (Vector DB query)
  3. CrossEncoder Ranker (optional)
  4. LLM Generator (Ollama mistral:7b-q4)
  ↓
Response + Citations
  ↓
LangGraph → TTS (Piper) → Device
```

### 2.3 Service Layout

**Service Name:** `athena-haystack`

**API Endpoints:**
- `POST /v1/rag/query` - Main RAG query endpoint
- `GET /v1/rag/pipelines` - List available pipelines
- `POST /v1/rag/pipelines/{name}/config` - Update pipeline config
- `GET /health` - Health check

**Request Schema:**
```json
{
  "query": "string",
  "category": "weather|news|airports|sports|recipes|media|dining|streaming|general",
  "mode": "guest|owner",
  "top_k": 8,
  "rerank": false,
  "max_context_tokens": 4096,
  "filters": {
    "airport_codes": ["PHL", "BWI", "EWR"],
    "date_range": "2025-11-11T00:00:00Z/2025-11-12T00:00:00Z"
  }
}
```

**Response Schema:**
```json
{
  "answer": "string",
  "citations": [
    {
      "source": "weather.gov",
      "title": "Baltimore Forecast",
      "url": "https://...",
      "retrieved_at": "2025-11-11T10:30:00Z",
      "confidence": 0.92
    }
  ],
  "metadata": {
    "pipeline": "weather_standard",
    "retrieval_time_ms": 87,
    "generation_time_ms": 423,
    "total_time_ms": 510,
    "model": "mistral:7b-q4",
    "top_k_used": 8,
    "rerank_enabled": false
  }
}
```

### 2.4 Configuration Toggles

**Global Feature Flag:**
```bash
ATHENA_FEATURE_HAYSTACK=true|false
```

**Per-Category Toggles:**
```bash
# Enable/disable RAG categories
RAG_WEATHER_ENABLED=true
RAG_NEWS_ENABLED=true
RAG_AIRPORT_ENABLED=true
RAG_SPORTS_ENABLED=true
RAG_RECIPES_ENABLED=true
RAG_MEDIA_ENABLED=true
RAG_DINING_ENABLED=true
RAG_STREAMING_ENABLED=true
```

**Retrieval Configuration:**
```bash
# Retrieval settings
RAG_TOPK=8                    # Number of documents to retrieve
RAG_RERANK=true|false         # Enable cross-encoder reranking
RAG_MAX_CONTEXT_TOKENS=4096   # Max context for LLM
RAG_RETRIEVAL_TIMEOUT_MS=150  # Timeout for retrieval

# Ranker settings (if enabled)
RAG_RANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RAG_RANKER_TOP_K=5            # Re-rank top 5 from retrieval
```

**LLM Configuration:**
```bash
# Generator/LLM binding
RAG_LLM_TARGET=ollama://mistral:7b-q4
# Alternatives:
# RAG_LLM_TARGET=ollama://llama3.1:8b-q4
# RAG_LLM_TARGET=ollama://phi3:mini-q8
# RAG_LLM_TARGET=http://llm-gateway:8000/v1/completions
```

**Mode-Specific Profiles:**
```bash
# Guest mode uses stricter settings
RAG_GUEST_MODE_PROFILE=strict|standard|off

# Strict profile (default for guests):
# - top_k: 6
# - rerank: false (latency priority)
# - max_context: 3072
# - timeout: 100ms

# Standard profile (owner default):
# - top_k: 8
# - rerank: true
# - max_context: 4096
# - timeout: 150ms
```

### 2.5 Pipeline Definitions

**Weather Pipeline:**
```yaml
# pipelines/weather_standard.yaml
name: weather_standard
components:
  - name: retriever
    type: EmbeddingRetriever
    params:
      document_store: qdrant
      embedding_model: sentence-transformers/all-MiniLM-L6-v2
      top_k: 8
      filters:
        category: weather
  - name: prompt_builder
    type: PromptBuilder
    params:
      template: |
        Answer the weather question using the provided context.
        Include temperature, conditions, and any relevant alerts.

        Context:
        {% for doc in documents %}
        - {{ doc.content }}
        {% endfor %}

        Question: {{ query }}
        Answer:
  - name: generator
    type: LLMGenerator
    params:
      model: mistral:7b-q4
      temperature: 0.3
      max_tokens: 300

pipelines:
  - name: weather_query
    nodes:
      - name: retriever
        inputs: [Query]
      - name: prompt_builder
        inputs: [retriever]
      - name: generator
        inputs: [prompt_builder]
```

**Airport Pipeline (with filters):**
```yaml
# pipelines/airport_standard.yaml
name: airport_standard
components:
  - name: query_rewriter
    type: QueryRewriter
    params:
      model: phi3:mini-q8
      prompt: "Extract airport codes and convert to full names"
  - name: retriever
    type: EmbeddingRetriever
    params:
      document_store: qdrant
      top_k: 10
      filters:
        category: airport
        airport_code: [PHL, BWI, EWR, LGA, JFK, IAD, DCA]
  - name: ranker
    type: CrossEncoderRanker
    params:
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
      top_k: 5
  - name: generator
    type: LLMGenerator
    params:
      model: mistral:7b-q4
      temperature: 0.2

pipelines:
  - name: airport_query
    nodes:
      - name: query_rewriter
        inputs: [Query]
      - name: retriever
        inputs: [query_rewriter]
      - name: ranker
        inputs: [retriever]
      - name: generator
        inputs: [ranker]
```

### 2.6 Docker Compose Integration

```yaml
services:
  athena-haystack:
    image: deepset/haystack:latest
    container_name: athena-haystack
    restart: unless-stopped
    environment:
      # Feature flags
      ATHENA_FEATURE_HAYSTACK: "${ATHENA_FEATURE_HAYSTACK:-true}"

      # LLM configuration
      RAG_LLM_TARGET: "${RAG_LLM_TARGET:-ollama://mistral:7b-q4}"
      OLLAMA_BASE_URL: "http://ollama:11434"

      # Retrieval settings
      RAG_TOPK: "${RAG_TOPK:-8}"
      RAG_RERANK: "${RAG_RERANK:-false}"
      RAG_MAX_CONTEXT_TOKENS: "${RAG_MAX_CONTEXT_TOKENS:-4096}"

      # Data sources
      VECTOR_DB_URL: "${VECTOR_DB_URL:-http://qdrant:6333}"
      VECTOR_DB_COLLECTION: "${VECTOR_DB_COLLECTION:-athena_knowledge}"

      # Mode profiles
      RAG_GUEST_MODE_PROFILE: "${RAG_GUEST_MODE_PROFILE:-strict}"

      # Category toggles
      RAG_WEATHER_ENABLED: "${RAG_WEATHER_ENABLED:-true}"
      RAG_NEWS_ENABLED: "${RAG_NEWS_ENABLED:-true}"
      RAG_AIRPORT_ENABLED: "${RAG_AIRPORT_ENABLED:-true}"
      RAG_SPORTS_ENABLED: "${RAG_SPORTS_ENABLED:-true}"
      RAG_RECIPES_ENABLED: "${RAG_RECIPES_ENABLED:-true}"
      RAG_MEDIA_ENABLED: "${RAG_MEDIA_ENABLED:-true}"

    volumes:
      - ./config/haystack/pipelines:/app/pipelines:ro
      - ./config/haystack/models:/app/models:ro

    depends_on:
      - qdrant
      - ollama

    networks:
      - athena

    ports:
      - "8001:8000"  # Haystack API

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 2.7 Kubernetes Integration

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena-haystack
  namespace: athena
spec:
  replicas: 2
  selector:
    matchLabels:
      app: athena-haystack
  template:
    metadata:
      labels:
        app: athena-haystack
    spec:
      containers:
      - name: haystack
        image: deepset/haystack:latest
        env:
        - name: ATHENA_FEATURE_HAYSTACK
          value: "true"
        - name: RAG_LLM_TARGET
          value: "ollama://mistral:7b-q4"
        - name: OLLAMA_BASE_URL
          value: "http://ollama:11434"
        - name: VECTOR_DB_URL
          value: "http://qdrant:6333"
        - name: RAG_TOPK
          value: "8"
        - name: RAG_RERANK
          value: "false"
        volumeMounts:
        - name: pipelines
          mountPath: /app/pipelines
          readOnly: true
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: pipelines
        configMap:
          name: haystack-pipelines
---
apiVersion: v1
kind: Service
metadata:
  name: athena-haystack
  namespace: athena
spec:
  selector:
    app: athena-haystack
  ports:
  - name: http
    port: 8000
    targetPort: 8000
```

**Helm Values:**
```yaml
# values.yaml
haystack:
  enabled: true
  replicaCount: 2
  image:
    repository: deepset/haystack
    tag: latest
    pullPolicy: IfNotPresent

  config:
    llm_target: "ollama://mistral:7b-q4"
    vector_db_url: "http://qdrant:6333"
    top_k: 8
    rerank: false
    max_context_tokens: 4096
    guest_mode_profile: "strict"

  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

  # Optional GPU support for ranker
  gpu:
    enabled: false
    count: 0
```

### 2.8 Admin UI Integration

**New Sections in Admin Interface:**

**1. RAG Configuration Page** (`/admin/rag`)
- **Pipeline Profiles:**
  - Dropdown per category: weather, news, airports, sports, recipes, media, dining, streaming
  - Select pipeline: `{category}_strict`, `{category}_standard`, `{category}_advanced`
  - Preview pipeline components (read-only YAML viewer)

- **Retrieval Settings:**
  - Top-K slider (1-20, default 8)
  - Rerank toggle (on/off)
  - Max context tokens (1024-8192, default 4096)
  - Retrieval timeout (50-500ms, default 150ms)

- **LLM Target:**
  - Dropdown: ollama://mistral:7b-q4, ollama://llama3.1:8b-q4, ollama://phi3:mini-q8
  - Connection test button
  - Model info (parameters, quantization)

- **Mode Profiles:**
  - Guest mode profile: strict/standard/off
  - Owner mode profile: standard/advanced
  - Per-mode overrides (top-k, rerank, timeout)

**2. Data Source Management** (`/admin/rag/sources`)
- **Category Toggles:**
  - Enable/disable per category with toggle switches
  - Connection status indicators (green/yellow/red)
  - Last refresh timestamp

- **Airport Feed Configuration:**
  - Multi-select: PHL, BWI, EWR, LGA, JFK, IAD, DCA
  - Refresh interval (5-60 min, default 15 min)
  - API key status

- **Source Health:**
  - Table showing: source name, status, last successful fetch, error count
  - Test connection button per source
  - Force refresh button

**3. Pipeline Testing** (`/admin/rag/test`)
- **Query Tester:**
  - Input: test query
  - Category dropdown
  - Mode selection (guest/owner)
  - Execute button
  - Results display: answer, citations, metadata (timing, model, top-k)

- **A/B Comparison:**
  - Side-by-side comparison of two pipelines
  - Latency comparison
  - Quality comparison (if eval enabled)

### 2.9 Performance Guardrails

**Latency Optimization:**

1. **Keep retrieval fast:**
   - Top-K ≤ 10 for most queries
   - Lightweight embeddings (MiniLM-L6-v2, 384 dims)
   - Vector DB query timeout: 150ms

2. **Conditional reranking:**
   - Disable rerank for guest mode (latency priority)
   - Enable rerank for owner mode or complex queries
   - Use lightweight ranker (MiniLM-L-6-v2, ~23ms per query)

3. **Caching:**
   - Cache embeddings for common queries (15-60 min TTL)
   - Cache results per category (weather: 10 min, news: 15 min, airports: 5 min)
   - Redis-backed cache with automatic eviction

4. **Timeouts:**
   - Retrieval: 150ms
   - Reranking: 50ms
   - Generation: 2000ms
   - Total query timeout: 3000ms (fail gracefully)

**SLOs:**
- Retrieval latency P95 < 120ms
- RAG end-to-end P95 < 3.5s
- Cache hit rate > 30%
- Error rate < 2%

---

## 3. Open-RAG-Eval - Quality & Hallucination Monitoring

### 3.1 Purpose

Provide **continuous evaluation** and **hallucination tracking** for RAG answers without blocking the hot path (unless explicitly enabled for owners).

**Key Benefits:**
- Detect hallucinations and low-quality answers
- Track faithfulness to retrieved documents
- Monitor citation coverage
- Identify categories needing improvement
- Support A/B testing of pipelines

### 3.2 Integration Points

**Where RAG Eval Plugs In:**

1. **After** LangGraph produces a response, Orchestrator asynchronously posts record to `athena-rageval`
2. **Optionally** in owner mode, block and run quick sanity check before TTS
3. **Nightly batch:** Analyze all evaluations, compute trends, flag issues

**Evaluation Modes:**

**Async Mode (Recommended):**
- Logs evaluation events to queue
- Offline scoring (0-60 seconds delay)
- Dashboards and alerts
- **No latency impact on users**

**Semi-Sync Mode (Owner Only, Optional):**
- Run fast rule checks + brief verifier model before TTS
- Small local LLM (phi3:mini-q8) for verification
- **Adds ~150-400ms**
- Catches obvious hallucinations in real-time

**Full Cross-Model Validation (Owner Only, Optional):**
- Main model answer → validate with second model
- Quorum voting (2 out of 3 models agree)
- **Adds ~300-700ms**
- Highest confidence, highest latency

### 3.3 Service Layout

**Service Name:** `athena-rageval`

**API Endpoints:**
- `POST /v1/eval/submit` - Submit evaluation event
- `GET /v1/eval/scores/{request_id}` - Get evaluation scores
- `GET /v1/eval/trends` - Get quality trends by category
- `GET /v1/eval/flags` - Get flagged answers requiring review
- `GET /health` - Health check

**Evaluation Event Schema:**
```json
{
  "request_id": "uuid",
  "timestamp": "2025-11-11T10:30:00Z",
  "query": "What's the weather in Baltimore?",
  "category": "weather",
  "mode": "guest",
  "retrieved_docs": [
    {
      "content": "Baltimore weather forecast: Sunny, 72°F...",
      "source": "weather.gov",
      "score": 0.92
    }
  ],
  "answer": "The weather in Baltimore today is sunny with...",
  "citations": [
    {
      "source": "weather.gov",
      "url": "https://..."
    }
  ],
  "metadata": {
    "pipeline": "weather_standard",
    "model": "mistral:7b-q4",
    "generation_time_ms": 423
  }
}
```

**Evaluation Response Schema:**
```json
{
  "request_id": "uuid",
  "scores": {
    "faithfulness": 0.94,
    "citation_coverage": 1.0,
    "answerability": 0.88,
    "context_relevance": 0.91,
    "overall": 0.93
  },
  "flags": [
    {
      "type": "low_faithfulness",
      "severity": "warning",
      "message": "Answer contains unsupported claim",
      "details": "Claim: 'high of 85°F' not found in retrieved docs"
    }
  ],
  "verified": true,
  "verifier_model": "phi3:mini-q8"
}
```

### 3.4 Configuration Toggles

**Global Feature Flag:**
```bash
ATHENA_FEATURE_RAGEVAL=true|false
```

**Evaluation Modes:**
```bash
# Mode selection
RAGEVAL_MODE=async|semi_sync|sync_owner_only

# async: Log events, offline scoring (default)
# semi_sync: Run fast checks before TTS (owner only)
# sync_owner_only: Full cross-model validation for owner
```

**Cross-Model Validation:**
```bash
# Enable cross-model validation
RAGEVAL_CMV_ENABLED=true|false

# Verifier LLM (lightweight, fast)
RAGEVAL_VERIFIER_LLM=ollama://phi3:mini-q8

# Alternative verifiers
# RAGEVAL_VERIFIER_LLM=ollama://qwen2:1.5b-q8
# RAGEVAL_VERIFIER_LLM=ollama://tinyllama:1.1b-q8
```

**Rule-Based Checks:**
```bash
# Enable domain-specific heuristics
RAGEVAL_RULESETS=weather,airports,sports

# Weather rules: require temperature, condition, location
# Airport rules: require airport code, terminal, gate (if available)
# Sports rules: require team names, scores, date
```

**Guest Mode Enforcement:**
```bash
# How to handle low-quality answers in guest mode
RAGEVAL_ENFORCEMENT_GUEST=log_only|soft_block|off

# log_only: Log but allow answer (default)
# soft_block: Ask clarifying question instead
# off: Disable enforcement
```

**Thresholds:**
```bash
# Faithfulness threshold
RAGEVAL_FAITHFULNESS_THRESHOLD=0.75

# Citation coverage threshold
RAGEVAL_CITATION_THRESHOLD=0.80

# Answerability threshold
RAGEVAL_ANSWERABILITY_THRESHOLD=0.70
```

### 3.5 Evaluation Metrics

**Faithfulness Score (0-1):**
- Measures if answer is supported by retrieved documents
- Uses NLI (Natural Language Inference) model
- Breaks answer into claims, checks each against docs

**Citation Coverage (0-1):**
- Percentage of answer supported by citations
- Checks if sources are actually used in answer
- Flags missing or incorrect citations

**Answerability (0-1):**
- Can the query be answered from retrieved docs?
- Low score indicates retrieval failure
- Helps identify missing data sources

**Context Relevance (0-1):**
- Are retrieved docs relevant to the query?
- Helps tune retrieval parameters
- Low score indicates noisy retrieval

**Overall Score:**
```python
overall = (
    0.4 * faithfulness +
    0.3 * citation_coverage +
    0.2 * answerability +
    0.1 * context_relevance
)
```

### 3.6 Hallucination Detection Rules

**Domain-Specific Heuristics:**

**Weather Category:**
```python
def check_weather_answer(query, answer, retrieved_docs):
    flags = []

    # Extract temperature from answer
    answer_temp = extract_temperature(answer)
    doc_temps = [extract_temperature(doc) for doc in retrieved_docs]

    # Check if temperature is within range
    if answer_temp and doc_temps:
        if not any(abs(answer_temp - t) <= 5 for t in doc_temps):
            flags.append({
                "type": "temperature_mismatch",
                "severity": "warning",
                "message": f"Answer temp {answer_temp}°F not in docs {doc_temps}"
            })

    # Check for required elements
    required = ["temperature", "condition", "location"]
    missing = [r for r in required if r not in extract_elements(answer)]
    if missing:
        flags.append({
            "type": "missing_elements",
            "severity": "info",
            "message": f"Missing: {', '.join(missing)}"
        })

    return flags
```

**Airport Category:**
```python
def check_airport_answer(query, answer, retrieved_docs):
    flags = []

    # Extract airport codes
    query_codes = extract_airport_codes(query)
    answer_codes = extract_airport_codes(answer)
    doc_codes = [extract_airport_codes(doc) for doc in retrieved_docs]

    # Check if answer mentions queried airport
    if query_codes and not any(c in answer_codes for c in query_codes):
        flags.append({
            "type": "airport_mismatch",
            "severity": "error",
            "message": f"Query asked about {query_codes}, answer mentions {answer_codes}"
        })

    # Check if codes in answer are supported by docs
    unsupported = [c for c in answer_codes if not any(c in dc for dc in doc_codes)]
    if unsupported:
        flags.append({
            "type": "unsupported_airport",
            "severity": "warning",
            "message": f"Airports {unsupported} not in retrieved docs"
        })

    return flags
```

**Sports Category:**
```python
def check_sports_answer(query, answer, retrieved_docs):
    flags = []

    # Check score accuracy
    answer_scores = extract_scores(answer)
    doc_scores = [extract_scores(doc) for doc in retrieved_docs]

    if answer_scores and doc_scores:
        if not any(s == answer_scores for s in doc_scores):
            flags.append({
                "type": "score_mismatch",
                "severity": "error",
                "message": f"Answer score {answer_scores} not in docs"
            })

    # Check team name accuracy
    answer_teams = extract_team_names(answer)
    doc_teams = [extract_team_names(doc) for doc in retrieved_docs]

    unsupported_teams = [t for t in answer_teams if not any(t in dt for dt in doc_teams)]
    if unsupported_teams:
        flags.append({
            "type": "unsupported_team",
            "severity": "warning",
            "message": f"Teams {unsupported_teams} not in docs"
        })

    return flags
```

### 3.7 Cross-Model Validation

**When Enabled:**
- Owner mode with `RAGEVAL_CMV_ENABLED=true`
- Optionally: complex queries (user opt-in)
- Configurable per category

**Flow:**
```
1. Main LLM generates answer (Model A: mistral:7b)
2. Verifier LLM generates answer (Model B: phi3:mini)
3. Compare answers:
   - Semantic similarity (cosine > 0.85)
   - Fact agreement (key entities, numbers)
   - Citation overlap
4. If disagreement:
   - Third model tie-breaker (Model C: llama3.1:8b)
   - Quorum voting (2 out of 3)
5. Return most confident answer + confidence score
```

**Latency Impact:**
```
Mode A only:           ~500ms (baseline)
Mode A + B:            ~800ms (+300ms)
Mode A + B + C:        ~1200ms (+700ms)
```

**Configuration:**
```bash
# Enable CMV
RAGEVAL_CMV_ENABLED=true

# Models
RAGEVAL_PRIMARY_LLM=ollama://mistral:7b-q4
RAGEVAL_VERIFIER_LLM=ollama://phi3:mini-q8
RAGEVAL_TIEBREAKER_LLM=ollama://llama3.1:8b-q4

# Thresholds
RAGEVAL_CMV_SIMILARITY_THRESHOLD=0.85  # Cosine similarity
RAGEVAL_CMV_ENTITY_AGREEMENT=0.90      # Named entity overlap

# When to trigger CMV
RAGEVAL_CMV_CATEGORIES=airports,sports,dining  # High-stakes categories
RAGEVAL_CMV_OWNER_ONLY=true                    # Only for owner mode
```

### 3.8 Docker Compose Integration

```yaml
services:
  athena-rageval:
    image: vectara/open-rag-eval:latest
    container_name: athena-rageval
    restart: unless-stopped
    environment:
      # Feature flags
      ATHENA_FEATURE_RAGEVAL: "${ATHENA_FEATURE_RAGEVAL:-true}"

      # Mode configuration
      RAGEVAL_MODE: "${RAGEVAL_MODE:-async}"
      RAGEVAL_CMV_ENABLED: "${RAGEVAL_CMV_ENABLED:-false}"

      # LLM configuration
      RAGEVAL_VERIFIER_LLM: "${RAGEVAL_VERIFIER_LLM:-ollama://phi3:mini-q8}"
      OLLAMA_BASE_URL: "http://ollama:11434"

      # Rulesets
      RAGEVAL_RULESETS: "${RAGEVAL_RULESETS:-weather,airports,sports}"

      # Thresholds
      RAGEVAL_FAITHFULNESS_THRESHOLD: "${RAGEVAL_FAITHFULNESS_THRESHOLD:-0.75}"
      RAGEVAL_CITATION_THRESHOLD: "${RAGEVAL_CITATION_THRESHOLD:-0.80}"
      RAGEVAL_ANSWERABILITY_THRESHOLD: "${RAGEVAL_ANSWERABILITY_THRESHOLD:-0.70}"

      # Guest mode enforcement
      RAGEVAL_ENFORCEMENT_GUEST: "${RAGEVAL_ENFORCEMENT_GUEST:-log_only}"

      # Storage
      STORAGE_URL: "${EVAL_STORE_URL:-postgresql://eval_user:password@postgres:5432/athena_eval}"
      REDIS_URL: "${REDIS_URL:-redis://redis:6379/2}"

    volumes:
      - ./config/rageval/rules:/app/rules:ro
      - eval_data:/app/data

    depends_on:
      - postgres
      - redis
      - ollama
      - athena-orchestrator

    networks:
      - athena

    ports:
      - "8002:8000"  # RAG Eval API

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  eval_data:
```

### 3.9 Kubernetes Integration

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena-rageval
  namespace: athena
spec:
  replicas: 2
  selector:
    matchLabels:
      app: athena-rageval
  template:
    metadata:
      labels:
        app: athena-rageval
    spec:
      containers:
      - name: rageval
        image: vectara/open-rag-eval:latest
        env:
        - name: ATHENA_FEATURE_RAGEVAL
          value: "true"
        - name: RAGEVAL_MODE
          value: "async"
        - name: RAGEVAL_CMV_ENABLED
          value: "false"
        - name: RAGEVAL_VERIFIER_LLM
          value: "ollama://phi3:mini-q8"
        - name: OLLAMA_BASE_URL
          value: "http://ollama:11434"
        - name: STORAGE_URL
          valueFrom:
            secretKeyRef:
              name: rageval-secrets
              key: postgres-url
        - name: REDIS_URL
          value: "redis://redis:6379/2"
        volumeMounts:
        - name: rules
          mountPath: /app/rules
          readOnly: true
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "1"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: rules
        configMap:
          name: rageval-rules
---
apiVersion: v1
kind: Service
metadata:
  name: athena-rageval
  namespace: athena
spec:
  selector:
    app: athena-rageval
  ports:
  - name: http
    port: 8000
    targetPort: 8000
```

### 3.10 Admin UI Integration

**New Sections:**

**1. Quality Dashboard** (`/admin/quality`)
- **Overview Cards:**
  - Average faithfulness (last 24h)
  - Citation coverage (last 24h)
  - Flagged answers count
  - Total evaluations

- **Trend Charts:**
  - Faithfulness over time (line chart, per category)
  - Category breakdown (bar chart: weather, news, airports, sports, etc.)
  - Mode comparison (guest vs owner quality)

- **Recent Flags:**
  - Table: timestamp, query, category, flag type, severity
  - Click to view full evaluation details
  - Filter by category, severity, mode

**2. Evaluation Details** (`/admin/quality/eval/{request_id}`)
- **Query Information:**
  - Original query
  - Category, mode, timestamp
  - User ID (anonymized for guest)

- **Retrieved Documents:**
  - List of docs with relevance scores
  - Highlight: which docs were cited

- **Generated Answer:**
  - Full answer text
  - Citations with click-to-source
  - Confidence score

- **Evaluation Scores:**
  - Faithfulness: 0.94 (green/yellow/red indicator)
  - Citation coverage: 1.0
  - Answerability: 0.88
  - Context relevance: 0.91

- **Flags:**
  - List of all flags with severity
  - Detailed explanations
  - Rule/model that triggered flag

- **Cross-Model Validation (if enabled):**
  - Model A answer
  - Model B answer
  - Model C answer (if tie-breaker used)
  - Agreement scores
  - Final consensus

**3. Ruleset Configuration** (`/admin/quality/rules`)
- **Enable Rules per Category:**
  - Weather: temperature_check, condition_check, location_check
  - Airports: code_check, terminal_check, gate_check
  - Sports: score_check, team_check, date_check

- **Threshold Configuration:**
  - Faithfulness threshold slider (0.5-1.0, default 0.75)
  - Citation threshold slider (0.5-1.0, default 0.80)
  - Answerability threshold slider (0.5-1.0, default 0.70)

- **Custom Rules:**
  - Add regex-based checks
  - Entity extraction rules
  - Numeric validation rules

**4. Cross-Model Validation Policy** (`/admin/quality/cmv`)
- **Global Settings:**
  - Enable CMV: on/off toggle
  - Owner only: checkbox
  - Guest opt-in: checkbox (allow guests to request validation)

- **Model Configuration:**
  - Primary LLM: dropdown
  - Verifier LLM: dropdown
  - Tie-breaker LLM: dropdown
  - Test connection buttons

- **Category Settings:**
  - Enable CMV per category: weather, news, airports, sports, etc.
  - Priority categories (always validate): airports, sports, dining

- **Thresholds:**
  - Similarity threshold (0.80-0.95, default 0.85)
  - Entity agreement (0.80-0.95, default 0.90)

---

## 4. DVC - Model/Data/Version Governance

### 4.1 Purpose

Track **prompt templates**, **retriever settings**, **model versions**, **few-shot exemplars**, and **RAG corpora** so you can:

- Audit exactly what produced any answer
- Roll back bad changes quickly
- A/B test configuration changes
- Reproduce evaluation results
- Track model/prompt evolution over time

**DVC (Data Version Control)** extends Git to handle large files and datasets, providing:
- Versioned storage for models, configs, datasets
- Remote storage backends (S3, GCS, Azure, NFS, SSH)
- Lightweight metadata in Git (actual data in remote)
- Pipeline tracking and reproduction

### 4.2 What Gets Tracked

**Configuration Files:**
```
/configs/
  haystack/
    pipelines/
      weather_standard.yaml
      airport_standard.yaml
      sports_standard.yaml
      ...
    models/
      embedding_config.yaml
      ranker_config.yaml
      generator_config.yaml
  langgraph/
    graphs/
      owner_graph.json
      guest_graph.json
    policies/
      owner_policy.yaml
      guest_policy.yaml
  security_modes.yaml
  rag_sources.yaml
  evaluation_thresholds.yaml
```

**Prompt Templates:**
```
/models/
  prompts/
    weather_prompt.txt
    airport_prompt.txt
    sports_prompt.txt
    general_prompt.txt
    owner_system_prompt.txt
    guest_system_prompt.txt
  few_shot/
    weather_examples.json
    airport_examples.json
    sports_examples.json
```

**Evaluation Datasets:**
```
/data/
  eval/
    weather_test_set.json       # 50 weather queries + ground truth
    airport_test_set.json        # 50 airport queries + ground truth
    sports_test_set.json         # 50 sports queries + ground truth
    regression_suite.json        # Core 200 queries, must pass
  seeds/
    golden_answers.json          # High-quality reference answers
    edge_cases.json              # Known challenging queries
```

**Model Metadata (not actual weights):**
```
/models/
  registry.yaml                  # Model versions in use
  # Example:
  # embedding_model: sentence-transformers/all-MiniLM-L6-v2@v2.2.0
  # primary_llm: mistral:7b-q4@2024-11-01
  # verifier_llm: phi3:mini-q8@2024-10-15
```

### 4.3 DVC Setup

**Installation:**
```bash
# In project-athena repo
cd /Users/jaystuart/dev/project-athena

# Install DVC
pip install dvc dvc-s3  # or dvc-gs, dvc-azure, dvc-ssh

# Initialize DVC
dvc init

# Configure remote (Synology NFS)
dvc remote add -d synology ssh://synology.local/volume1/athena-dvc
dvc remote modify synology user jstuart

# Or use S3-compatible
dvc remote add -d minio s3://athena-dvc
dvc remote modify minio endpointurl http://192.168.10.164:9000
```

**Track Directories:**
```bash
# Track config directories
dvc add configs/
dvc add models/prompts/
dvc add data/eval/

# Commit to Git
git add configs.dvc models/prompts.dvc data/eval.dvc .gitignore
git commit -m "Add DVC tracking for configs, prompts, eval data"

# Push data to remote
dvc push
```

### 4.4 Configuration Toggles

```bash
# Feature flag
ATHENA_FEATURE_DVC=true|false

# Remote storage
DVC_REMOTE=synology|minio|s3|gcs|azure
DVC_REMOTE_URL=ssh://synology.local/volume1/athena-dvc

# Tracked directories
DVC_TRACK_DIRS=/configs,/models/prompts,/data/eval

# Auto-commit on config changes
DVC_AUTO_COMMIT=true|false

# Require DVC tag for production deploys
DVC_ENFORCE_TAGS=true|false
```

### 4.5 Workflow Examples

**Development Workflow:**

**1. Make Configuration Changes:**
```bash
# Edit Haystack pipeline
vim configs/haystack/pipelines/weather_standard.yaml

# Change: top_k from 8 to 10
# Change: enable reranking

# Track changes
dvc add configs/
git add configs.dvc
git commit -m "Increase weather pipeline top_k to 10, enable reranking"
dvc push
```

**2. Test Changes:**
```bash
# Run regression tests
pytest tests/eval/test_weather_pipeline.py

# Check quality metrics
python scripts/eval_pipeline.py --category weather --dataset data/eval/weather_test_set.json

# Compare to baseline
python scripts/compare_versions.py --baseline v1.2.0 --current HEAD
```

**3. Deploy with Tag:**
```bash
# Tag deployment
git tag deploy-2025-11-11
dvc tag add deploy-2025-11-11

# Push tag
git push origin deploy-2025-11-11
dvc push
```

**Rollback Workflow:**

**1. Identify Bad Deploy:**
```bash
# Admin UI shows quality drop after deploy-2025-11-11
# Roll back to previous tag: deploy-2025-11-10
```

**2. Rollback:**
```bash
# Checkout previous tag
git checkout deploy-2025-11-10
dvc checkout

# Verify configs
ls -la configs/haystack/pipelines/

# Redeploy
docker compose up -d athena-haystack
# or
helm upgrade athena ./charts/athena --set version=deploy-2025-11-10
```

**3. Verify Rollback:**
```bash
# Check quality dashboard
# Confirm metrics recovered

# Document incident
git tag rollback-2025-11-11-incident
git push origin rollback-2025-11-11-incident
```

### 4.6 Integration with CI/CD

**GitHub Actions Workflow:**

```yaml
# .github/workflows/test-config-changes.yaml
name: Test Configuration Changes

on:
  pull_request:
    paths:
      - 'configs/**'
      - 'models/prompts/**'

jobs:
  test-configs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup DVC
        run: |
          pip install dvc dvc-s3
          dvc remote modify synology --local user ${{ secrets.DVC_USER }}
          dvc remote modify synology --local password ${{ secrets.DVC_PASSWORD }}

      - name: Pull DVC data
        run: dvc pull

      - name: Run Regression Tests
        run: |
          pytest tests/eval/test_all_categories.py

      - name: Evaluate Quality
        run: |
          python scripts/eval_all_pipelines.py --dataset data/eval/regression_suite.json

      - name: Compare to Baseline
        run: |
          python scripts/compare_versions.py --baseline main --current ${{ github.sha }}

      - name: Post Results
        uses: actions/github-script@v6
        with:
          script: |
            // Post quality comparison as PR comment
            const fs = require('fs');
            const results = fs.readFileSync('comparison_results.json', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Quality Comparison\n\n${results}`
            });
```

### 4.7 Admin UI Integration

**New Sections:**

**1. Version Control Page** (`/admin/versions`)
- **Current Deployment:**
  - Version tag: `deploy-2025-11-11`
  - Commit hash: `a1b2c3d`
  - Deployed at: 2025-11-11 10:30 UTC
  - Deployed by: jstuart

- **Version History:**
  - Table: tag, commit, timestamp, deployer, status (active/rolled back)
  - Click to view diff
  - Rollback button (with confirmation)

- **Rollback Workflow:**
  - Select previous version from dropdown
  - Preview changes (diff view)
  - Confirm rollback button
  - Automatic health check after rollback

**2. Change History** (`/admin/versions/changes`)
- **Recent Changes:**
  - Timeline view: config changes, prompt updates, model changes
  - Filter by: component (Haystack, LangGraph, security), date range

- **Diff Viewer:**
  - Side-by-side comparison
  - Highlight: changed lines in YAML/JSON
  - Show impact: which categories affected

**3. Configuration Comparison** (`/admin/versions/compare`)
- **A/B Comparison:**
  - Select two versions to compare
  - Show: all config differences
  - Performance comparison (if both tested)
  - Quality comparison (faithfulness, latency, error rate)

### 4.8 Repository Layout

```
/project-athena/
  .dvc/
    config                         # DVC remote configuration
    .gitignore                     # DVC internal files

  configs/                         # DVC tracked
    haystack/
      pipelines/
        weather_standard.yaml
        weather_strict.yaml
        airport_standard.yaml
        sports_standard.yaml
        ...
      models/
        embedding_config.yaml
        ranker_config.yaml
    langgraph/
      graphs/
        owner_graph.json
        guest_graph.json
      policies/
        owner_policy.yaml
        guest_policy.yaml
    security_modes.yaml
    rag_sources.yaml
    evaluation_thresholds.yaml

  models/                          # DVC tracked
    prompts/
      weather_prompt.txt
      airport_prompt.txt
      sports_prompt.txt
      owner_system_prompt.txt
      guest_system_prompt.txt
    few_shot/
      weather_examples.json
      airport_examples.json
    registry.yaml                  # Model versions

  data/                            # DVC tracked
    eval/
      weather_test_set.json
      airport_test_set.json
      sports_test_set.json
      regression_suite.json
    seeds/
      golden_answers.json
      edge_cases.json

  scripts/
    eval_pipeline.py               # Run evaluation on dataset
    compare_versions.py            # Compare two DVC versions
    deploy_version.py              # Deploy specific DVC version

  configs.dvc                      # DVC metadata (Git tracked)
  models.dvc                       # DVC metadata (Git tracked)
  data.dvc                         # DVC metadata (Git tracked)

  .gitignore                       # Ignore actual data files
```

**.gitignore:**
```
# DVC tracked files (metadata is in .dvc files)
/configs
/models/prompts
/models/few_shot
/data/eval
/data/seeds

# DVC cache
/.dvc/cache
```

---

## 5. Architecture Integration

### 5.1 LangGraph Integration

**Add RAG Node:**
```python
# langgraph/nodes/rag_node.py
import httpx
from typing import TypedDict

class RAGRequest(TypedDict):
    query: str
    category: str
    mode: str
    top_k: int
    rerank: bool

class RAGResponse(TypedDict):
    answer: str
    citations: list
    metadata: dict

async def rag_node(state: dict) -> dict:
    """
    RAG node for info queries using Haystack.
    """
    if not os.getenv("ATHENA_FEATURE_HAYSTACK", "false") == "true":
        # Fall back to legacy RAG
        return legacy_rag_node(state)

    # Prepare request
    request = RAGRequest(
        query=state["query"],
        category=state["category"],
        mode=state["mode"],
        top_k=state.get("rag_top_k", 8),
        rerank=state.get("rag_rerank", False)
    )

    # Call Haystack API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://athena-haystack:8000/v1/rag/query",
            json=request,
            timeout=3.0
        )
        response.raise_for_status()
        rag_result = RAGResponse(**response.json())

    # Update state
    state["answer"] = rag_result["answer"]
    state["citations"] = rag_result["citations"]
    state["rag_metadata"] = rag_result["metadata"]

    return state
```

**Add Eval Sink Node:**
```python
# langgraph/nodes/eval_sink_node.py
import httpx
from typing import Optional

async def eval_sink_node(state: dict) -> dict:
    """
    Async evaluation sink node.
    Sends evaluation event to athena-rageval.
    """
    if not os.getenv("ATHENA_FEATURE_RAGEVAL", "false") == "true":
        return state

    # Prepare evaluation event
    eval_event = {
        "request_id": state["request_id"],
        "timestamp": state["timestamp"],
        "query": state["query"],
        "category": state["category"],
        "mode": state["mode"],
        "retrieved_docs": state.get("retrieved_docs", []),
        "answer": state["answer"],
        "citations": state.get("citations", []),
        "metadata": state.get("rag_metadata", {})
    }

    # Async submit (fire and forget)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://athena-rageval:8000/v1/eval/submit",
                json=eval_event,
                timeout=1.0
            )
    except Exception as e:
        # Log but don't fail request
        logging.warning(f"Failed to submit eval event: {e}")

    return state
```

**Add Policy Edges:**
```python
# langgraph/graphs/info_graph.py
from langgraph.graph import StateGraph, END

def build_info_graph():
    """
    Build info query graph with RAG and evaluation.
    """
    graph = StateGraph()

    # Nodes
    graph.add_node("classify", classify_node)
    graph.add_node("rag", rag_node)
    graph.add_node("eval_sink", eval_sink_node)
    graph.add_node("validate", validate_node)  # Optional CMV

    # Edges
    graph.add_edge("classify", "rag")

    # Conditional: validate if owner + CMV enabled
    graph.add_conditional_edges(
        "rag",
        should_validate,
        {
            True: "validate",
            False: "eval_sink"
        }
    )
    graph.add_edge("validate", "eval_sink")
    graph.add_edge("eval_sink", END)

    return graph.compile()

def should_validate(state: dict) -> bool:
    """
    Determine if cross-model validation should run.
    """
    cmv_enabled = os.getenv("RAGEVAL_CMV_ENABLED", "false") == "true"
    owner_mode = state["mode"] == "owner"
    high_stakes = state["category"] in ["airports", "sports", "dining"]

    return cmv_enabled and (owner_mode or high_stakes)
```

**Use Graph Config Profiles Tracked in DVC:**
```python
# langgraph/config.py
import yaml
import os

def load_graph_config(mode: str) -> dict:
    """
    Load LangGraph configuration from DVC-tracked YAML.
    """
    config_path = f"configs/langgraph/graphs/{mode}_graph.yaml"

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Graph config not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config

# Example: configs/langgraph/graphs/owner_graph.yaml
# nodes:
#   - classify
#   - rag
#   - validate  # CMV enabled for owner
#   - eval_sink
#
# edges:
#   - from: classify
#     to: rag
#   - from: rag
#     to: validate
#     condition: high_stakes_category
#   - from: validate
#     to: eval_sink
#
# settings:
#   rag_top_k: 8
#   rag_rerank: true
#   cmv_enabled: true
```

### 5.2 Orchestrator Integration

**Respect Feature Flags:**
```python
# orchestrator/main.py
import os

class AthenaOrchestrator:
    def __init__(self):
        # Feature flags
        self.haystack_enabled = os.getenv("ATHENA_FEATURE_HAYSTACK", "false") == "true"
        self.rageval_enabled = os.getenv("ATHENA_FEATURE_RAGEVAL", "false") == "true"
        self.dvc_enabled = os.getenv("ATHENA_FEATURE_DVC", "false") == "true"

        # Load appropriate graph
        if self.haystack_enabled:
            self.info_graph = build_info_graph()
        else:
            self.info_graph = build_legacy_info_graph()

    async def handle_info_query(self, query: str, mode: str, category: str):
        """
        Handle info query with RAG.
        """
        state = {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "mode": mode,
            "category": category,
            "rag_top_k": 8,
            "rag_rerank": mode == "owner"  # Enable rerank for owner
        }

        # Run graph
        result = await self.info_graph.ainvoke(state)

        return result["answer"], result.get("citations", [])
```

**Attach Metadata to Eval Events:**
```python
# orchestrator/eval.py
def create_eval_event(state: dict, config_version: str) -> dict:
    """
    Create evaluation event with full metadata.
    """
    return {
        "request_id": state["request_id"],
        "timestamp": state["timestamp"],
        "query": state["query"],
        "category": state["category"],
        "mode": state["mode"],
        "retrieved_docs": state.get("retrieved_docs", []),
        "answer": state["answer"],
        "citations": state.get("citations", []),
        "metadata": {
            **state.get("rag_metadata", {}),
            "config_version": config_version,  # DVC tag
            "pipeline": state.get("pipeline_name"),
            "model": state.get("model_name"),
            "graph_version": state.get("graph_version")
        }
    }
```

### 5.3 Home Assistant Integration

**No Changes for Device Control:**
- Direct path: Device → HA → Orchestrator → HA API
- No RAG involved

**Info Intents Route to LangGraph:**
```yaml
# home-assistant/configuration.yaml
conversation:
  intents:
    GetWeather:
      - "What's the weather [in {location}]"
      - "Weather forecast for {location}"
    GetAirportInfo:
      - "Airport status for {airport_code}"
      - "Delays at {airport_code}"
    GetSportsScore:
      - "What's the score of the {team} game"
      - "Did the {team} win"

# Route to Athena orchestrator
intent_script:
  GetWeather:
    action: rest_command.athena_info_query
    data:
      query: "{{ trigger.slots.sentence }}"
      category: "weather"
  GetAirportInfo:
    action: rest_command.athena_info_query
    data:
      query: "{{ trigger.slots.sentence }}"
      category: "airports"
  GetSportsScore:
    action: rest_command.athena_info_query
    data:
      query: "{{ trigger.slots.sentence }}"
      category: "sports"

rest_command:
  athena_info_query:
    url: "http://athena-orchestrator:8000/v1/query"
    method: POST
    payload: '{"query": "{{ query }}", "category": "{{ category }}", "mode": "{{ mode }}"}'
```

**Guest Mode Flips Stricter Profiles:**
```python
# mode_service determines mode
mode = mode_service.get_current_mode()  # "guest" or "owner"

# Pass to orchestrator
response = await orchestrator.handle_info_query(
    query=query,
    mode=mode,
    category=category
)

# Orchestrator uses mode to select:
# - Graph config (guest_graph.yaml vs owner_graph.yaml)
# - RAG profile (strict vs standard)
# - Eval enforcement (log_only vs soft_block)
```

---

## 6. Packaging (Docker & K8s)

### 6.1 Docker Compose - New Environment Variables

**Complete .env Example:**
```bash
# ========================================
# Feature Flags
# ========================================
ATHENA_FEATURE_HAYSTACK=true
ATHENA_FEATURE_RAGEVAL=true
ATHENA_FEATURE_DVC=true

# ========================================
# Haystack Configuration
# ========================================
# LLM target
RAG_LLM_TARGET=ollama://mistral:7b-q4
OLLAMA_BASE_URL=http://ollama:11434

# Retrieval settings
RAG_TOPK=8
RAG_RERANK=false
RAG_MAX_CONTEXT_TOKENS=4096
RAG_RETRIEVAL_TIMEOUT_MS=150

# Ranker settings (if enabled)
RAG_RANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RAG_RANKER_TOP_K=5

# Vector DB
VECTOR_DB_URL=http://qdrant:6333
VECTOR_DB_COLLECTION=athena_knowledge

# Mode profiles
RAG_GUEST_MODE_PROFILE=strict
RAG_OWNER_MODE_PROFILE=standard

# Category toggles
RAG_WEATHER_ENABLED=true
RAG_NEWS_ENABLED=true
RAG_AIRPORT_ENABLED=true
RAG_SPORTS_ENABLED=true
RAG_RECIPES_ENABLED=true
RAG_MEDIA_ENABLED=true
RAG_DINING_ENABLED=true
RAG_STREAMING_ENABLED=true

# ========================================
# Open-RAG-Eval Configuration
# ========================================
# Mode
RAGEVAL_MODE=async
RAGEVAL_CMV_ENABLED=false
RAGEVAL_VERIFIER_LLM=ollama://phi3:mini-q8

# Rulesets
RAGEVAL_RULESETS=weather,airports,sports

# Thresholds
RAGEVAL_FAITHFULNESS_THRESHOLD=0.75
RAGEVAL_CITATION_THRESHOLD=0.80
RAGEVAL_ANSWERABILITY_THRESHOLD=0.70

# Enforcement
RAGEVAL_ENFORCEMENT_GUEST=log_only

# Storage
EVAL_STORE_URL=postgresql://eval_user:secure_password@postgres:5432/athena_eval
REDIS_URL=redis://redis:6379/2

# Cross-model validation (owner only)
RAGEVAL_PRIMARY_LLM=ollama://mistral:7b-q4
RAGEVAL_TIEBREAKER_LLM=ollama://llama3.1:8b-q4
RAGEVAL_CMV_SIMILARITY_THRESHOLD=0.85
RAGEVAL_CMV_ENTITY_AGREEMENT=0.90
RAGEVAL_CMV_CATEGORIES=airports,sports,dining
RAGEVAL_CMV_OWNER_ONLY=true

# ========================================
# DVC Configuration
# ========================================
DVC_REMOTE=synology
DVC_REMOTE_URL=ssh://192.168.10.164/volume1/athena-dvc
DVC_TRACK_DIRS=/app/configs,/app/models,/app/data/eval
DVC_AUTO_COMMIT=false
DVC_ENFORCE_TAGS=true
```

### 6.2 Docker Compose - Service Additions

**Complete docker-compose.yaml with new services:**
```yaml
version: '3.8'

services:
  # ========================================
  # Existing Services
  # ========================================
  # (orchestrator, ollama, qdrant, redis, postgres, etc.)

  # ========================================
  # NEW: Haystack RAG Service
  # ========================================
  athena-haystack:
    image: deepset/haystack:latest
    container_name: athena-haystack
    restart: unless-stopped
    environment:
      ATHENA_FEATURE_HAYSTACK: "${ATHENA_FEATURE_HAYSTACK:-true}"
      RAG_LLM_TARGET: "${RAG_LLM_TARGET:-ollama://mistral:7b-q4}"
      OLLAMA_BASE_URL: "${OLLAMA_BASE_URL:-http://ollama:11434}"
      RAG_TOPK: "${RAG_TOPK:-8}"
      RAG_RERANK: "${RAG_RERANK:-false}"
      RAG_MAX_CONTEXT_TOKENS: "${RAG_MAX_CONTEXT_TOKENS:-4096}"
      RAG_RANKER_MODEL: "${RAG_RANKER_MODEL:-cross-encoder/ms-marco-MiniLM-L-6-v2}"
      RAG_RANKER_TOP_K: "${RAG_RANKER_TOP_K:-5}"
      VECTOR_DB_URL: "${VECTOR_DB_URL:-http://qdrant:6333}"
      VECTOR_DB_COLLECTION: "${VECTOR_DB_COLLECTION:-athena_knowledge}"
      RAG_GUEST_MODE_PROFILE: "${RAG_GUEST_MODE_PROFILE:-strict}"
      RAG_WEATHER_ENABLED: "${RAG_WEATHER_ENABLED:-true}"
      RAG_NEWS_ENABLED: "${RAG_NEWS_ENABLED:-true}"
      RAG_AIRPORT_ENABLED: "${RAG_AIRPORT_ENABLED:-true}"
      RAG_SPORTS_ENABLED: "${RAG_SPORTS_ENABLED:-true}"
      RAG_RECIPES_ENABLED: "${RAG_RECIPES_ENABLED:-true}"
      RAG_MEDIA_ENABLED: "${RAG_MEDIA_ENABLED:-true}"
    volumes:
      - ./configs/haystack:/app/configs:ro
      - ./models/prompts:/app/prompts:ro
    depends_on:
      - qdrant
      - ollama
    networks:
      - athena
    ports:
      - "8001:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ========================================
  # NEW: Open-RAG-Eval Service
  # ========================================
  athena-rageval:
    image: vectara/open-rag-eval:latest
    container_name: athena-rageval
    restart: unless-stopped
    environment:
      ATHENA_FEATURE_RAGEVAL: "${ATHENA_FEATURE_RAGEVAL:-true}"
      RAGEVAL_MODE: "${RAGEVAL_MODE:-async}"
      RAGEVAL_CMV_ENABLED: "${RAGEVAL_CMV_ENABLED:-false}"
      RAGEVAL_VERIFIER_LLM: "${RAGEVAL_VERIFIER_LLM:-ollama://phi3:mini-q8}"
      OLLAMA_BASE_URL: "${OLLAMA_BASE_URL:-http://ollama:11434}"
      RAGEVAL_RULESETS: "${RAGEVAL_RULESETS:-weather,airports,sports}"
      RAGEVAL_FAITHFULNESS_THRESHOLD: "${RAGEVAL_FAITHFULNESS_THRESHOLD:-0.75}"
      RAGEVAL_CITATION_THRESHOLD: "${RAGEVAL_CITATION_THRESHOLD:-0.80}"
      RAGEVAL_ANSWERABILITY_THRESHOLD: "${RAGEVAL_ANSWERABILITY_THRESHOLD:-0.70}"
      RAGEVAL_ENFORCEMENT_GUEST: "${RAGEVAL_ENFORCEMENT_GUEST:-log_only}"
      STORAGE_URL: "${EVAL_STORE_URL}"
      REDIS_URL: "${REDIS_URL:-redis://redis:6379/2}"
      # CMV settings
      RAGEVAL_PRIMARY_LLM: "${RAGEVAL_PRIMARY_LLM:-ollama://mistral:7b-q4}"
      RAGEVAL_TIEBREAKER_LLM: "${RAGEVAL_TIEBREAKER_LLM:-ollama://llama3.1:8b-q4}"
      RAGEVAL_CMV_SIMILARITY_THRESHOLD: "${RAGEVAL_CMV_SIMILARITY_THRESHOLD:-0.85}"
      RAGEVAL_CMV_ENTITY_AGREEMENT: "${RAGEVAL_CMV_ENTITY_AGREEMENT:-0.90}"
      RAGEVAL_CMV_CATEGORIES: "${RAGEVAL_CMV_CATEGORIES:-airports,sports,dining}"
      RAGEVAL_CMV_OWNER_ONLY: "${RAGEVAL_CMV_OWNER_ONLY:-true}"
    volumes:
      - ./configs/rageval/rules:/app/rules:ro
      - eval_data:/app/data
    depends_on:
      - postgres
      - redis
      - ollama
      - athena-orchestrator
    networks:
      - athena
    ports:
      - "8002:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  athena:
    driver: bridge

volumes:
  eval_data:
```

### 6.3 Kubernetes - Helm Values

**values.yaml additions:**
```yaml
# ========================================
# Haystack Configuration
# ========================================
haystack:
  enabled: true
  replicaCount: 2
  image:
    repository: deepset/haystack
    tag: latest
    pullPolicy: IfNotPresent

  config:
    llm_target: "ollama://mistral:7b-q4"
    ollama_base_url: "http://ollama:11434"
    vector_db_url: "http://qdrant:6333"
    vector_db_collection: "athena_knowledge"
    top_k: 8
    rerank: false
    max_context_tokens: 4096
    retrieval_timeout_ms: 150
    ranker_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ranker_top_k: 5
    guest_mode_profile: "strict"
    owner_mode_profile: "standard"

  categories:
    weather: true
    news: true
    airports: true
    sports: true
    recipes: true
    media: true
    dining: true
    streaming: true

  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

  # Optional GPU for ranker
  gpu:
    enabled: false
    count: 0

  service:
    type: ClusterIP
    port: 8000

# ========================================
# Open-RAG-Eval Configuration
# ========================================
rageval:
  enabled: true
  replicaCount: 2
  image:
    repository: vectara/open-rag-eval
    tag: latest
    pullPolicy: IfNotPresent

  config:
    mode: "async"
    cmv_enabled: false
    verifier_llm: "ollama://phi3:mini-q8"
    ollama_base_url: "http://ollama:11434"
    rulesets: "weather,airports,sports"
    faithfulness_threshold: 0.75
    citation_threshold: 0.80
    answerability_threshold: 0.70
    enforcement_guest: "log_only"
    # CMV
    primary_llm: "ollama://mistral:7b-q4"
    tiebreaker_llm: "ollama://llama3.1:8b-q4"
    cmv_similarity_threshold: 0.85
    cmv_entity_agreement: 0.90
    cmv_categories: "airports,sports,dining"
    cmv_owner_only: true

  storage:
    postgres_url: "postgresql://eval_user:password@postgres:5432/athena_eval"
    redis_url: "redis://redis:6379/2"

  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "1"
      memory: "2Gi"

  service:
    type: ClusterIP
    port: 8000

# ========================================
# DVC Configuration
# ========================================
dvc:
  enabled: true
  remote: "synology"
  remote_url: "ssh://synology.local/volume1/athena-dvc"
  track_dirs: "/app/configs,/app/models,/app/data/eval"
  auto_commit: false
  enforce_tags: true
```

### 6.4 Kubernetes - Helm Chart Structure

**Updated chart structure:**
```
charts/athena/
  Chart.yaml
  values.yaml
  values-dev.yaml
  values-gpu.yaml
  values-baremetal.yaml
  values-cloud.yaml

  charts/
    orchestrator/
    mode-service/
    ha-bridge/
    stt/
    tts/
    router-small-llm/
    router-large-llm/
    rag-api/
    admin/
    qdrant/
    redis/

    # NEW:
    haystack/
      Chart.yaml
      values.yaml
      templates/
        deployment.yaml
        service.yaml
        configmap.yaml
        servicemonitor.yaml

    rageval/
      Chart.yaml
      values.yaml
      templates/
        deployment.yaml
        service.yaml
        secret.yaml
        servicemonitor.yaml
```

---

## 7. Observability & Performance

### 7.1 Prometheus Metrics

**Haystack Metrics:**
```python
# Expose metrics endpoint
from prometheus_client import Counter, Histogram, Gauge

# Counters
rag_queries_total = Counter(
    "athena_rag_queries_total",
    "Total RAG queries",
    ["category", "mode", "status"]
)

# Histograms
rag_latency_seconds = Histogram(
    "athena_rag_latency_seconds",
    "RAG query latency",
    ["category", "mode", "pipeline"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

retrieval_latency_seconds = Histogram(
    "athena_retrieval_latency_seconds",
    "Retrieval latency",
    ["category"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3]
)

generation_latency_seconds = Histogram(
    "athena_generation_latency_seconds",
    "Generation latency",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0]
)

# Gauges
rag_cache_hit_rate = Gauge(
    "athena_rag_cache_hit_rate",
    "RAG cache hit rate",
    ["category"]
)
```

**RAG Eval Metrics:**
```python
# Histograms
eval_faithfulness_score = Histogram(
    "athena_eval_faithfulness",
    "Faithfulness score distribution",
    ["category", "mode"],
    buckets=[0.0, 0.25, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
)

eval_citation_coverage = Histogram(
    "athena_eval_citation_coverage",
    "Citation coverage distribution",
    ["category", "mode"],
    buckets=[0.0, 0.25, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
)

# Counters
eval_flags_total = Counter(
    "athena_eval_flags_total",
    "Total flagged answers",
    ["category", "flag_type", "severity"]
)

eval_cmv_disagreements = Counter(
    "athena_eval_cmv_disagreements_total",
    "Cross-model validation disagreements",
    ["category"]
)

# Gauges
eval_queue_depth = Gauge(
    "athena_eval_queue_depth",
    "Evaluation queue depth"
)

eval_backlog_age_seconds = Gauge(
    "athena_eval_backlog_age_seconds",
    "Oldest event in eval queue"
)
```

### 7.2 Grafana Dashboards

**New Dashboard: RAG Performance**

**Panels:**
1. **Query Rate:** `rate(athena_rag_queries_total[5m])` by category
2. **Success Rate:** `rate(athena_rag_queries_total{status="success"}[5m]) / rate(athena_rag_queries_total[5m])`
3. **Latency P95:** `histogram_quantile(0.95, athena_rag_latency_seconds)` by category
4. **Retrieval Latency:** `histogram_quantile(0.95, athena_retrieval_latency_seconds)` by category
5. **Generation Latency:** `histogram_quantile(0.95, athena_generation_latency_seconds)` by model
6. **Cache Hit Rate:** `athena_rag_cache_hit_rate` by category

**New Dashboard: RAG Quality**

**Panels:**
1. **Faithfulness Score:** `histogram_quantile(0.5, athena_eval_faithfulness)` by category (median)
2. **Citation Coverage:** `histogram_quantile(0.5, athena_eval_citation_coverage)` by category
3. **Flagged Answers:** `rate(athena_eval_flags_total[5m])` by flag type
4. **Category Quality:** Heatmap showing faithfulness by category over time
5. **CMV Disagreements:** `rate(athena_eval_cmv_disagreements_total[5m])` by category
6. **Eval Queue Depth:** `athena_eval_queue_depth`
7. **Eval Backlog Age:** `athena_eval_backlog_age_seconds`

### 7.3 Service Level Objectives (SLOs)

**Haystack SLOs:**
- Retrieval latency P95 < 120ms
- RAG end-to-end P95 < 3.5s
- Cache hit rate > 30%
- Error rate < 2%
- Success rate > 98%

**RAG Eval SLOs:**
- Eval queue depth < 1000
- Eval backlog age < 60s (async mode)
- Faithfulness score P50 > 0.85
- Citation coverage P50 > 0.90
- Flagged answer rate < 5%

### 7.4 Alerts

**Prometheus Alerting Rules:**

```yaml
# alerts/rag_alerts.yaml
groups:
  - name: rag_performance
    interval: 30s
    rules:
      - alert: HighRAGLatency
        expr: |
          histogram_quantile(0.95, athena_rag_latency_seconds) > 5.0
        for: 5m
        labels:
          severity: warning
          component: haystack
        annotations:
          summary: "High RAG latency detected"
          description: "RAG P95 latency is {{ $value }}s (threshold: 5.0s)"

      - alert: LowRAGCacheHitRate
        expr: |
          athena_rag_cache_hit_rate < 0.20
        for: 10m
        labels:
          severity: info
          component: haystack
        annotations:
          summary: "Low RAG cache hit rate"
          description: "Cache hit rate is {{ $value }} (threshold: 20%)"

      - alert: HighRAGErrorRate
        expr: |
          rate(athena_rag_queries_total{status="error"}[5m]) / rate(athena_rag_queries_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          component: haystack
        annotations:
          summary: "High RAG error rate"
          description: "Error rate is {{ $value }} (threshold: 5%)"

  - name: rag_quality
    interval: 1m
    rules:
      - alert: LowFaithfulnessScore
        expr: |
          histogram_quantile(0.5, athena_eval_faithfulness{category="weather"}) < 0.70
        for: 15m
        labels:
          severity: warning
          component: rageval
          category: weather
        annotations:
          summary: "Low faithfulness score for weather queries"
          description: "Median faithfulness is {{ $value }} (threshold: 0.70)"

      - alert: HighFlaggedAnswerRate
        expr: |
          rate(athena_eval_flags_total{severity="error"}[10m]) / rate(athena_rag_queries_total[10m]) > 0.10
        for: 10m
        labels:
          severity: critical
          component: rageval
        annotations:
          summary: "High rate of flagged answers"
          description: "{{ $value }} of answers flagged with errors (threshold: 10%)"

      - alert: EvalQueueBacklog
        expr: |
          athena_eval_queue_depth > 5000
        for: 5m
        labels:
          severity: warning
          component: rageval
        annotations:
          summary: "Large evaluation queue backlog"
          description: "Eval queue has {{ $value }} events (threshold: 5000)"

      - alert: EvalQueueStale
        expr: |
          athena_eval_backlog_age_seconds > 300
        for: 5m
        labels:
          severity: warning
          component: rageval
        annotations:
          summary: "Eval queue is stale"
          description: "Oldest event is {{ $value }}s old (threshold: 300s)"
```

---

## 8. Security & Privacy

### 8.1 Guest Mode Privacy

**PII Redaction in Eval Logs:**
```python
# rageval/privacy.py
import re
from typing import Dict, Any

def redact_pii(text: str, mode: str) -> str:
    """
    Redact PII from text for evaluation logging.
    More aggressive in guest mode.
    """
    if mode == "guest":
        # Redact email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)

        # Redact phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)

        # Redact names (if detected via NER)
        text = redact_named_entities(text, entity_types=['PERSON'])

        # Redact addresses
        text = redact_named_entities(text, entity_types=['LOCATION', 'ADDRESS'])

    return text

def sanitize_eval_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize evaluation event for guest mode.
    """
    mode = event.get("mode", "guest")

    if mode == "guest":
        # Redact PII from query and answer
        event["query"] = redact_pii(event["query"], mode)
        event["answer"] = redact_pii(event["answer"], mode)

        # Redact from retrieved docs
        for doc in event.get("retrieved_docs", []):
            doc["content"] = redact_pii(doc["content"], mode)

        # Anonymize user ID
        if "user_id" in event:
            event["user_id"] = hash_user_id(event["user_id"])

        # Remove IP address
        event.pop("ip_address", None)

    return event
```

**Auto-Purge on Checkout:**
```python
# rageval/cleanup.py
from datetime import datetime, timedelta
import asyncio

async def auto_purge_guest_data(checkout_time: datetime):
    """
    Auto-purge guest data 1 hour after checkout.
    """
    purge_time = checkout_time + timedelta(hours=1)
    delay = (purge_time - datetime.utcnow()).total_seconds()

    if delay > 0:
        await asyncio.sleep(delay)

    # Purge all eval events for guest mode during stay
    await purge_eval_events(
        mode="guest",
        start_time=checkout_time - timedelta(days=7),  # Max stay duration
        end_time=checkout_time
    )

    logging.info(f"Purged guest data after checkout at {checkout_time}")
```

### 8.2 Configuration Security

**DVC Metadata Contains No Secrets:**
```yaml
# configs/haystack/pipelines/weather_standard.yaml
# ✅ SAFE - no secrets
name: weather_standard
components:
  - name: retriever
    type: EmbeddingRetriever
    params:
      document_store: qdrant
      embedding_model: sentence-transformers/all-MiniLM-L6-v2
      top_k: 8

# API keys stored in .env or K8s Secrets, NOT in DVC-tracked files
```

**.env and Secrets Management:**
```bash
# .env (NOT tracked by DVC or Git)
WEATHER_API_KEY=abc123...
SPORTS_API_KEY=xyz789...
EVAL_STORE_PASSWORD=secure_password
```

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: haystack-secrets
  namespace: athena
type: Opaque
stringData:
  weather-api-key: "abc123..."
  sports-api-key: "xyz789..."
```

### 8.3 Audit Logging

**Track Config Changes:**
```python
# admin/audit.py
import hashlib
import hmac

def log_config_change(user: str, component: str, before: dict, after: dict):
    """
    Log configuration change with tamper-evident HMAC.
    """
    change_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "component": component,
        "before_hash": hash_config(before),
        "after_hash": hash_config(after),
        "diff": compute_diff(before, after)
    }

    # Compute HMAC for tamper detection
    secret = os.getenv("AUDIT_LOG_SECRET")
    signature = hmac.new(
        secret.encode(),
        json.dumps(change_record, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()

    change_record["signature"] = signature

    # Store in audit log table
    await store_audit_log(change_record)
```

---

## 9. Rollout Plan

### 9.1 Phase A - Shadow Mode (Week 1-2)

**Goal:** Enable RAG Eval without user impact

**Tasks:**
1. Deploy `athena-rageval` service (Docker/K8s)
2. Enable `ATHENA_FEATURE_RAGEVAL=true`, `RAGEVAL_MODE=async`
3. Configure eval storage (Postgres + Redis)
4. Integrate eval sink node into LangGraph
5. Start logging quality without blocking requests

**Validation:**
- Eval events flowing to `athena-rageval`
- Scores computed and stored
- Admin UI showing quality dashboard
- No latency impact on users (< 1ms overhead)

**Rollback:** Disable `ATHENA_FEATURE_RAGEVAL=false`

---

### 9.2 Phase B - Low-Risk Haystack Switch (Week 3-4)

**Goal:** Enable Haystack for weather/sports/airports only

**Tasks:**
1. Deploy `athena-haystack` service
2. Create pipelines for weather, sports, airports
3. Enable `ATHENA_FEATURE_HAYSTACK=true`
4. Enable categories: `RAG_WEATHER_ENABLED=true`, `RAG_SPORTS_ENABLED=true`, `RAG_AIRPORT_ENABLED=true`
5. Keep other categories on legacy RAG
6. Monitor latency & faithfulness

**Validation:**
- Latency P95 < 3.5s for enabled categories
- Faithfulness P50 > 0.85
- No increase in error rate
- User experience unchanged or improved

**Rollback:** Disable `ATHENA_FEATURE_HAYSTACK=false` (fall back to legacy RAG)

---

### 9.3 Phase C - Expand Categories (Week 5-6)

**Goal:** Add news/recipes/media

**Tasks:**
1. Create pipelines for news, recipes, media
2. Enable categories one by one
3. Monitor quality metrics
4. Enable guest strict profile: `RAG_GUEST_MODE_PROFILE=strict`
5. Optionally enable rerank for owner: `RAG_RERANK=true` (owner mode only)

**Validation:**
- All categories showing good faithfulness (> 0.85)
- Guest mode latency < 3.0s P95
- Owner mode latency < 4.0s P95 (with rerank)
- Cache hit rate > 30%

**Rollback:** Disable problematic categories, keep others enabled

---

### 9.4 Phase D - DVC & CI Gate (Week 7-8)

**Goal:** Version control and CI/CD integration

**Tasks:**
1. Set up DVC remote (Synology NFS or S3)
2. Track configs, prompts, eval datasets
3. Tag current deployment: `dvc tag add deploy-YYYY-MM-DD`
4. Add GitHub Actions workflow (test config changes)
5. Require regression test pass before deploy: `DVC_ENFORCE_TAGS=true`
6. Admin UI version control page

**Validation:**
- All configs tracked in DVC
- CI runs regression tests on config changes
- Admin UI shows current version tag
- Rollback tested and working

**Rollback:** Disable `ATHENA_FEATURE_DVC=false`, continue manual deploys

---

### 9.5 Phase E - Cross-Model Validation (Optional, Week 9-10)

**Goal:** Enable CMV for owner mode (optional)

**Tasks:**
1. Deploy verifier LLM (phi3:mini-q8)
2. Deploy tie-breaker LLM (llama3.1:8b-q4)
3. Enable `RAGEVAL_CMV_ENABLED=true`, `RAGEVAL_CMV_OWNER_ONLY=true`
4. Configure categories: `RAGEVAL_CMV_CATEGORIES=airports,sports,dining`
5. Monitor latency impact (+300-700ms)
6. A/B test owner experience

**Validation:**
- Owner mode faithfulness > 0.95
- Disagreement rate < 10%
- Owner feedback positive (quality improvement worth latency)
- Guest mode unaffected (CMV disabled)

**Rollback:** Disable `RAGEVAL_CMV_ENABLED=false`

---

## 10. Implementation Timeline

### Week 1-2: Shadow Mode
- [ ] Deploy RAG Eval service (Docker + K8s)
- [ ] Integrate eval sink node in LangGraph
- [ ] Configure eval storage (Postgres + Redis)
- [ ] Admin UI: Quality dashboard
- [ ] Validation: Eval events flowing, no latency impact

### Week 3-4: Low-Risk Haystack Switch
- [ ] Deploy Haystack service (Docker + K8s)
- [ ] Create pipelines: weather, sports, airports
- [ ] Enable Haystack for 3 categories
- [ ] Monitor latency and faithfulness
- [ ] Validation: P95 < 3.5s, faithfulness > 0.85

### Week 5-6: Expand Categories
- [ ] Create pipelines: news, recipes, media, dining, streaming
- [ ] Enable categories one by one
- [ ] Enable guest strict profile
- [ ] Enable owner reranking
- [ ] Validation: All categories performing well

### Week 7-8: DVC & CI Gate
- [ ] Set up DVC remote (Synology NFS)
- [ ] Track configs, prompts, eval datasets
- [ ] GitHub Actions: test config changes
- [ ] Admin UI: Version control page
- [ ] Validation: Rollback tested

### Week 9-10: Cross-Model Validation (Optional)
- [ ] Deploy verifier + tie-breaker LLMs
- [ ] Enable CMV for owner mode only
- [ ] A/B test owner experience
- [ ] Monitor disagreement rate
- [ ] Validation: Faithfulness > 0.95, owners happy

---

## Summary

This addendum integrates **Haystack**, **Open-RAG-Eval**, and **DVC** into Project Athena with:

1. **Zero/low hot-path overhead** when disabled
2. **Modular service architecture** (thin adapters in orchestrator)
3. **Comprehensive configuration** (env flags, Admin UI, per-request policies)
4. **Portable deployment** (Docker Compose + Kubernetes Helm)

**Key Benefits:**

- **Haystack:** Production-grade RAG with pluggable components, observability, easy A/B testing
- **Open-RAG-Eval:** Continuous quality monitoring, hallucination detection, cross-model validation
- **DVC:** Version control for configs/prompts/datasets, audit trails, safe rollback

**Rollout:** Safe, incremental (shadow → low-risk switch → expand → governance → optional CMV)

**Timeline:** 8-10 weeks (CMV optional)

---

**Related Documentation:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)
- [Guest Mode & Quality Tracking](2025-11-11-guest-mode-and-quality-tracking.md)
- [Admin Interface Specification](2025-11-11-admin-interface-specification.md)
- [Kubernetes Deployment Strategy](2025-11-11-kubernetes-deployment-strategy.md)
