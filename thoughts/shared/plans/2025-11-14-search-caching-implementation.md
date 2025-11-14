# Search Result Caching Implementation

**Date:** 2025-11-14
**Status:** 📋 Planning
**Related:**
- `thoughts/shared/plans/2025-11-14-parallel-search-implementation.md`
- `thoughts/shared/plans/2025-11-14-anti-hallucination-implementation.md`

## Objective

Implement caching layer for parallel search results to:
1. Reduce redundant API calls to Ticketmaster, Eventbrite, DuckDuckGo
2. Improve response times for repeated queries
3. Stay within free tier rate limits
4. Provide faster responses for common queries

## Problem Statement

**Current Behavior:**
- Every query triggers fresh API calls to all 3 providers
- Same query asked twice = 6 API calls total
- Wastes rate limits (5,000/day Ticketmaster, 1,000/day Eventbrite)
- Increases latency (~1-3s for parallel search)

**Desired Behavior:**
- Cache search results for 15 minutes (configurable)
- Serve cached results instantly (<50ms)
- Refresh cache automatically after expiration
- Cache per-provider results (not just final fused results)

## Caching Strategy

### Cache Key Design

**Format:** `search:{provider}:{query_hash}:{location_hash}`

**Examples:**
```
search:ticketmaster:a3f5d8:baltimore_md
search:eventbrite:a3f5d8:baltimore_md
search:duckduckgo:a3f5d8:none
```

**Why per-provider caching:**
- Different providers may have different data freshness requirements
- Allows selective cache invalidation
- Enables provider-specific TTLs

### Cache Storage: Redis

**Already available:** Redis at 192.168.10.181:6379 (Mac mini)

**Data Structure:**
```python
{
    "query": "concerts in baltimore",
    "location": "Baltimore, MD",
    "provider": "ticketmaster",
    "results": [  # List of SearchResult.to_dict()
        {
            "source": "ticketmaster",
            "title": "Event Name",
            "snippet": "Event description",
            "url": "https://...",
            "confidence": 1.0,
            "event_date": "2025-11-20",
            "venue": "Venue Name",
            ...
        }
    ],
    "cached_at": "2025-11-14T13:47:25Z",
    "ttl": 900  # 15 minutes
}
```

### TTL (Time To Live) Strategy

**By Query Intent:**
```python
TTL_BY_INTENT = {
    "event_search": 900,      # 15 minutes (events change slowly)
    "concert": 900,           # 15 minutes
    "news": 300,              # 5 minutes (news changes fast)
    "weather": 600,           # 10 minutes (weather changes moderately)
    "general": 1800,          # 30 minutes (general info stable)
}
```

**By Provider:**
```python
TTL_BY_PROVIDER = {
    "ticketmaster": 900,      # 15 minutes (official event data)
    "eventbrite": 900,        # 15 minutes (official event data)
    "duckduckgo": 1800,       # 30 minutes (general knowledge)
}
```

**Final TTL:** `min(TTL_BY_INTENT[intent], TTL_BY_PROVIDER[provider])`

### Cache Hit/Miss Flow

```
User Query → Parallel Search Engine
    ↓
For each provider:
    ↓
Check cache (cache_key = hash(query + location + provider))
    ├─ Cache HIT → Return cached results immediately
    └─ Cache MISS → Execute API call
        ↓
        Store results in cache with TTL
        ↓
        Return results
    ↓
Fuse all results (cached + fresh)
    ↓
Return to user
```

## Implementation Plan

### Phase 1: Cache Infrastructure

**File:** `src/orchestrator/search_providers/cache.py`

```python
class SearchCache:
    """Redis-based cache for search results."""

    def __init__(self, redis_url: str, default_ttl: int = 900):
        self.redis = redis.from_url(redis_url)
        self.default_ttl = default_ttl

    def _make_key(self, provider: str, query: str, location: Optional[str]) -> str:
        """Generate cache key."""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:8]
        location_hash = hashlib.md5((location or "").lower().encode()).hexdigest()[:8]
        return f"search:{provider}:{query_hash}:{location_hash}"

    async def get(
        self,
        provider: str,
        query: str,
        location: Optional[str] = None
    ) -> Optional[List[SearchResult]]:
        """Get cached results."""
        key = self._make_key(provider, query, location)
        cached = await self.redis.get(key)

        if cached:
            data = json.loads(cached)
            # Reconstruct SearchResult objects
            return [SearchResult(**r) for r in data["results"]]

        return None

    async def set(
        self,
        provider: str,
        query: str,
        results: List[SearchResult],
        location: Optional[str] = None,
        ttl: Optional[int] = None
    ):
        """Cache search results."""
        key = self._make_key(provider, query, location)
        ttl = ttl or self.default_ttl

        data = {
            "query": query,
            "location": location,
            "provider": provider,
            "results": [r.to_dict() for r in results],
            "cached_at": datetime.utcnow().isoformat(),
            "ttl": ttl
        }

        await self.redis.setex(key, ttl, json.dumps(data))
```

### Phase 2: Integrate with ParallelSearchEngine

**Modify:** `src/orchestrator/search_providers/parallel_search.py`

```python
class ParallelSearchEngine:
    def __init__(self, ..., cache: Optional[SearchCache] = None):
        # ... existing code ...
        self.cache = cache  # NEW

    async def search(self, query: str, location: Optional[str] = None, ...):
        """Execute parallel search with caching."""

        # NEW: Check cache for each provider
        tasks = []
        for provider in self.providers:
            task = asyncio.create_task(
                self._search_with_cache(provider, query, location, ...)
            )
            tasks.append(task)

        # ... rest of existing code ...

    async def _search_with_cache(
        self,
        provider: SearchProvider,
        query: str,
        location: Optional[str],
        limit: int,
        **kwargs
    ) -> tuple[str, List[SearchResult]]:
        """Search with cache layer."""
        provider_name = provider.name

        # Try cache first
        if self.cache:
            cached_results = await self.cache.get(provider_name, query, location)
            if cached_results:
                logger.info(f"Cache HIT for {provider_name}: {len(cached_results)} results")
                return (provider_name, cached_results)

        # Cache miss - execute search
        try:
            results = await provider.search(query, location=location, limit=limit, **kwargs)

            # Store in cache
            if self.cache and results:
                await self.cache.set(provider_name, query, results, location)
                logger.info(f"Cached {len(results)} results for {provider_name}")

            return (provider_name, results)

        except Exception as e:
            logger.warning(f"Provider '{provider_name}' search failed: {e}")
            return (provider_name, [])
```

### Phase 3: Update Orchestrator

**Modify:** `src/orchestrator/main.py` lifespan function

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global parallel_search_engine, result_fusion, search_cache  # NEW

    # ... existing code ...

    # Initialize search cache (NEW)
    search_cache = SearchCache(
        redis_url=os.getenv("REDIS_URL", "redis://192.168.10.181:6379"),
        default_ttl=int(os.getenv("SEARCH_CACHE_TTL", "900"))
    )
    logger.info("Search cache initialized")

    # Initialize parallel search engine with cache
    parallel_search_engine = ParallelSearchEngine.from_environment(
        cache=search_cache  # Pass cache to engine
    )

    # ... rest of existing code ...

    yield

    # Shutdown
    if search_cache:
        await search_cache.close()
```

### Phase 4: Configuration

**Add to `.env`:**
```bash
# Search Caching
SEARCH_CACHE_TTL=900              # Default cache TTL (15 minutes)
SEARCH_CACHE_ENABLED=true         # Enable/disable caching
```

## Performance Impact

### Before Caching:
- Query 1: 3 API calls, ~2.5s response
- Query 2 (same): 3 API calls, ~2.5s response
- Query 3 (same): 3 API calls, ~2.5s response
- **Total:** 9 API calls, ~7.5s total

### After Caching:
- Query 1: 3 API calls, ~2.5s response (cache miss)
- Query 2 (same): 0 API calls, ~0.3s response (cache hit)
- Query 3 (same): 0 API calls, ~0.3s response (cache hit)
- **Total:** 3 API calls, ~3.1s total

**Improvements:**
- 67% fewer API calls
- 59% faster response times (for cached queries)
- Extends rate limits by 3x (fewer wasted calls)

## Rate Limit Protection

With caching, for a popular query asked 100 times in 15 minutes:
- **Without cache:** 300 API calls (100 queries × 3 providers)
- **With cache:** 3 API calls (first query only)

**Daily limits preserved:**
- Ticketmaster: 5,000/day → Supports ~1,600 unique queries/day
- Eventbrite: 1,000/day → Supports ~330 unique queries/day

## Monitoring Metrics

**Add to orchestrator metrics:**
```python
search_cache_hits = Counter(
    'search_cache_hits_total',
    'Cache hits by provider',
    ['provider']
)

search_cache_misses = Counter(
    'search_cache_misses_total',
    'Cache misses by provider',
    ['provider']
)

search_cache_latency = Histogram(
    'search_cache_latency_seconds',
    'Cache operation latency',
    ['operation']  # 'get' or 'set'
)
```

## Testing Strategy

### Unit Tests

```python
async def test_cache_hit():
    cache = SearchCache(redis_url="redis://localhost:6379")
    results = [SearchResult(...)]

    # Store in cache
    await cache.set("ticketmaster", "test query", results)

    # Retrieve from cache
    cached = await cache.get("ticketmaster", "test query")
    assert cached == results

async def test_cache_miss():
    cache = SearchCache(redis_url="redis://localhost:6379")

    # No data in cache
    cached = await cache.get("ticketmaster", "new query")
    assert cached is None
```

### Integration Tests

```python
async def test_parallel_search_with_cache():
    engine = ParallelSearchEngine(..., cache=SearchCache(...))

    # First call - cache miss
    results1 = await engine.search("concerts baltimore")
    assert len(results1) > 0

    # Second call - cache hit
    start = time.time()
    results2 = await engine.search("concerts baltimore")
    latency = time.time() - start

    assert results1 == results2
    assert latency < 0.5  # Cached response is fast
```

## Rollout Plan

### Phase 1: Deploy Cache Infrastructure (30 min)
- [x] Redis already running on Mac mini (192.168.10.181:6379)
- [ ] Implement SearchCache class
- [ ] Unit tests

### Phase 2: Integrate with ParallelSearchEngine (30 min)
- [ ] Modify _search_with_timeout to use cache
- [ ] Update initialization to accept cache
- [ ] Integration tests

### Phase 3: Deploy and Monitor (30 min)
- [ ] Update .env with cache settings
- [ ] Deploy to Mac Studio
- [ ] Monitor cache hit rate
- [ ] Verify Redis memory usage

### Phase 4: Optimization (ongoing)
- [ ] Tune TTLs based on usage patterns
- [ ] Add cache warming for common queries
- [ ] Implement cache invalidation API

## Success Criteria

- [ ] Cache hit rate > 50% after 1 hour of use
- [ ] Cached queries return in < 500ms
- [ ] API call reduction > 40%
- [ ] No increase in error rate
- [ ] Redis memory usage < 100MB

## Future Enhancements

### Phase 5: Smart Cache Warming
Pre-fetch popular queries during off-peak hours:
- "weather baltimore"
- "ravens game"
- "concerts this weekend"

### Phase 6: Cache Analytics
Track most popular queries and optimize caching strategy:
- Query frequency analysis
- Cache effectiveness by provider
- Automatic TTL adjustment

### Phase 7: Distributed Caching
If scaling beyond single Redis instance:
- Redis Cluster for high availability
- Cache sharding by provider
- Replication for read scaling

---

**Next Steps:**
1. Implement SearchCache class
2. Integrate with ParallelSearchEngine
3. Deploy and test
4. Monitor and optimize TTLs
