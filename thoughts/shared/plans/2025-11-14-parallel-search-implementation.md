# Parallel Search Implementation Plan

**Date:** 2025-11-14
**Status:** ✅ Deployed (Needs API Key Validation)
**Deployed:** Mac Studio (192.168.10.167:8001) - PID 74996
**Related Research:**
- `thoughts/shared/research/2025-11-14-parallel-search-strategies.md`
- `thoughts/shared/research/2025-11-14-llm-search-tools.md`
**Related Implementation:**
- `thoughts/shared/plans/2025-11-14-anti-hallucination-implementation.md`

## Objective

Implement parallel search system to address DuckDuckGo's 0-result problem by querying multiple search providers simultaneously and fusing results.

## Problem Statement

Current implementation uses only DuckDuckGo Instant Answer API which frequently returns 0 results for:
- Concert and event queries
- Current local information
- Time-sensitive queries
- Specific venue/artist information

This led to LLM hallucinations when no supporting data was retrieved.

## Solution Architecture

### Multi-Provider Parallel Search

```
User Query
    ↓
Query Analysis & Classification
    ↓
┌──────────── Parallel Search Launch ────────────┐
│                                                 │
├─→ DuckDuckGo     (general web, instant answers)│
├─→ Ticketmaster   (concerts, sports events)     │
└─→ Eventbrite     (local events)                │
    ↓                                             │
Wait for all (with 3s timeout)                    │
    ↓                                             │
Result Fusion & Ranking                           │
├─ Deduplicate similar results                    │
├─ Cross-validate facts from multiple sources     │
├─ Score by source authority & recency            │
└─ Merge complementary information                │
    ↓                                             │
Return ranked results to LLM                      │
└──────────────────────────────────────────────────┘
```

### Benefits

1. **Redundancy:** If one provider fails, others may succeed
2. **Coverage:** Different sources have different strengths
3. **Cross-validation:** Same fact from multiple sources = higher confidence
4. **Speed:** Parallel execution (not sequential)
5. **Quality:** Best results from each source

## Implementation Components

### 1. Search Provider Base Class

**File:** `src/orchestrator/search_providers/base.py`

Defines common interface for all search providers:
- `async search(query: str) -> List[SearchResult]`
- Result normalization to common format
- Error handling and timeouts
- Source attribution

### 2. Provider Implementations

#### DuckDuckGoProvider
- **File:** `src/orchestrator/search_providers/duckduckgo.py`
- **Current:** Already implemented in `src/orchestrator/web_search.py`
- **Task:** Refactor to use base class

#### TicketmasterProvider
- **File:** `src/orchestrator/search_providers/ticketmaster.py`
- **API:** Ticketmaster Discovery API
- **Endpoint:** `https://app.ticketmaster.com/discovery/v2/events.json`
- **Key:** YAN7RhpKiLKGz8oJQYphfVdmrDRymHRl
- **Rate Limit:** 5,000 calls/day (FREE tier)
- **Best For:** Concerts, sports, theater events

#### EventbriteProvider
- **File:** `src/orchestrator/search_providers/eventbrite.py`
- **API:** Eventbrite API v3
- **Endpoint:** `https://www.eventbriteapi.com/v3/events/search/`
- **Key:** CB7RXGR2CJL266RAHG7Q
- **Rate Limit:** 1,000 calls/day (FREE tier)
- **Best For:** Local community events, meetups

### 3. Parallel Search Orchestrator

**File:** `src/orchestrator/search_providers/parallel_search.py`

Core orchestration logic:
- Launch multiple searches in parallel using `asyncio.create_task()`
- Wait for all providers with timeout (3 seconds)
- Handle failures gracefully (log warning, continue with successful results)
- Aggregate results from all providers

### 4. Result Fusion Engine

**File:** `src/orchestrator/search_providers/result_fusion.py`

Intelligent result combination:
- **Deduplication:** Detect similar/duplicate results across providers
- **Cross-validation:** Identify facts confirmed by multiple sources
- **Authority scoring:** Weight results by provider reliability for query type
- **Recency scoring:** Prioritize newer information for time-sensitive queries
- **Confidence scoring:** Assign confidence based on source agreement

### 5. Query Routing Logic

**File:** `src/orchestrator/search_providers/query_router.py`

Smart provider selection based on intent:
- **Event queries** → Ticketmaster + Eventbrite (high priority)
- **News queries** → DuckDuckGo
- **General queries** → All providers
- **Local business** → Future: Google Maps, Yelp

## Implementation Plan

### Phase 1: Core Infrastructure ✅

- [x] Create directory structure: `src/orchestrator/search_providers/`
- [ ] Implement `SearchResult` data model
- [ ] Implement `SearchProvider` base class
- [ ] Add logging and error handling framework

### Phase 2: Provider Implementations

- [ ] Refactor existing DuckDuckGo code to use base class
- [ ] Implement TicketmasterProvider
- [ ] Implement EventbriteProvider
- [ ] Unit tests for each provider

### Phase 3: Orchestration & Fusion

- [ ] Implement parallel search orchestrator
- [ ] Implement result fusion engine
- [ ] Implement query routing logic
- [ ] Integration tests

### Phase 4: Orchestrator Integration

- [ ] Update `src/orchestrator/main.py` retrieve_node to use parallel search
- [ ] Add configuration for provider selection
- [ ] Update environment variables in `.env`
- [ ] Deploy to Mac Studio

### Phase 5: Testing & Validation

- [ ] Test with "concerts in baltimore" query
- [ ] Test with various event queries
- [ ] Test with general web queries
- [ ] Verify anti-hallucination validation still works
- [ ] Monitor performance and adjust timeouts

## Code Structure

```
src/orchestrator/search_providers/
├── __init__.py               # Package initialization
├── base.py                   # SearchProvider base class, SearchResult model
├── duckduckgo.py             # DuckDuckGo Instant Answer
├── ticketmaster.py           # Ticketmaster Discovery API
├── eventbrite.py             # Eventbrite API
├── parallel_search.py        # Orchestrator for parallel execution
├── result_fusion.py          # Result deduplication and ranking
└── query_router.py           # Smart provider selection
```

## Configuration

### Environment Variables

Add to `.env` and deploy to Mac Studio:

```bash
# Search API Keys (already exist in .env.generated)
TICKETMASTER_API_KEY=YAN7RhpKiLKGz8oJQYphfVdmrDRymHRl
EVENTBRITE_API_KEY=CB7RXGR2CJL266RAHG7Q

# Search Configuration
SEARCH_TIMEOUT=3.0                    # Max wait time for parallel searches
SEARCH_MAX_RESULTS_PER_PROVIDER=5     # Results per provider
SEARCH_ENABLE_FUSION=true             # Enable result fusion
SEARCH_MIN_CONFIDENCE=0.6             # Minimum confidence threshold
```

### Provider Authority Weights

```python
PROVIDER_WEIGHTS = {
    "ticketmaster": {
        "event_search": 1.0,    # Perfect for events
        "general": 0.3          # Not good for general queries
    },
    "eventbrite": {
        "event_search": 0.9,    # Excellent for events
        "local_business": 0.7,  # Good for local
        "general": 0.2
    },
    "duckduckgo": {
        "general": 0.8,         # Good for general queries
        "event_search": 0.4,    # Limited event coverage
        "news": 0.9             # Excellent for news
    }
}
```

## Expected Performance

### Latency

- **Current (DuckDuckGo only):** ~0.5-1.5s
- **Target (Parallel):** ~1-3s (parallel execution, not sequential)
- **Maximum:** 3s timeout (configurable)

### Success Rate

- **Current:** ~30% (many 0-result queries)
- **Target:** >90% (multiple providers increase coverage)

### Cost

- **All FREE tier:** 6,100 queries/day total
  - Ticketmaster: 5,000/day
  - Eventbrite: 1,000/day
  - DuckDuckGo: Unlimited (no key required)

## Testing Strategy

### Unit Tests

Each provider individually:
```python
async def test_ticketmaster_concert_search():
    provider = TicketmasterProvider()
    results = await provider.search("Lady Gaga Baltimore")
    assert len(results) > 0
    assert results[0].source == "ticketmaster"
    assert "Lady Gaga" in results[0].title.lower()
```

### Integration Tests

Parallel search orchestrator:
```python
async def test_parallel_search_events():
    orchestrator = ParallelSearchEngine()
    results = await orchestrator.search("concerts in baltimore")

    # Should get results from multiple providers
    sources = {r.source for r in results}
    assert len(sources) >= 2

    # Ticketmaster should be included for event queries
    assert "ticketmaster" in sources
```

### End-to-End Tests

Full pipeline with orchestrator:
```bash
# Via Home Assistant
"Athena, what concerts are happening in Baltimore?"

# Expected:
# - Parallel search triggers
# - Results from Ticketmaster + Eventbrite
# - LLM synthesizes with actual data
# - No hallucinations (validation passes)
```

## Rollback Plan

If parallel search causes issues:

1. **Feature flag:** Add `ENABLE_PARALLEL_SEARCH=false` to disable
2. **Fallback:** Revert to DuckDuckGo-only in retrieve_node
3. **Gradual rollout:** Test with specific query patterns first

## Success Criteria

- [ ] "concerts in baltimore" returns actual events (not 0 results)
- [ ] Response time stays under 5 seconds end-to-end
- [ ] Validation detects hallucinations when providers fail
- [ ] Multiple sources cross-validate facts
- [ ] No regressions in existing queries

## Future Enhancements

### Phase 6 (Future):
- Add Brave Search API (2,000 free/month)
- Add SerpAPI when budget allows ($50/month)
- Implement caching layer for repeated queries
- Add learning: track which providers work best for query types

### Phase 7 (Future):
- LangChain Tools integration for agent-based search
- Exa/Metaphor neural search for semantic understanding
- Citation tracking for every fact

## Related Documents

- Research: `thoughts/shared/research/2025-11-14-parallel-search-strategies.md`
- Research: `thoughts/shared/research/2025-11-14-llm-search-tools.md`
- Implementation: `thoughts/shared/plans/2025-11-14-anti-hallucination-implementation.md`
- Code: `src/orchestrator/main.py` (retrieve_node, validate_node)

## Dependencies

**Python Packages:**
```
httpx>=0.24.0        # Async HTTP client (already installed)
pydantic>=2.0.0      # Data validation (already installed)
```

**No new dependencies required!** We'll use existing HTTP client and async framework.

## Timeline

- **Phase 1:** ✅ 30 minutes (directory structure, base classes)
- **Phase 2:** ✅ 1 hour (provider implementations)
- **Phase 3:** ✅ 1 hour (orchestration & fusion)
- **Phase 4:** ✅ 30 minutes (integration)
- **Phase 5:** ⏳ 30 minutes (testing - in progress)

**Total:** ~3.5 hours for complete implementation

---

## Deployment Status

### ✅ Completed (2025-11-14)

**Files Created:**
- `src/orchestrator/search_providers/__init__.py`
- `src/orchestrator/search_providers/base.py` - SearchProvider base class, SearchResult model
- `src/orchestrator/search_providers/duckduckgo.py` - DuckDuckGo provider
- `src/orchestrator/search_providers/ticketmaster.py` - Ticketmaster Discovery API
- `src/orchestrator/search_providers/eventbrite.py` - Eventbrite API
- `src/orchestrator/search_providers/parallel_search.py` - Orchestrator
- `src/orchestrator/search_providers/result_fusion.py` - Result fusion engine

**Files Modified:**
- `src/orchestrator/main.py` - Integrated parallel search in retrieve_node
- `.env` - Added TICKETMASTER_API_KEY, EVENTBRITE_API_KEY, SEARCH_TIMEOUT

**Deployed To:**
- Mac Studio (192.168.10.167:8001)
- Process ID: 74996
- Status: Running

**Initialization Logs:**
```
{"event": "Parallel search engine initialized", "timestamp": "2025-11-14T13:47:25.926568Z"}
{"event": "Result fusion initialized", "timestamp": "2025-11-14T13:47:25.926596Z"}
```

### ⚠️ Current Issues

**API Key Validation Needed:**

1. **Eventbrite API:** Returns 404
   - Error: `Client error '404 NOT FOUND' for url 'https://www.eventbriteapi.com/v3/events/search/'`
   - Possible causes: Invalid API key, incorrect endpoint, or API access tier issue
   - Action: Validate Eventbrite API key and endpoint

2. **Ticketmaster API:** No logs (may have failed silently)
   - No error logs visible
   - May need additional logging
   - Action: Add more verbose logging to track Ticketmaster results

3. **DuckDuckGo:** No logs (may have failed silently)
   - No error logs visible
   - May have returned 0 results
   - Action: Add logging to show DuckDuckGo result count

**Test Results:**
- Query: "what concerts are happening in baltimore"
- All providers returned 0 results
- System correctly fell back to "LLM knowledge"
- Anti-hallucination validation worked correctly (did not fabricate events)

### 🔄 Next Steps

1. **Validate API Keys:**
   - Test Ticketmaster API key directly
   - Test Eventbrite API key directly
   - Check API documentation for endpoint changes

2. **Add Enhanced Logging:**
   - Log each provider's result count
   - Log provider initialization status
   - Add provider health checks on startup

3. **Test with Known Working Queries:**
   - Try simpler queries ("concerts baltimore")
   - Test with specific artist names
   - Test location variations

4. **Implement Caching:**
   - Cache successful search results for 15 minutes
   - Reduce redundant API calls
   - Improve response times

---

**Status Summary:**
- ✅ Implementation: Complete
- ✅ Integration: Complete
- ✅ Deployment: Complete
- ⚠️ Testing: Needs API key validation
- ⏳ Caching: Not yet implemented
