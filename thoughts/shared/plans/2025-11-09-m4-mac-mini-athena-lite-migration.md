# M4 Mac Mini Integration - Athena Lite Feature Migration Addendum

**Date:** 2025-11-09
**Status:** CRITICAL ADDENDUM to main M4 Mac Mini plan
**Parent Plan:** `2025-11-09-m4-mac-mini-integration.md`

---

## PURPOSE

This addendum documents how to migrate **all existing Athena Lite features** to the M4 Mac Mini architecture. The main plan covers basic infrastructure but does NOT account for the advanced features already working on the Jetson.

**What's at risk if we don't account for this:**
- Losing multi-intent handling capability
- Losing facade pattern with API integrations (10+ services)
- Losing 3-tier caching (300-600ms responses vs 3-5s)
- Losing anti-hallucination validation
- Losing function calling for HA device control
- Having to rebuild features that already work

---

## ATHENA LITE FEATURES TO MIGRATE

### 1. Multi-Intent Handling (Production-Ready)

**Current Status on Jetson:**
- ✅ Phase 1-4 complete (query_splitter, intent_processor, response_merger)
- ⏸️ Phase 5 (facade integration) pending
- **Files:** `facade/query_splitter.py`, `facade/intent_processor.py`, `facade/response_merger.py`

**Migration to Mac Mini:**
- **Service:** Intent Classification (:8001)
- **Action:** Copy all 3 modules to Mac Mini intent service
- **Integration:** Wire into Phi-3 intent classifier
- **Feature Flag:** `MULTI_INTENT_MODE=false` (default off for safety)

**Updated Intent Service Architecture:**
```python
# Mac Mini :8001 Intent Service
@app.route('/classify', methods=['POST'])
def classify():
    transcription = request.json['transcription']

    # Check if multi-intent enabled
    if MULTI_INTENT_MODE:
        # Split query into multiple parts
        parts = query_splitter.split(transcription)

        if len(parts) > 1:
            # Classify each part independently
            intents = []
            for part in parts:
                intent = phi3_classify(part)
                intents.append(intent)

            return {"mode": "multi", "intents": intents}

    # Single intent (default path)
    intent = phi3_classify(transcription)
    return {"mode": "single", "intent": intent}
```

**Files to Migrate:**
1. `src/jetson/facade/query_splitter.py` → `mac-mini/services/intent/query_splitter.py`
2. `src/jetson/facade/intent_processor.py` → `mac-mini/services/command/intent_processor.py`
3. `src/jetson/facade/response_merger.py` → `mac-mini/services/command/response_merger.py`

---

### 2. Facade Pattern & API Handlers (Critical Performance Feature)

**Current Status on Jetson:**
- ✅ 7-category intent classifier
- ✅ 8 specialized handlers (weather, sports, news, events, streaming, finance, location, web search)
- ✅ 10+ API integrations
- ✅ 300-600ms response times (vs 3-5s LLM)

**Migration to Mac Mini:**
- **Service:** Command Execution (:8002)
- **Action:** Migrate all handler modules and API clients
- **Critical:** This is what makes Athena fast - don't lose it!

**Handler Migration Map:**

| Handler | API | Athena Lite Location | Mac Mini Location |
|---------|-----|----------------------|-------------------|
| Weather | OpenWeatherMap | `facade/weather_handler.py` | `services/command/handlers/weather_handler.py` |
| Sports | ESPN | `sports_client.py` | `services/command/handlers/sports_handler.py` |
| Events | Ticketmaster | `facade/events_handler.py` | `services/command/handlers/events_handler.py` |
| Streaming | JustWatch | `facade/streaming_handler.py` | `services/command/handlers/streaming_handler.py` |
| News | NewsAPI | `facade/news_handler.py` | `services/command/handlers/news_handler.py` |
| Finance | Alpha Vantage | `facade/finance_handler.py` | `services/command/handlers/finance_handler.py` |
| Location | Google Places | `facade/location_handler.py` | `services/command/handlers/location_handler.py` |
| Web Search | DuckDuckGo | `facade/web_search_handler.py` | `services/command/handlers/web_search_handler.py` |

**Updated Command Service Architecture:**
```python
# Mac Mini :8002 Command Service
@app.route('/execute', methods=['POST'])
def execute():
    classification = request.json['classification']
    zone = request.json['zone']

    # Check if facade-capable intent
    if classification['intent'] in FACADE_HANDLERS:
        handler = FACADE_HANDLERS[classification['intent']]

        # Try API handler first (fast path)
        try:
            response = handler.execute(classification, zone)
            if response:
                return {"success": True, "response": response, "source": "api"}
        except Exception as e:
            logger.warning(f"API handler failed: {e}, falling back to LLM")

    # LLM path (slow path)
    response = llm_generate(classification, zone)
    return {"success": True, "response": response, "source": "llm"}
```

**API Keys to Configure on Mac Mini:**
```bash
# .env file on Mac Mini
OPENWEATHER_API_KEY=xxx
GOOGLE_PLACES_API_KEY=xxx
TICKETMASTER_API_KEY=xxx
NEWSAPI_KEY=xxx
ALPHAVANTAGE_API_KEY=xxx
HA_TOKEN=xxx
```

---

### 3. Three-Tier Caching System

**Current Status on Jetson:**
- ✅ Memory cache (1-hour TTL)
- ✅ Redis cache (24-hour TTL)
- ✅ Disk cache (7-day TTL)
- ✅ 85% hit rate for weather, 95% for time

**Migration to Mac Mini:**
- **Service:** Command Execution (:8002)
- **Action:** Migrate caching.py module
- **Redis:** Run Redis on Mac Mini (brew install redis)

**Files to Migrate:**
1. `src/jetson/caching.py` → `mac-mini/services/command/caching.py`

**Configuration:**
```python
# Mac Mini caching config
CACHE_CONFIG = {
    "memory": {
        "ttl": 3600,  # 1 hour
        "max_entries": 1000
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "ttl": 86400  # 24 hours
    },
    "disk": {
        "path": "/mnt/athena-data/cache",
        "ttl": 604800  # 7 days
    }
}
```

---

### 4. Anti-Hallucination Validation

**Current Status on Jetson:**
- ✅ Validates LLM responses against API data
- ✅ Rejects hallucinated facts
- ✅ Forces regeneration on invalid data

**Migration to Mac Mini:**
- **Service:** Command Execution (:8002)
- **Action:** Migrate validation.py module

**Files to Migrate:**
1. `src/jetson/validation.py` → `mac-mini/services/command/validation.py`

**Integration:**
```python
# Mac Mini command service with validation
response = llm_generate(classification, zone)

# Validate against known facts
if not validation.validate_response(response, classification):
    logger.warning("Hallucination detected, regenerating...")
    response = llm_generate(classification, zone, temperature=0.1)

return response
```

---

### 5. Function Calling for HA Device Control

**Current Status on Jetson:**
- ✅ Auto-extracts entity IDs from queries
- ✅ Direct HA API calls (no LLM needed for simple commands)
- ✅ "Turn on office lights" → 300ms response

**Migration to Mac Mini:**
- **Service:** Command Execution (:8002)
- **Action:** Migrate function_calling.py module

**Files to Migrate:**
1. `src/jetson/function_calling.py` → `mac-mini/services/command/function_calling.py`
2. `src/jetson/ha_client.py` → `mac-mini/services/command/ha_client.py`

**Integration:**
```python
# Mac Mini command service with function calling
if classification['intent'] == 'home_control':
    # Extract function call from query
    function_call = function_calling.extract(transcription, classification)

    if function_call:
        # Direct HA API call (no LLM needed)
        result = ha_client.execute(function_call)
        return {"success": True, "response": result, "source": "function_call"}
```

---

### 6. Conversation Context Management

**Current Status on Jetson:**
- ✅ Tracks conversation history
- ✅ Multi-turn conversation support
- ✅ Context-aware responses

**Migration to Mac Mini:**
- **Service:** Orchestration Hub (:8080 on Proxmox VM)
- **Action:** Migrate context_manager.py module
- **Storage:** Redis on Mac Mini

**Files to Migrate:**
1. `src/jetson/context_manager.py` → `orchestration-hub/context_manager.py`

**Integration:**
```python
# Orchestration hub with context
context = context_manager.get_context(zone)

# Send context to Mac Mini intent service
intent = requests.post('http://192.168.10.17:8001/classify', json={
    "transcription": transcription,
    "context": context
})

# Update context after response
context_manager.update_context(zone, intent, response)
```

---

### 7. Prometheus Metrics Collection

**Current Status on Jetson:**
- ✅ Request counts
- ✅ Latency tracking
- ✅ Cache hit rates
- ✅ Error rates

**Migration to Mac Mini:**
- **Service:** All Mac Mini services (:9090-9093)
- **Action:** Migrate metrics.py module

**Files to Migrate:**
1. `src/jetson/metrics.py` → `mac-mini/services/common/metrics.py`

**Metrics Endpoints:**
```
http://192.168.10.17:9090/metrics  # STT metrics
http://192.168.10.17:9091/metrics  # Intent metrics
http://192.168.10.17:9092/metrics  # Command metrics
http://192.168.10.17:9093/metrics  # TTS metrics
```

---

## UPDATED MAC MINI SERVICE ARCHITECTURE

### Intent Service (:8001) - ENHANCED

**Original Plan:**
- Phi-3-mini for intent classification

**Enhanced with Athena Lite Features:**
```
/usr/local/athena/services/intent/
├── intent_server.py              # Main Flask service
├── query_splitter.py             # Multi-intent query splitting
├── intent_processor.py           # Multi-intent processing
├── airbnb_classifier.py          # 7-category classifier
├── metrics.py                    # Prometheus metrics
└── config.py                     # Feature flags
```

**Features:**
- Multi-intent handling (feature flag)
- 7-category classification (weather, location, transportation, entertainment, news, finance, web_search)
- Metrics collection
- Error handling with fallbacks

---

### Command Service (:8002) - ENHANCED

**Original Plan:**
- Llama-3.2-3B for command generation
- Home Assistant API integration

**Enhanced with Athena Lite Features:**
```
/usr/local/athena/services/command/
├── command_server.py             # Main Flask service
├── response_merger.py            # Multi-intent response merging
├── caching.py                    # 3-tier caching
├── validation.py                 # Anti-hallucination
├── function_calling.py           # HA function extraction
├── ha_client.py                  # HA API client
├── metrics.py                    # Prometheus metrics
├── handlers/                     # Facade handlers
│   ├── weather_handler.py        # OpenWeatherMap
│   ├── sports_handler.py         # ESPN
│   ├── events_handler.py         # Ticketmaster
│   ├── streaming_handler.py      # JustWatch
│   ├── news_handler.py           # NewsAPI
│   ├── finance_handler.py        # Alpha Vantage
│   ├── location_handler.py       # Google Places
│   └── web_search_handler.py     # DuckDuckGo
└── config.py                     # Feature flags, API keys
```

**Features:**
- Multi-intent response merging
- Facade pattern (API-first, LLM fallback)
- 3-tier caching (memory → Redis → disk)
- Anti-hallucination validation
- Function calling for HA device control
- 10+ API integrations
- Metrics collection

---

### Orchestration Hub (Proxmox VM) - ENHANCED

**Original Plan:**
- Wake word routing
- Zone determination
- Audio coordination

**Enhanced with Athena Lite Features:**
```
/home/athena/athena-orchestration/
├── orchestration_service.py      # Main WebSocket service
├── context_manager.py            # Conversation context
├── metrics.py                    # Prometheus metrics
└── config/
    └── zones.yaml                # Zone configuration
```

**Features:**
- Conversation context tracking
- Multi-turn conversation support
- Zone-aware context
- Session management

---

## MIGRATION CHECKLIST

### Pre-Migration Validation (On Jetson)

- [ ] **Verify all features working on Jetson**
  - [ ] Multi-intent handling (test compound queries)
  - [ ] Facade handlers (test weather, sports, news, etc.)
  - [ ] Caching (check hit rates)
  - [ ] Function calling (test HA device control)
  - [ ] Anti-hallucination (verify no false facts)

- [ ] **Document current performance baselines**
  - [ ] Response times per intent type
  - [ ] Cache hit rates
  - [ ] Error rates
  - [ ] API latencies

- [ ] **Export configuration**
  - [ ] API keys from .env
  - [ ] Feature flags from mode_config.py
  - [ ] Cache TTL settings
  - [ ] HA connection details

### Mac Mini Setup (Before Migration)

- [ ] **Install additional dependencies**
  ```bash
  brew install redis
  pip3 install redis duckduckgo-search requests
  ```

- [ ] **Start Redis**
  ```bash
  brew services start redis
  # Verify: redis-cli ping (should return PONG)
  ```

- [ ] **Create enhanced directory structure**
  ```bash
  cd /usr/local/athena/services
  mkdir -p intent/handlers
  mkdir -p command/handlers
  mkdir -p common
  ```

### File Migration (Jetson → Mac Mini)

#### Phase 1: Core Modules
- [ ] Copy `query_splitter.py` to Mac Mini intent service
- [ ] Copy `intent_processor.py` to Mac Mini command service
- [ ] Copy `response_merger.py` to Mac Mini command service
- [ ] Copy `caching.py` to Mac Mini command service
- [ ] Copy `validation.py` to Mac Mini command service
- [ ] Copy `function_calling.py` to Mac Mini command service
- [ ] Copy `ha_client.py` to Mac Mini command service
- [ ] Copy `metrics.py` to Mac Mini common/

#### Phase 2: Facade Handlers
- [ ] Copy `facade/weather_handler.py` to Mac Mini command/handlers/
- [ ] Copy `sports_client.py` to Mac Mini command/handlers/sports_handler.py
- [ ] Copy `facade/events_handler.py` to Mac Mini command/handlers/
- [ ] Copy `facade/streaming_handler.py` to Mac Mini command/handlers/
- [ ] Copy `facade/news_handler.py` to Mac Mini command/handlers/
- [ ] Copy `facade/finance_handler.py` to Mac Mini command/handlers/
- [ ] Copy `facade/location_handler.py` to Mac Mini command/handlers/
- [ ] Copy `facade/web_search_handler.py` to Mac Mini command/handlers/

#### Phase 3: Configuration
- [ ] Copy API keys from Jetson .env to Mac Mini .env
- [ ] Copy feature flags from mode_config.py to Mac Mini config.py
- [ ] Update HA_URL to use Mac Mini perspective
- [ ] Configure Redis connection settings

#### Phase 4: Context Management
- [ ] Copy `context_manager.py` to orchestration hub VM
- [ ] Configure Redis connection to Mac Mini
- [ ] Test context persistence

### Integration Testing (Post-Migration)

#### Test 1: Single Intent Queries (Baseline)
- [ ] "What's the weather?" → Returns weather (facade handler)
- [ ] "What time is it?" → Returns time (direct calculation)
- [ ] "Ravens score?" → Returns sports score (ESPN API)
- [ ] "Turn on office lights" → Controls lights (function calling)
- [ ] Verify response times <3s

#### Test 2: Multi-Intent Queries
- [ ] "What's the weather and what time is it?" → Returns both
- [ ] "Tell me about restaurants and the Ravens score" → Returns both
- [ ] "Weather, restaurants, and events tonight" → Returns all 3
- [ ] Verify response times <8s (3 intents × 2.5s avg)

#### Test 3: Facade Handlers (API Fast Path)
- [ ] Weather query → OpenWeatherMap → <600ms
- [ ] Sports query → ESPN → <600ms
- [ ] News query → NewsAPI → <600ms
- [ ] Events query → Ticketmaster → <800ms
- [ ] Stock query → Alpha Vantage → <600ms

#### Test 4: Caching
- [ ] Repeat same weather query → Memory cache hit → <100ms
- [ ] Wait 1 hour, repeat → Redis cache hit → <200ms
- [ ] Check cache hit rates via metrics

#### Test 5: Anti-Hallucination
- [ ] Ask factual question → Verify no hallucinated data
- [ ] Check validation logs for rejected responses

#### Test 6: Function Calling
- [ ] "Turn on office lights" → Direct HA API call → <500ms
- [ ] "Set bedroom temperature to 72" → HA climate control
- [ ] Verify no LLM involved in simple device control

#### Test 7: Context Management
- [ ] Ask question requiring context
- [ ] Follow-up question → Uses previous context
- [ ] Verify context persists in Redis

---

## PERFORMANCE COMPARISON

### Expected Performance After Migration

| Query Type | Athena Lite (Jetson) | Mac Mini (Enhanced) | Improvement |
|------------|----------------------|---------------------|-------------|
| Weather (facade) | 2.5s | 1.5s | 40% faster |
| Sports (facade) | 2.8s | 1.6s | 43% faster |
| Time (direct) | 2.3s | 1.3s | 43% faster |
| Device control (function) | 2.4s | 1.4s | 42% faster |
| LLM query (complex) | 6.5s | 3.5s | 46% faster |
| Multi-intent (2 queries) | ~5s | ~2.8s | 44% faster |
| Multi-intent (3 queries) | ~7.5s | ~4.2s | 44% faster |

**Overall expected improvement: 40-45% faster response times**

---

## RISK MITIGATION

### Risk 1: Feature Parity Loss
**Risk:** Lose working features during migration
**Mitigation:**
- [ ] Document all working features before migration
- [ ] Test each feature independently on Mac Mini before integration
- [ ] Keep Jetson running during migration for comparison testing
- [ ] Feature flags default to OFF until validated

### Risk 2: Performance Regression
**Risk:** Mac Mini slower than Jetson for some queries
**Mitigation:**
- [ ] Baseline all performance metrics on Jetson first
- [ ] Compare Mac Mini metrics against baselines
- [ ] Profile slow queries with cProfile
- [ ] Optimize before declaring migration complete

### Risk 3: API Integration Failures
**Risk:** API keys or endpoints break during migration
**Mitigation:**
- [ ] Test each API handler independently first
- [ ] Verify API keys work from Mac Mini network perspective
- [ ] Check API rate limits and quotas
- [ ] Implement robust error handling and fallbacks

### Risk 4: Cache Corruption
**Risk:** Redis cache data incompatible between systems
**Mitigation:**
- [ ] Flush Redis cache before migration
- [ ] Start with fresh cache on Mac Mini
- [ ] Monitor cache hit rates during migration
- [ ] Verify cache TTLs match expectations

### Risk 5: Context Loss
**Risk:** Conversation context breaks during migration
**Mitigation:**
- [ ] Test context persistence independently
- [ ] Verify Redis persistence configuration
- [ ] Test multi-turn conversations thoroughly
- [ ] Implement context recovery mechanisms

---

## ROLLBACK PLAN

If migration fails or performance degrades:

1. **Immediate Rollback:**
   - Keep Jetson Athena Lite running during migration
   - Can switch back by pointing orchestration hub to Jetson
   - No data loss (Jetson remains untouched)

2. **Partial Rollback:**
   - Disable problematic features with feature flags
   - Fall back to basic LLM path
   - Investigate issues without breaking entire system

3. **Incremental Migration:**
   - Migrate one feature at a time (multi-intent first, then facade, then caching)
   - Validate each before proceeding
   - Easier to isolate issues

---

## TIMELINE ESTIMATE

### Enhanced Migration Timeline (vs Original Plan)

| Phase | Original Estimate | Enhanced Estimate | Delta |
|-------|-------------------|-------------------|-------|
| Mac Mini Setup | 1-2 hours | 2-3 hours | +1 hour (Redis, deps) |
| STT Service | 2-3 hours | 2-3 hours | No change |
| Intent Service | 3-4 hours | 5-6 hours | +2 hours (multi-intent) |
| Command Service | 3-4 hours | 8-10 hours | +5 hours (facade, caching, validation) |
| TTS Service | 2-3 hours | 2-3 hours | No change |
| Orchestration Hub | 2-3 hours | 3-4 hours | +1 hour (context mgmt) |
| Testing | 2-4 hours | 4-6 hours | +2 hours (more features) |
| **TOTAL** | **15-23 hours** | **26-35 hours** | **+11-12 hours** |

**Total Enhanced Estimate: 26-35 hours (3-5 days of focused work)**

---

## SUCCESS CRITERIA

### Functional Requirements
- [ ] All Athena Lite features working on Mac Mini
- [ ] Multi-intent handling functional (compound queries work)
- [ ] All 8 facade handlers working (API integrations)
- [ ] 3-tier caching operational (hit rates >80%)
- [ ] Anti-hallucination validation active
- [ ] Function calling for HA device control working
- [ ] Conversation context persisting across sessions

### Performance Requirements
- [ ] Response times 40-45% faster than Athena Lite
- [ ] Single-intent queries <2s average
- [ ] Multi-intent queries (2 intents) <3s average
- [ ] Multi-intent queries (3 intents) <5s average
- [ ] Facade queries <1.5s average
- [ ] Cache hit rate >85% for weather
- [ ] Cache hit rate >95% for time

### Reliability Requirements
- [ ] Error rate <5%
- [ ] API fallback chains working (API → WebSearch → LLM)
- [ ] No hallucinated responses passing validation
- [ ] Context persistence survives service restarts

---

## NEXT STEPS

**Before starting M4 Mac Mini migration:**

1. **Complete Athena Lite Phase 5** (if not done)
   - Integrate multi-intent into facade_integration.py
   - Test thoroughly on Jetson
   - Document working configuration

2. **Create Athena Lite Backup**
   - Full backup of /mnt/nvme/athena-lite/
   - Export all configuration
   - Document current performance baselines

3. **Review This Addendum**
   - Validate file migration checklist
   - Confirm all features accounted for
   - Update timeline estimates based on priorities

4. **Proceed with Enhanced Migration**
   - Follow main M4 Mac Mini plan
   - Use this addendum for feature migration
   - Test incrementally

---

## CONCLUSION

The M4 Mac Mini migration is significantly more complex than the original plan suggested. Athena Lite has **10+ production-ready features** that must be migrated to avoid losing critical functionality.

**Key Points:**
- Original plan estimated 15-23 hours
- Enhanced migration requires 26-35 hours
- Delta is +11-12 hours for feature migration
- Risk of losing working features if not accounted for
- Performance gains are substantial (40-45% faster)

**This addendum is REQUIRED reading before starting the migration.**

---

**Last Updated:** 2025-11-09
**Author:** Claude (Sonnet 4.5)
**Status:** Ready for review and validation
**Priority:** CRITICAL - Must be incorporated into migration plan
