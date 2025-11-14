# Intent-Based Search Provider Routing

**Date:** 2025-11-14
**Status:** 📋 Planning
**Related:**
- `thoughts/shared/plans/2025-11-14-parallel-search-implementation.md`
- `thoughts/shared/plans/2025-11-14-search-caching-implementation.md`

## Objective

Implement intelligent intent-based routing that triggers different sets of search providers based on query intent. This ensures:
1. Event queries use event-specific APIs (Ticketmaster, Eventbrite) + general search
2. General queries use multiple general web search providers (DuckDuckGo, Brave Search)
3. News queries prioritize news-focused sources
4. Each intent gets optimal provider coverage

## Problem Statement

**Current Approach (TOO SIMPLE):**
- All queries use same 3 providers: DuckDuckGo + Ticketmaster + Eventbrite
- Ticketmaster and Eventbrite are USELESS for non-event queries
- DuckDuckGo alone is insufficient for general web search
- No specialization based on what user is actually asking

**User Feedback:**
> "for parallel processing... it would be more effective if it was doing web search multiple ways... ticketmaster and eventbrite are only for very particular use cases"

> "the system should do parallel processing with eventbrite and ticket master if the intent is live events"

> "different intents should have parallel processing for the intent if there are multiple sources for that intent"

## Intent-Based Architecture

### Intent Classification

**Query Intent Types:**

1. **`event_search`** - Concerts, shows, sports events, performances
   - Keywords: "concert", "show", "event", "game", "performance", "tour", "festival"
   - Example: "what concerts are in Baltimore?"

2. **`general`** - General knowledge, facts, how-to
   - Default for queries that don't match other intents
   - Example: "what is the capital of France?"

3. **`news`** - Current events, breaking news
   - Keywords: "news", "breaking", "latest", "today's", "current"
   - Example: "latest news on AI"

4. **`weather`** - Weather conditions, forecasts
   - Keywords: "weather", "temperature", "forecast", "rain", "snow"
   - Example: "weather in Baltimore" (NOTE: Already handled by RAG service)

5. **`sports`** - Sports scores, schedules, stats
   - Keywords: "ravens", "orioles", "score", "game", "team"
   - Example: "ravens score" (NOTE: Already handled by RAG service)

6. **`local_business`** - Restaurants, shops, services
   - Keywords: "restaurant", "coffee", "store", "near me"
   - Example: "best pizza near me"

### Provider Sets by Intent

**Intent → Provider Mapping:**

```python
INTENT_PROVIDER_SETS = {
    "event_search": [
        "ticketmaster",    # Official event data (5,000/day free)
        "eventbrite",      # Local events (1,000/day free)
        "duckduckgo",      # General web search backup
        "brave"            # Additional web search coverage
    ],

    "general": [
        "duckduckgo",      # Free unlimited
        "brave",           # 2,000/month free
        # Future: "bing" (1,000/month free)
    ],

    "news": [
        "duckduckgo",      # News articles
        "brave",           # News search
        # Future: "newsapi" (dedicated news)
    ],

    "local_business": [
        "duckduckgo",      # General search
        "brave",           # Web search
        # Future: "google_places", "yelp"
    ],

    # RAG intents - handled by dedicated RAG services, no web search
    "weather": [],       # Use athena-weather-rag (already implemented)
    "sports": [],        # Use athena-sports-rag (already implemented)
    "airports": []       # Use athena-airports-rag (already implemented)
}
```

## Implementation Components

### 1. Intent Classifier

**File:** `src/orchestrator/search_providers/intent_classifier.py`

**Purpose:** Classify query intent based on keywords and patterns

**Key Methods:**
- `classify(query: str) -> str` - Returns intent type
- `extract_keywords(query: str) -> List[str]` - Extract key terms
- `confidence_score(query: str, intent: str) -> float` - Intent confidence

**Intent Detection Rules:**

```python
INTENT_PATTERNS = {
    "event_search": [
        r"\b(concert|show|event|performance|tour|festival|game)\b",
        r"\b(tickets|venue|live)\b",
        r"\b(playing|performing|appearing)\b"
    ],
    "news": [
        r"\b(news|breaking|latest|today|current)\b",
        r"\b(headline|report|update)\b"
    ],
    "weather": [
        r"\b(weather|temperature|forecast|rain|snow|sunny)\b",
        r"\b(degrees|fahrenheit|celsius)\b"
    ],
    "sports": [
        r"\b(ravens|orioles|score|game|team|win|loss)\b",
        r"\b(playoff|championship|season)\b"
    ],
    "local_business": [
        r"\b(restaurant|coffee|store|shop|near me)\b",
        r"\b(best|top|good)\b.*\b(food|pizza|burger)\b"
    ]
}
```

### 2. Provider Router

**File:** `src/orchestrator/search_providers/provider_router.py`

**Purpose:** Route queries to appropriate provider sets based on intent

**Key Methods:**
- `get_providers_for_intent(intent: str) -> List[SearchProvider]` - Return providers for intent
- `should_use_rag(intent: str) -> bool` - Check if RAG should handle this
- `get_provider_weights(intent: str) -> Dict[str, float]` - Provider authority weights

**Provider Initialization:**

```python
class ProviderRouter:
    def __init__(self, api_keys: Dict[str, str]):
        # Initialize ALL available providers
        self.all_providers = {
            "duckduckgo": DuckDuckGoProvider(),
            "brave": BraveSearchProvider(api_key=api_keys.get("brave")),
            "ticketmaster": TicketmasterProvider(api_key=api_keys.get("ticketmaster")),
            "eventbrite": EventbriteProvider(api_key=api_keys.get("eventbrite"))
        }

        # Intent-to-provider mapping
        self.intent_provider_sets = {
            "event_search": ["ticketmaster", "eventbrite", "duckduckgo", "brave"],
            "general": ["duckduckgo", "brave"],
            "news": ["duckduckgo", "brave"],
            "local_business": ["duckduckgo", "brave"]
        }

    def get_providers_for_intent(self, intent: str) -> List[SearchProvider]:
        """Get provider instances for given intent."""
        provider_names = self.intent_provider_sets.get(intent, ["duckduckgo"])
        return [self.all_providers[name] for name in provider_names if name in self.all_providers]
```

### 3. Brave Search Provider

**File:** `src/orchestrator/search_providers/brave.py`

**Purpose:** General web search via Brave Search API (2,000 free queries/month)

**API Details:**
- **Endpoint:** `https://api.search.brave.com/res/v1/web/search`
- **Auth:** API key in `X-Subscription-Token` header
- **Rate Limit:** 2,000 queries/month free tier
- **Documentation:** https://brave.com/search/api/

**Implementation:**

```python
class BraveSearchProvider(SearchProvider):
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "brave"

    async def search(self, query: str, location: Optional[str] = None, limit: int = 5, **kwargs) -> List[SearchResult]:
        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json"
        }

        params = {
            "q": query,
            "count": limit,
            "search_lang": "en",
            "country": "US"
        }

        response = await self.client.get(self.BASE_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:limit]:
            result = SearchResult(
                source="brave",
                title=item.get("title", ""),
                snippet=item.get("description", ""),
                url=item.get("url"),
                confidence=0.8,  # Brave is reliable
                metadata={
                    "age": item.get("age"),
                    "language": item.get("language")
                }
            )
            results.append(result)

        return results
```

### 4. Updated Parallel Search Engine

**File:** `src/orchestrator/search_providers/parallel_search.py`

**Changes:**
- Accept `IntentClassifier` and `ProviderRouter` in constructor
- Classify intent before searching
- Route to appropriate provider set
- Log which providers are being used for each intent

**New Flow:**

```python
class ParallelSearchEngine:
    def __init__(
        self,
        intent_classifier: IntentClassifier,
        provider_router: ProviderRouter,
        timeout: float = 3.0
    ):
        self.intent_classifier = intent_classifier
        self.provider_router = provider_router
        self.timeout = timeout

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit_per_provider: int = 5,
        **kwargs
    ) -> Tuple[str, List[SearchResult]]:
        """
        Execute parallel search with intent-based provider routing.

        Returns:
            (intent, results) tuple
        """
        # 1. Classify query intent
        intent = self.intent_classifier.classify(query)
        logger.info(f"Classified query intent: {intent}")

        # 2. Check if RAG should handle this
        if self.provider_router.should_use_rag(intent):
            logger.info(f"Intent '{intent}' handled by RAG service, skipping web search")
            return (intent, [])

        # 3. Get providers for this intent
        providers = self.provider_router.get_providers_for_intent(intent)
        logger.info(f"Using {len(providers)} providers for intent '{intent}': {[p.name for p in providers]}")

        # 4. Execute parallel search across selected providers
        tasks = [
            asyncio.create_task(self._search_with_timeout(provider, query, location, limit_per_provider, **kwargs))
            for provider in providers
        ]

        # 5. Wait for results
        done, pending = await asyncio.wait(tasks, timeout=self.timeout, return_when=asyncio.ALL_COMPLETED)

        # 6. Gather results
        all_results = []
        for task in done:
            provider_name, results = await task
            all_results.extend(results)
            logger.info(f"Provider '{provider_name}' returned {len(results)} results")

        return (intent, all_results)
```

### 5. Updated Orchestrator Integration

**File:** `src/orchestrator/main.py`

**Changes:**
- Initialize `IntentClassifier` and `ProviderRouter` in lifespan
- Pass intent to result fusion for proper weighting
- Log intent classification results

**Updated retrieve_node:**

```python
async def retrieve_node(state: OrchestratorState) -> OrchestratorState:
    """Retrieve data from RAG services or web search."""
    logger.info(f"Retrieving data for query: {state.query}")

    # Try specialized RAG services first (weather, sports, airports handled automatically)
    # ... existing RAG code ...

    else:
        # Use intent-based parallel web search
        logger.info("Attempting intent-based parallel search")

        intent, search_results = await parallel_search_engine.search(
            query=state.query,
            location="Baltimore, MD",
            limit_per_provider=5
        )

        logger.info(f"Intent: {intent}, Total results: {len(search_results)}")

        if search_results:
            # Fuse and rank results based on intent
            fused_results = result_fusion.get_top_results(
                results=search_results,
                query=state.query,
                intent=intent,
                limit=5
            )

            search_data = {
                "intent": intent,
                "results": [r.to_dict() for r in fused_results],
                "sources": list(set(r.source for r in fused_results)),
                "total_results": len(search_results),
                "fused_results": len(fused_results)
            }

            state.retrieved_data = search_data
            state.data_source = f"Parallel Search ({intent}): {', '.join(search_data['sources'])}"
```

## Configuration

### Environment Variables

**Add to `.env`:**

```bash
# General Web Search
BRAVE_SEARCH_API_KEY=<get-from-brave.com>     # 2,000 queries/month free
ENABLE_BRAVE_SEARCH=true

# Event-Specific Search (only for event intents)
TICKETMASTER_API_KEY=YAN7RhpKiLKGz8oJQYphfVdmrDRymHRl
EVENTBRITE_API_KEY=CB7RXGR2CJL266RAHG7Q
ENABLE_TICKETMASTER=true
ENABLE_EVENTBRITE=true

# Search Configuration
SEARCH_TIMEOUT=3.0
SEARCH_MAX_RESULTS_PER_PROVIDER=5
```

### Intent Provider Weights

**Update in `result_fusion.py`:**

```python
PROVIDER_WEIGHTS = {
    "ticketmaster": {
        "event_search": 1.0,    # Perfect for events
        "concert": 1.0,
        "general": 0.0          # Don't use for general queries
    },
    "eventbrite": {
        "event_search": 0.9,    # Excellent for events
        "local_business": 0.5,  # Sometimes useful for local events
        "general": 0.0          # Don't use for general queries
    },
    "duckduckgo": {
        "general": 0.8,         # Good for general
        "event_search": 0.5,    # OK for events
        "news": 0.9,            # Great for news
        "local_business": 0.7
    },
    "brave": {
        "general": 0.9,         # Excellent for general
        "event_search": 0.6,    # Decent for events
        "news": 0.9,            # Great for news
        "local_business": 0.8
    }
}
```

## Example Query Flows

### Event Query: "concerts in baltimore"

```
1. Intent Classification: "event_search" (detected: "concerts")
2. Provider Selection: ["ticketmaster", "eventbrite", "duckduckgo", "brave"]
3. Parallel Execution:
   - Ticketmaster → 5 concert results (weight: 1.0)
   - Eventbrite → 3 local event results (weight: 0.9)
   - DuckDuckGo → 2 concert listings (weight: 0.5)
   - Brave → 4 event pages (weight: 0.6)
4. Result Fusion:
   - Deduplicate similar events
   - Cross-validate (same concert from multiple sources = confidence boost)
   - Apply intent weights (Ticketmaster wins for events)
5. Return: Top 5 concerts ranked by confidence
```

### General Query: "what is the capital of france"

```
1. Intent Classification: "general" (no special keywords)
2. Provider Selection: ["duckduckgo", "brave"]
3. Parallel Execution:
   - DuckDuckGo → Instant answer: "Paris" (weight: 0.8)
   - Brave → Web results about Paris (weight: 0.9)
4. Result Fusion:
   - Both sources confirm "Paris"
   - Cross-validation boost
5. Return: High-confidence answer: "Paris"
```

### News Query: "latest AI news"

```
1. Intent Classification: "news" (detected: "latest", "news")
2. Provider Selection: ["duckduckgo", "brave"]
3. Parallel Execution:
   - DuckDuckGo → Recent news articles (weight: 0.9)
   - Brave → News search results (weight: 0.9)
4. Result Fusion:
   - Recency scoring applied
   - Multiple sources = higher confidence
5. Return: Top 5 recent AI news articles
```

### Weather Query: "weather in baltimore"

```
1. Intent Classification: "weather" (detected: "weather")
2. RAG Check: Weather intent → Use athena-weather-rag
3. Provider Selection: [] (skip web search)
4. Return: RAG service handles directly
```

## Implementation Plan

### Phase 1: Core Intent Routing (2 hours)

- [ ] Create `IntentClassifier` class with pattern matching
- [ ] Create `ProviderRouter` class with intent-to-provider mapping
- [ ] Update `ParallelSearchEngine` to use intent routing
- [ ] Add intent classification unit tests

### Phase 2: Brave Search Provider (1 hour)

- [ ] Implement `BraveSearchProvider` class
- [ ] Add Brave API key to environment
- [ ] Test Brave search with various queries
- [ ] Add Brave to provider router

### Phase 3: Integration (1 hour)

- [ ] Update orchestrator `retrieve_node` to use intent-based search
- [ ] Update result fusion weights for new provider
- [ ] Add intent logging and metrics
- [ ] Integration tests

### Phase 4: Testing & Validation (1 hour)

- [ ] Test event queries (should use Ticketmaster + Eventbrite)
- [ ] Test general queries (should use DuckDuckGo + Brave)
- [ ] Test news queries
- [ ] Verify RAG services still work (weather, sports)
- [ ] Monitor API usage rates

## Success Criteria

- [ ] Event queries use event-specific providers + general search
- [ ] General queries use multiple general web search providers
- [ ] No event providers wasted on non-event queries
- [ ] Intent classification accuracy > 90%
- [ ] Response times stay under 5 seconds
- [ ] API rate limits respected (2,000 Brave/month, 5,000 Ticketmaster/day)

## Future Enhancements

### Additional Providers by Intent

**General Search:**
- Bing Web Search API (1,000/month free)
- SerpAPI ($50/month for 5,000 searches)

**News:**
- NewsAPI (500 requests/day free)
- GNews API (100 requests/day free)

**Local Business:**
- Google Places API
- Yelp Fusion API

**Shopping:**
- Amazon Product API
- eBay Search API

### Advanced Intent Classification

- Use lightweight LLM for intent classification (Phi-3-mini)
- Multi-label classification (query can have multiple intents)
- Confidence thresholds for provider selection

### Dynamic Provider Selection

- Learn which providers work best for which queries
- A/B testing for provider combinations
- Automatic fallback if primary providers fail

---

**Next Steps:**
1. Implement `IntentClassifier`
2. Implement `ProviderRouter`
3. Implement `BraveSearchProvider`
4. Update `ParallelSearchEngine` for intent routing
5. Deploy and test
