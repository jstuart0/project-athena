# Intent Classification Approach Comparison

## Purpose
Compare three intent classification approaches to determine optimal balance of accuracy vs speed.

## Three Versions

### V1: Pattern Matching (CURRENT - ARCHIVED)
**File**: `airbnb_intent_classifier_v1_patterns.py`

**Approach**:
- Pure substring/keyword matching
- 230+ manual patterns across 7 categories
- Order-dependent (first match wins)
- Location and recipe filters added

**Pros**:
- Fast (~10-50ms classification)
- No LLM latency
- Predictable behavior

**Cons**:
- Pattern conflicts ("best museums" matches "best" → routes to restaurants)
- Requires manual pattern maintenance
- No semantic understanding
- Order-dependent failures

**Known Issues**:
- ✅ FIXED: D.C. museums → Baltimore museums (added location filter)
- ✅ FIXED: Recipe queries → restaurants (added recipe filter)
- ⚠️ REMAINING: "best museums in Baltimore" → restaurants (order issue)

---

### V2: Hybrid Approach (TO IMPLEMENT)
**File**: `airbnb_intent_classifier_v2_hybrid.py`

**Approach**:
- Fast pattern matching for unambiguous queries
- LLM classification for ambiguous queries
- Best of both worlds

**Classification Logic**:
```python
def classify(query):
    # Fast path: Unambiguous patterns
    if exact_time_pattern(query):
        return handle_time()

    if exact_weather_keyword(query):
        return handle_weather()

    # Ambiguous: Use LLM
    if has_ambiguous_keywords(query):
        intent = llm_classify(query)
        return route_by_intent(intent, query)

    # Default patterns...
```

**Fast Path (No LLM)**:
- Time: "what time", "current time"
- Weather: "weather", "temperature", "forecast"
- Sports: team names + score keywords
- Location: "directions to", "how far"

**LLM Path (Ambiguous)**:
- "best X" - could be restaurants, museums, etc.
- "good X" - could be food, recipes, recommendations
- "find me X" - could be locations, information, services
- "where X" - could be dining, entertainment, directions

**Expected Performance**:
- Fast path queries: 10-50ms (70% of queries)
- LLM path queries: 200-500ms (30% of queries)
- Average: ~150-200ms classification time

**Pros**:
- Solves ambiguity issues
- Maintains speed for common queries
- Semantic understanding when needed
- Easy to extend

**Cons**:
- More complex logic
- Requires LLM access
- Variable latency

---

### V3: Full LLM Classification (TO IMPLEMENT)
**File**: `airbnb_intent_classifier_v3_llm.py`

**Approach**:
- All queries classified by LLM
- Single, simple classification prompt
- No pattern matching

**Classification Logic**:
```python
def classify(query):
    # Always use LLM
    system_prompt = """Classify user intent into ONE category:
    - time_date
    - weather
    - location
    - dining
    - entertainment
    - sports
    - recipe
    - out_of_area
    - general

    Respond with ONLY the category name."""

    intent = llm_classify(system_prompt, query)
    return route_by_intent(intent, query)
```

**Expected Performance**:
- All queries: 200-500ms
- Consistent latency

**Pros**:
- Simplest code
- Best semantic understanding
- No pattern conflicts
- Easy to maintain
- Easy to add categories

**Cons**:
- Slowest option
- LLM dependency for all queries
- Higher compute cost

---

## Test Queries for Benchmarking

### Unambiguous (Should be fast in V2)
- "what time is it"
- "current temperature"
- "Ravens score"
- "directions to BWI"

### Ambiguous (Needs LLM intelligence)
- "best museums in Baltimore"
- "good bread recipe"
- "what museums are in washington d.c."
- "find me a coffee shop"
- "where should I eat"

### Edge Cases
- "how to make pizza" (recipe, not restaurant)
- "best restaurants near me" (dining, not general)
- "who won the game" (sports, not web search)
- "is it nice outside" (weather)

---

## Benchmark Metrics

For each version, measure:

1. **Accuracy**: Correct intent classification
   - % correct on test set of 50 queries
   - Focus on ambiguous query accuracy

2. **Latency**: Classification time
   - Min/Max/Average/P95
   - Breakdown by query type

3. **Consistency**: Same query, same result
   - Run each query 10x
   - Measure variance

4. **Cost**: Compute resources
   - V1: CPU only
   - V2: CPU + some LLM calls
   - V3: All LLM calls

---

## Recommended Approach

**Initial recommendation**: V2 (Hybrid)

**Rationale**:
- Maintains speed for common queries
- Fixes ambiguity issues
- Good balance of accuracy vs performance
- Can tune the threshold (when to use LLM)

**Alternative scenarios**:
- If latency < 100ms critical → V1 with better patterns
- If accuracy > 98% critical → V3
- If cost is concern → V1

---

## Implementation Plan

1. ✅ Archive V1 (pattern matching)
2. Create V2 (hybrid):
   - Add LLM classification method
   - Define ambiguous keyword list
   - Route ambiguous queries to LLM
   - Keep fast paths for unambiguous
3. Create V3 (full LLM):
   - Single classification method
   - Simplified routing logic
4. Create benchmark script:
   - Test query suite
   - Timing measurements
   - Accuracy comparison
5. Run benchmarks and analyze results
