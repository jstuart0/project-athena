# LLM-Based Intent Classification for Orchestrator

**Date:** 2025-11-17
**Status:** In Progress (Phase 1 Complete)
**Priority:** High
**Estimated Effort:** 4-6 hours

## Problem Statement

Currently, the Orchestrator uses pattern-based keyword matching for intent classification (WEATHER, SPORTS, AIRPORTS, GENERAL, HOME). This approach has limitations:

- Limited flexibility for ambiguous queries
- Misses contextual nuances (e.g., "football schedule" wasn't recognized as SPORTS until patterns were expanded)
- Requires manual pattern updates for new query types
- No confidence scoring for routing decisions

The Gateway already uses LLM-based classification (phi3:mini) to route between orchestrator and ollama with good results (50-200ms latency). We should apply a similar approach to the Orchestrator's intent classification.

## Current State

**Gateway's LLM Classification** (src/gateway/main.py:340-398):
- Uses phi3:mini model via Ollama API
- Binary classification: "athena" vs "general"
- Low temperature (0.1) for consistency
- Limited tokens (num_predict: 10) for speed
- Falls back to keyword matching on failure
- Target latency: 50-200ms

**Orchestrator's Current Classification** (src/orchestrator/main.py:350-421):
- Pattern-based keyword matching
- Categories: WEATHER, SPORTS, AIRPORTS, GENERAL, HOME, GREETING
- Immediate response (0ms overhead)
- No confidence scoring
- Hard-coded patterns require manual updates

## Goals

1. **Add LLM-based intent classification** to Orchestrator while maintaining pattern-based fallback
2. **Multi-category classification** (not binary like Gateway)
3. **Confidence scoring** for routing decisions
4. **Maintain low latency** (target: 50-200ms added latency)
5. **Graceful degradation** when LLM is unavailable

## Technical Approach

### 1. Create New Classification Function

Add `classify_intent_llm()` function to Orchestrator similar to Gateway's implementation:

```python
async def classify_intent_llm(query: str) -> Tuple[IntentCategory, float]:
    """
    Use LLM to classify query intent with confidence scoring.

    Returns:
        Tuple of (IntentCategory, confidence_score)

    Confidence:
        - 1.0: High confidence (explicit intent)
        - 0.7-0.9: Medium confidence (contextual clues)
        - 0.3-0.6: Low confidence (ambiguous)
        - Falls back to pattern matching if < 0.3
    """
    prompt = f"""Classify this query into ONE category:

Query: "{query}"

Categories:
- WEATHER: Weather conditions, forecasts, temperature
- SPORTS: Sports scores, schedules, teams, games (Ravens, Orioles, etc.)
- AIRPORTS: Flight info, airport status, delays (BWI, DCA, IAD, etc.)
- HOME: Smart home control (lights, switches, temperature, devices)
- GREETING: Greetings, introductions, casual conversation
- GENERAL: General knowledge, facts, explanations, anything else

Respond in this format:
CATEGORY: <category_name>
CONFIDENCE: <0.0-1.0>
REASON: <brief explanation>"""

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "phi3:mini",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 50  # Need more tokens for structured response
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            llm_response = result.get("response", "").strip()

            # Parse structured response
            category, confidence = _parse_classification_response(llm_response)

            logger.info(f"LLM classified '{query}' as {category} (confidence: {confidence:.2f})")
            return (category, confidence)

    except Exception as e:
        logger.error(f"LLM classification failed: {e}, falling back to pattern matching")
        # Fallback to existing keyword-based classification
        category = classify_intent_keywords(query)
        return (category, 0.5)  # Medium confidence for fallback
```

### 2. Response Parser

Add helper function to parse LLM's structured response:

```python
def _parse_classification_response(response: str) -> Tuple[IntentCategory, float]:
    """Parse LLM classification response into category and confidence."""
    try:
        # Extract category
        category_match = re.search(r'CATEGORY:\s*(\w+)', response, re.IGNORECASE)
        category_str = category_match.group(1).upper() if category_match else None

        # Extract confidence
        confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5

        # Map to IntentCategory enum
        category_map = {
            "WEATHER": IntentCategory.WEATHER,
            "SPORTS": IntentCategory.SPORTS,
            "AIRPORTS": IntentCategory.AIRPORTS,
            "HOME": IntentCategory.HOME,
            "GREETING": IntentCategory.GREETING,
            "GENERAL": IntentCategory.GENERAL,
        }

        category = category_map.get(category_str, IntentCategory.GENERAL)

        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))

        return (category, confidence)

    except Exception as e:
        logger.warning(f"Failed to parse LLM response: {e}")
        return (IntentCategory.GENERAL, 0.3)  # Low confidence fallback
```

### 3. Integration with LangGraph State

Modify the `classify_intent` node in the LangGraph workflow:

```python
async def classify_intent(state: ConversationState) -> ConversationState:
    """
    Classify user query intent using LLM with pattern-based fallback.

    Uses phi3:mini for intelligent classification with confidence scoring.
    Falls back to keyword matching if LLM unavailable or low confidence.
    """
    query = state.query
    query_lower = query.lower()

    # Try LLM classification first
    category, confidence = await classify_intent_llm(query)

    # If low confidence, verify with pattern matching
    if confidence < 0.6:
        pattern_category = classify_intent_keywords(query)

        # If pattern matching disagrees strongly, log and use pattern result
        if pattern_category != category:
            logger.warning(
                f"LLM classified as {category} (confidence: {confidence:.2f}), "
                f"but patterns suggest {pattern_category}. Using pattern result."
            )
            category = pattern_category
            confidence = 0.7  # Pattern matching has medium confidence

    state.intent = category
    state.metadata["classification_method"] = "llm" if confidence >= 0.6 else "pattern"
    state.metadata["classification_confidence"] = confidence

    logger.info(f"Final classification: {category} (confidence: {confidence:.2f})")
    return state
```

### 4. Feature Flag for Gradual Rollout

Add admin configuration to enable/disable LLM classification:

```python
# In admin database, add to admin_configs table:
INSERT INTO admin_configs (config_key, config_value, description)
VALUES (
    'enable_llm_intent_classification',
    'false',
    'Use LLM (phi3:mini) for intent classification instead of pattern matching'
);

# In orchestrator main.py:
ENABLE_LLM_CLASSIFICATION = get_admin_config("enable_llm_intent_classification", default=False)

async def classify_intent(state: ConversationState) -> ConversationState:
    """Classify intent with optional LLM enhancement."""
    query = state.query

    if ENABLE_LLM_CLASSIFICATION:
        category, confidence = await classify_intent_llm(query)
    else:
        category = classify_intent_keywords(query)
        confidence = 0.7  # Fixed confidence for pattern matching

    state.intent = category
    state.metadata["classification_confidence"] = confidence
    return state
```

## Performance Considerations

**Expected Latency:**
- LLM classification: 50-200ms (based on Gateway metrics)
- Pattern matching: 0-1ms
- Total added latency: 50-200ms per query

**Optimization Strategies:**
1. Use phi3:mini (not phi3:mini-q8) for fastest inference
2. Limit num_predict to 50 tokens (structured response is short)
3. Set low temperature (0.1) for consistency
4. Cache common queries (optional future enhancement)
5. Feature flag allows disabling if latency is problematic

**Error Handling:**
- Timeout after 5 seconds
- Graceful fallback to pattern matching
- Log all LLM failures for monitoring
- No user-facing errors (always returns a classification)

## Testing Strategy

### Unit Tests

```python
# tests/test_llm_classification.py
import pytest
from orchestrator.main import classify_intent_llm, _parse_classification_response

@pytest.mark.asyncio
async def test_weather_classification():
    """Test weather query classification."""
    category, confidence = await classify_intent_llm("What's the weather today?")
    assert category == IntentCategory.WEATHER
    assert confidence > 0.7

@pytest.mark.asyncio
async def test_sports_classification():
    """Test sports query classification."""
    category, confidence = await classify_intent_llm("When do the Ravens play?")
    assert category == IntentCategory.SPORTS
    assert confidence > 0.7

@pytest.mark.asyncio
async def test_ambiguous_classification():
    """Test handling of ambiguous queries."""
    category, confidence = await classify_intent_llm("What do you think?")
    # Should default to GENERAL with medium-low confidence
    assert category in [IntentCategory.GENERAL, IntentCategory.GREETING]
    assert 0.3 <= confidence <= 0.8

def test_response_parser():
    """Test parsing LLM structured response."""
    response = """CATEGORY: WEATHER
CONFIDENCE: 0.95
REASON: Query asks about weather forecast"""

    category, confidence = _parse_classification_response(response)
    assert category == IntentCategory.WEATHER
    assert confidence == 0.95
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_end_to_end_classification():
    """Test full classification workflow in LangGraph state machine."""
    state = ConversationState(
        session_id="test-123",
        query="What's the Ravens score?",
        conversation_history=[]
    )

    # Run through classify_intent node
    state = await classify_intent(state)

    assert state.intent == IntentCategory.SPORTS
    assert "classification_confidence" in state.metadata
    assert state.metadata["classification_confidence"] > 0.6
```

### Manual Testing

1. **Test with known queries:**
   - "What's the weather?" → WEATHER
   - "Ravens game score?" → SPORTS
   - "BWI flight delays?" → AIRPORTS
   - "Turn on office lights" → HOME
   - "Hello Athena" → GREETING
   - "What is quantum physics?" → GENERAL

2. **Test edge cases:**
   - "Is it going to rain during the Ravens game?" (multi-intent)
   - "Turn on the weather channel" (HOME or WEATHER?)
   - Empty string
   - Very long query (>500 chars)

3. **Test fallback behavior:**
   - Stop Ollama service → should fall back to patterns
   - Send malformed response → should fall back gracefully
   - High latency (>5s) → should timeout and fall back

## Deployment Plan

### Phase 1: Implementation (2-3 hours)
1. Add `classify_intent_llm()` function to orchestrator/main.py
2. Add `_parse_classification_response()` helper
3. Add feature flag to admin database
4. Update `classify_intent` node to use LLM when enabled

### Phase 2: Testing (1-2 hours)
1. Write unit tests for classification logic
2. Write integration tests for LangGraph workflow
3. Manual testing with diverse queries
4. Measure latency impact

### Phase 3: Gradual Rollout (1 hour)
1. Deploy with feature flag disabled
2. Enable for 10% of queries (add sampling logic)
3. Monitor latency and accuracy metrics
4. Increase to 50%, then 100% if metrics are good

### Phase 4: Optimization (ongoing)
1. Monitor classification accuracy vs pattern matching
2. Tune prompt if needed
3. Add query caching if latency is problematic
4. Consider using smaller/faster model if available

## Success Criteria

1. **Accuracy**: LLM classification matches or exceeds pattern matching accuracy (>90% correct)
2. **Latency**: Added latency stays under 200ms for 95th percentile
3. **Reliability**: Fallback works seamlessly when LLM unavailable
4. **No Regressions**: All existing queries still work correctly
5. **Better Edge Cases**: Ambiguous queries handled better than pattern matching

## Risks and Mitigations

**Risk 1: Added Latency**
- Mitigation: Feature flag allows quick disable
- Mitigation: Set aggressive timeout (5s)
- Mitigation: Cache common queries (future)

**Risk 2: LLM Unavailability**
- Mitigation: Always fall back to pattern matching
- Mitigation: No user-facing errors
- Mitigation: Log failures for monitoring

**Risk 3: Incorrect Classifications**
- Mitigation: Confidence scoring allows verification
- Mitigation: Pattern matching can override low-confidence LLM results
- Mitigation: Extensive testing before rollout

**Risk 4: Increased Ollama Load**
- Mitigation: Monitor Ollama resource usage
- Mitigation: Feature flag allows quick disable
- Mitigation: Consider rate limiting if needed

## Future Enhancements

1. **Query Caching**: Cache LLM classifications for repeated queries
2. **A/B Testing**: Compare LLM vs pattern accuracy systematically
3. **Multi-Intent Detection**: Detect queries with multiple intents
4. **Confidence Tuning**: Adjust confidence thresholds based on metrics
5. **Model Upgrades**: Try newer/faster models as they become available

## References

- Gateway LLM classification: `src/gateway/main.py:340-439`
- Current pattern matching: `src/orchestrator/main.py:350-421`
- IntentCategory enum: `src/orchestrator/main.py:71-77`
- LangGraph workflow: `src/orchestrator/main.py:760-801`
- Admin config system: `src/shared/admin_config.py`

## Implementation Checklist

### Phase 1: Core Implementation (COMPLETED)
- [x] Add `classify_intent_llm()` function (src/orchestrator/main.py:298-362)
- [x] Add `_parse_classification_response()` helper (src/orchestrator/main.py:254-295)
- [x] Update `classify_node` to support LLM with feature flag (src/orchestrator/main.py:365-486)
- [x] Manual testing with diverse queries (weather, sports queries validated)
- [x] Deployed to Mac Studio with pattern-based fallback as default

### Phase 2: Testing & Rollout (PENDING)
- [ ] Add feature flag `enable_llm_intent_classification` to admin database
- [ ] Write unit tests for classification logic
- [ ] Write integration tests for LangGraph workflow
- [ ] Measure baseline latency with LLM enabled
- [ ] Enable feature flag for testing
- [ ] Monitor classification accuracy and latency
- [ ] Gradual rollout (10% → 50% → 100%)
- [ ] Document results in Wiki

### Notes
- Current deployment uses pattern-based classification (feature flag defaults to False)
- LLM classification available but disabled pending admin feature flag creation
- All metadata errors fixed - classification working correctly
- Git checkpoint created at tag: checkpoint-before-simplified-llm-classification
