---
date: 2025-11-12
researcher: Claude Code (Sonnet 4.5)
commit: 822d785
branch: main
tags: [admin-interface, configuration, rag, voice-pipeline, research]
---

# Research: Admin Configuration Features and Historical Functionality

## Executive Summary

This research documents the historical configuration features that existed in the Athena Admin interface, including server IP configuration, RAG connector management, and voice pipeline testing capabilities. The research was conducted in response to user feedback that these features "used to be there" and need to be re-implemented in the current admin interface.

**Key Findings:**
- Server IP addresses were configured for Mac Studio (192.168.10.167) and Mac mini (192.168.10.181)
- RAG system uses 7 distinct service connectors with centralized configuration
- Voice pipeline testing included 10+ different test scripts and endpoints
- Admin app setup script (`/tmp/admin-setup.py`) provided initialization but lacked ongoing configuration UI
- Current admin interface (Phase 2) only implements Policies, Secrets, Devices, and Audit Logs

## Research Methodology

**Approach:** Parallel research using 4 specialized agents
1. **codebase-locator**: Located all admin application files
2. **thoughts-locator**: Found historical documentation and implementation notes
3. **codebase-pattern-finder (RAG)**: Identified RAG connector patterns
4. **codebase-pattern-finder (voice)**: Identified voice pipeline testing patterns

**Scope:** Entire `/Users/jaystuart/dev/project-athena/` codebase
**Date:** November 12, 2025

## 1. Server IP Configuration

### Historical Configuration

The system historically tracked these server IP addresses:

**Mac Studio M4 64GB (192.168.10.167)**
- Gateway service (port 8000)
- Orchestrator service (port 8001)
- Ollama LLM service (port 11434)
- RAG services: Weather (8010), Airports (8011), Sports (8012)

**Mac mini M4 16GB (192.168.10.181)**
- Qdrant vector database (port 6333)
- Redis cache (port 6379)

**Home Assistant (192.168.10.168)**
- HTTP API (port 8123)
- Wyoming protocol integration

### Current State

**Where IPs are referenced:**
- `admin/backend/main.py:227-362` - Service status endpoint hardcodes IPs
- `deployment/mac-studio/docker-compose.yml:1-110` - Docker environment variables
- `deployment/mac-mini/docker-compose.yml:1-93` - Docker environment variables
- `/tmp/admin-setup.py:19-22` - Database connection string hardcoded

**Problem:** No UI for viewing or editing server IPs. All configuration is hardcoded in deployment files or environment variables.

### Recommendation

Create a "System Configuration" section in admin UI with:
- Server registry (Name, IP, Role, Status)
- Port mappings for each service
- Health check URLs
- Editable via admin/owner roles only

## 2. RAG Connector Configuration

### RAG System Architecture

The RAG (Retrieval Augmented Generation) system uses multiple specialized connectors:

#### 2.1 Vector Database (Qdrant)

**Location:** `scripts/init_qdrant.py:1-170`

**Configuration:**
```python
QDRANT_URL = "http://192.168.10.181:6333"
COLLECTION_NAME = "athena_knowledge"
VECTOR_SIZE = 384  # sentence-transformers/all-MiniLM-L6-v2
DISTANCE_METRIC = Distance.COSINE
```

**Key Features:**
- 384-dimensional embeddings (MiniLM-L6-v2 model)
- Cosine similarity distance metric
- Supports multiple collections
- Optimized indexing parameters

**File Reference:** `scripts/init_qdrant.py:15-32`

#### 2.2 Redis Caching Layer

**Location:** `src/shared/cache.py:1-77`

**Configuration:**
```python
REDIS_URL = "redis://192.168.10.181:6379"
CACHE_TTL = 3600  # 1 hour default
CACHE_ENABLED = True
```

**Key Features:**
- LRU eviction policy (2GB max memory)
- TTL-based expiration
- Decorator-based caching: `@cached(ttl=3600)`
- Automatic key prefixing by service

**Deployment:** `deployment/mac-mini/docker-compose.yml:70-93`

#### 2.3 Weather RAG Service

**Location:** `src/rag/weather_rag.py:1-173`

**Configuration:**
```python
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
WEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
WEATHER_PORT = 8010
```

**Capabilities:**
- Current weather conditions
- 5-day forecast
- Weather alerts
- Cached responses (1 hour TTL)

**File Reference:** `src/rag/weather_rag.py:12-32`

#### 2.4 Airports/Flights RAG Service

**Location:** `src/rag/airports_rag.py:1-164`

**Configuration:**
```python
FLIGHTAWARE_API_KEY = os.getenv("FLIGHTAWARE_API_KEY")
AIRPORTS_PORT = 8011
```

**Capabilities:**
- Airport information lookup
- Flight status tracking
- Arrival/departure boards
- Cached responses (30 minute TTL)

**File Reference:** `src/rag/airports_rag.py:14-29`

#### 2.5 Sports RAG Service

**Location:** `src/rag/sports_rag.py:1-171`

**Configuration:**
```python
SPORTS_API_KEY = os.getenv("THESPORTSDB_API_KEY")
SPORTS_PORT = 8012
```

**Capabilities:**
- Team information
- Live scores
- Schedule lookups
- League standings
- Cached responses (15 minute TTL)

**File Reference:** `src/rag/sports_rag.py:13-31`

#### 2.6 Policy-Based Configuration

**Location:** `admin/backend/app/models.py:59-99`

**Configuration Storage:**
```python
class Policy(Base):
    mode = Column(String(16))  # 'fast', 'medium', 'custom', 'rag'
    config = Column(JSONB)     # Flexible JSON configuration
    version = Column(Integer)   # Version tracking
```

**Policy Config Examples:**
```json
{
  "model": "llama3.1:8b-q4",
  "temperature": 0.8,
  "max_tokens": 1000,
  "use_rag": true,
  "use_tools": true,
  "rag_top_k": 5
}
```

**File Reference:** `/tmp/admin-setup.py:60-109`

### Current State

**What exists:**
- Policy configurations with JSONB flexibility
- Secret management for API keys (OpenWeatherMap, FlightAware, TheSportsDB)
- Service status monitoring endpoint

**What's missing:**
- UI for enabling/disabling RAG connectors
- UI for configuring connector-specific settings
- UI for testing individual connectors
- UI for viewing connector health and cache stats

### Recommendation

Create a "RAG Connectors" section in admin UI with:
- List of available connectors (Weather, Airports, Sports, Custom)
- Enable/disable toggle for each
- Configuration form for connector-specific settings
- "Test Connection" button with sample query
- Cache statistics (hit rate, size, TTL)
- API key management (link to Secrets tab)

## 3. Voice Pipeline Testing

### Voice Pipeline Architecture

The voice pipeline consists of several stages:
1. Wake word detection (OpenWakeWord)
2. Voice Activity Detection (VAD)
3. Speech-to-Text (Faster-Whisper)
4. LLM Processing (Phi-3 / Llama-3.1)
5. Home Assistant Execution
6. Text-to-Speech (Piper TTS)

### 3.1 Wake Word Testing

**Location:** `research/jetson-iterations/test_wake_words.py:1-57`

**Test Capabilities:**
- Multiple wake word models (Jarvis, Athena)
- Threshold tuning (0.1 to 0.5)
- Audio file testing
- Real-time microphone testing
- Confidence score reporting

**Example Code:**
```python
WAKE_WORD_MODELS = [
    '/mnt/nvme/athena-lite/models/jarvis.tflite',
    '/mnt/nvme/athena-lite/models/athena.tflite'
]
oww_model = Model(wakeword_models=WAKE_WORD_MODELS, inference_framework='tflite')

# Test with multiple thresholds
for threshold in [0.1, 0.2, 0.3, 0.4, 0.5]:
    prediction = oww_model.predict(audio_data)
    if prediction['jarvis'] > threshold:
        print(f'DETECTED: jarvis = {prediction["jarvis"]:.3f}')
```

**File Reference:** `research/jetson-iterations/test_wake_words.py:12-45`

### 3.2 Audio Input Testing

**Location:** `research/jetson-iterations/test_audio.py:1-61`

**Test Capabilities:**
- PyAudio stream verification
- Microphone input testing
- Audio format validation
- Real-time audio visualization
- Recording and playback testing

**Key Configuration:**
```python
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
```

**File Reference:** `research/jetson-iterations/test_audio.py:8-25`

### 3.3 Full Pipeline Testing (Athena Lite)

**Location:** `research/jetson-iterations/athena_lite.py:1-342`

**Test Capabilities:**
- End-to-end voice pipeline (wake → STT → LLM → HA → TTS)
- Timing metrics for each stage
- VAD integration
- Home Assistant API integration
- Response generation and playback

**Performance Metrics:**
```python
# Timing tracking
wake_detection_time = 0.0
stt_time = 0.0
llm_processing_time = 0.0
ha_execution_time = 0.0
tts_generation_time = 0.0
total_response_time = 0.0  # Target: 2-5 seconds
```

**File Reference:** `research/jetson-iterations/athena_lite.py:145-180`

### 3.4 LLM Processing Testing

**Location:** `scripts/test_ollama.sh:1-19`

**Test Capabilities:**
- Ollama service connectivity
- Model availability checking
- Generation speed benchmarking
- Response quality validation

**Example Test:**
```bash
curl http://192.168.10.167:11434/api/generate -d '{
  "model": "phi3:mini-q8",
  "prompt": "What is the capital of France?",
  "stream": false
}'
```

**File Reference:** `scripts/test_ollama.sh:5-18`

### 3.5 System Status Monitoring

**Location:** `admin/backend/main.py:227-362`

**Monitored Services:**
- Gateway (192.168.10.167:8000)
- Orchestrator (192.168.10.167:8001)
- Weather RAG (192.168.10.167:8010)
- Airports RAG (192.168.10.167:8011)
- Sports RAG (192.168.10.167:8012)
- Whisper STT (192.168.10.167:10300) - Wyoming protocol
- Piper TTS (192.168.10.167:10200) - Wyoming protocol
- Ollama LLM (192.168.10.167:11434)
- Qdrant Vector DB (192.168.10.181:6333)
- Redis Cache (192.168.10.181:6379)
- Home Assistant (192.168.10.168:8123)

**Health Check Example:**
```python
async def check_service(host: str, port: int, service_name: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{host}:{port}/health", timeout=2) as resp:
                if resp.status == 200:
                    return {"status": "online", "response_time": resp.elapsed.total_seconds()}
    except:
        return {"status": "offline"}
```

**File Reference:** `admin/backend/main.py:245-290`

### 3.6 Device Heartbeat Monitoring

**Location:** `admin/backend/app/routes/devices.py:254-283`

**Test Capabilities:**
- Device registration
- Heartbeat tracking (last_seen timestamp)
- Status updates (online, offline, degraded)
- Zone-based device filtering

**API Endpoint:**
```python
@router.post("/{device_id}/heartbeat")
async def device_heartbeat(device_id: int, status: str = 'online'):
    device.last_seen = datetime.utcnow()
    device.status = status
    return {"device_id": device.id, "last_seen": device.last_seen.isoformat()}
```

**File Reference:** `admin/backend/app/routes/devices.py:254-283`

### Current State

**What exists:**
- Comprehensive test scripts for each pipeline stage
- Service health monitoring endpoint
- Device heartbeat tracking

**What's missing:**
- UI for running voice pipeline tests
- UI for viewing test results and metrics
- UI for benchmarking response times
- UI for testing specific components (wake word, STT, LLM, TTS)
- UI for viewing historical test results

### Recommendation

Create a "Voice Testing" section in admin UI with:
- **Quick Tests:**
  - Test Wake Word Detection (with threshold slider)
  - Test Speech-to-Text (record audio → see transcript)
  - Test LLM Processing (type query → see response + timing)
  - Test Text-to-Speech (type text → hear audio)
  - Test Full Pipeline (speak → hear response + timing breakdown)

- **Advanced Tests:**
  - Component benchmarking (measure latency for each stage)
  - Historical test results (graph response times over time)
  - Audio quality testing (upload audio file → run pipeline)
  - Concurrent request testing (simulate multiple users)

- **System Status:**
  - Service health dashboard (live status of all components)
  - Device heartbeat monitor (online/offline Wyoming devices)
  - Resource utilization (CPU, memory, GPU for each service)

## 4. Other Configurable System Components

### 4.1 Zones Configuration

**Current Implementation:** Hardcoded in documentation
**File Reference:** `CLAUDE.md:195-206`

**10 Zones:**
1. Office
2. Kitchen
3. Living Room
4. Master Bedroom
5. Master Bath
6. Main Bath
7. Alpha (Guest Bedroom 1)
8. Beta (Guest Bedroom 2)
9. Basement Bathroom
10. Dining Room

**Missing:** UI for adding/editing/deleting zones

### 4.2 API Keys / Credentials

**Current Implementation:** Secrets management (Phase 2)
**File Reference:** `admin/backend/app/routes/secrets.py:1-309`

**Supported APIs:**
- OpenWeatherMap (weather data)
- FlightAware (flight tracking)
- TheSportsDB (sports data)
- Ticketmaster (events - not yet implemented)

**Setup Script:** `/tmp/admin-setup.py:141-198` creates placeholders

### 4.3 Policy Versioning

**Current Implementation:** Automatic versioning on config changes
**File Reference:** `admin/backend/app/routes/policies.py:294-388`

**Features:**
- Version history tracking
- Rollback to previous versions
- Change descriptions

### 4.4 Audit Logging

**Current Implementation:** Comprehensive audit trail
**File Reference:** `admin/backend/app/models.py:146-168`

**Logged Actions:**
- Policy create/update/delete/rollback
- Secret create/update/delete/reveal
- Device create/update/delete
- User authentication events

## 5. Missing Features Analysis

### 5.1 Server Configuration UI

**Priority:** High
**Complexity:** Medium

**Requirements:**
- CRUD operations for server registry
- Service-to-server mapping
- Health check configuration
- Port allocation management

### 5.2 RAG Connector Management UI

**Priority:** High
**Complexity:** Medium

**Requirements:**
- Enable/disable connectors
- Configure connector settings
- Test individual connectors
- View cache statistics
- Monitor API usage/quotas

### 5.3 Voice Testing UI

**Priority:** High
**Complexity:** High

**Requirements:**
- Interactive test interface
- Audio recording/playback
- Real-time metrics display
- Historical test results
- Component-level testing

### 5.4 Zone Management UI

**Priority:** Medium
**Complexity:** Low

**Requirements:**
- CRUD operations for zones
- Device-to-zone assignment
- Zone status monitoring

### 5.5 Wyoming Device Management

**Priority:** Medium
**Complexity:** Medium

**Requirements:**
- Device discovery/registration
- Wyoming protocol configuration
- Audio pipeline settings
- Wake word threshold tuning

## 6. Implementation Recommendations

### Phase 1: Server Configuration (Quick Win)
1. Create "Settings" tab in admin UI
2. Add server registry with IP/port/status
3. Link to existing service status endpoint
4. Add health check visualization

**Estimated Effort:** 4-6 hours

### Phase 2: RAG Connector Management
1. Create "RAG Connectors" tab
2. Add connector enable/disable toggles
3. Add configuration forms for each connector
4. Add "Test Connection" functionality
5. Display cache statistics

**Estimated Effort:** 8-12 hours

### Phase 3: Voice Testing Interface
1. Create "Voice Testing" tab
2. Add component-level test buttons
3. Implement audio recording/playback
4. Add metrics visualization
5. Add historical test results

**Estimated Effort:** 16-20 hours

### Phase 4: Advanced Features
1. Zone management UI
2. Wyoming device auto-discovery
3. Real-time monitoring dashboard
4. Performance analytics

**Estimated Effort:** 20-30 hours

## 7. File References

### Admin Application Files (40+)

**Backend Core:**
- `admin/backend/main.py` - FastAPI application, service status endpoint
- `admin/backend/app/models.py` - Database models (User, Policy, Secret, Device, AuditLog)
- `admin/backend/app/routes/policies.py` - Policy CRUD operations
- `admin/backend/app/routes/secrets.py` - Secret management with encryption
- `admin/backend/app/routes/devices.py` - Device management
- `admin/backend/app/routes/users.py` - User management
- `admin/backend/app/routes/audit.py` - Audit log access

**Frontend:**
- `admin/frontend/app.js` - Single-page application with tab-based interface
- `admin/frontend/styles.css` - UI styling

**Deployment:**
- `admin/k8s/deployment.yaml` - Kubernetes deployment manifests
- `deployment/mac-studio/docker-compose.yml` - Mac Studio service configuration
- `deployment/mac-mini/docker-compose.yml` - Mac mini service configuration

### RAG Service Files (7 patterns)

**Infrastructure:**
- `scripts/init_qdrant.py` - Qdrant initialization and management
- `src/shared/cache.py` - Redis caching decorator
- `deployment/mac-mini/docker-compose.yml` - Qdrant + Redis deployment

**RAG Services:**
- `src/rag/weather_rag.py` - Weather data retrieval
- `src/rag/airports_rag.py` - Airport/flight information
- `src/rag/sports_rag.py` - Sports data and scores

### Voice Testing Files (10+ scripts)

**Component Tests:**
- `research/jetson-iterations/test_wake_words.py` - Wake word detection testing
- `research/jetson-iterations/test_audio.py` - Audio input testing
- `scripts/test_ollama.sh` - LLM connectivity testing

**Integration Tests:**
- `research/jetson-iterations/athena_lite.py` - Full pipeline testing
- `admin/backend/main.py` - Service health monitoring

**Device Management:**
- `admin/backend/app/routes/devices.py` - Device heartbeat tracking

### Documentation (22 files)

**Implementation Status:**
- `CURRENT_IMPLEMENTATION_STATUS.md`
- `IMPLEMENTATION_COMPLETE.md`
- `FULL_IMPLEMENTATION_PROGRESS.md`

**Phase Documentation:**
- `thoughts/shared/plans/2025-11-03-admin-phase2-completion.md`
- Multiple daily progress documents

## 8. Conclusions

The Athena Admin interface historically had or was designed to have significantly more configuration capabilities than currently implemented:

**Server Configuration:** IP addresses and service mappings were documented but never exposed in a UI
**RAG Connectors:** 7 distinct services with flexible configuration, but no centralized management UI
**Voice Testing:** Extensive test scripts exist, but no interactive testing interface
**System Settings:** Many configurable components lack UI for modification

**Current State (Phase 2):**
- ✅ Policies: Implemented with versioning and rollback
- ✅ Secrets: Implemented with encryption and audit trail
- ✅ Devices: Implemented with heartbeat monitoring
- ✅ Audit Logs: Comprehensive logging of all actions
- ❌ Server Configuration: Missing
- ❌ RAG Connector Management: Missing
- ❌ Voice Testing Interface: Missing
- ❌ Zone Management: Missing

**Next Steps:**
1. Prioritize feature implementation (recommend Server Config → RAG Connectors → Voice Testing)
2. Create detailed specifications for each feature
3. Design UI mockups for user approval
4. Implement iteratively with user testing

---

**Research Completed:** November 12, 2025
**Researcher:** Claude Code (Sonnet 4.5)
**Repository:** `/Users/jaystuart/dev/project-athena/`
**Git Commit:** 822d785 (main branch)
