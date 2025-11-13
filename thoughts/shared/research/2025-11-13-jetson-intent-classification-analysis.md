# Jetson Intent Classification System Analysis

## Executive Summary

After comprehensive analysis of the Jetson iterations in `research/jetson-iterations/`, I've discovered that the "43 versions of intent classification" mentioned in the research document refers to the iterative evolution of the facade pattern implementations, not a single file with 43 versions. The sophisticated intent classification system is distributed across multiple facade implementations, each progressively more refined.

## Key Discoveries

### 1. Intent Classification Architecture

The Jetson implementations use a **layered approach** rather than a single classifier:

1. **Fast Path Classification** (`get_quick_response()` / `analyze_query()`)
   - Pattern-based routing for known query types
   - Zero-latency responses for common queries
   - Caching for frequently accessed data

2. **Slow Path Classification** (LLM-based)
   - Complex queries routed to Ollama
   - Context-aware processing
   - Natural language understanding

### 2. Intent Categories Found

From analyzing the facade implementations, here are the comprehensive intent categories:

#### Control Intents
```python
control_patterns = [
    "turn on", "turn off", "set", "dim", "brighten",
    "lights", "switch", "temperature", "thermostat",
    "scene", "mood", "routine", "schedule",
    "lock", "unlock", "open", "close",
    "goodnight", "good morning", "movie", "dinner"
]
```

#### Information Queries
```python
info_categories = {
    "sports": ["ravens", "orioles", "game", "score", "stadium"],
    "weather": ["weather", "temperature", "rain", "snow", "forecast"],
    "transit": ["bus", "train", "marc", "light rail", "metro", "uber"],
    "airport": ["airport", "bwi", "flight", "flying", "terminal"],
    "events": ["event", "concert", "show", "museum", "entertainment"],
    "emergency": ["emergency", "hospital", "doctor", "urgent care", "911"],
    "food": ["restaurant", "food", "crab", "seafood", "coffee", "eat"],
    "location": ["address", "where", "neighborhood", "how far", "distance"]
}
```

### 3. Multi-Intent Handling

While explicit multi-intent splitting wasn't found, the system handles compound queries through:

1. **Query Analysis** (`analyze_query()` in smart_facade)
   - Extracts primary intent
   - Returns specific information needed
   - Routes to appropriate handler

2. **Context Injection**
   - Home Assistant state added to all queries
   - Time/date context
   - Location context

### 4. Anti-Hallucination Validation System

Found in `ollama_baltimore_ultimate.py` - a sophisticated two-layer validation system:

#### Layer 1: Self-Validation
```python
def validate_any_answer(user_query, proposed_answer):
    """
    Validates if answer addresses the query
    - Checks for required elements (scores must have numbers)
    - Verifies answer relevance
    - Can modify answer if needed
    """
```

#### Layer 2: Dual-Model Cross-Check
```python
def dual_model_cross_check(query, answer_3b):
    """
    Cross-checks answer with different model
    - Returns consistency score (0.0-1.0)
    - High confidence: 0.8-1.0
    - Medium confidence: 0.5-0.8
    - Low confidence: <0.5
    """
```

### 5. Performance Optimizations

The facades implement several optimization strategies:

1. **Caching with TTL**
   ```python
   CACHE_TTLS = {
       "sports": 300,      # 5 minutes
       "transit": 60,      # 1 minute for real-time
       "weather": 600,     # 10 minutes
       "flights": 120,     # 2 minutes
       "events": 3600,     # 1 hour
       "static": 86400,    # 24 hours
   }
   ```

2. **Fast Path / Slow Path Routing**
   - Quick responses for known patterns
   - LLM only for complex queries

3. **Streaming Responses**
   - Stream quick responses line by line
   - Reduces perceived latency

## Migration Strategy for LangGraph

### Phase 1: Enhanced Intent Classification

Replace the basic pattern matching in `classify_node` with the layered approach:

```python
class EnhancedIntentClassifier:
    def __init__(self):
        # Import all patterns from facades
        self.control_patterns = [...]
        self.info_categories = {...}
        self.cache_ttls = {...}

    async def classify(self, query: str) -> IntentClassification:
        # 1. Fast path - pattern matching
        intent = self._pattern_match(query)
        if intent.confidence > 0.8:
            return intent

        # 2. Slow path - LLM classification
        intent = await self._llm_classify(query)

        # 3. Extract entities
        intent.entities = self._extract_entities(query)

        return intent
```

### Phase 2: Multi-Intent Support

Add query analysis to support compound intents:

```python
class QueryAnalyzer:
    def analyze(self, query: str) -> List[Intent]:
        # Split compound queries
        intents = []

        # Check for multiple action words
        if "and" in query or "then" in query:
            parts = self._split_compound(query)
            for part in parts:
                intents.append(self._classify_part(part))
        else:
            intents.append(self._classify_part(query))

        return intents
```

### Phase 3: Anti-Hallucination Integration

Integrate the two-layer validation into `validate_node`:

```python
async def enhanced_validate_node(state: OrchestratorState) -> OrchestratorState:
    """Enhanced validation with anti-hallucination"""

    # Layer 1: Self-validation
    is_valid, validated = await validate_answer(
        state.query,
        state.response
    )

    if not is_valid:
        state.needs_retry = True
        state.validation_errors.append("Failed self-validation")
        return state

    # Layer 2: Cross-model validation (if confidence needed)
    if state.requires_high_confidence:
        is_consistent, final, confidence = await cross_check(
            state.query,
            validated
        )

        state.confidence_score = confidence

        if confidence < 0.5:
            state.needs_retry = True
            state.validation_errors.append(f"Low confidence: {confidence}")

    state.response = final
    return state
```

### Phase 4: Performance Optimizations

Add caching and fast-path routing:

```python
class ResponseCache:
    def __init__(self):
        self.cache = {}
        self.ttls = CACHE_TTLS

    async def get_cached(self, category: str, key: str):
        # Check cache with TTL
        ...

    async def set_cached(self, category: str, key: str, data: Any):
        # Store with timestamp
        ...
```

## Implementation Priority

1. **High Priority**
   - Import comprehensive pattern lists from facades
   - Implement layered classification (pattern + LLM fallback)
   - Add basic validation

2. **Medium Priority**
   - Add caching layer
   - Implement confidence scoring
   - Add entity extraction

3. **Low Priority**
   - Multi-intent splitting
   - Cross-model validation
   - Advanced query analysis

## Code Migration Checklist

- [ ] Extract all intent patterns from facade implementations
- [ ] Create `IntentClassifier` class with pattern matching
- [ ] Add LLM fallback for unknown patterns
- [ ] Implement validation functions
- [ ] Add confidence scoring
- [ ] Create caching layer with TTLs
- [ ] Add entity extraction
- [ ] Implement multi-intent analysis
- [ ] Add cross-model validation
- [ ] Create performance metrics

## Files to Reference

Key files for migration:
1. `ollama_baltimore_complete_facade.py` - Comprehensive pattern list
2. `ollama_baltimore_smart_facade.py` - Query analysis logic
3. `ollama_baltimore_ultimate.py` - Validation system
4. `athena_lite_llm.py` - LLM integration patterns

## Next Steps

1. Create `src/orchestrator/intent_classifier.py` with consolidated patterns
2. Create `src/orchestrator/validator.py` with anti-hallucination logic
3. Update `classify_node` to use new classifier
4. Update `validate_node` to use new validator
5. Add caching layer to orchestrator
6. Test with comprehensive query set