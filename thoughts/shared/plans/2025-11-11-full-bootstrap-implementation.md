# Full Bootstrap Implementation Plan - Zero to Working Voice Assistant

**Date:** 2025-11-11
**Status:** Planning - Part of Architecture Pivot
**Related:**
- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md)
- [Phase 1 Implementation](2025-11-11-phase1-core-services-implementation.md)
- [Component Deep-Dive](2025-11-11-component-deep-dive-plans.md)

---

## Executive Summary

This plan provides a **complete step-by-step guide** to bootstrap Project Athena from scratch, transforming from Jetson-based research code to production-ready Mac Studio/mini deployment with full voice assistant capabilities.

**Starting Point:** Empty Mac Studio M4 + Mac mini M4
**End Point:** Working voice assistant responding to "Jarvis" and "Athena" wake words

**Timeline:** 6-8 weeks for complete Phase 1 deployment

---

## Prerequisites Checklist

Before beginning implementation, ensure you have:

### Hardware

- [ ] **Mac Studio M4 (64GB RAM)** delivered and networked at 192.168.10.20
- [ ] **Mac mini M4 (16GB RAM)** delivered and networked at 192.168.10.29
- [ ] **Home Assistant** running on Proxmox VM at 192.168.10.168
- [ ] **HA Voice preview device** (at least 1 for testing) at 192.168.10.50
- [ ] Network connectivity between all devices (10GbE preferred for Mac Studio)

### Software & Access

- [ ] macOS installed on both Macs
- [ ] Docker Desktop installed on both Macs
- [ ] SSH access configured (passwordless recommended)
- [ ] Git repository cloned on Mac Studio: `/Users/jaystuart/dev/project-athena/`
- [ ] Home Assistant admin access (Settings → System → Users)
- [ ] Existing Jetson code accessible for migration

### API Keys & Credentials

- [ ] **Home Assistant long-lived token** (Settings → Profile → Long-Lived Access Tokens)
- [ ] **OpenWeatherMap API key** (free tier sufficient)
- [ ] **FlightAware API key** (for airport data)
- [ ] **TheSportsDB API key** (free tier)
- [ ] **Twilio account** (SID, auth token, phone number) - optional for Phase 1
- [ ] **SMTP credentials** (Gmail app password or SendGrid) - optional for Phase 1

### Network Configuration

- [ ] Static IP assigned to Mac Studio: 192.168.10.20
- [ ] Static IP assigned to Mac mini: 192.168.10.29
- [ ] Firewall rules allow:
  - Mac Studio → Mac mini (Redis 6379, Qdrant 6333)
  - Home Assistant → Mac Studio (Gateway 8000)
  - All devices → internet (API calls)

---

## Bootstrap Phases

### Phase 0: Environment Setup (Week 1, Days 1-2)

**Goal:** Prepare development environment and tools

#### Step 0.1: Mac Studio Setup

```bash
# SSH to Mac Studio
ssh jstuart@192.168.10.20

# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install essential tools
brew install git python@3.11 docker docker-compose curl jq redis

# Clone repository
cd /Users/jaystuart/dev
git clone <repo-url> project-athena
cd project-athena

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install global Python tools
pip install pytest pytest-asyncio black flake8 mypy
```

#### Step 0.2: Mac mini Setup

```bash
# SSH to Mac mini
ssh jstuart@192.168.10.29

# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker
brew install docker docker-compose

# Start Docker
open /Applications/Docker.app

# Verify Docker running
docker ps
```

#### Step 0.3: Install Ollama on Mac Studio

```bash
# On Mac Studio
brew install ollama

# Start Ollama service
ollama serve &

# Pull models (this will take ~30 minutes)
ollama pull phi3:mini-q8          # ~2.5GB
ollama pull llama3.1:8b-q4        # ~4.7GB
# ollama pull llama3.1:13b-q4     # ~7.3GB (optional for Phase 1)

# Verify models
ollama list
```

#### Step 0.4: Configure Environment Variables

```bash
# On Mac Studio
cd /Users/jaystuart/dev/project-athena

# Create config directory
mkdir -p config/env

# Copy environment template
cp config/env/.env.example config/env/.env

# Edit with actual values
nano config/env/.env
```

**Required variables:**
```bash
# Home Assistant
HA_URL=https://192.168.10.168:8123
HA_TOKEN=eyJhbGci...  # Your HA long-lived token

# Ollama
OLLAMA_URL=http://localhost:11434

# Gateway
LITELLM_MASTER_KEY=sk-1234567890abcdef  # Generate random key

# Vector DB & Cache
QDRANT_URL=http://192.168.10.29:6333
REDIS_URL=redis://192.168.10.29:6379/0

# RAG API Keys
OPENWEATHER_API_KEY=your_key_here
FLIGHTAWARE_API_KEY=your_key_here
THESPORTSDB_API_KEY=your_key_here

# Feature Flags (Phase 1)
ENABLE_GUEST_MODE=false
ENABLE_SHARE_SERVICE=false
ENABLE_CROSS_MODEL_VALIDATION=false

# Logging
LOG_LEVEL=INFO
```

#### Step 0.5: Success Criteria

- [ ] Both Macs accessible via SSH
- [ ] Docker running on both Macs
- [ ] Ollama serving on Mac Studio (port 11434)
- [ ] Models downloaded: `ollama list` shows phi3 and llama3.1
- [ ] Environment file created and populated
- [ ] Git repository cloned and accessible

---

### Phase 1: Mac mini Services (Week 1, Days 3-4)

**Goal:** Deploy Qdrant and Redis on Mac mini

#### Step 1.1: Deploy Qdrant and Redis

```bash
# SSH to Mac mini
ssh jstuart@192.168.10.29

# Create deployment directory
mkdir -p ~/athena/mac-mini
cd ~/athena/mac-mini

# Create docker-compose.yml
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
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
EOF

# Start services
docker compose up -d

# Wait for health checks
sleep 30

# Verify services
curl http://localhost:6333/healthz
redis-cli PING
```

#### Step 1.2: Initialize Qdrant Collection

```bash
# On Mac Studio (connect remotely to Qdrant on Mac mini)
cd /Users/jaystuart/dev/project-athena

# Create initialization script
cat > scripts/init_qdrant.py <<'EOF'
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://192.168.10.29:6333")

# Create collection
client.create_collection(
    collection_name="athena_knowledge",
    vectors_config=VectorParams(
        size=384,  # all-MiniLM-L6-v2 dimension
        distance=Distance.COSINE
    )
)

print("✅ Qdrant collection 'athena_knowledge' created")
EOF

# Run initialization
python scripts/init_qdrant.py
```

#### Step 1.3: Success Criteria

- [ ] Qdrant accessible: `curl http://192.168.10.29:6333/healthz`
- [ ] Redis accessible: `redis-cli -h 192.168.10.29 PING`
- [ ] Qdrant collection created: Check via web UI http://192.168.10.29:6333/dashboard
- [ ] Both services survive restart: `docker compose restart` then verify

---

### Phase 2: Repository Restructuring (Week 1-2, Days 5-7)

**Goal:** Transform research code into production structure

See [Phase 1 Implementation Plan - Section 4.1](2025-11-11-phase1-core-services-implementation.md#phase-11-repository-restructuring-week-1) for detailed steps.

**Key Tasks:**
1. Create apps/ directory structure
2. Extract core modules from src/jetson/
3. Refactor HA client with async support
4. Migrate RAG handlers (weather, airports, sports)
5. Extract intent classifier (v43)
6. Create configuration templates

**Verification:**
```bash
# Directory structure check
ls -la apps/
# Should show: gateway/, orchestrator/, rag/, shared/, validators/

# Python imports work
python -c "from apps.shared.ha_client import HomeAssistantClient"

# Configuration template exists
test -f config/env/.env.example && echo "✅ Config template exists"
```

---

### Phase 3: Gateway Deployment (Week 2, Days 8-10)

**Goal:** Deploy OpenAI-compatible gateway using LiteLLM

See [Phase 1 Implementation Plan - Section 4.2](2025-11-11-phase1-core-services-implementation.md#phase-12-openai-compatible-gateway-week-1-2) and [Component Deep-Dive - Gateway](2025-11-11-component-deep-dive-plans.md#1-gateway-openai-compatible-api) for detailed specs.

#### Step 3.1: Create Gateway Configuration

```bash
cd /Users/jaystuart/dev/project-athena

# Create gateway directory
mkdir -p apps/gateway

# Create config.yaml (see Component Deep-Dive for full config)
cat > apps/gateway/config.yaml <<'EOF'
model_list:
  - model_name: athena-small
    litellm_params:
      model: ollama/phi3:mini-q8
      api_base: http://host.docker.internal:11434

  - model_name: athena-medium
    litellm_params:
      model: ollama/llama3.1:8b-q4
      api_base: http://host.docker.internal:11434

  - model_name: gpt-3.5-turbo
    litellm_params:
      model: ollama/llama3.1:8b-q4
      api_base: http://host.docker.internal:11434

router_settings:
  routing_strategy: simple-shuffle
  num_retries: 2
  timeout: 300

general_settings:
  master_key: ${LITELLM_MASTER_KEY}
  proxy_logging: true
  success_callback: ["prometheus"]
EOF
```

#### Step 3.2: Deploy Gateway via Docker

```bash
# Create docker-compose for gateway
cat > deploy/compose/docker-compose.gateway.yml <<'EOF'
version: '3.8'

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
    volumes:
      - ../../apps/gateway/config.yaml:/app/config.yaml:ro
      - ../../logs/gateway:/app/logs
    command: ["--config", "/app/config.yaml", "--port", "8000"]
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF

# Start gateway
docker compose -f deploy/compose/docker-compose.gateway.yml up -d

# Wait for startup
sleep 10

# Test gateway
curl http://localhost:8000/health
```

#### Step 3.3: Test OpenAI Compatibility

```bash
# Test completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -d '{
    "model": "athena-small",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "temperature": 0.7
  }'

# Should return: {"choices": [{"message": {"content": "4"}}]}
```

#### Step 3.4: Success Criteria

- [ ] Gateway starts: `docker ps | grep athena-gateway`
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] Completion works: Test script returns valid response
- [ ] Metrics available: `curl http://localhost:8000/metrics`
- [ ] Logs visible: `docker logs athena-gateway`

---

### Phase 4: RAG Services (Week 2-3, Days 11-14)

**Goal:** Deploy weather, airports, sports microservices

See [Phase 1 Implementation Plan - Section 4.4](2025-11-11-phase1-core-services-implementation.md#phase-14-rag-services-week-3-4) and [Component Deep-Dive - RAG Services](2025-11-11-component-deep-dive-plans.md#3-rag-services-microservice-architecture) for detailed specs.

#### Step 4.1: Migrate RAG Handlers

```bash
# Weather service
mkdir -p apps/rag/weather
# Copy handler logic from src/jetson/facade/handlers/weather.py
# Wrap in FastAPI (see Component Deep-Dive for full code)

# Airports service
mkdir -p apps/rag/airports
# Migrate from src/jetson/facade/handlers/airports.py

# Sports service
mkdir -p apps/rag/sports
# Migrate from src/jetson/facade/handlers/sports.py
```

#### Step 4.2: Deploy RAG Services

```bash
# Build Docker images
docker build -t athena-rag-weather apps/rag/weather
docker build -t athena-rag-airports apps/rag/airports
docker build -t athena-rag-sports apps/rag/sports

# Create docker-compose for RAG services
cat > deploy/compose/docker-compose.rag.yml <<'EOF'
version: '3.8'

services:
  rag-weather:
    image: athena-rag-weather
    container_name: athena-rag-weather
    restart: unless-stopped
    ports:
      - "8010:8010"
    environment:
      OPENWEATHER_API_KEY: ${OPENWEATHER_API_KEY}
      REDIS_URL: redis://192.168.10.29:6379/0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]

  rag-airports:
    image: athena-rag-airports
    ports:
      - "8011:8011"
    environment:
      FLIGHTAWARE_API_KEY: ${FLIGHTAWARE_API_KEY}
      REDIS_URL: redis://192.168.10.29:6379/0

  rag-sports:
    image: athena-rag-sports
    ports:
      - "8012:8012"
    environment:
      THESPORTSDB_API_KEY: ${THESPORTSDB_API_KEY}
      REDIS_URL: redis://192.168.10.29:6379/0
EOF

# Start RAG services
docker compose -f deploy/compose/docker-compose.rag.yml up -d

# Test each service
curl http://localhost:8010/health
curl http://localhost:8011/health
curl http://localhost:8012/health
```

#### Step 4.3: Success Criteria

- [ ] All 3 services running: `docker ps | grep rag`
- [ ] Health checks pass for all services
- [ ] Weather query works: `curl -X POST http://localhost:8010/query -d '{"query":"weather","location":"Baltimore"}'`
- [ ] Caching works: Second query returns `cached: true`

---

### Phase 5: LangGraph Orchestrator (Week 3-4, Days 15-21)

**Goal:** Deploy orchestrator with classify → route → retrieve → synthesize flow

See [Phase 1 Implementation Plan - Section 4.3](2025-11-11-phase1-core-services-implementation.md#phase-13-langgraph-orchestrator-week-2-3) and [Component Deep-Dive - Orchestrator](2025-11-11-component-deep-dive-plans.md#2-orchestrator-langgraph-flow) for detailed implementation.

#### Step 5.1: Create Orchestrator Service

```bash
# Create orchestrator directory
mkdir -p apps/orchestrator

# Copy main.py from Component Deep-Dive specs
# Includes: classify, route_control, route_info, retrieve, synthesize, validate, finalize nodes

# Create Dockerfile
cat > apps/orchestrator/Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["python", "main.py"]
EOF

# Create requirements.txt
cat > apps/orchestrator/requirements.txt <<'EOF'
langgraph==0.0.20
langchain==0.1.0
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.0
aiohttp==3.9.1
redis==5.0.1
prometheus-client==0.19.0
EOF
```

#### Step 5.2: Deploy Orchestrator

```bash
# Build image
docker build -t athena-orchestrator apps/orchestrator

# Start orchestrator
docker run -d \
  --name athena-orchestrator \
  -p 8001:8001 \
  -e LITELLM_URL=http://host.docker.internal:8000 \
  -e LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY} \
  -e REDIS_URL=redis://192.168.10.29:6379/0 \
  --add-host host.docker.internal:host-gateway \
  athena-orchestrator

# Test orchestrator
curl http://localhost:8001/health
```

#### Step 5.3: Test End-to-End Flow

```bash
# Test control query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query":"turn on office lights","mode":"guest","room":"office"}'

# Test weather query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query":"what is the weather in Baltimore","mode":"guest","room":"office"}'

# Should return: answer, category, model_tier, citations, metadata
```

#### Step 5.4: Success Criteria

- [ ] Orchestrator starts: `docker ps | grep orchestrator`
- [ ] Health check passes: `curl http://localhost:8001/health`
- [ ] Classification works: Control query returns category="control"
- [ ] RAG integration works: Weather query returns real weather data
- [ ] Latency acceptable: Response time ≤5.5s for knowledge queries

---

### Phase 6: Home Assistant Integration (Week 4-5, Days 22-28)

**Goal:** Configure HA Assist Pipelines and Wyoming protocol

See [Phase 1 Implementation Plan - Section 4.6](2025-11-11-phase1-core-services-implementation.md#phase-16-home-assistant-configuration-week-4-5) for detailed steps.

#### Step 6.1: Install Wyoming Add-ons

**In Home Assistant UI:**
1. Navigate to **Settings → Add-ons**
2. Click **Add-on Store**
3. Click ⋮ (menu) → **Repositories**
4. Add: `https://github.com/rhasspy/hassio-addons`
5. Install **Faster Whisper** add-on
6. Install **Piper** add-on

**Configure Faster Whisper:**
```yaml
language: en
model: tiny-en
beam_size: 1
```

**Configure Piper:**
```yaml
voice: en_US-lessac-medium
```

#### Step 6.2: Configure OpenAI Integration

**In Home Assistant UI:**
1. **Settings → Devices & Services**
2. **Add Integration** → Search "OpenAI Conversation"
3. Configure:
   - **API Key:** `dummy-key` (not validated by LiteLLM)
   - **Base URL:** `http://192.168.10.20:8000/v1`
   - **Model:** `athena-medium`
   - **Temperature:** 0.3
   - **Max Tokens:** 1000

#### Step 6.3: Create Assist Pipelines

**Pipeline 1: Control (Local)**
1. **Settings → Voice Assistants → Add Pipeline**
2. **Name:** Control Pipeline
3. **Conversation Agent:** Home Assistant
4. **Speech-to-Text:** Faster Whisper
5. **Text-to-Speech:** Piper
6. **Wake Word:** jarvis (if available)
7. **Save**

**Pipeline 2: Knowledge (LLM)**
1. **Settings → Voice Assistants → Add Pipeline**
2. **Name:** Knowledge Pipeline
3. **Conversation Agent:** OpenAI Conversation
4. **Speech-to-Text:** Faster Whisper
5. **Text-to-Speech:** Piper
6. **Wake Word:** athena (if available)
7. **Save**

#### Step 6.4: Test Pipelines

**Test Control Pipeline:**
1. **Settings → Voice Assistants → Control Pipeline**
2. Click **Test**
3. Type: "turn on office lights"
4. Verify: HA processes command locally (check logs)

**Test Knowledge Pipeline:**
1. **Settings → Voice Assistants → Knowledge Pipeline**
2. Click **Test**
3. Type: "what's the weather in Baltimore"
4. Verify:
   - Gateway logs show request from HA
   - Orchestrator logs show query processing
   - Response includes weather data

#### Step 6.5: Setup HA Voice Device

**If you have HA Voice preview device:**
1. **Settings → Devices & Services → ESPHome**
2. **Add Device** → Follow pairing instructions
3. Assign to room (e.g., "Office")
4. Set default pipeline: **Knowledge Pipeline**
5. Test: Say "Athena, what's the weather?"

#### Step 6.6: Success Criteria

- [ ] Wyoming add-ons installed and running
- [ ] OpenAI integration configured with Mac Studio gateway
- [ ] Both pipelines created (Control + Knowledge)
- [ ] Control pipeline test works (HA UI test)
- [ ] Knowledge pipeline test works (calls Mac Studio)
- [ ] HA Voice device paired (if available)
- [ ] End-to-end voice query works: "Athena, what's the weather?"

---

### Phase 7: Integration Testing (Week 5-6, Days 29-35)

**Goal:** End-to-end testing and validation

See [Phase 1 Implementation Plan - Section 4.7](2025-11-11-phase1-core-services-implementation.md#phase-17-integration-and-testing-week-5-6) for detailed test suite.

#### Step 7.1: Deploy All Services

```bash
# Create master docker-compose
cat > deploy/compose/docker-compose.yml <<'EOF'
version: '3.8'

services:
  gateway:
    extends:
      file: docker-compose.gateway.yml
      service: gateway

  orchestrator:
    image: athena-orchestrator
    ports:
      - "8001:8001"
    depends_on:
      - gateway

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
EOF

# Deploy all
docker compose -f deploy/compose/docker-compose.yml up -d

# Verify all services
docker compose ps
```

#### Step 7.2: Run Integration Tests

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run test suite
pytest tests/integration/test_phase1.py -v

# Tests should cover:
# - Gateway health and completions
# - Orchestrator classification
# - RAG service queries
# - End-to-end knowledge queries
# - Latency targets
```

#### Step 7.3: Manual Voice Testing

**Test Scenarios:**
1. **Simple Control:** "Jarvis, turn on office lights"
   - Expected: Lights turn on via HA
   - Latency: ≤3.5s

2. **Weather Query:** "Athena, what's the weather in Baltimore?"
   - Expected: Accurate weather with temperature
   - Latency: ≤5.5s

3. **Airport Query:** "Athena, any delays at BWI?"
   - Expected: Airport status with delays/on-time
   - Latency: ≤5.5s

4. **Sports Query:** "Athena, when is the next Ravens game?"
   - Expected: Game schedule
   - Latency: ≤5.5s

5. **Error Handling:** "Athena, what is the meaning of life?"
   - Expected: Graceful fallback answer

#### Step 7.4: Performance Validation

```bash
# Run latency benchmark
for i in {1..20}; do
    time curl -X POST http://localhost:8001/query \
        -d '{"query":"what is the weather"}' \
        -H "Content-Type: application/json"
done | grep "real" | awk '{print $2}' | sort -n

# Calculate P95
# Should be ≤5.5s
```

#### Step 7.5: Success Criteria

- [ ] All services running: `docker compose ps` shows all healthy
- [ ] Integration tests pass: `pytest` returns 0 failures
- [ ] Voice queries work end-to-end
- [ ] Latency targets met (control ≤3.5s, knowledge ≤5.5s)
- [ ] No crashes or errors in logs
- [ ] Prometheus metrics collected from all services

---

### Phase 8: Documentation and Handoff (Week 6, Days 36-42)

**Goal:** Document deployment and create operational runbooks

#### Step 8.1: Create Operational Documentation

```bash
# Create docs directory
mkdir -p docs/operations

# Document deployment
cat > docs/operations/DEPLOYMENT.md <<'EOF'
# Deployment Guide

## Services Overview
- Gateway: http://192.168.10.20:8000
- Orchestrator: http://192.168.10.20:8001
- RAG Services: http://192.168.10.20:8010-8012
- Qdrant: http://192.168.10.29:6333
- Redis: redis://192.168.10.29:6379

## Start All Services
\`\`\`bash
docker compose -f deploy/compose/docker-compose.yml up -d
\`\`\`

## Stop All Services
\`\`\`bash
docker compose -f deploy/compose/docker-compose.yml down
\`\`\`

## View Logs
\`\`\`bash
docker compose logs -f orchestrator
\`\`\`

## Restart Service
\`\`\`bash
docker compose restart orchestrator
\`\`\`
EOF

# Document troubleshooting
cat > docs/operations/TROUBLESHOOTING.md <<'EOF'
# Troubleshooting Guide

## Gateway Not Responding
\`\`\`bash
# Check status
docker ps | grep gateway

# Check logs
docker logs athena-gateway

# Verify Ollama running
curl http://localhost:11434/api/tags

# Restart gateway
docker compose restart gateway
\`\`\`

## Orchestrator Failing
\`\`\`bash
# Check logs
docker logs athena-orchestrator

# Verify gateway accessible
curl http://localhost:8000/health

# Verify Redis accessible
redis-cli -h 192.168.10.29 PING

# Restart orchestrator
docker compose restart orchestrator
\`\`\`
EOF
```

#### Step 8.2: Create Monitoring Dashboard

**Setup Prometheus & Grafana (Optional for Phase 1):**
```bash
# Add to docker-compose
cat >> deploy/compose/docker-compose.yml <<'EOF'
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
EOF

# Create prometheus config
cat > deploy/compose/prometheus.yml <<'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'gateway'
    static_configs:
      - targets: ['gateway:8000']

  - job_name: 'orchestrator'
    static_configs:
      - targets: ['orchestrator:8001']

  - job_name: 'rag-services'
    static_configs:
      - targets: ['rag-weather:8010', 'rag-airports:8011', 'rag-sports:8012']
EOF
```

#### Step 8.3: Update README

```bash
# Update main README
cat > README.md <<'EOF'
# Project Athena - Voice Assistant

**Status:** Phase 1 Complete ✅

## Architecture

- **Mac Studio M4** @ 192.168.10.20 - Gateway, Orchestrator, LLMs, RAG
- **Mac mini M4** @ 192.168.10.29 - Vector DB, Cache, Monitoring
- **Home Assistant** @ 192.168.10.168 - Voice pipelines, device control

## Quick Start

\`\`\`bash
# Start all services
docker compose -f deploy/compose/docker-compose.yml up -d

# Test voice query
curl -X POST http://localhost:8001/query -d '{"query":"what is the weather"}'
\`\`\`

## Documentation

- [Deployment Guide](docs/operations/DEPLOYMENT.md)
- [Troubleshooting](docs/operations/TROUBLESHOOTING.md)
- [Architecture](docs/ARCHITECTURE.md)

## Voice Commands

- **"Jarvis, turn on office lights"** - Control pipeline (HA native)
- **"Athena, what's the weather?"** - Knowledge pipeline (LLM + RAG)

## Phase 1 Capabilities

- ✅ Dual pipelines (Control + Knowledge)
- ✅ 3 RAG sources (Weather, Airports, Sports)
- ✅ Local LLM inference (Ollama)
- ✅ Vector DB (Qdrant)
- ✅ Cache (Redis)
- ✅ End-to-end voice queries

## Next Steps (Phase 2)

- Add remaining RAG sources (News, Recipes, Streaming, Dining)
- Guest mode with Airbnb calendar integration
- Performance optimization (≤4.0s target)
- Cross-model validation

EOF
```

#### Step 8.4: Success Criteria

- [ ] Operational docs created (DEPLOYMENT.md, TROUBLESHOOTING.md)
- [ ] README updated with Phase 1 status
- [ ] Monitoring dashboard deployed (optional)
- [ ] All services documented with start/stop commands
- [ ] Known issues documented
- [ ] Next steps clearly defined

---

## Final Validation Checklist

### Infrastructure

- [ ] Mac Studio accessible at 192.168.10.20
- [ ] Mac mini accessible at 192.168.10.29
- [ ] All services running: `docker compose ps`
- [ ] Qdrant healthy: `curl http://192.168.10.29:6333/healthz`
- [ ] Redis healthy: `redis-cli -h 192.168.10.29 PING`

### Services

- [ ] Gateway responding: `curl http://localhost:8000/health`
- [ ] Orchestrator responding: `curl http://localhost:8001/health`
- [ ] Weather RAG responding: `curl http://localhost:8010/health`
- [ ] Airports RAG responding: `curl http://localhost:8011/health`
- [ ] Sports RAG responding: `curl http://localhost:8012/health`

### Home Assistant

- [ ] Wyoming add-ons installed (Faster Whisper, Piper)
- [ ] OpenAI integration configured (pointing to Mac Studio)
- [ ] Control pipeline created
- [ ] Knowledge pipeline created
- [ ] HA Voice device paired (if available)

### End-to-End Testing

- [ ] Control query works: "turn on lights"
- [ ] Weather query works: "what's the weather"
- [ ] Airport query works: "delays at BWI"
- [ ] Sports query works: "next Ravens game"
- [ ] Latency targets met (≤5.5s for knowledge)

### Documentation

- [ ] DEPLOYMENT.md exists and is accurate
- [ ] TROUBLESHOOTING.md covers common issues
- [ ] README.md updated with Phase 1 status
- [ ] All API keys documented in .env.example
- [ ] Architecture diagram updated

---

## Timeline Summary

| Phase | Duration | Tasks | Verification |
|-------|----------|-------|--------------|
| 0: Environment Setup | 2 days | Mac setup, Docker, Ollama, env vars | SSH works, models downloaded |
| 1: Mac mini Services | 2 days | Qdrant, Redis deployment | Services accessible |
| 2: Repo Restructuring | 3 days | Create apps/, migrate code | Imports work, structure clean |
| 3: Gateway | 3 days | LiteLLM deployment, testing | Gateway responds, OpenAI compatible |
| 4: RAG Services | 4 days | Weather, Airports, Sports | All 3 services responding |
| 5: Orchestrator | 7 days | LangGraph implementation, testing | End-to-end flow works |
| 6: HA Integration | 7 days | Wyoming setup, pipelines | Voice queries work |
| 7: Integration Testing | 7 days | Test suite, manual testing | All tests pass, latency OK |
| 8: Documentation | 7 days | Docs, runbooks, handoff | Complete operational docs |
| **Total** | **6-8 weeks** | **Full Phase 1** | **Working voice assistant** |

---

## Next Steps After Phase 1

Once Phase 1 is complete and validated:

1. **Optimize Performance** (Phase 2 prep)
   - Profile latency bottlenecks
   - Optimize model quantization
   - Add caching layers
   - Target: ≤4.0s for knowledge queries

2. **Add Remaining RAG Sources** (Phase 2)
   - News (NewsAPI)
   - Recipes (Spoonacular)
   - Streaming (JustWatch/TMDB)
   - Dining (Yelp/Google Places)

3. **Guest Mode Implementation** (Phase 2)
   - Airbnb calendar integration
   - Permission scoping
   - PII protection
   - Auto-purge on checkout

4. **Admin Interface** (Phase 3)
   - Web UI for configuration
   - Feedback review
   - Mode control
   - Observability dashboard

---

## Related Documentation

- [Complete Architecture Pivot](../research/2025-11-11-complete-architecture-pivot.md) - Overall vision
- [Phase 1 Implementation](2025-11-11-phase1-core-services-implementation.md) - Detailed Phase 1 steps
- [Component Deep-Dive](2025-11-11-component-deep-dive-plans.md) - Technical specs
- [Guest Mode Plan](2025-11-11-guest-mode-and-quality-tracking.md) - Phase 2 guest features
- [Admin Interface](2025-11-11-admin-interface-specification.md) - Phase 3 web UI
- [Kubernetes Strategy](2025-11-11-kubernetes-deployment-strategy.md) - K8s deployment (future)
- [Haystack Integration](2025-11-11-haystack-rageval-dvc-integration.md) - Production RAG (future)

---

**Timeline:** 6-8 weeks for complete bootstrap
**Last Updated:** 2025-11-11
**Status:** Ready for implementation
