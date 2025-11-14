# Anti-Hallucination Validation Layer Research

**Date:** 2025-11-14
**Author:** Claude Code
**Status:** Implemented

## Problem Statement

The current validation layer in the orchestrator is a stub that only checks basic response properties (length, error keywords). It does not prevent hallucinations when the LLM generates responses without supporting data.

### Observed Issue

Query: "what concerts are going on in baltimore"
- Web search attempted but returned 0 results
- LLM generated plausible but completely fabricated concert listings:
  - "The National at Rams Head Live (March 15th)"
  - "Trey Anastasio Band at The Lyric (March 16th)"
  - Specific dates, venues, and artist names - all hallucinated

### Current Validation (Inadequate)

```python
async def validate_node(state: OrchestratorState) -> OrchestratorState:
    # Basic validation for Phase 1
    if not state.answer or len(state.answer) < 10:
        state.validation_passed = False
    elif len(state.answer) > 2000:
        state.validation_passed = False
    elif "error" in state.answer.lower() and "sorry" in state.answer.lower():
        state.validation_passed = False
    else:
        state.validation_passed = True
```

**Validation time:** ~0.000011 seconds (essentially a no-op)

## Solution: Multi-Layer Anti-Hallucination Validation

### Layer 1: Data Source Verification
**Check if response claims match retrieved data**

- If `retrieved_data` is empty or minimal, flag any specific factual claims
- Pattern detection: dates, names, numbers, specific events
- Cross-reference claims against `state.citations`

### Layer 2: LLM-Based Fact Checking
**Use a second LLM call to verify the response**

Prompt:
```
You are a fact-checking assistant. Review this response and determine if it contains made-up information.

Original Query: {query}
Retrieved Data: {retrieved_data}
Generated Response: {response}

Does this response contain specific facts (dates, names, events, numbers) that are NOT present in the Retrieved Data?
Answer with JSON: {"contains_hallucinations": true/false, "reason": "explanation"}
```

### Layer 3: Uncertainty Markers
**Ensure LLM acknowledges when it lacks information**

When `retrieved_data` is empty or search fails:
- Response should contain uncertainty markers
- Acceptable: "I don't have current information", "I cannot find...", "I recommend checking..."
- Unacceptable: Specific facts, dates, names without caveats

### Layer 4: Citation Validation
**Every factual claim must have a citation**

- Track which facts came from which sources
- Flag uncited specific claims
- Require data provenance

## Implementation Strategy

### Phase 1: Immediate (Implemented)
1. Enhance synthesis prompt when no data retrieved
2. Add LLM-based fact checking as validation step
3. Implement pattern detection for specific facts
4. Update validation to take ~1-2 seconds (thorough checking)

### Phase 2: Future Enhancements
1. Add confidence scores to retrieved data
2. Implement citation tracking throughout pipeline
3. Add user feedback loop for hallucination detection
4. Train/fine-tune models on non-hallucination

## Expected Behavior After Fix

### Query: "what concerts are going on in baltimore"
**With no web search results:**

Response should be:
```
I don't have access to current concert information for Baltimore. I recommend checking:
- Ticketmaster for upcoming events
- Venue websites like Rams Head Live, The Lyric, or Pier Six Pavilion
- Local event calendars

Would you like me to help you find contact information for these venues?
```

**With web search results:**
```
Based on current information:
1. [Artist] at [Venue] on [Date] (Source: Ticketmaster)
2. [Artist] at [Venue] on [Date] (Source: Venue website)

[Include actual retrieved data with citations]
```

## Performance Considerations

- Current validation: ~0.00001s (useless)
- Target validation: 1-2s (thorough)
- Acceptable trade-off: Slightly slower response for accuracy

Total orchestrator response time budget: 5-7 seconds
- Classify: 0.5-1s
- Retrieve: 0.2-2s (depends on data source)
- Synthesize: 2-3s
- **Validate: 1-2s** (new)
- Finalize: <0.1s

## Metrics to Track

1. **Hallucination Rate**: % of responses flagged by validation
2. **False Positive Rate**: Valid responses incorrectly flagged
3. **User Corrections**: Times user reports incorrect information
4. **Validation Time**: P50, P95, P99 latencies
5. **Data Coverage**: % queries with supporting data vs LLM-only

## References

- LangGraph conditional edges for validation retry
- RAG best practices: always cite sources
- LLM hallucination detection research
- Production LLM safety layers (OpenAI, Anthropic)
