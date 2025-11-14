# Implementation Plan: Benchmarking System + Performance Optimizations

**Created:** 2025-11-14
**Author:** Claude Code
**Status:** Ready for Implementation
**Related Research:** [2025-11-14-benchmarking-optimization-framework.md](../research/2025-11-14-benchmarking-optimization-framework.md)

## Overview

This plan implements a comprehensive benchmarking and optimization cycle for Project Athena:
1. **Build benchmarking infrastructure** to run 20 standardized test queries with cache control
2. **Run baseline benchmark** to establish current performance metrics
3. **Implement high-impact optimizations** targeting 30-50% latency reduction
4. **Run post-optimization benchmark** to measure improvements
5. **Compare results** with statistical analysis

**Expected Outcome:** Measurable 30-50% improvement in average response time across all query types.

## Current State Analysis

### Existing Infrastructure

**Testing:**
- Integration tests with latency requirements (≤3.5s control, ≤5.5s knowledge)
- 20+ test queries across 5 categories
- Prometheus metrics at gateway and orchestrator levels
- State-based timing in `node_timings` dictionary

**Caching:**
- Redis at 192.168.10.181:6379 (production)
- 3 cache layers (RAG services, decorator-based, intent classification)
- Configurable TTL (1-3600 seconds)
- No cache flushing utilities

**Performance:**
- Control queries: ~2-3s typical
- Knowledge queries: ~3-5s typical
- No systematic benchmark runner
- No before/after comparison tools

### Performance Bottlenecks Identified

**Critical Bottlenecks (Research Analysis):**

1. **Intent Classification** (`main.py:192-263`):
   - Every query calls LLM (500-1500ms)
   - No caching of classification results
   - Pattern-based classifier exists but unused
   - **Impact:** 500-1500ms per query

2. **LLM Synthesis** (`main.py:477-548`):
   - Blocks on full LLM response generation (1000-5000ms)
   - No response caching for identical contexts
   - Streaming disabled (`stream=False`)
   - **Impact:** 1000-5000ms per query (largest bottleneck)

3. **Validation Node** (`main.py:550-676`):
   - Optional LLM fact-checking adds 500-1500ms
   - Runs even for high-confidence queries
   - Bug: Uses undefined `ModelTier.FAST` (line 627)
   - **Impact:** 500-1500ms when activated

4. **Redis Connection Pooling** (`cache.py:66-85`):
   - Creates new connection per cache operation
   - Immediately closes connection after use
   - **Impact:** 10-50ms overhead per cache hit (reduces cache benefit by 200%)

5. **HTTP Client Creation** (All RAG services):
   - New `httpx.AsyncClient()` per API call
   - No connection reuse across requests
   - No timeouts specified (can hang indefinitely)
   - **Impact:** 20-100ms per API call

6. **Parallel Search Duplicate Intent Classification** (`parallel_search.py:73`):
   - Classifies intent again (already done in classify_node)
   - **Impact:** 50-100ms wasted

## Desired End State

After implementation:

**Benchmarking System:**
- Run `python3 scripts/benchmark_runner.py --baseline` → baseline.json
- Make optimizations
- Run `python3 scripts/benchmark_runner.py --optimized` → optimized.json
- Run `python3 scripts/compare_benchmarks.py baseline.json optimized.json`
- See clear before/after improvements with statistical significance

**Performance Improvements:**
- Control queries: 2-3s → 1-2s (30-50% improvement)
- Knowledge queries: 3-5s → 2-3.5s (30-40% improvement)
- Cache hit latency: 15-65ms → 5-15ms (70-80% improvement)
- Intent classification: 500-1500ms → 1-50ms for common queries (95%+ improvement)

**System Capabilities:**
- Repeatable benchmark execution
- Clean testing environment (isolated Redis)
- Cache control between runs
- Comprehensive metrics collection
- Statistical comparison tools

## What We're NOT Doing

**Out of Scope:**
- ❌ Real-time monitoring dashboard (use Prometheus/Grafana)
- ❌ Automated optimization suggestions
- ❌ Load testing with concurrent users
- ❌ Voice pipeline benchmarking (text queries only)
- ❌ Streaming synthesis implementation (deferred)
- ❌ Circuit breaker pattern for RAG services (deferred)
- ❌ Background query preloading (deferred)

## Implementation Phases

---

## Phase 1: Build Benchmark Infrastructure

**Goal:** Create tools to run 20 queries and measure performance.

### Tasks:

#### 1. Create benchmark_runner.py

**File:** `scripts/benchmark_runner.py` (new file, ~250 lines)

**Implementation:**

```python
#!/usr/bin/env python3
"""
Benchmark runner for Project Athena orchestrator.

Runs 20 standardized queries and collects detailed performance metrics.
"""
import asyncio
import httpx
import time
import json
import redis
import argparse
import hashlib
from typing import List, Dict
from pathlib import Path

# Orchestrator and Redis configuration
ORCHESTRATOR_URL = "http://192.168.10.167:8001"
REDIS_TEST_URL = "redis://192.168.10.181:6380/0"  # Isolated test instance

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


def flush_redis_cache():
    """Flush test Redis database to ensure clean benchmark."""
    try:
        r = redis.from_url(REDIS_TEST_URL)
        r.flushdb()
        print("✓ Redis cache flushed")
    except Exception as e:
        print(f"⚠ Warning: Could not flush Redis: {e}")


async def run_single_query(client: httpx.AsyncClient, query_data: Dict, run_number: int) -> Dict:
    """Run single query and collect comprehensive metrics."""
    query = query_data["query"]
    start_time = time.time()

    try:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/query",
            json={
                "query": query,
                "user_id": "benchmark",
                "conversation_id": f"bench_{run_number}_{int(start_time)}"
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
                "confidence": data.get("confidence"),
                "data_source": data.get("metadata", {}).get("data_source"),
                "node_timings": data.get("metadata", {}).get("node_timings", {}),
                "success": True,
                "error": None
            }
        else:
            return {
                "query": query,
                "category": query_data["category"],
                "target_ms": query_data["target_ms"],
                "actual_ms": elapsed_ms,
                "met_target": False,
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return {
            "query": query,
            "category": query_data["category"],
            "target_ms": query_data["target_ms"],
            "actual_ms": elapsed_ms,
            "met_target": False,
            "success": False,
            "error": str(e)
        }


async def run_benchmark(output_file: str, flush_cache: bool = True):
    """Run complete benchmark suite."""
    print(f"\n{'='*70}")
    print(f"  PROJECT ATHENA BENCHMARK")
    print(f"{'='*70}\n")
    print(f"Queries:     {len(BENCHMARK_QUERIES)}")
    print(f"Output:      {output_file}")
    print(f"Flush cache: {flush_cache}")
    print(f"Target URL:  {ORCHESTRATOR_URL}\n")

    # Flush Redis if requested
    if flush_cache:
        flush_redis_cache()

    print(f"{'='*70}\n")

    async with httpx.AsyncClient() as client:
        results = []

        for i, query_data in enumerate(BENCHMARK_QUERIES, 1):
            print(f"[{i:2d}/{len(BENCHMARK_QUERIES)}] {query_data['query']:<45}", end=" ", flush=True)

            # Flush cache before each query if requested
            if flush_cache:
                flush_redis_cache()

            result = await run_single_query(client, query_data, i)
            results.append(result)

            # Print result
            if result["success"]:
                status = "✓" if result["met_target"] else "✗"
                print(f"{status} {result['actual_ms']:6.0f}ms")
            else:
                print(f"✗ FAILED: {result['error'][:30]}")

            # Brief pause between queries
            await asyncio.sleep(0.5)

    # Calculate summary statistics
    successful = [r for r in results if r["success"]]
    control_queries = [r for r in successful if r["category"] == "control"]
    knowledge_queries = [r for r in successful if r["category"] != "control"]

    # Per-category averages
    categories = {}
    for r in successful:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r["actual_ms"])

    category_avgs = {cat: sum(times)/len(times) for cat, times in categories.items()}

    summary = {
        "total_queries": len(BENCHMARK_QUERIES),
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "targets_met": sum(1 for r in successful if r.get("met_target", False)),
        "targets_missed": sum(1 for r in successful if not r.get("met_target", True)),
        "avg_response_time_ms": sum(r["actual_ms"] for r in successful) / len(successful) if successful else 0,
        "control_avg_ms": sum(r["actual_ms"] for r in control_queries) / len(control_queries) if control_queries else 0,
        "knowledge_avg_ms": sum(r["actual_ms"] for r in knowledge_queries) / len(knowledge_queries) if knowledge_queries else 0,
        "category_averages": category_avgs
    }

    output = {
        "timestamp": time.time(),
        "orchestrator_url": ORCHESTRATOR_URL,
        "cache_flushed": flush_cache,
        "summary": summary,
        "results": results
    }

    # Ensure output directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Save results
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}")
    print(f"Total Queries:     {summary['total_queries']}")
    print(f"Successful:        {summary['successful']}")
    print(f"Failed:            {summary['failed']}")
    print(f"Targets Met:       {summary['targets_met']}/{summary['successful']}")
    print(f"Targets Missed:    {summary['targets_missed']}/{summary['successful']}")
    print(f"\nAvg Response Time: {summary['avg_response_time_ms']:.0f}ms")
    print(f"  Control Avg:     {summary['control_avg_ms']:.0f}ms (target: ≤3500ms)")
    print(f"  Knowledge Avg:   {summary['knowledge_avg_ms']:.0f}ms (target: ≤5500ms)")
    print(f"\nCategory Breakdown:")
    for cat, avg in category_avgs.items():
        print(f"  {cat:12s}: {avg:6.0f}ms")
    print(f"\nResults saved to: {output_file}")
    print(f"{'='*70}\n")

    return output


def main():
    parser = argparse.ArgumentParser(description="Run Project Athena benchmark")
    parser.add_argument("--output", default="results/baseline.json", help="Output file path")
    parser.add_argument("--no-flush", action="store_true", help="Don't flush cache between queries")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.output, flush_cache=not args.no_flush))


if __name__ == "__main__":
    main()
```

#### 2. Create setup script for test Redis

**File:** `scripts/setup_benchmark_redis.sh` (new file)

```bash
#!/bin/bash
# Setup isolated Redis instance for benchmarking

CONTAINER_NAME="athena-benchmark-redis"
PORT=6380

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container ${CONTAINER_NAME} already exists"

    # Check if it's running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "✓ ${CONTAINER_NAME} is already running on port ${PORT}"
    else
        echo "Starting existing container..."
        docker start ${CONTAINER_NAME}
        echo "✓ ${CONTAINER_NAME} started on port ${PORT}"
    fi
else
    echo "Creating new Redis container for benchmarking..."
    docker run -d \
        --name ${CONTAINER_NAME} \
        -p ${PORT}:6379 \
        redis:7-alpine

    echo "✓ ${CONTAINER_NAME} created and running on port ${PORT}"
fi

# Test connectivity
echo ""
echo "Testing Redis connectivity..."
if redis-cli -h localhost -p ${PORT} PING > /dev/null 2>&1; then
    echo "✓ Redis is responding on port ${PORT}"
    echo ""
    echo "Test Redis URL: redis://192.168.10.181:${PORT}/0"
    echo "Ready for benchmarking!"
else
    echo "✗ Redis not responding on port ${PORT}"
    exit 1
fi
```

#### 3. Create results directory structure

**Files:**
- `results/.gitignore` (new file):
  ```
  *.json
  !.gitkeep
  ```
- `results/.gitkeep` (new file, empty)
- `results/README.md` (new file):
  ```markdown
  # Benchmark Results

  This directory stores benchmark results from performance testing runs.

  ## Naming Convention

  - `baseline-YYYY-MM-DD.json` - Baseline benchmarks before optimization
  - `optimized-YYYY-MM-DD.json` - Post-optimization benchmarks
  - Keep historical results for trend analysis

  ## File Format

  Each JSON file contains:
  - `timestamp` - Unix timestamp of benchmark run
  - `summary` - Aggregate statistics
  - `results` - Individual query results with timing data
  ```

### Success Criteria:

#### Automated Verification:
- [ ] `scripts/benchmark_runner.py` executes without errors
- [ ] All 20 queries complete (may have failures, but script continues)
- [ ] JSON output file created with valid structure
- [ ] Test Redis container starts successfully: `docker ps | grep athena-benchmark-redis`
- [ ] Redis flush works: `redis-cli -p 6380 DBSIZE` returns 0

#### Manual Verification:
- [ ] Review JSON output structure - has `summary` and `results` keys
- [ ] Verify timing values are reasonable (no 0ms or negative values)
- [ ] Check that queries execute in expected order
- [ ] Confirm progress output is readable and helpful
- [ ] Verify test Redis is isolated (production port 6379 untouched)

**Implementation Note:** Make scripts executable after creation: `chmod +x scripts/*.sh scripts/*.py`

---

## Phase 2: Run Baseline Benchmark

**Goal:** Establish current performance baseline before optimizations.

### Tasks:

#### 1. Set up test environment

```bash
# Start test Redis instance
./scripts/setup_benchmark_redis.sh

# Verify orchestrator is running
curl http://192.168.10.167:8001/health

# Point services to test Redis (optional - for full isolation)
# export REDIS_URL="redis://192.168.10.181:6380/0"
```

#### 2. Run baseline benchmark

```bash
# Run with cache flushing (clean baseline)
python3 scripts/benchmark_runner.py --output results/baseline-$(date +%Y-%m-%d).json

# Outputs: results/baseline-2025-11-14.json
```

#### 3. Review baseline results

```bash
# View summary
cat results/baseline-2025-11-14.json | jq '.summary'

# Expected output example:
# {
#   "total_queries": 20,
#   "successful": 20,
#   "failed": 0,
#   "targets_met": 15,
#   "targets_missed": 5,
#   "avg_response_time_ms": 3250,
#   "control_avg_ms": 2400,
#   "knowledge_avg_ms": 3850
# }
```

### Success Criteria:

#### Automated Verification:
- [ ] Benchmark completes without Python errors
- [ ] At least 18/20 queries succeed (90% success rate)
- [ ] JSON file created and parseable
- [ ] All 20 results have `actual_ms` field populated

#### Manual Verification:
- [ ] Review full benchmark output - looks reasonable
- [ ] Check for any unexpected errors in failed queries
- [ ] Verify average times align with expectations (~2-5s range)
- [ ] Confirm cache was flushed (first query of each type slower)
- [ ] Save baseline results for later comparison

**Implementation Note:** Keep this baseline file - it's your reference point for measuring optimization improvements!

---

## Phase 3: Implement High-Impact Optimizations

**Goal:** Implement optimizations with 30-50% latency reduction potential.

### Optimization 1: Add Intent Classification Caching

**File:** `src/orchestrator/main.py:192-263`

**Change:**

```python
async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """Classify user intent with Redis caching."""
    start = time.time()

    # OPTIMIZATION: Check cache first
    cache_key = f"intent:{hashlib.md5(state.query.lower().encode()).hexdigest()}"

    try:
        cached = await cache_client.get(cache_key)
        if cached:
            state.intent = IntentCategory(cached["intent"])
            state.confidence = cached.get("confidence", 0.9)
            state.entities = cached.get("entities", {})
            state.node_timings["classify"] = time.time() - start
            logger.info(f"Intent cache HIT for '{state.query}': {state.intent}")
            return state
    except Exception as e:
        logger.warning(f"Intent cache lookup failed: {e}")

    # ... existing LLM classification code (lines 201-252) ...

    # OPTIMIZATION: Cache the result (5 minute TTL)
    try:
        await cache_client.set(cache_key, {
            "intent": state.intent.value,
            "confidence": state.confidence,
            "entities": state.entities
        }, ttl=300)
        logger.info(f"Intent classification cached for '{state.query}'")
    except Exception as e:
        logger.warning(f"Intent cache write failed: {e}")

    state.node_timings["classify"] = time.time() - start
    return state
```

**Expected Impact:**
- Cache hit: <1ms (vs 500-1500ms LLM call)
- 95-99% latency reduction for repeated queries
- 30-40% hit rate expected

---

### Optimization 2: Fix Redis Connection Pooling

**File:** `src/shared/cache.py:66-85`

**Change:** Use module-level cache client instead of creating new one per call.

```python
# At module level (after CacheClient class definition)
_global_cache_client: Optional[CacheClient] = None

def get_cache_client() -> CacheClient:
    """Get or create global cache client singleton."""
    global _global_cache_client
    if _global_cache_client is None:
        _global_cache_client = CacheClient()
    return _global_cache_client


def cached(ttl: int = 3600, key_prefix: str = "athena"):
    """Cache decorator with connection reuse."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # OPTIMIZATION: Reuse global cache client
            cache = get_cache_client()

            try:
                cached_result = await cache.get(cache_key)

                if cached_result is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache lookup error: {e}")

            # Cache miss - call function
            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)

            try:
                await cache.set(cache_key, result, ttl)
            except Exception as e:
                logger.warning(f"Cache write error: {e}")

            return result

        return wrapper
    return decorator
```

**Expected Impact:**
- Cache hit latency: 15-65ms → 5-15ms (70-80% improvement)
- Reduced Redis connection churn
- Better Redis resource utilization

---

### Optimization 3: Reuse HTTP Clients in RAG Services

**Files:**
- `src/rag/weather/main.py`
- `src/rag/sports/main.py`
- `src/rag/airports/main.py`

**Pattern (apply to all 3 services):**

**Weather Service Example:**

```python
# At module level, after imports
_http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client singleton."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with proper cleanup."""
    global cache, _http_client
    logger.info("Starting Weather RAG service")

    # Initialize cache
    cache = CacheClient(redis_url=REDIS_URL)
    await cache.connect()

    # Initialize HTTP client
    _http_client = httpx.AsyncClient(timeout=10.0)

    yield

    # Cleanup
    await cache.close()
    if _http_client:
        await _http_client.aclose()
    logger.info("Weather RAG service stopped")


# Update all API call functions
@cached(ttl=600, key_prefix="geocode")
async def geocode_location(location: str) -> Dict:
    """Geocode location to coordinates."""
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": location, "limit": 1, "appid": OPENWEATHER_API_KEY}

    # OPTIMIZATION: Reuse HTTP client
    client = get_http_client()
    response = await client.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    # ... rest of function ...
```

**Locations to update:**
- `weather/main.py`: Lines 93, 132, 162 (3 locations)
- `sports/main.py`: Lines 94, 117, 143, 166 (4 locations)
- `airports/main.py`: Lines 95, 119, 143 (3 locations)

**Expected Impact:**
- 20-100ms saved per API call
- Eliminates connection setup overhead
- Better HTTP keep-alive utilization

---

### Optimization 4: Remove Duplicate Intent Classification in Parallel Search

**File:** `src/orchestrator/search_providers/parallel_search.py:51-79`

**Change:** Pass intent from orchestrator instead of re-classifying.

```python
async def search(
    self,
    query: str,
    intent: Optional[str] = None,  # OPTIMIZATION: Accept intent parameter
    location: Optional[str] = "Baltimore, MD",
    limit_per_provider: int = 5,
    **kwargs
) -> Tuple[str, List[SearchResult]]:
    """
    Execute intent-based parallel search.

    Args:
        query: Search query
        intent: Pre-classified intent (if None, will classify)
        location: Location for search
        limit_per_provider: Max results per provider
    """
    # OPTIMIZATION: Skip classification if intent provided
    if intent is None:
        intent, confidence = self.intent_classifier.classify_with_confidence(query)
        logger.info(f"Classified query intent: '{intent}' (confidence: {confidence:.2f})")
    else:
        logger.info(f"Using provided intent: '{intent}'")

    # ... rest of function unchanged ...
```

**Caller Update** (`main.py:427-431`):

```python
# In retrieve_node function
if state.intent in [IntentCategory.GENERAL, IntentCategory.EVENT_SEARCH, ...]:
    # OPTIMIZATION: Pass already-classified intent
    intent, search_results = await parallel_search_engine.search(
        query=state.query,
        intent=state.intent.value,  # Pass pre-classified intent
        location=state.entities.get("location", "Baltimore, MD")
    )
```

**Expected Impact:**
- 50-100ms saved per search query
- Eliminates redundant LLM call

---

### Optimization 5: Extend Cache TTLs for Stable Data

**Files:** `src/rag/weather/main.py`, `sports/main.py`, `airports/main.py`

**Changes:**

```python
# weather/main.py:73 - Geocoding rarely changes
@cached(ttl=3600, key_prefix="geocode")  # Was 600 → Now 3600 (1 hour)

# sports/main.py:101 - Team info is stable
@cached(ttl=86400, key_prefix="team_info")  # Was 3600 → Now 86400 (24 hours)

# airports/main.py:101 - Airport details never change
@cached(ttl=604800, key_prefix="airport_info")  # Was 3600 → Now 604800 (7 days)
```

**Expected Impact:**
- Higher cache hit rates (40% → 70%+)
- Fewer unnecessary API calls
- Faster responses for common queries

---

### Optimization 6: Fix Validation Node Bug

**File:** `src/orchestrator/main.py:627`

**Change:**

```python
# Line 627: Fix undefined ModelTier.FAST
model_tier=ModelTier.SMALL,  # Was: ModelTier.FAST (doesn't exist)
```

**Expected Impact:**
- Fixes runtime error in validation
- Ensures validation runs with correct model

---

### Success Criteria:

#### Automated Verification:
- [ ] All Python files have valid syntax: `python3 -m py_compile src/**/*.py`
- [ ] No undefined variables: `python3 -m pylint src/orchestrator/main.py`
- [ ] Services start without errors: Check orchestrator logs
- [ ] Redis cache client singleton works: Query test should show cache hits

#### Manual Verification:
- [ ] Run 2-3 test queries manually - confirm faster response
- [ ] Check Redis with `redis-cli KEYS '*'` - see cached intents
- [ ] Verify HTTP client reuse: Check connection pooling in logs
- [ ] Confirm no duplicate intent classifications in logs
- [ ] Test validation node: Verify no `ModelTier.FAST` errors

**Implementation Note:** Test each optimization individually before combining. If an optimization causes issues, it can be reverted without affecting others.

---

## Phase 4: Run Optimized Benchmark + Compare

**Goal:** Measure improvements and validate optimizations.

### Tasks:

#### 1. Run optimized benchmark

```bash
# Restart orchestrator to load optimized code
ssh jstuart@192.168.10.167 'pkill -9 python3 && cd ~/dev/project-athena && bash /tmp/start_orchestrator.sh'

# Wait for orchestrator to be ready
sleep 10

# Run optimized benchmark (flush cache for fair comparison)
python3 scripts/benchmark_runner.py --output results/optimized-$(date +%Y-%m-%d).json
```

#### 2. Create comparison script

**File:** `scripts/compare_benchmarks.py` (new file, ~200 lines)

```python
#!/usr/bin/env python3
"""
Compare two benchmark runs and show improvements.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List

def load_benchmark(filepath: str) -> Dict:
    """Load benchmark JSON file."""
    with open(filepath) as f:
        return json.load(f)

def calculate_percentiles(values: List[float], percentiles: List[int]) -> Dict[int, float]:
    """Calculate percentile values."""
    sorted_values = sorted(values)
    n = len(sorted_values)

    result = {}
    for p in percentiles:
        index = int((p / 100.0) * (n - 1))
        result[p] = sorted_values[index]

    return result

def compare_benchmarks(baseline_file: str, optimized_file: str):
    """Compare two benchmark runs and show detailed analysis."""
    baseline = load_benchmark(baseline_file)
    optimized = load_benchmark(optimized_file)

    print("\n" + "="*80)
    print("  BENCHMARK COMPARISON REPORT".center(80))
    print("="*80 + "\n")

    # Overall summary
    baseline_summary = baseline["summary"]
    optimized_summary = optimized["summary"]

    print("Files:")
    print(f"  Baseline:  {baseline_file}")
    print(f"  Optimized: {optimized_file}")
    print()

    # Overall performance
    baseline_avg = baseline_summary["avg_response_time_ms"]
    optimized_avg = optimized_summary["avg_response_time_ms"]
    improvement = ((baseline_avg - optimized_avg) / baseline_avg) * 100

    print("Overall Performance:")
    print(f"  Baseline:   {baseline_avg:6.0f}ms")
    print(f"  Optimized:  {optimized_avg:6.0f}ms")
    print(f"  Change:     {improvement:+6.1f}%")
    print()

    # Control queries
    baseline_control = baseline_summary["control_avg_ms"]
    optimized_control = optimized_summary["control_avg_ms"]
    control_improvement = ((baseline_control - optimized_control) / baseline_control) * 100

    print("Control Queries (target: ≤3500ms):")
    print(f"  Baseline:   {baseline_control:6.0f}ms")
    print(f"  Optimized:  {optimized_control:6.0f}ms")
    print(f"  Change:     {control_improvement:+6.1f}%")
    print()

    # Knowledge queries
    baseline_knowledge = baseline_summary["knowledge_avg_ms"]
    optimized_knowledge = optimized_summary["knowledge_avg_ms"]
    knowledge_improvement = ((baseline_knowledge - optimized_knowledge) / baseline_knowledge) * 100

    print("Knowledge Queries (target: ≤5500ms):")
    print(f"  Baseline:   {baseline_knowledge:6.0f}ms")
    print(f"  Optimized:  {optimized_knowledge:6.0f}ms")
    print(f"  Change:     {knowledge_improvement:+6.1f}%")
    print()

    # Category breakdown
    print("Category Analysis:")
    print(f"{'Category':<15} {'Baseline':>10} {'Optimized':>10} {'Change':>10}")
    print("-" * 50)

    baseline_cats = baseline_summary.get("category_averages", {})
    optimized_cats = optimized_summary.get("category_averages", {})

    for cat in sorted(set(baseline_cats.keys()) | set(optimized_cats.keys())):
        base_val = baseline_cats.get(cat, 0)
        opt_val = optimized_cats.get(cat, 0)
        if base_val > 0:
            change = ((base_val - opt_val) / base_val) * 100
            print(f"{cat:<15} {base_val:8.0f}ms {opt_val:8.0f}ms {change:+8.1f}%")
    print()

    # Targets met
    print("Targets Met:")
    print(f"  Baseline:   {baseline_summary['targets_met']}/{baseline_summary['total_queries']}")
    print(f"  Optimized:  {optimized_summary['targets_met']}/{optimized_summary['total_queries']}")
    print()

    # Per-query analysis
    print("Per-Query Analysis:")
    print(f"{'Query':<45} {'Before':>10} {'After':>10} {'Change':>10}")
    print("-" * 80)

    improvements = []
    for baseline_result, optimized_result in zip(baseline["results"], optimized["results"]):
        query = baseline_result["query"]
        if len(query) > 42:
            query = query[:39] + "..."

        baseline_ms = baseline_result.get("actual_ms", 0)
        optimized_ms = optimized_result.get("actual_ms", 0)

        if baseline_ms > 0:
            change_pct = ((baseline_ms - optimized_ms) / baseline_ms) * 100
            improvements.append(change_pct)

            status = "✓" if optimized_result.get("met_target", False) else "✗"
            print(f"{query:<45} {baseline_ms:8.0f}ms {optimized_ms:8.0f}ms {change_pct:+8.1f}% {status}")

    print()

    # Percentile analysis
    if improvements:
        percentiles = calculate_percentiles(improvements, [50, 75, 90, 95, 99])

        print("Improvement Distribution:")
        for p, val in percentiles.items():
            print(f"  P{p:<2}: {val:+6.1f}%")
        print()

    # Summary
    print("="*80)
    print("Summary:")
    print("="*80)

    improved = sum(1 for i in improvements if i > 0)
    regressed = sum(1 for i in improvements if i < 0)

    print(f"✓ Overall improvement: {improvement:+.1f}%")
    print(f"✓ {improved}/{len(improvements)} queries improved")
    if regressed > 0:
        print(f"⚠ {regressed}/{len(improvements)} queries regressed")
    print(f"✓ {optimized_summary['targets_met']}/{optimized_summary['total_queries']} queries met targets (vs {baseline_summary['targets_met']}/{baseline_summary['total_queries']} before)")

    if improvement > 25:
        print(f"\n🎉 Excellent optimization! {improvement:.1f}% improvement achieved.")
    elif improvement > 10:
        print(f"\n✓ Good optimization! {improvement:.1f}% improvement achieved.")
    elif improvement > 0:
        print(f"\n✓ Modest improvement: {improvement:.1f}%")
    else:
        print(f"\n⚠ Performance regressed by {abs(improvement):.1f}%")

    print("="*80 + "\n")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compare_benchmarks.py baseline.json optimized.json")
        sys.exit(1)

    baseline_file = sys.argv[1]
    optimized_file = sys.argv[2]

    if not Path(baseline_file).exists():
        print(f"Error: Baseline file not found: {baseline_file}")
        sys.exit(1)

    if not Path(optimized_file).exists():
        print(f"Error: Optimized file not found: {optimized_file}")
        sys.exit(1)

    compare_benchmarks(baseline_file, optimized_file)

if __name__ == "__main__":
    main()
```

#### 3. Run comparison

```bash
# Compare baseline vs optimized
python3 scripts/compare_benchmarks.py \
    results/baseline-2025-11-14.json \
    results/optimized-2025-11-14.json
```

### Success Criteria:

#### Automated Verification:
- [ ] Optimized benchmark completes successfully
- [ ] At least 18/20 queries succeed (≥90% success rate)
- [ ] Comparison script runs without errors
- [ ] Improvement percentage calculated correctly

#### Manual Verification:
- [ ] Overall improvement ≥30% (target: 30-50%)
- [ ] Control queries improve by ≥25%
- [ ] Knowledge queries improve by ≥20%
- [ ] No queries regress by >10%
- [ ] At least 2 more queries meet targets vs baseline
- [ ] Results make sense (no impossibly fast times like 0ms)

**Implementation Note:** If improvements are less than expected, review logs to identify which optimizations are working and which aren't. May need to iterate on specific optimizations.

---

## Phase 5: Documentation

**Goal:** Document benchmarking workflow and optimization results.

### Create Benchmarking README

**File:** `scripts/benchmarking/README.md` (new file)

```markdown
# Project Athena Benchmarking System

## Overview

Systematic performance measurement for Project Athena's orchestrator using 20 standardized queries across 5 categories.

## Quick Start

```bash
# 1. Setup (one-time)
./scripts/setup_benchmark_redis.sh

# 2. Run baseline
python3 scripts/benchmark_runner.py --output results/baseline.json

# 3. Make optimizations to code...

# 4. Run optimized benchmark
python3 scripts/benchmark_runner.py --output results/optimized.json

# 5. Compare
python3 scripts/compare_benchmarks.py results/baseline.json results/optimized.json
```

## Prerequisites

- Python 3.9+
- Docker (for test Redis instance)
- Project Athena orchestrator running on 192.168.10.167:8001
- redis-cli installed

## Test Queries

20 queries across 5 categories:
- **Control** (7 queries): Device control commands, target ≤3.5s
- **Weather** (3 queries): Weather information, target ≤5.5s
- **Sports** (3 queries): Sports scores and schedules, target ≤5.5s
- **Airports** (2 queries): Flight and airport info, target ≤5.5s
- **Local** (5 queries): Baltimore-specific queries, target ≤5.5s

## Cache Control

The benchmark uses an isolated Redis instance on port 6380 to prevent contaminating production cache (port 6379). Cache is flushed before each query by default to ensure fair testing.

To run without cache flushing:
```bash
python3 scripts/benchmark_runner.py --no-flush --output results/cached-run.json
```

## Interpreting Results

### Summary Statistics

- **avg_response_time_ms**: Overall average across all queries
- **control_avg_ms**: Average for control commands (target: ≤3500ms)
- **knowledge_avg_ms**: Average for knowledge queries (target: ≤5500ms)
- **targets_met**: Number of queries that met their performance target

### Comparison Report

The comparison script shows:
- **Overall improvement**: Percentage change in average response time
- **Per-category analysis**: Improvement by query type
- **Per-query breakdown**: Individual query improvements
- **Regressions**: Queries that got slower

### What's Good Performance?

- **30%+ improvement**: Excellent optimization
- **15-30% improvement**: Good optimization
- **5-15% improvement**: Modest but measurable
- **<5% improvement**: May be within noise/variance

## Troubleshooting

### Benchmark fails with connection error
- Check orchestrator is running: `curl http://192.168.10.167:8001/health`
- Check network connectivity: `ping 192.168.10.167`

### Redis flush fails
- Verify test Redis is running: `docker ps | grep athena-benchmark-redis`
- Test connectivity: `redis-cli -p 6380 PING`

### Queries timing out
- Increase timeout in `benchmark_runner.py` (default: 30s)
- Check orchestrator logs for errors

### Results seem inconsistent
- Run benchmark multiple times and average results
- Ensure no other load on orchestrator during testing
- Verify cache is actually being flushed

## Related Documentation

- [Research: Benchmarking Framework](../../thoughts/shared/research/2025-11-14-benchmarking-optimization-framework.md)
- [Implementation Plan](../../thoughts/shared/plans/2025-11-14-benchmarking-system-implementation.md)
```

### Success Criteria:

#### Automated Verification:
- [ ] README markdown is valid
- [ ] All links in documentation work
- [ ] Code examples in docs have valid syntax

#### Manual Verification:
- [ ] Documentation is clear and comprehensive
- [ ] Quick start guide works for new user
- [ ] Troubleshooting covers common issues
- [ ] Examples match actual code

---

## Testing Strategy

### Per-Phase Testing

**Phase 1:** Run benchmark script with no optimizations, verify infrastructure works
**Phase 2:** Run baseline 2-3 times, verify consistency (±5%)
**Phase 3:** Test each optimization individually before combining
**Phase 4:** Run optimized benchmark 2-3 times, verify improvements are consistent
**Phase 5:** Follow documentation as new user would

### Validation Tests

Before considering complete:
1. Fresh environment test: Run on different machine
2. Consistency test: Run 3 baselines, verify ±5% variance
3. Regression test: Confirm no queries regress by >10%
4. Documentation test: Follow README from scratch

## Dependencies

**Python Libraries (add to requirements.txt):**
```
redis>=4.5.0
httpx>=0.24.0
```

**External Services:**
- Docker (for test Redis)
- Redis 7+ (via Docker)
- Project Athena orchestrator at 192.168.10.167:8001

## Rollback Plan

If optimizations cause issues:
1. Revert to git commit before optimizations: `git revert <commit>`
2. Restart orchestrator with old code
3. Each optimization is independent - can selectively revert specific changes
4. Test Redis is isolated - no impact on production

**Safe to roll back at any time** - benchmarking system is read-only.

## Expected Results

### Baseline (Before Optimizations)

- Control queries: 2000-3000ms
- Knowledge queries: 3000-5000ms
- Targets met: 15/20 (75%)

### Optimized (After Phase 3)

- Control queries: 1200-2000ms (40% improvement)
- Knowledge queries: 2000-3500ms (35% improvement)
- Targets met: 18/20 (90%)

### Key Improvements

- Intent classification: 500-1500ms → <5ms (cache hits)
- Cache hit latency: 15-65ms → 5-15ms
- RAG API calls: Faster due to connection reuse
- Parallel search: No duplicate intent classification

## References

- **Research:** [2025-11-14-benchmarking-optimization-framework.md](../research/2025-11-14-benchmarking-optimization-framework.md)
- **Orchestrator:** `src/orchestrator/main.py`
- **Cache Implementation:** `src/shared/cache.py`
- **RAG Services:** `src/rag/{weather,sports,airports}/main.py`
- **Parallel Search:** `src/orchestrator/search_providers/parallel_search.py`

---

**Total Estimated Time:** 12-16 hours
- Phase 1: 3-4 hours (benchmarking infrastructure)
- Phase 2: 1 hour (baseline)
- Phase 3: 5-7 hours (6 optimizations)
- Phase 4: 2-3 hours (optimized benchmark + comparison)
- Phase 5: 1-2 hours (documentation)

**Success Metric:** ≥30% improvement in average response time with statistical significance.
