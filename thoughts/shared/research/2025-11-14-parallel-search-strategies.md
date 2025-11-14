# Parallel Search Strategies & API Options

**Date:** 2025-11-14
**Author:** Claude Code
**Status:** Research

## Problem Statement

DuckDuckGo Instant Answer API returns 0 results for many queries (concerts, events, current information). Need multiple search providers running in parallel with intelligent result fusion.

## Parallel Search Architecture

### Strategy: Fan-Out / Fan-In Pattern

```
User Query
    ↓
  Classify
    ↓
[Parallel Search Launch]
    ├─→ DuckDuckGo API
    ├─→ SerpAPI (Google)
    ├─→ Brave Search API
    ├─→ Bing Web Search
    ├─→ Ticketmaster (events)
    └─→ Web Scraper (specific sites)
    ↓
[Wait for all / first N results]
    ↓
[Result Fusion & Ranking]
    ├─ Deduplicate
    ├─ Score by relevance
    ├─ Cross-validate facts
    └─ Merge complementary info
    ↓
[Feed to LLM]
    ↓
[Validate & Respond]
```

### Benefits:
1. **Redundancy:** If one search fails, others may succeed
2. **Coverage:** Different sources have different strengths
3. **Cross-validation:** Same fact from multiple sources = higher confidence
4. **Speed:** Parallel execution (not sequential)
5. **Quality:** Best results from each source

## Search API Options

### 1. SerpAPI (Recommended)
**URL:** https://serpapi.com/
**Type:** Google Search API wrapper

**Pros:**
- ✅ Accesses actual Google search results
- ✅ Multiple search engines (Google, Bing, Yahoo, DuckDuckGo)
- ✅ Structured JSON responses
- ✅ Rich snippets, knowledge panels, local results
- ✅ News, images, videos, shopping
- ✅ Location-aware results

**Cons:**
- ❌ Paid (free tier: 100 searches/month)
- ❌ Cost: $50/month for 5,000 searches

**Pricing:**
- Free: 100 searches/month
- Developer: $50/month (5,000 searches)
- Production: $150/month (20,000 searches)

**Best For:** General web search, news, local events

**Example Response:**
```json
{
  "organic_results": [
    {
      "title": "Lady Gaga Tour Dates 2024",
      "link": "https://...",
      "snippet": "Lady Gaga will perform at...",
      "date": "2024-03-15"
    }
  ],
  "knowledge_graph": {...},
  "local_results": [...]
}
```

### 2. Brave Search API
**URL:** https://brave.com/search/api/
**Type:** Privacy-focused search API

**Pros:**
- ✅ Independent index (not Google/Bing)
- ✅ Privacy-focused (no tracking)
- ✅ Web, news, images
- ✅ Good pricing
- ✅ Fast responses

**Cons:**
- ❌ Smaller index than Google
- ❌ May miss niche content

**Pricing:**
- Free: 2,000 queries/month
- Data for AI: $0.50 per 1,000 queries

**Best For:** Privacy-conscious search, general queries

### 3. Bing Web Search API (Microsoft)
**URL:** https://azure.microsoft.com/en-us/services/cognitive-services/bing-web-search-api/
**Type:** Official Bing search

**Pros:**
- ✅ Large index (2nd to Google)
- ✅ Rich entity data
- ✅ News, images, videos
- ✅ Azure integration
- ✅ Reliable uptime

**Cons:**
- ❌ Paid (free tier limited)
- ❌ Azure account required

**Pricing:**
- Free: 1,000 transactions/month
- S1: $7 per 1,000 transactions

**Best For:** Enterprise use, when Google unavailable

### 4. Tavily Search API
**URL:** https://tavily.com/
**Type:** AI-optimized search API

**Pros:**
- ✅ Designed specifically for RAG/AI
- ✅ Filters out low-quality content
- ✅ Returns clean, relevant text
- ✅ Fast parallel search
- ✅ Good for research queries

**Cons:**
- ❌ Paid service
- ❌ Smaller than major search engines

**Pricing:**
- Free: 1,000 searches/month
- Pro: $30/month (5,000 searches)

**Best For:** RAG applications, research queries

### 5. Ticketmaster Discovery API
**URL:** https://developer.ticketmaster.com/
**Type:** Event-specific API

**Pros:**
- ✅ FREE (no cost)
- ✅ Comprehensive event data
- ✅ Real-time availability
- ✅ Venue information
- ✅ Artist tour dates
- ✅ Geographic search

**Cons:**
- ❌ Events only (concerts, sports, theater)
- ❌ Rate limited (5,000 requests/day free tier)

**Pricing:**
- Discovery API: FREE
- Rate limit: 5,000 API calls/day

**Best For:** Concert/event queries (PERFECT for your use case!)

**Example:**
```bash
GET https://app.ticketmaster.com/discovery/v2/events.json
  ?city=Baltimore
  &classificationName=music
  &apikey=YOUR_KEY

Response:
{
  "events": [
    {
      "name": "Lady Gaga",
      "dates": {"start": {"localDate": "2024-03-15"}},
      "venues": [{"name": "M&T Bank Stadium"}],
      "priceRanges": [{"min": 89.50, "max": 250.00}]
    }
  ]
}
```

### 6. Jina AI Search API
**URL:** https://jina.ai/reader/
**Type:** LLM-optimized web reader

**Pros:**
- ✅ Converts web pages to LLM-friendly text
- ✅ Cleans HTML, extracts content
- ✅ Good for scraping specific sites
- ✅ Free tier available

**Cons:**
- ❌ Not a search API (need URLs first)
- ❌ Rate limited

**Best For:** Converting search results to clean text

### 7. Web Scraping (Playwright/Selenium)
**Type:** DIY web scraping

**Pros:**
- ✅ Free (except compute)
- ✅ Access any public website
- ✅ Full control over extraction
- ✅ Can handle dynamic content

**Cons:**
- ❌ Fragile (breaks when sites change)
- ❌ Slow (page load time)
- ❌ May violate ToS
- ❌ Blocked by anti-bot measures
- ❌ Maintenance overhead

**Best For:** Specific sites with structured data

### 8. You.com API
**URL:** https://you.com/
**Type:** AI-enhanced search

**Pros:**
- ✅ AI-summarized results
- ✅ Multiple sources
- ✅ Citation tracking

**Cons:**
- ❌ API availability unclear
- ❌ Pricing unknown

### 9. Perplexity API
**URL:** https://www.perplexity.ai/
**Type:** AI search engine

**Pros:**
- ✅ AI-native search
- ✅ Cited sources
- ✅ Good for research

**Cons:**
- ❌ API not publicly available (yet)
- ❌ Would be expensive

## Recommended Stack for Project Athena

### Tier 1: Free/Low Cost (Immediate Implementation)
1. **DuckDuckGo Instant Answer** (current)
   - Free, fast for simple queries

2. **Ticketmaster Discovery API** (FREE!)
   - Perfect for concert/event queries
   - 5,000 calls/day free

3. **Brave Search API**
   - 2,000 queries/month free
   - Good for general web search

### Tier 2: Paid (When Budget Allows)
4. **SerpAPI**
   - $50/month for 5,000 searches
   - Best overall coverage
   - Use for high-value queries

5. **Tavily**
   - $30/month for 5,000 searches
   - Optimized for AI/RAG

## Implementation: Parallel Search with Fusion

### Step 1: Create Search Providers Module

```python
# src/orchestrator/search_providers.py

from typing import List, Dict, Optional
import asyncio
import httpx

class SearchResult:
    source: str
    title: str
    snippet: str
    url: str
    confidence: float
    metadata: Dict

class SearchProvider:
    async def search(self, query: str) -> List[SearchResult]:
        raise NotImplementedError

class DuckDuckGoProvider(SearchProvider):
    # Current implementation

class TicketmasterProvider(SearchProvider):
    async def search(self, query: str, location: str = "Baltimore") -> List[SearchResult]:
        # Search Ticketmaster events

class BraveSearchProvider(SearchProvider):
    async def search(self, query: str) -> List[SearchResult]:
        # Search Brave API

class SerpAPIProvider(SearchProvider):
    async def search(self, query: str) -> List[SearchResult]:
        # Search via SerpAPI
```

### Step 2: Parallel Search Orchestrator

```python
# src/orchestrator/parallel_search.py

class ParallelSearchEngine:
    def __init__(self):
        self.providers = [
            DuckDuckGoProvider(),
            TicketmasterProvider(),
            BraveSearchProvider(),
        ]

    async def search(self, query: str, timeout: float = 3.0) -> List[SearchResult]:
        """Search all providers in parallel."""
        tasks = [
            asyncio.create_task(provider.search(query))
            for provider in self.providers
        ]

        # Wait for all to complete or timeout
        done, pending = await asyncio.wait(
            tasks,
            timeout=timeout,
            return_when=asyncio.ALL_COMPLETED
        )

        # Cancel any still running
        for task in pending:
            task.cancel()

        # Gather results
        all_results = []
        for task in done:
            try:
                results = await task
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Provider failed: {e}")

        # Deduplicate and rank
        return self.fuse_results(all_results)

    def fuse_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Intelligent result fusion."""
        # 1. Deduplicate by URL/content similarity
        # 2. Cross-validate facts (same info from multiple sources = higher confidence)
        # 3. Score by recency, relevance, source authority
        # 4. Return top N results

        return ranked_results[:5]
```

### Step 3: Query Classification for Provider Selection

```python
def select_providers(query: str, intent: str) -> List[SearchProvider]:
    """Smart provider selection based on query type."""

    if intent == "event_search" or "concert" in query:
        return [TicketmasterProvider(), SerpAPIProvider()]

    elif intent == "news":
        return [BraveSearchProvider(), SerpAPIProvider()]

    elif intent == "local_business":
        return [GoogleMapsProvider(), YelpProvider()]

    else:
        # General search - use all
        return [DuckDuckGoProvider(), BraveSearchProvider()]
```

## Result Fusion Strategies

### 1. Majority Voting
If 3+ sources say same fact → High confidence

### 2. Source Authority Weighting
- Ticketmaster for events: 1.0
- Google/Bing for general: 0.9
- DuckDuckGo: 0.7
- Random blog: 0.3

### 3. Recency Scoring
Newer results ranked higher for time-sensitive queries

### 4. Content Similarity Deduplication
Use embeddings to detect duplicate info from different sources

### 5. Consensus Building
```python
facts = extract_facts(all_results)
fact_sources = group_by_fact(facts)

for fact, sources in fact_sources.items():
    if len(sources) >= 2:  # Multiple sources confirm
        confidence = 0.9
    else:
        confidence = 0.6
```

## Performance Considerations

### Latency:
- Sequential search: 3s × 3 providers = 9s ❌
- Parallel search: max(3s, 3s, 3s) = 3s ✅

### Cost:
- Free tier: DuckDuckGo + Ticketmaster + Brave = 2,100 free queries/month
- With SerpAPI: Add $50/month for 5,000 more

### Reliability:
- If 1 provider fails: Still have 2 others
- If 2 providers fail: Still have 1
- Current: If DuckDuckGo returns 0 results, we have nothing

## Immediate Action Plan

### Phase 1: Add Ticketmaster (FREE!)
1. Sign up for Ticketmaster API key
2. Implement TicketmasterProvider
3. Add to parallel search for event queries
4. Test with concert queries

### Phase 2: Add Brave Search (2K free/month)
1. Sign up for Brave API
2. Implement BraveSearchProvider
3. Use for general web queries
4. Monitor usage

### Phase 3: Implement Result Fusion
1. Deduplicate results
2. Cross-validate facts
3. Score and rank

### Phase 4: Add Paid Providers (Optional)
1. SerpAPI for high-value queries
2. Usage-based routing (free first, paid if needed)

## Example: "Concerts in Baltimore" Query

**Parallel Execution:**
```
t=0s:  Launch 3 searches in parallel
t=0.5s: Ticketmaster returns:
        - Lady Gaga, M&T Stadium, May 15, 2024
        - The Weeknd, CFG Bank Arena, June 3, 2024

t=1.2s: Brave returns:
        - "Upcoming Baltimore concerts" article
        - Mentions Lady Gaga show

t=2.5s: DuckDuckGo returns: 0 results

t=2.5s: Fusion:
        - Lady Gaga: 2 sources confirm ✅ High confidence
        - The Weeknd: 1 source ✅ Medium confidence
        - Return both with confidence scores
```

**LLM Response:**
```
Based on current event listings:

1. Lady Gaga - M&T Bank Stadium - May 15, 2024
   (Source: Ticketmaster, confirmed by Brave Search)

2. The Weeknd - CFG Bank Arena - June 3, 2024
   (Source: Ticketmaster)

For more upcoming events, visit Ticketmaster or venue websites.
```

## Conclusion

**Recommended Approach:**
1. ✅ Implement parallel search (Ticketmaster + Brave + DuckDuckGo)
2. ✅ All free tier (2,100+ searches/month)
3. ✅ Result fusion with confidence scoring
4. ✅ Cross-validation prevents hallucinations
5. ⏳ Add paid providers when usage grows

**Cost:** $0/month (free tier sufficient for personal use)
**Reliability:** 3× redundancy
**Quality:** Best results from each source
**Speed:** Parallel execution (no additional latency)
