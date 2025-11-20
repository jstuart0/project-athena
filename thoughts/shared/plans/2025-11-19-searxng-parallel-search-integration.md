# SearXNG Parallel Search Integration Implementation Plan

## Overview

Integrate SearXNG metasearch engine as a new parallel search provider in Project Athena's orchestrator, adding comprehensive web search coverage that aggregates results from multiple search engines (DuckDuckGo, Startpage, Bing, etc.). Results from all providers (including SearXNG) will be fused, deduplicated, and synthesized by a mini-LLM (phi3:mini) to provide concise, accurate responses.

## Current State Analysis

### Existing Parallel Search System

**Location:** `src/orchestrator/search_providers/`

**Current Providers:**
- **DuckDuckGo** (`duckduckgo.py`) - Free, no API key, general queries
- **Brave Search** (`brave.py`) - 2,000/month free tier, excellent news search
- **Ticketmaster** (`ticketmaster.py`) - Event-specific API
- **Eventbrite** (`eventbrite.py`) - Community events

**Architecture:**
- `ParallelSearchEngine` (`parallel_search.py`): Orchestrates parallel execution
- `ProviderRouter` (`provider_router.py`): Intent-based provider selection
- `ResultFusion` (`result_fusion.py`): Deduplication and ranking
- `SearchProvider` base class (`base.py`): Common interface
- LLM synthesis in orchestrator (`main.py:synthesize_node()`) uses phi3:mini

### Key Discoveries:

**File: `src/orchestrator/search_providers/parallel_search.py`**
- Line 19-29: `ParallelSearchEngine` class orchestrates parallel searches
- Line 94-99: Tasks created for each provider, executed concurrently
- Line 137: Returns `(intent, all_results)` tuple

**File: `src/orchestrator/search_providers/provider_router.py`**
- Line 34-61: `INTENT_PROVIDER_SETS` mapping (intent → provider list)
- Line 64: `RAG_INTENTS` set defines which intents use RAG vs web search
- Line 90-127: Provider initialization with enable flags

**File: `src/orchestrator/search_providers/result_fusion.py`**
- Line 31-64: `PROVIDER_WEIGHTS` dict scores providers by intent
- Line 81-120: `fuse_results()` method handles deduplication and ranking
- Line 264-284: `get_top_results()` returns top N ranked results

**File: `src/orchestrator/main.py`**
- Line 1117-1208: `synthesize_node()` uses LLM (phi3:mini or llama3.1) to generate natural language responses from search results
- Line 1131-1147: Builds synthesis prompt with retrieved data
- Line 1183-1192: Calls `llm_router.generate()` to create response

**File: `src/orchestrator/search_providers/duckduckgo.py`**
- Lines 14-117: Example provider implementation pattern
- Line 39-40: `name` property returns provider identifier
- Line 42-102: `search()` method returns `List[SearchResult]`
- Line 114-116: `close()` method for cleanup

### SearXNG Deployment

**Deployment completed:** 2025-11-19
**Internal URL:** `http://searxng.athena-admin.svc.cluster.local:8080`
**Public URL:** `https://athena-admin.xmojo.net/searxng/`
**Status:** ✅ Healthy, 2 replicas running in `athena-admin` namespace

**API Format:** (tested with `curl`)
```json
{
  "results": [
    {
      "url": "https://example.com",
      "title": "Result Title",
      "content": "Snippet description...",
      "engine": "bing",
      "score": 1.0,
      "category": "general",
      "publishedDate": null
    }
  ]
}
```

## Desired End State

After implementation:

1. **SearXNG Provider Available:**
   - New provider class `SearXNGProvider` in `src/orchestrator/search_providers/searxng.py`
   - Implements `SearchProvider` interface
   - Normalizes SearXNG results to `SearchResult` format

2. **Intent-Based Routing:**
   - SearXNG added to appropriate intent provider sets
   - Weighted scoring in ResultFusion for optimal ranking
   - Executes in parallel with DuckDuckGo, Brave, etc.

3. **LLM Synthesis:**
   - Existing `synthesize_node()` automatically handles SearXNG results
   - Mini-LLM (phi3:mini) creates concise responses from fused results
   - Citations include SearXNG as source

4. **Verification:**
   - Test queries return results from SearXNG + other providers
   - ResultFusion deduplicates across all providers
   - LLM synthesizes accurate, concise responses

## What We're NOT Doing

- NOT modifying the LLM synthesis logic (already exists and works)
- NOT changing the parallel search orchestration (already optimal)
- NOT adding SearXNG-specific API keys (SearXNG is free/open)
- NOT creating a separate search path (uses existing parallel system)
- NOT modifying result fusion algorithm (existing algorithm handles new providers)

## Implementation Approach

**Strategy:** Extend the existing parallel search system by adding SearXNG as a new provider. The existing orchestration, fusion, and LLM synthesis infrastructure will automatically handle SearXNG results alongside other providers.

**Key Insight:** The user's requirement for "mini LLM to make sense of the answer" is ALREADY IMPLEMENTED in `synthesize_node()` which uses phi3:mini. No changes needed to LLM synthesis.

---

## Phase 1: Create SearXNG Provider

### Overview
Implement `SearXNGProvider` class following the `SearchProvider` interface pattern.

### Changes Required:

#### 1. Create SearXNG Provider Implementation
**File**: `src/orchestrator/search_providers/searxng.py` (NEW FILE)

```python
"""
SearXNG metasearch provider.

Aggregates results from multiple search engines via self-hosted SearXNG instance.
"""

import httpx
from typing import List, Optional
from urllib.parse import quote_plus

from .base import SearchProvider, SearchResult


class SearXNGProvider(SearchProvider):
    """
    SearXNG metasearch engine provider.

    Advantages:
    - Aggregates multiple search engines (DuckDuckGo, Startpage, Bing, etc.)
    - Privacy-focused (no tracking)
    - Self-hosted (no API limits)
    - Comprehensive coverage

    Configuration:
    - No API key required (self-hosted instance)
    - Internal URL: http://searxng.athena-admin.svc.cluster.local:8080
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize SearXNG provider.

        Args:
            base_url: SearXNG instance URL (defaults to internal cluster service)
            api_key: Not used (SearXNG doesn't require API keys)
        """
        super().__init__(api_key=None)
        self.base_url = base_url or "http://searxng.athena-admin.svc.cluster.local:8080"
        self.client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Athena/1.0)"
            }
        )

    @property
    def name(self) -> str:
        return "searxng"

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search using SearXNG metasearch engine.

        Args:
            query: Search query
            location: Not used by SearXNG (ignored)
            limit: Maximum number of results (default 5)
            **kwargs: Additional parameters (ignored)

        Returns:
            List of SearchResult objects
        """
        try:
            self.logger.info(f"SearXNG search started: {query}")

            # SearXNG JSON API
            url = f"{self.base_url}/search?q={quote_plus(query)}&format=json&pageno=1"

            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            results = []

            # Parse SearXNG results
            for item in data.get("results", [])[:limit]:
                # Calculate confidence based on SearXNG score and engine
                base_score = item.get("score", 0.7)

                # Boost confidence for results from multiple engines
                engines = item.get("engines", [])
                multi_engine_boost = min(0.1 * (len(engines) - 1), 0.2) if len(engines) > 1 else 0.0

                confidence = min(1.0, base_score + multi_engine_boost)

                result = self.normalize_result(
                    title=item.get("title", ""),
                    snippet=item.get("content", ""),
                    url=item.get("url", ""),
                    confidence=confidence,
                    metadata={
                        "engines": engines,
                        "category": item.get("category", "general"),
                        "published_date": item.get("publishedDate")
                    }
                )
                results.append(result)

            self.logger.info(f"SearXNG search completed: {len(results)} results")

            return results

        except httpx.HTTPStatusError as e:
            self.logger.error(f"SearXNG HTTP error: {e}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"SearXNG request error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"SearXNG search failed: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
```

### Success Criteria:

#### Automated Verification:
- [ ] File created: `src/orchestrator/search_providers/searxng.py`
- [ ] Imports are valid: `python3 -c "from src.orchestrator.search_providers.searxng import SearXNGProvider"`
- [ ] Linting passes: `pylint src/orchestrator/search_providers/searxng.py --disable=C0114,C0116`

#### Manual Verification:
- [ ] Provider can be instantiated: `SearXNGProvider()`
- [ ] Search method returns results: Test with "kubernetes" query
- [ ] Results have correct format (title, snippet, url, confidence)
- [ ] Multi-engine boost works (results from multiple engines get higher confidence)

---

## Phase 2: Integrate into ProviderRouter

### Overview
Add SearXNG to the provider router and configure intent-based routing.

### Changes Required:

#### 1. Update ProviderRouter - Add SearXNG Import
**File**: `src/orchestrator/search_providers/provider_router.py`
**Changes**: Add import at top of file

```python
from .searxng import SearXNGProvider  # Add this line after line 16
```

#### 2. Update ProviderRouter - Add to Intent Provider Sets
**File**: `src/orchestrator/search_providers/provider_router.py`
**Location**: Lines 34-61 (`INTENT_PROVIDER_SETS` dict)
**Changes**: Add "searxng" to appropriate intent lists

```python
INTENT_PROVIDER_SETS: Dict[str, List[str]] = {
    "event_search": [
        "ticketmaster",
        "eventbrite",
        "duckduckgo",
        "brave",
        "searxng"  # Add SearXNG for comprehensive event coverage
    ],
    "general": [
        "duckduckgo",
        "brave",
        "searxng"  # Add SearXNG as primary general search
    ],
    "news": [
        "brave",
        "duckduckgo",
        "searxng"  # Add SearXNG for news aggregation
    ],
    "local_business": [
        "brave",
        "duckduckgo",
        "searxng"  # Add SearXNG for local search
    ],
    "sports": [
        "duckduckgo",
        "brave",
        "searxng"  # Add SearXNG for sports coverage
    ],
    "weather": [
        "duckduckgo",
        "brave",
        "searxng"  # Add SearXNG as fallback for weather queries
    ]
}
```

#### 3. Update ProviderRouter - Initialize SearXNG Provider
**File**: `src/orchestrator/search_providers/provider_router.py`
**Location**: After line 127 (in `__init__` method)
**Changes**: Add SearXNG initialization

```python
# Add after line 127 (after Eventbrite initialization)

# Initialize SearXNG
if enable_searxng:
    try:
        searxng_base_url = searxng_base_url or "http://searxng.athena-admin.svc.cluster.local:8080"
        self.all_providers["searxng"] = SearXNGProvider(base_url=searxng_base_url)
        logger.info(f"Initialized SearXNG provider (base_url={searxng_base_url})")
    except Exception as e:
        logger.error(f"Failed to initialize SearXNG provider: {e}")
elif not enable_searxng:
    logger.info("SearXNG provider disabled")
```

#### 4. Update ProviderRouter - Add Constructor Parameters
**File**: `src/orchestrator/search_providers/provider_router.py`
**Location**: Line 66-75 (`__init__` signature)
**Changes**: Add parameters for SearXNG

```python
def __init__(
    self,
    ticketmaster_api_key: Optional[str] = None,
    eventbrite_api_key: Optional[str] = None,
    brave_api_key: Optional[str] = None,
    searxng_base_url: Optional[str] = None,  # Add this parameter
    enable_ticketmaster: bool = True,
    enable_eventbrite: bool = True,
    enable_brave: bool = True,
    enable_duckduckgo: bool = True,
    enable_searxng: bool = True  # Add this parameter
):
```

#### 5. Update ProviderRouter - Add to from_environment()
**File**: `src/orchestrator/search_providers/provider_router.py`
**Location**: Line 322-330 (return statement in `from_environment()`)
**Changes**: Add SearXNG parameters

```python
# Update environment variable loading (before return statement)
searxng_base_url = os.getenv("SEARXNG_BASE_URL", "http://searxng.athena-admin.svc.cluster.local:8080")

return cls(
    ticketmaster_api_key=ticketmaster_api_key,
    eventbrite_api_key=eventbrite_api_key,
    brave_api_key=brave_api_key,
    searxng_base_url=searxng_base_url,  # Add this line
    enable_ticketmaster=os.getenv("ENABLE_TICKETMASTER", "true").lower() == "true",
    enable_eventbrite=os.getenv("ENABLE_EVENTBRITE", "true").lower() == "true",
    enable_brave=os.getenv("ENABLE_BRAVE_SEARCH", "true").lower() == "true",
    enable_duckduckgo=os.getenv("ENABLE_DUCKDUCKGO", "true").lower() == "true",
    enable_searxng=os.getenv("ENABLE_SEARXNG", "true").lower() == "true"  # Add this line
)
```

### Success Criteria:

#### Automated Verification:
- [ ] Python imports work: `python3 -c "from src.orchestrator.search_providers.provider_router import ProviderRouter"`
- [ ] Linting passes: `pylint src/orchestrator/search_providers/provider_router.py --disable=C0114,C0116`
- [ ] Type checking passes: `mypy src/orchestrator/search_providers/provider_router.py --ignore-missing-imports`

#### Manual Verification:
- [ ] ProviderRouter initializes with SearXNG: Check logs for "Initialized SearXNG provider"
- [ ] `get_providers_for_intent("general")` includes SearXNG
- [ ] `get_available_providers()` lists "searxng"

---

## Phase 3: Update ResultFusion Weights

### Overview
Add authority weights for SearXNG to optimize result ranking by intent type.

### Changes Required:

#### 1. Add SearXNG to Provider Weights
**File**: `src/orchestrator/search_providers/result_fusion.py`
**Location**: Lines 31-64 (`PROVIDER_WEIGHTS` dict)
**Changes**: Add "searxng" weights

```python
PROVIDER_WEIGHTS = {
    # ... existing providers ...
    "searxng": {
        "general": 0.95,  # Excellent for general queries (aggregates multiple engines)
        "event_search": 0.7,  # Good for events (web results + aggregation)
        "news": 0.9,  # Excellent news coverage (multiple sources)
        "local_business": 0.85,  # Good local search (aggregated results)
        "definition": 0.9,  # Good for definitions (multiple sources)
        "sports": 0.8,  # Good sports coverage
        "weather": 0.75  # Decent weather info (as fallback)
    }
}
```

**Reasoning:**
- **General queries (0.95):** SearXNG aggregates multiple engines, providing comprehensive coverage
- **News (0.9):** Excellent due to multi-source aggregation
- **Local business (0.85):** Strong due to aggregation from multiple local search engines
- **Events (0.7):** Good but not as authoritative as Ticketmaster/Eventbrite APIs
- **Sports/Weather (0.8/0.75):** Decent fallback, but RAG services are primary

### Success Criteria:

#### Automated Verification:
- [ ] Python imports work: `python3 -c "from src.orchestrator.search_providers.result_fusion import ResultFusion"`
- [ ] Linting passes: `pylint src/orchestrator/search_providers/result_fusion.py --disable=C0114,C0116`

#### Manual Verification:
- [ ] ResultFusion applies SearXNG weights correctly
- [ ] SearXNG results ranked appropriately by intent type
- [ ] Cross-validation works with SearXNG results (confidence boost for multi-source facts)

---

## Phase 4: End-to-End Testing

### Overview
Verify the complete integration with real queries through the orchestrator.

### Changes Required:

None. This phase is pure testing and verification.

### Testing Strategy:

#### Test Queries by Intent:

1. **General Query:**
   - Query: "What is Kubernetes?"
   - Expected: Results from DuckDuckGo, Brave, SearXNG
   - Verify: LLM synthesizes concise answer citing all sources

2. **News Query:**
   - Query: "Latest tech news"
   - Expected: Results from Brave, DuckDuckGo, SearXNG
   - Verify: SearXNG results weighted appropriately (0.9 confidence)

3. **Event Query:**
   - Query: "Concerts in Baltimore this week"
   - Expected: Ticketmaster, Eventbrite, SearXNG, DuckDuckGo, Brave
   - Verify: Event APIs ranked higher than SearXNG (correct authority weights)

4. **Sports Query (RAG with web fallback):**
   - Query: "Did the Ravens win?"
   - Expected: Sports RAG service primary, SearXNG as fallback if RAG fails
   - Verify: Web search fallback includes SearXNG results

### Success Criteria:

#### Automated Verification:
- [ ] Orchestrator starts successfully: `python3 -m src.orchestrator.main` (health check)
- [ ] Parallel search engine initializes: Check logs for "SearXNG" initialization
- [ ] No errors in startup logs

#### Manual Verification:
- [ ] General query returns results from all providers including SearXNG
- [ ] ResultFusion deduplicates correctly across all providers
- [ ] LLM synthesis creates accurate, concise responses
- [ ] Citations include "searxng" as source
- [ ] SearXNG results contribute to multi-source confidence boosts
- [ ] Authority weights applied correctly (check logs for scoring details)
- [ ] Response time acceptable (< 5 seconds end-to-end)

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_searxng_provider.py` (NEW)

```python
import pytest
from src.orchestrator.search_providers.searxng import SearXNGProvider

@pytest.mark.asyncio
async def test_searxng_provider_search():
    """Test SearXNG provider returns valid results."""
    provider = SearXNGProvider()
    results = await provider.search("kubernetes", limit=5)

    assert len(results) > 0
    assert all(r.source == "searxng" for r in results)
    assert all(r.title for r in results)
    assert all(r.snippet for r in results)
    assert all(r.url for r in results)
    assert all(0.0 <= r.confidence <= 1.0 for r in results)

    await provider.close()

@pytest.mark.asyncio
async def test_searxng_multi_engine_boost():
    """Test confidence boost for multi-engine results."""
    provider = SearXNGProvider()
    results = await provider.search("kubernetes", limit=10)

    # Find results from multiple engines
    multi_engine = [r for r in results if len(r.metadata.get("engines", [])) > 1]
    single_engine = [r for r in results if len(r.metadata.get("engines", [])) == 1]

    if multi_engine and single_engine:
        # Multi-engine results should have higher average confidence
        avg_multi = sum(r.confidence for r in multi_engine) / len(multi_engine)
        avg_single = sum(r.confidence for r in single_engine) / len(single_engine)
        assert avg_multi >= avg_single

    await provider.close()
```

### Integration Tests

**File**: `tests/integration/test_parallel_search_searxng.py` (NEW)

```python
import pytest
from src.orchestrator.search_providers.parallel_search import ParallelSearchEngine

@pytest.mark.asyncio
async def test_searxng_in_parallel_search():
    """Test SearXNG participates in parallel search."""
    engine = await ParallelSearchEngine.from_environment()

    intent, results = await engine.search("kubernetes", limit_per_provider=5)

    # Verify SearXNG contributed results
    searxng_results = [r for r in results if r.source == "searxng"]
    assert len(searxng_results) > 0

    await engine.close_all()

@pytest.mark.asyncio
async def test_result_fusion_with_searxng():
    """Test ResultFusion handles SearXNG results correctly."""
    from src.orchestrator.search_providers.result_fusion import ResultFusion

    engine = await ParallelSearchEngine.from_environment()
    fusion = ResultFusion()

    _, results = await engine.search("kubernetes", limit_per_provider=10)
    fused = fusion.get_top_results(results, "kubernetes", intent="general", limit=5)

    # Verify deduplication and ranking
    assert len(fused) <= 5
    assert all(r.confidence > 0 for r in fused)

    # Verify SearXNG results are included if relevant
    sources = {r.source for r in fused}
    # SearXNG should be included for general queries

    await engine.close_all()
```

### Manual Testing Steps

1. **Start Orchestrator:**
   ```bash
   cd /Users/jaystuart/dev/project-athena
   python3 -m src.orchestrator.main
   ```

2. **Test Query via API:**
   ```bash
   curl -X POST http://localhost:8001/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What is Kubernetes?", "mode": "owner", "room": "office"}'
   ```

3. **Verify Response:**
   - Check `metadata.data_source` includes "searxng"
   - Check `citations` includes results from SearXNG
   - Verify `answer` is concise and accurate
   - Check logs for parallel search execution

4. **Test Different Intents:**
   - General: "What is Docker?"
   - News: "Latest AI developments"
   - Events: "Concerts in Baltimore"
   - Sports: "Ravens score" (should use RAG, SearXNG as fallback)

## Performance Considerations

### Expected Impact:

**Response Time:**
- Current: ~2-3 seconds (DuckDuckGo + Brave parallel)
- With SearXNG: ~2.5-3.5 seconds (3 providers in parallel)
- Impact: +0.5 seconds (acceptable, still under 5s target)

**Result Quality:**
- Current: 2 providers (DDG, Brave) = ~10-20 results
- With SearXNG: 3 providers = ~15-30 results
- ResultFusion deduplicates to top 5 results
- Benefit: Better coverage, multi-source validation

**Resource Usage:**
- SearXNG: Already deployed, 2 replicas, minimal overhead
- Orchestrator: +1 HTTP client, minimal memory impact
- Network: +1 concurrent request (async, non-blocking)

### Optimization:

- ResultFusion already handles deduplication efficiently
- Parallel execution ensures no sequential delays
- LLM synthesis time unchanged (same phi3:mini model)

## Migration Notes

### Backward Compatibility:

- Existing queries continue to work (SearXNG is additive)
- Existing providers unaffected (independent execution)
- Environment variable `ENABLE_SEARXNG=false` to disable if needed

### Rollback Plan:

If issues arise:

1. **Disable SearXNG via environment variable:**
   ```bash
   export ENABLE_SEARXNG=false
   # Restart orchestrator
   ```

2. **Remove from intent provider sets:**
   - Comment out "searxng" entries in `INTENT_PROVIDER_SETS`
   - Restart orchestrator

3. **Full rollback:**
   - Revert `searxng.py` file creation
   - Revert provider_router.py changes
   - Revert result_fusion.py changes
   - Restart orchestrator

## References

- **SearXNG Deployment Plan:** `thoughts/shared/plans/2025-11-19-searxng-thor-deployment.md`
- **SearXNG Instance:** https://athena-admin.xmojo.net/searxng/
- **SearXNG API Docs:** https://docs.searxng.org/dev/search_api.html
- **Parallel Search Implementation:** `src/orchestrator/search_providers/parallel_search.py`
- **Provider Router:** `src/orchestrator/search_providers/provider_router.py`
- **Result Fusion:** `src/orchestrator/search_providers/result_fusion.py`
- **Orchestrator LLM Synthesis:** `src/orchestrator/main.py:1117-1208`

## Environment Variables

```bash
# SearXNG Configuration (optional)
SEARXNG_BASE_URL="http://searxng.athena-admin.svc.cluster.local:8080"  # Default
ENABLE_SEARXNG="true"  # Enable/disable SearXNG provider
```

## Summary

This plan integrates SearXNG as a parallel search provider, enhancing Project Athena's web search capabilities with comprehensive multi-engine coverage. The existing LLM synthesis (phi3:mini in `synthesize_node()`) will automatically process SearXNG results alongside other providers, creating concise, accurate responses. No changes to LLM synthesis logic are needed - the user's requirement for "mini LLM to make sense of the answer" is already implemented.

**Key Benefits:**
- Comprehensive search coverage (SearXNG aggregates 10+ engines)
- Privacy-focused (self-hosted, no tracking)
- No API limits (self-hosted instance)
- Automatic result fusion and deduplication
- Mini-LLM synthesis for concise responses (already implemented)

**Implementation Effort:** ~4-6 hours
- Phase 1: 1-2 hours
- Phase 2: 1-2 hours
- Phase 3: 30 minutes
- Phase 4: 1-2 hours (testing)
