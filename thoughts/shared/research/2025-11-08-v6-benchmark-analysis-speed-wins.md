# V6 Benchmark Analysis: Speed Win, No Accuracy Gain

**Date:** 2025-11-08
**Status:** Research Complete
**Next Action:** Create V7 with corrected routing logic

---

## Executive Summary

V6 achieved a **60% speed improvement** over V5 (42.2ms vs 107.3ms average) but **no accuracy improvement** (still 48.7%). The pre-classification approach works but routes to wrong handlers.

---

## Benchmark Results Comparison

| Version | Accuracy | Avg Latency | Key Features |
|---------|----------|-------------|--------------|
| V1 | 48.7% | 0.0ms | Pattern-only baseline |
| V2 | 48.7% | 1009.0ms | Hybrid + Llama 3.2:3b (slow!) |
| V3 | 46.2% | 2393.7ms | Full LLM Llama 3.2:3b (slower!) |
| V4 | 12.8% | 1886.1ms | Full LLM TinyLlama (terrible) |
| V5 | 48.7% | 107.3ms | Hybrid + TinyLlama |
| **V6** | **48.7%** | **42.2ms** | **Pre-classification + TinyLlama** |

### V6 Key Metrics

**Accuracy: 48.7%** (19/39 correct)
- Unambiguous: 9/15 (60.0%)
- Ambiguous: 1/12 (8.3%)
- Edge case: 4/7 (57.1%)

**Latency:**
- Average: 42.2ms
- Median: 0.1ms
- Min: 0.0ms
- Max: 336.2ms
- P95: 334.0ms
- Unambiguous: 0.1ms avg
- Ambiguous: 109.0ms avg (pattern hits are instant!)

**Speed Ranking:** #2 (only V1 pattern-only is faster)

---

## What V6 Fixed (Partially)

V6's pre-classification caught queries that were failing to `time_date` and prevented the worst errors:

### Queries That Changed Behavior

**"best museums" and "best museums in Baltimore":**
- V5 Result: `time_date` ❌ (completely wrong)
- V6 Result: `general` ⚠️ (less wrong, but still not `entertainment`)
- Expected: `entertainment` ✅

**Impact:** Pre-classification prevented routing to a completely irrelevant handler (time_date), but still didn't route to the correct handler (entertainment).

### Queries That Still Fail (No Change from V5)

**Date/Time Pattern Failures:**
- "what day is it" → `general` (expected: `time_date`)
- "what's today's date" → `general` (expected: `time_date`)

**Location Pattern Failures:**
- "directions to BWI" → `general` (expected: `location`)
- "what's the address" → `general` (expected: `location`)

**Dining Query Failures:**
- "best restaurants near me" → `time_date` (expected: `dining`)
- "where should I eat" → `time_date` (expected: `dining`)
- "where can I get good crab cakes" → `time_date` (expected: `dining`)
- "good seafood" → `time_date` (expected: `dining`)

**Entertainment Failures:**
- "museums open today" → `time_date` (expected: `entertainment`)

**Find Queries:**
- "find me pizza" → `general` (expected: `dining`)
- "find me a coffee shop" → `general` (expected: `dining`)

---

## Why V6's Fixes Didn't Work

### Issue #1: Pre-classification Returns Wrong Intent Type

In V6's `_pre_classify_high_confidence()`, when catching "best museums":

```python
# "best museums" / "good museums" → entertainment
if any(pattern in q for pattern in ['best museum', 'good museum', 'best attraction',
                                      'good attraction']):
    logger.info(f"🎨 Pre-classified: entertainment (best/good + museum)")
    return (IntentType.WEB_SEARCH, None, {"query": q})  # ❌ WRONG!
```

**Problem:** Returns `IntentType.WEB_SEARCH` (shows as "general" in benchmark) instead of calling `_classify_entertainment(q)`.

**Fix for V7:** Should return the result of the appropriate classification method:
```python
return self._classify_entertainment(q)
```

### Issue #2: Date/Time Patterns Not Actually Added

V6 claims to add "what day is it" and "what's today's date" to time_date patterns (line 374), but these patterns still fail.

**Hypothesis:** These patterns may not be matching due to case sensitivity or the queries falling through to a different classification path before hitting the pattern check.

**Investigation needed:** Check if patterns are being checked correctly in the classification flow.

### Issue #3: Location/Directions Patterns Not Matching

V6 added "directions to", "directions for", "how do i reach" to location patterns (line 593), but "directions to BWI" still fails.

**Hypothesis:** Similar to date/time, these patterns may not be reached in the classification flow, or there's a case sensitivity issue.

---

## Key Insight: Speed Improvement Strategy Works!

The **pre-classification approach is sound** and delivers significant speed improvements:

**Before Pre-classification (V5):**
- Ambiguous queries: 294.8ms avg (hit LLM)
- Overall: 107.3ms avg

**After Pre-classification (V6):**
- Ambiguous queries: 109.0ms avg (many bypass LLM!)
- Overall: 42.2ms avg

**Speed gain: 60% reduction in average latency**

This proves that **identifying high-confidence patterns early** and bypassing ambiguity detection + LLM is the right strategy.

---

## V7 Requirements

Based on V6 analysis, V7 must fix:

### 1. Pre-classification Routing (HIGH PRIORITY)

**Current bug:** Pre-classification returns wrong IntentType

**Fix:**
```python
# "best museums" / "good museums" → entertainment
if any(pattern in q for pattern in ['best museum', 'good museum']):
    logger.info(f"🎨 Pre-classified: entertainment (best/good + museum)")
    return self._classify_entertainment(q)  # ✅ Call the right method

# "best restaurants" → dining
if any(pattern in q for pattern in ['best restaurant', 'good restaurant']):
    logger.info(f"🍽️ Pre-classified: dining (best/good + restaurant)")
    return self._classify_location(q)  # ✅ Call location (which handles dining)

# "best way to" + location → location
if any(pattern in q for pattern in ['best way to get to', 'fastest way to']):
    logger.info(f"🗺️ Pre-classified: location (best way to)")
    return self._classify_transportation(q) or self._classify_location(q)
```

### 2. Debug Date/Time Pattern Matching (HIGH PRIORITY)

**Failing queries:**
- "what day is it"
- "what's today's date"

**Action:** Add logging to see if patterns are being checked, and verify pattern matching logic.

### 3. Debug Location Pattern Matching (MEDIUM PRIORITY)

**Failing queries:**
- "directions to BWI"
- "what's the address"

**Action:** Similar debugging to date/time patterns.

### 4. Add More Pre-classification Patterns (MEDIUM PRIORITY)

Based on remaining failures, add pre-classification for:

**Dining queries:**
- "where should I eat" → dining
- "where can I get" + food → dining
- "good" + food type → dining

**Entertainment:**
- "museums open today" → entertainment

**Find queries:**
- "find me" + food type → dining
- "find me a" + venue type → dining/location

---

## Expected V7 Results

If fixes work correctly:

**Accuracy improvement:**
- Current: 19/39 (48.7%)
- V7 Target: 24-26/39 (61.5-66.7%)
- Gain: +5-7 queries fixed

**Speed:**
- Maintain or improve on V6's 42.2ms average
- More pre-classification = faster

**Queries we should fix in V7:**
1. "best museums" (2 queries) → entertainment ✅
2. "what day is it" → time_date ✅
3. "what's today's date" → time_date ✅
4. "directions to BWI" → location ✅
5. "where should I eat" → dining ✅

**Minimum expected:** 24/39 = 61.5% accuracy

---

## Lessons Learned

### What Worked

1. **Pre-classification for speed:** 60% latency reduction is huge!
2. **Hybrid approach:** Pattern-first, LLM fallback is the right architecture
3. **TinyLlama over Llama 3.2:3b:** 95% faster, same accuracy

### What Didn't Work

1. **Simply adding patterns isn't enough:** Must verify patterns are actually being checked
2. **Pre-classification must route correctly:** Returning wrong IntentType defeats the purpose
3. **Need better debugging:** Should log which classification path each query takes

### Future Improvements (Post-V7)

1. **Add classification path logging:** Track pattern hits, ambiguity checks, LLM calls
2. **Pattern coverage analysis:** Identify which patterns are never hit
3. **A/B testing framework:** Compare versions on real user queries
4. **Fallback confidence scoring:** Let patterns have confidence scores, fall back to LLM if low

---

## References

- V6 Implementation: `src/jetson/facade/airbnb_intent_classifier_v6_hybrid_improved.py`
- Benchmark Script: `tests/facade/benchmark_intent_classifiers.py`
- Benchmark Results: `/tmp/intent_classifier_benchmark.txt` (on Jetson)
- Real Impact Analysis: `analysis/intent_classification_real_impact.md`

---

## Next Steps

1. ✅ Document V6 findings (this file)
2. 🔄 Create V7 with corrected routing logic
3. 🔄 Run V7 benchmark
4. 📋 Analyze V7 results and iterate if needed
5. 📋 Consider V8 with additional pre-classification patterns based on V7 results
