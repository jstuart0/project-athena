---
date: 2025-11-14T15:06:51+0000
researcher: Claude (AI Assistant)
git_commit: fd223befd41ef8e7c78b19114552fad274d8e1e7
branch: main
repository: project-athena
topic: "Benchmarking and Optimization Framework for Project Athena"
tags: [research, benchmarking, optimization, metrics, caching, testing, performance]
status: complete
last_updated: 2025-11-14
last_updated_by: Claude (AI Assistant)
---

# Research: Benchmarking and Optimization Framework for Project Athena

**Date**: 2025-11-14T15:06:51+0000
**Researcher**: Claude (AI Assistant)
**Git Commit**: fd223befd41ef8e7c78b19114552fad274d8e1e7
**Branch**: main
**Repository**: project-athena

## Research Question

How can Project Athena be systematically optimized through benchmarking? Specifically:
1. What infrastructure exists for running benchmark tests with 20 example queries?
2. How are metrics collected and measured?
3. How can caching be controlled to ensure fair before/after comparisons?
4. What test datasets and evaluation frameworks are available?

## Summary

Project Athena has a **comprehensive benchmarking and optimization infrastructure** ready for systematic performance testing. The system includes:

- **5 testing layers**: Integration tests, unit tests, voice testing APIs, research/iteration tests, and infrastructure tests
- **Prometheus metrics** for real-time monitoring at gateway and orchestrator levels
- **Database-backed metrics storage** (RAGStats, VoiceTest, AuditLog tables) for historical analysis
- **Redis-based caching** with configurable TTL (1-3600 seconds) that can be disabled for testing
- **20+ example queries** spanning control commands, weather, sports, airports, transit, and food categories
- **Performance targets**: ≤3.5s for control queries, ≤5.5s for knowledge queries
- **Multiple optimization levers**: Caching strategies, parallel search, intent-based routing, RAG connectors

The system is **fully instrumented for before/after optimization measurement** with cache control mechanisms that prevent result contamination between test runs.

## Detailed Findings

### 1. Benchmarking Infrastructure

Project Athena has **five distinct testing layers** for comprehensive evaluation:

#### Integration Tests (`tests/integration/test_orchestrator_gateway.py:1-160`)

End-to-end system validation with:
- **OpenAI-compatible API format** for realistic testing
- **Latency requirement tests**:
  - Control queries: ≤3.5 seconds (line 115-120)
  - Knowledge queries: ≤5.5 seconds (line 122-127)
- **Streaming response testing**
- **Prometheus metrics validation**

Example queries:
```python
# Control command test
"Turn on the office lights"       # Target: ≤3.5s

# Knowledge query test
"What's the weather in Baltimore?" # Target: ≤5.5s
```

#### Unit Tests

**Gateway Tests** (`src/gateway/test_gateway.py:1-42`):
- Query detection validation (Athena vs general)
- Routing logic verification

**Setup Validation** (`scripts/test_basic_setup.py:1-92`):
- Shared utilities import checks
- Component initialization validation

#### Voice Testing API (`admin/backend/app/routes/voice_tests.py:1-277`)

REST endpoints for individual component testing:

| Endpoint | Component | Service URL | Metrics Tracked |
|----------|-----------|-------------|-----------------|
| `/api/voice-tests/stt/test` | Speech-to-Text | `192.168.10.167:10300` | processing_time, confidence |
| `/api/voice-tests/tts/test` | Text-to-Speech | `192.168.10.167:10200` | processing_time, audio_path |
| `/api/voice-tests/llm/test` | Language Model | `192.168.10.167:11434` | tokens, tokens_per_second |
| `/api/voice-tests/rag/test` | RAG Connectors | Ports 8010-8012 | latency, cache_hits |
| `/api/voice-tests/pipeline/test` | Full Pipeline | Multiple | total_time, stage_timings |

Test results are **stored in PostgreSQL** (`VoiceTest` table, models.py:453-472) with:
- `test_type`: "stt", "tts", "llm", "rag_query", "full_pipeline"
- `result`: JSONB field containing timing data
- `executed_at`: Timestamp for historical tracking

#### Research/Iteration Tests (`research/jetson-iterations/`)

Proof-of-concept and component validation:
- `test_wake_words.py`: OpenWakeWord model testing
- `test_universal_data.py`: API integration testing (DuckDuckGo, weather, ESPN)
- `simple_llm_test.py`: LLM processing benchmarks
- `simple_audio_test.py`: Audio device validation

#### Infrastructure Tests

**Qdrant Vector DB** (`scripts/init_qdrant.py:89-131`):
- 384-dimensional vector search testing
- Similarity scoring validation
- Test point insertion/retrieval/cleanup

**Day 1 Verification** (`scripts/verify_day1.sh`):
- Network connectivity checks (Mac mini, Mac Studio, Home Assistant)
- Service health validation (Qdrant, Redis, Ollama)
- API key verification (OpenWeatherMap, FlightAware, TheSportsDB)

### 2. Metrics Collection Infrastructure

#### Prometheus Metrics (Real-Time Monitoring)

**Gateway Service** (`src/gateway/main.py:412`):
```python
request_counter: Counter  # Requests by endpoint/status
request_duration: Histogram  # Response time distribution
```

**Orchestrator Service** (`src/orchestrator/main.py:49-58, 920`):
```python
request_counter: Counter  # Intent processing by type/status
request_duration: Histogram  # Total request duration
node_duration: Histogram  # Individual node execution times
```

Metrics exposed at `/metrics` endpoint in Prometheus format.

#### Database-Stored Metrics

**RAG Performance Statistics** (`admin/backend/app/models.py:427-445`):

`RAGStats` table tracks:
- `requests_count`: Total queries processed
- `cache_hits` / `cache_misses`: Cache effectiveness
- `avg_response_time`: Performance in milliseconds
- `error_count`: Failure tracking
- `timestamp`: Indexed for time-series analysis

API endpoint: `/api/rag-connectors/{id}/stats` (routes/rag_connectors.py:458-532)

Returns:
- `total_requests`
- `cache_hit_rate` (percentage)
- `avg_response_time` (milliseconds)

**Voice Test Results** (`admin/backend/app/models.py:453-472`):

`VoiceTest` table stores:
- `test_type`: Component being tested
- `test_config`: Parameters (JSONB)
- `result`: Performance data including timing (JSONB)
- `success`: Boolean outcome
- `executed_at`: Test timestamp

**Audit Trail** (`admin/backend/app/models.py:202-245`):

`AuditLog` table records:
- `timestamp`: Action time (indexed)
- `action`: Type (create, update, delete, view)
- `success` / `error_message`: Outcome tracking

Statistics API: `/api/audit/stats` (routes/audit.py:94-148)

#### Structured Logging (`src/shared/logging_config.py`)

All services use `structlog` for JSON logging with:
- Automatic service name context
- Timestamp injection
- Stack trace rendering
- Request ID tracking

Log entries include:
- `processing_time` fields at multiple stages
- `node_timings` breakdown (classify, retrieve, synthesize, validate)
- `total_time` for end-to-end tracking

### 3. Caching Mechanisms & Control

#### Cache Architecture

Project Athena uses **Redis** (running at `redis://192.168.10.181:6379/0`) with three caching layers:

**Layer 1: RAG Service Base Caching** (`src/rag/base_rag_service.py:108-142`)

```python
# Cache key generation (line 108-111)
def _get_cache_key(query, params):
    return hashlib.md5(f"{service_name}:{query}:{json_params}").hexdigest()

# Cache retrieval (line 113-126)
async def _get_cached_response(cache_key):
    cached = await redis_client.get(cache_key)
    if cached:
        logger.debug(f"Cache hit for {service_name}")
        return json.loads(cached)
    return None

# Cache storage (line 128-142)
async def _cache_response(cache_key, response):
    ttl = self.config.get('cache_ttl', 300)  # Default 5 minutes
    await redis_client.setex(cache_key, ttl, json.dumps(response))
```

**Layer 2: Decorator-Based Caching** (`src/shared/cache.py:57-85`)

```python
@cached(ttl=3600, key_prefix="athena")
async def some_function():
    # Result cached for 1 hour
    pass

# Cache key format: {key_prefix}:{func_name}:{args_hash}
```

**Layer 3: Intent Classification Caching** (`src/orchestrator/intent_classifier.py:396-405`)

```python
# Normalized query with stopword filtering
def _generate_cache_key(query, category):
    normalized = re.sub(r'\s+', ' ', query.lower().strip())
    stopwords = ["the", "a", "an", "is", "are", "what", "please", "can", "you"]
    filtered = [w for w in normalized.split() if w not in stopwords]
    return f"{category.value}:{'_'.join(filtered[:5])}"
```

#### Cache TTL Configuration

Configurable per service in PostgreSQL `rag_services` table (default: 300 seconds):

| Service Component | TTL (seconds) | File Location | Rationale |
|-------------------|---------------|---------------|-----------|
| Geocoding (location→coords) | 600 | `weather/main.py:73` | Locations static |
| Current Weather | 300 | `weather/main.py:110` | Updates every 5min |
| Weather Forecast | 600 | `weather/main.py:138` | Stable for 10min |
| Team Search | 3600 | `sports/main.py:78` | Rosters rarely change |
| Team Info | 3600 | `sports/main.py:101` | Static team data |
| Next Events | 600 | `sports/main.py:127` | Schedule changes |
| Last Events | 600 | `sports/main.py:150` | Final scores |
| Airport Search | 3600 | `airports/main.py:77` | Directory stable |
| Airport Info | 3600 | `airports/main.py:101` | Details static |
| Flight Info | 300 | `airports/main.py:125` | Real-time updates |
| Intent Classification | Variable | Per category in DB | Domain-specific |

#### Disabling Cache for Testing

**Method 1: Temporary Redis Instance** (Recommended)
```bash
# Start clean Redis on different port (no persistence)
docker run --rm -p 6380:6379 redis:latest

# Point services to temporary Redis
export REDIS_URL="redis://localhost:6380/0"

# Flush between test runs
redis-cli -p 6380 FLUSHDB
```

**Method 2: Database Configuration**
```sql
-- Disable caching for specific service
UPDATE rag_services
SET cache_ttl = 0
WHERE name = 'weather';

-- Or set to 1 second (effectively disabled)
UPDATE rag_services
SET cache_ttl = 1
WHERE name IN ('weather', 'sports', 'airports');
```

**Method 3: Direct Redis Flush**
```python
from shared.cache import CacheClient

cache = CacheClient()
await cache.client.flushdb()  # Clear all cached data
await cache.close()
```

**Method 4: Per-Test Flush via Environment**
```bash
# Before running benchmark
redis-cli -h 192.168.10.181 FLUSHDB

# Run test suite
python run_benchmark.py

# After optimization
redis-cli -h 192.168.10.181 FLUSHDB

# Run test suite again
python run_benchmark.py
```

#### Cache Graceful Degradation

System **continues to function** if Redis fails (`base_rag_service.py:113-142`):

```python
async def _get_cached_response(cache_key):
    if not self.redis_client:
        return None  # Skip cache, proceed to API

    try:
        cached = await self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.error(f"Cache error: {e}")

    return None  # Fallback to API call
```

### 4. Test Datasets & Example Queries

Project Athena contains **20+ test queries** across multiple categories:

#### Control Commands (7 queries)

From `tests/integration/test_orchestrator_gateway.py` and `src/jetson/athena_lite_llm.py`:

```python
test_queries = [
    "Turn on the office lights",        # Basic control
    "Turn off bedroom lights",          # Basic off
    "Set brightness to 50%",            # Parameter control
    "Set the mood for dinner",          # Scene/complex
    "What time is it?",                 # Simple query
    "Help me turn off all lights",      # Natural language
    "Goodnight routine"                 # Scene automation
]
```

**Performance Target**: ≤3.5 seconds (`tests/integration/test_orchestrator_gateway.py:115-120`)

#### Weather Queries (3 queries)

From `tests/integration/test_orchestrator_gateway.py` and `research/jetson-iterations/test_universal_data.py`:

```python
weather_queries = [
    "What's the weather in Baltimore?",           # Current weather
    "What's the weather forecast for tomorrow?",  # Forecast
    "Is it going to rain today?"                  # Specific condition
]
```

**RAG Service**: `http://192.168.10.167:8010`
**Cache TTL**: 300s (current), 600s (forecast)

#### Sports Queries (3 queries)

From `src/gateway/test_gateway.py` and `research/jetson-iterations/test_universal_data.py`:

```python
sports_queries = [
    "When is the next Ravens game?",    # Schedule
    "Ravens score",                     # Live score
    "Did the Orioles win?"             # Result
]
```

**RAG Service**: `http://192.168.10.167:8012`
**Cache TTL**: 600s (events), 3600s (team info)

#### Airport/Flight Queries (2 queries)

From `src/gateway/test_gateway.py` and voice test routes:

```python
airport_queries = [
    "Any delays at BWI airport?",      # Status
    "When's the next flight to New York?"  # Schedule
]
```

**RAG Service**: `http://192.168.10.167:8011`
**Cache TTL**: 300s (flight info), 3600s (airport info)

#### Baltimore-Specific Local Queries (5 queries)

From `research/jetson-iterations/test_universal_data.py` and `ollama_baltimore_universal_data.py`:

```python
local_queries = [
    "Baltimore water taxi schedule",            # Transit
    "Best crab cakes near me",                 # Food/restaurant
    "Koco's restaurant hours",                 # Specific business
    "Things to do in Baltimore tonight",       # Events
    "Where to watch The Office streaming"      # Entertainment
]
```

**Data Sources**: DuckDuckGo, local database fallbacks

#### General Knowledge Queries (3 queries)

From `src/gateway/test_gateway.py` and `admin/backend/main.py:570-598`:

```python
general_queries = [
    "What is quantum physics?",    # Not routed to Athena
    "Write a poem about nature",   # Not routed to Athena
    "What is 2+2?"                # Default test query
]
```

**Performance Target**: ≤5.5 seconds for Athena-routed knowledge queries

#### Full Test Suite (20 Queries)

Combined benchmark-ready dataset:

```python
benchmark_queries = [
    # Control (7) - Target: ≤3.5s
    "Turn on the office lights",
    "Turn off bedroom lights",
    "Set brightness to 50%",
    "Set the mood for dinner",
    "What time is it?",
    "Help me turn off all lights",
    "Goodnight routine",

    # Weather (3) - Target: ≤5.5s
    "What's the weather in Baltimore?",
    "What's the weather forecast for tomorrow?",
    "Is it going to rain today?",

    # Sports (3) - Target: ≤5.5s
    "When is the next Ravens game?",
    "Ravens score",
    "Did the Orioles win?",

    # Airports (2) - Target: ≤5.5s
    "Any delays at BWI airport?",
    "When's the next flight to New York?",

    # Local (5) - Target: ≤5.5s
    "Baltimore water taxi schedule",
    "Best crab cakes near me",
    "Koco's restaurant hours",
    "Things to do in Baltimore tonight",
    "Where to watch The Office streaming"
]
```

### 5. Optimization Opportunities Documented in Codebase

Historical research documents provide optimization context:

**Performance Benchmarking Analysis** (`thoughts/shared/research/`):
- `2025-11-08-v6-benchmark-analysis-speed-wins.md`: V6 classifier performance improvements
- `2025-11-08-v7-benchmark-analysis-no-improvement.md`: V7 evaluation (no gains)
- `2025-01-08-pattern-matching-ceiling-analysis.md`: Pattern matching performance limits
- `2025-01-08-marathon-final-status-report.md`: Marathon testing results

**Caching Strategy Documents** (`thoughts/shared/plans/`):
- `2025-11-14-search-caching-implementation.md`: Redis search caching (900s default TTL)
- `2025-11-09-multi-intent-handling.md`: Multi-intent caching strategy

**Latency Reduction Strategies** (`thoughts/shared/research/`):
- `2025-11-13-jetson-intent-classification-analysis.md`: Zero-latency responses for common queries
- `2025-11-13-jetson-rag-handler-exploration.md`: Performance timing instrumentation

**Quality & Monitoring** (`thoughts/shared/plans/`):
- `2025-11-11-guest-mode-and-quality-tracking.md`: Quality tracking with vector DB
- `2025-01-08-post-marathon-guest-experience-validation.md`: Validation testing procedures

## Proposed Benchmarking Workflow

Based on existing infrastructure, here's how to run 20-query benchmarks with fair before/after comparison:

### Step 1: Prepare Test Environment

```bash
# 1. Ensure all services are running
cd /Users/jaystuart/dev/project-athena
./scripts/verify_day1.sh  # Validates Mac Studio, Mac mini, services

# 2. Set up isolated Redis for testing (prevents cache contamination)
docker run --name athena-test-redis -d -p 6380:6379 redis:latest

# 3. Point services to test Redis
export REDIS_URL="redis://localhost:6380/0"

# 4. Restart orchestrator with new Redis
ssh jstuart@192.168.10.167 'bash ~/start_orchestrator.sh'
```

### Step 2: Create Benchmark Script

```python
# benchmark_runner.py
import asyncio
import httpx
import time
import json
from typing import List, Dict

BENCHMARK_QUERIES = [
    # Control (7) - Target: ≤3.5s
    {"query": "Turn on the office lights", "category": "control", "target_ms": 3500},
    {"query": "Turn off bedroom lights", "category": "control", "target_ms": 3500},
    {"query": "Set brightness to 50%", "category": "control", "target_ms": 3500},
    {"query": "Set the mood for dinner", "category": "control", "target_ms": 3500},
    {"query": "What time is it?", "category": "control", "target_ms": 3500},
    {"query": "Help me turn off all lights", "category": "control", "target_ms": 3500},
    {"query": "Goodnight routine", "category": "control", "target_ms": 3500},

    # Weather (3) - Target: ≤5.5s
    {"query": "What's the weather in Baltimore?", "category": "weather", "target_ms": 5500},
    {"query": "What's the weather forecast for tomorrow?", "category": "weather", "target_ms": 5500},
    {"query": "Is it going to rain today?", "category": "weather", "target_ms": 5500},

    # Sports (3) - Target: ≤5.5s
    {"query": "When is the next Ravens game?", "category": "sports", "target_ms": 5500},
    {"query": "Ravens score", "category": "sports", "target_ms": 5500},
    {"query": "Did the Orioles win?", "category": "sports", "target_ms": 5500},

    # Airports (2) - Target: ≤5.5s
    {"query": "Any delays at BWI airport?", "category": "airports", "target_ms": 5500},
    {"query": "When's the next flight to New York?", "category": "airports", "target_ms": 5500},

    # Local (5) - Target: ≤5.5s
    {"query": "Baltimore water taxi schedule", "category": "local", "target_ms": 5500},
    {"query": "Best crab cakes near me", "category": "local", "target_ms": 5500},
    {"query": "Koco's restaurant hours", "category": "local", "target_ms": 5500},
    {"query": "Things to do in Baltimore tonight", "category": "local", "target_ms": 5500},
    {"query": "Where to watch The Office streaming", "category": "local", "target_ms": 5500},
]

async def run_single_query(client: httpx.AsyncClient, query_data: Dict) -> Dict:
    """Run single query and collect metrics."""
    query = query_data["query"]
    start_time = time.time()

    try:
        response = await client.post(
            "http://192.168.10.167:8001/query",
            json={
                "query": query,
                "user_id": "benchmark",
                "conversation_id": f"bench_{int(start_time)}"
            },
            timeout=30.0
        )

        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            return {
                "query": query,
                "category": query_data["category"],
                "target_ms": query_data["target_ms"],
                "actual_ms": elapsed_ms,
                "met_target": elapsed_ms <= query_data["target_ms"],
                "intent": data.get("intent"),
                "data_source": data.get("metadata", {}).get("data_source"),
                "node_timings": data.get("metadata", {}).get("node_timings", {}),
                "success": True,
                "error": None
            }
        else:
            return {
                "query": query,
                "category": query_data["category"],
                "actual_ms": elapsed_ms,
                "success": False,
                "error": f"HTTP {response.status_code}"
            }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return {
            "query": query,
            "category": query_data["category"],
            "actual_ms": elapsed_ms,
            "success": False,
            "error": str(e)
        }

async def run_benchmark(output_file: str = "benchmark_results.json"):
    """Run full benchmark suite."""
    print(f"Starting benchmark with {len(BENCHMARK_QUERIES)} queries...")

    async with httpx.AsyncClient() as client:
        results = []

        for i, query_data in enumerate(BENCHMARK_QUERIES, 1):
            print(f"\n[{i}/{len(BENCHMARK_QUERIES)}] Testing: {query_data['query']}")
            result = await run_single_query(client, query_data)
            results.append(result)

            status = "✓" if result.get("met_target", False) else "✗"
            print(f"  {status} {result['actual_ms']:.0f}ms (target: {query_data['target_ms']}ms)")

            # Brief pause between queries
            await asyncio.sleep(0.5)

    # Calculate summary statistics
    successful = [r for r in results if r["success"]]
    control_queries = [r for r in successful if r["category"] == "control"]
    knowledge_queries = [r for r in successful if r["category"] != "control"]

    summary = {
        "total_queries": len(BENCHMARK_QUERIES),
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "avg_response_time_ms": sum(r["actual_ms"] for r in successful) / len(successful) if successful else 0,
        "control_avg_ms": sum(r["actual_ms"] for r in control_queries) / len(control_queries) if control_queries else 0,
        "knowledge_avg_ms": sum(r["actual_ms"] for r in knowledge_queries) / len(knowledge_queries) if knowledge_queries else 0,
        "targets_met": sum(1 for r in successful if r.get("met_target", False)),
        "targets_missed": sum(1 for r in successful if not r.get("met_target", True))
    }

    output = {
        "timestamp": time.time(),
        "summary": summary,
        "results": results
    }

    # Save results
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"Total Queries:     {summary['total_queries']}")
    print(f"Successful:        {summary['successful']}")
    print(f"Failed:            {summary['failed']}")
    print(f"Targets Met:       {summary['targets_met']}")
    print(f"Targets Missed:    {summary['targets_missed']}")
    print(f"\nAvg Response Time: {summary['avg_response_time_ms']:.0f}ms")
    print(f"  Control Avg:     {summary['control_avg_ms']:.0f}ms (target: ≤3500ms)")
    print(f"  Knowledge Avg:   {summary['knowledge_avg_ms']:.0f}ms (target: ≤5500ms)")
    print(f"\nResults saved to: {output_file}")

    return output

if __name__ == "__main__":
    asyncio.run(run_benchmark())
```

### Step 3: Run Baseline Benchmark

```bash
# 1. Flush cache to ensure clean baseline
redis-cli -h localhost -p 6380 FLUSHDB

# 2. Run benchmark
python benchmark_runner.py

# Output: benchmark_results.json with baseline metrics
```

### Step 4: Implement Optimizations

Example optimization targets:
- Reduce RAG service TTL for faster updates
- Enable parallel search for multi-source queries
- Optimize intent classification patterns
- Add query result caching with longer TTL
- Improve LLM prompt templates for faster generation

### Step 5: Run Post-Optimization Benchmark

```bash
# 1. Flush cache again to ensure fair comparison
redis-cli -h localhost -p 6380 FLUSHDB

# 2. Run same benchmark
python benchmark_runner.py --output benchmark_results_optimized.json
```

### Step 6: Compare Results

```python
# compare_benchmarks.py
import json

def compare_benchmarks(baseline_file: str, optimized_file: str):
    """Compare two benchmark runs."""
    with open(baseline_file) as f:
        baseline = json.load(f)

    with open(optimized_file) as f:
        optimized = json.load(f)

    baseline_summary = baseline["summary"]
    optimized_summary = optimized["summary"]

    print("BENCHMARK COMPARISON")
    print("="*60)

    # Overall improvement
    baseline_avg = baseline_summary["avg_response_time_ms"]
    optimized_avg = optimized_summary["avg_response_time_ms"]
    improvement_pct = ((baseline_avg - optimized_avg) / baseline_avg) * 100

    print(f"\nOverall Performance:")
    print(f"  Baseline:   {baseline_avg:.0f}ms")
    print(f"  Optimized:  {optimized_avg:.0f}ms")
    print(f"  Change:     {improvement_pct:+.1f}%")

    # Control queries
    baseline_control = baseline_summary["control_avg_ms"]
    optimized_control = optimized_summary["control_avg_ms"]
    control_improvement = ((baseline_control - optimized_control) / baseline_control) * 100

    print(f"\nControl Queries (target: ≤3500ms):")
    print(f"  Baseline:   {baseline_control:.0f}ms")
    print(f"  Optimized:  {optimized_control:.0f}ms")
    print(f"  Change:     {control_improvement:+.1f}%")

    # Knowledge queries
    baseline_knowledge = baseline_summary["knowledge_avg_ms"]
    optimized_knowledge = optimized_summary["knowledge_avg_ms"]
    knowledge_improvement = ((baseline_knowledge - optimized_knowledge) / baseline_knowledge) * 100

    print(f"\nKnowledge Queries (target: ≤5500ms):")
    print(f"  Baseline:   {baseline_knowledge:.0f}ms")
    print(f"  Optimized:  {optimized_knowledge:.0f}ms")
    print(f"  Change:     {knowledge_improvement:+.1f}%")

    # Targets met
    print(f"\nTargets Met:")
    print(f"  Baseline:   {baseline_summary['targets_met']}/{baseline_summary['total_queries']}")
    print(f"  Optimized:  {optimized_summary['targets_met']}/{optimized_summary['total_queries']}")

    # Per-query comparison
    print(f"\nPer-Query Analysis:")
    print(f"{'Query':<40} {'Baseline':>10} {'Optimized':>10} {'Change':>10}")
    print("-"*75)

    for baseline_result, optimized_result in zip(baseline["results"], optimized["results"]):
        query = baseline_result["query"][:37] + "..." if len(baseline_result["query"]) > 40 else baseline_result["query"]
        baseline_ms = baseline_result["actual_ms"]
        optimized_ms = optimized_result["actual_ms"]
        change = ((baseline_ms - optimized_ms) / baseline_ms) * 100 if baseline_ms > 0 else 0

        print(f"{query:<40} {baseline_ms:>8.0f}ms {optimized_ms:>8.0f}ms {change:>+8.1f}%")

if __name__ == "__main__":
    compare_benchmarks("benchmark_results.json", "benchmark_results_optimized.json")
```

## Code References

### Testing Infrastructure
- `tests/integration/test_orchestrator_gateway.py:1-160` - Integration tests with latency requirements
- `src/gateway/test_gateway.py:1-42` - Gateway query detection tests
- `admin/backend/app/routes/voice_tests.py:1-277` - Voice testing API endpoints
- `scripts/test_basic_setup.py:1-92` - Setup validation
- `scripts/verify_day1.sh` - Day 1 verification script
- `scripts/init_qdrant.py:89-131` - Qdrant vector DB testing

### Metrics Collection
- `src/gateway/main.py:412` - Gateway Prometheus metrics endpoint
- `src/orchestrator/main.py:49-58,920` - Orchestrator metrics (counters, histograms)
- `admin/backend/app/models.py:427-445` - RAGStats table definition
- `admin/backend/app/models.py:453-472` - VoiceTest table definition
- `admin/backend/app/routes/rag_connectors.py:458-532` - RAG statistics API
- `src/shared/logging_config.py` - Structured logging configuration

### Caching
- `src/shared/cache.py:10-85` - CacheClient and @cached decorator
- `src/rag/base_rag_service.py:108-142` - RAG service caching methods
- `src/orchestrator/intent_classifier.py:396-405` - Intent classification cache keys
- `src/rag/weather/main.py:73,110,138` - Weather service caching decorators
- `src/rag/sports/main.py:78,101,127,150` - Sports service caching decorators
- `src/rag/airports/main.py:77,101,125` - Airports service caching decorators

### Test Queries
- `tests/integration/test_orchestrator_gateway.py:26-160` - Integration test queries
- `src/gateway/test_gateway.py:21-42` - Gateway detection test cases
- `research/jetson-iterations/test_universal_data.py:9-151` - Universal data tests
- `admin/backend/main.py:570-598` - Admin test query endpoint
- `src/jetson/athena_lite_llm.py:190-220` - Intelligent command tests

## Historical Context (from thoughts/)

- `thoughts/shared/research/2025-11-08-v6-benchmark-analysis-speed-wins.md` - V6 classifier performance analysis showing speed improvements
- `thoughts/shared/research/2025-11-08-v7-benchmark-analysis-no-improvement.md` - V7 evaluation indicating no gains over V6
- `thoughts/shared/plans/2025-11-14-search-caching-implementation.md` - Redis search caching strategy (900s TTL)
- `thoughts/shared/plans/2025-11-09-multi-intent-handling.md` - Multi-intent caching with domain-specific TTLs
- `thoughts/shared/research/2025-11-13-jetson-intent-classification-analysis.md` - Latency reduction via zero-latency responses
- `thoughts/shared/plans/2025-11-11-guest-mode-and-quality-tracking.md` - Quality tracking and cache TTL optimization recommendations

## Related Research

- Intent-based search routing: `thoughts/shared/plans/2025-11-14-intent-based-search-routing.md`
- Parallel search implementation: `thoughts/shared/plans/2025-11-14-parallel-search-implementation.md`
- Anti-hallucination validation: `thoughts/shared/plans/2025-11-14-anti-hallucination-implementation.md`

## Conclusion

Project Athena has a **production-ready benchmarking infrastructure** with:

1. **20+ test queries** spanning all major use cases
2. **Multi-layer metrics collection** (Prometheus + PostgreSQL + structured logs)
3. **Controllable caching** via Redis with configurable TTL and flush capabilities
4. **Clear performance targets** (3.5s control, 5.5s knowledge)
5. **Comprehensive testing layers** (integration, unit, voice, infrastructure)

The system supports **systematic before/after optimization comparison** by:
- Using isolated Redis instance to prevent cache contamination
- Flushing cache between runs for fair comparison
- Collecting detailed timing data (per-node execution, total time)
- Storing results in structured format for analysis

**Recommended next step**: Implement the `benchmark_runner.py` script to establish baseline metrics, then iteratively optimize and re-test to measure improvements.
