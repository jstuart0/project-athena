# V7 Benchmark Analysis: No Accuracy Improvement

**Date:** 2025-11-08
**Status:** Analysis Complete - V7 Failed
**Next Action:** Investigate root cause and create V8

---

## Executive Summary

V7 achieved **ZERO accuracy improvement** over V6 (48.7% unchanged) despite fixing the pre-classification routing bug. Speed improved slightly (40.5ms vs 42.9ms), but the core routing issues persist.

---

## Benchmark Results Comparison

| Version | Accuracy | Avg Latency | Key Changes |
|---------|----------|-------------|-------------|
| V1 | 48.7% | 0.1ms | Pattern-only baseline |
| V5 | 48.7% | 106.1ms | Hybrid + TinyLlama |
| V6 | 48.7% | 42.9ms | Pre-classification + fixes |
| **V7** | **48.7%** | **40.5ms** | **Corrected routing (no change)** |

### V7 Key Metrics

**Accuracy: 48.7%** (19/39 correct) - **NO CHANGE**
- Unambiguous: 9/15 (60.0%)
- Ambiguous: 1/12 (8.3%)
- Edge case: 4/7 (57.1%)

**Latency:**
- Average: 40.5ms (vs V6: 42.9ms - **5% improvement**)
- Median: 0.1ms
- Min: 0.0ms
- Max: 322.6ms
- P95: 322.4ms
- Unambiguous: 0.1ms avg
- Ambiguous: 104.9ms avg

**Speed Ranking:** #2 (only V1 pattern-only is faster)

---

## What V7 Fixed (In Code)

### Pre-classification Routing Correction

**V6 Bug (Line 126):**
```python
if any(pattern in q for pattern in ['best museum', 'good museum']):
    logger.info(f"🎨 Pre-classified: entertainment (best/good + museum)")
    return (IntentType.WEB_SEARCH, None, {"query": q})  # ❌ WRONG!
```

**V7 Fix (Line 126):**
```python
if any(pattern in q for pattern in ['best museum', 'good museum']):
    logger.info(f"🎨 Pre-classified: entertainment (best/good + museum)")
    return self._classify_entertainment(q)  # ✅ FIXED
```

### New Pre-classification Patterns Added

**Museums open today (Lines 152-155):**
```python
# V7: "museums open today" → entertainment
if 'museum' in q and ('open' in q or 'hour' in q or 'close' in q):
    logger.info(f"🎨 Pre-classified: entertainment (museum hours)")
    return self._classify_entertainment(q)
```

**Find me queries (Lines 157-161):**
```python
# V7: "find me" + food/dining → dining/location
if 'find me' in q or 'find a' in q:
    if any(food in q for food in ['pizza', 'coffee', 'restaurant', 'food']):
        logger.info(f"🍽️ Pre-classified: dining (find me + food)")
        return self._classify_location(q)
```

---

## What V7 Did NOT Fix (Benchmark Results)

### Queries Still Failing (Same as V6)

**"best museums" queries:**
- V6 Result: general ❌
- V7 Result: **time_date** ❌ (WORSE!)
- Expected: entertainment ✅

**"best museums in Baltimore":**
- V6 Result: general ❌
- V7 Result: **time_date** ❌ (WORSE!)
- Expected: entertainment ✅

**Other failures (unchanged):**
- "what day is it" → general (expected: time_date)
- "what's today's date" → general (expected: time_date)
- "directions to BWI" → general (expected: location)
- "best restaurants near me" → time_date (expected: dining)
- "museums open today" → time_date (expected: entertainment)
- "where should I eat" → time_date (expected: dining)
- "good seafood" → time_date (expected: dining)
- "find me pizza" → general (expected: dining)
- "find me a coffee shop" → general (expected: dining)

---

## Root Cause Analysis: Why V7 Failed

### Hypothesis #1: Pre-classification Returns Wrong Category Type

**What should happen:**
1. Pre-classification catches "best museums" (line 123)
2. Calls `self._classify_entertainment(q)` (line 126)
3. `_classify_entertainment()` matches 'museum' keyword (line 767)
4. Returns `(IntentType.ENTERTAINMENT, "entertainment", {...})`
5. Benchmark extracts "entertainment" as category

**What actually happens:**
1. Pre-classification catches "best museums" ✓
2. Calls `self._classify_entertainment(q)` ✓
3. `_classify_entertainment()` matches 'museum' keyword ✓
4. Returns `(IntentType.QUICK, "Top museums: BMA (free)...", None)` ❌
5. Benchmark extracts "Top museums: BMA..." as category ❌

**Problem:** `_classify_entertainment()` returns `IntentType.QUICK` with response text as category, not `IntentType.ENTERTAINMENT` with "entertainment" string.

### Hypothesis #2: Benchmark Category Extraction Issue

The benchmark may be extracting the category string from the second tuple element, but getting the actual response text instead of "entertainment".

**Need to verify:** How does the benchmark determine query category from the classifier result?

### Hypothesis #3: Pre-classification Not Actually Running

**Counter-evidence:** Latency is 0ms for "best museums" queries, indicating pattern matching (not LLM). If pre-classification was running and calling `_classify_entertainment()`, it should work.

**But:** V7 routes to `time_date` instead of `entertainment`, suggesting:
- Pre-classification might not be catching the pattern, OR
- `_classify_entertainment()` is returning `None`, OR
- The result is being overridden by something else

---

## Investigation Needed

### 1. Check Benchmark Category Extraction Logic (HIGH PRIORITY)

**File:** `tests/facade/benchmark_intent_classifiers.py`

**Question:** How does the benchmark extract the category from the classifier result tuple?

**Code to examine:**
```python
# How does benchmark compare expected vs actual category?
result = classifier.classify(query)
# What is result format?
# How is category extracted?
```

### 2. Trace V7 Execution for "best museums" (HIGH PRIORITY)

**Add debug logging to V7:**
- Log when pre-classification catches "best museum" pattern
- Log what `_classify_entertainment()` returns
- Log the final result tuple

**Test query:** "best museums"

**Expected logs:**
```
🎨 Pre-classified: entertainment (best/good + museum)
[_classify_entertainment] Matched 'museum' keyword
[_classify_entertainment] Returning: (IntentType.QUICK, "Top museums...", None)
```

### 3. Examine `_classify_entertainment()` Return Values (MEDIUM PRIORITY)

**Current code (line 777-782):**
```python
if 'museum' in q:
    if 'free' in q:
        return (IntentType.QUICK, "FREE museums...", None)
    elif 'aquarium' in q:
        return (IntentType.QUICK, "National Aquarium...", None)
    else:
        return (IntentType.QUICK, "Top museums...", None)
```

**Issue:** Returns `IntentType.QUICK` instead of `IntentType.ENTERTAINMENT`

**Expected behavior:** Should return a category that the benchmark recognizes as "entertainment"

---

## Possible Fixes for V8

### Option A: Fix `_classify_entertainment()` Return Type

**Change museum pattern returns from:**
```python
return (IntentType.QUICK, "Top museums...", None)
```

**To:**
```python
return (IntentType.ENTERTAINMENT, "entertainment", {"response": "Top museums..."})
```

**Pro:** Matches expected category format
**Con:** May break facade integration if it expects QUICK responses

### Option B: Add Direct Pattern to Pre-classification

**Instead of calling `_classify_entertainment(q)`, return direct entertainment category:**
```python
if any(pattern in q for pattern in ['best museum', 'good museum']):
    logger.info(f"🎨 Pre-classified: entertainment (best/good + museum)")
    return (IntentType.ENTERTAINMENT, "entertainment", None)
```

**Pro:** Simpler, avoids `_classify_entertainment()` complexity
**Con:** Loses specific museum responses

### Option C: Fix All Category Methods to Return Consistent Format

**Problem:** Different methods return different tuple formats:
- Some return `(IntentType.X, "category_name", {...})`
- Some return `(IntentType.QUICK, "response text", None)`

**Solution:** Standardize all methods to return `(IntentType, category_string, extra_data)` where category_string is ALWAYS the category name ("entertainment", "dining", etc.), not the response.

**Pro:** Consistent, predictable
**Con:** Large refactor, affects all classification methods

---

## Key Insights

### V7 Routing Fix Worked (Partially)

The pre-classification routing change from returning `WEB_SEARCH` to calling `_classify_entertainment()` DID work:
- V6: "best museums" → `general` (via WEB_SEARCH)
- V7: "best museums" → `time_date` (via `_classify_entertainment()` → wrong category extraction)

The fix successfully calls the right method, but the method returns the wrong category type.

### Speed Improvement Strategy Still Valid

**V7 maintained speed improvement:**
- V6: 42.9ms average
- V7: 40.5ms average (5% faster)
- Both ~60% faster than V5 (106.1ms)

Pre-classification approach is sound for speed. The accuracy issue is a category extraction/format problem, not a speed vs. accuracy tradeoff.

### Accuracy Ceiling May Be Architectural

**All hybrid versions stuck at 48.7%:**
- V1 (pattern-only): 48.7%
- V2 (hybrid + Llama 3.2:3b): 48.7%
- V5 (hybrid + TinyLlama): 48.7%
- V6 (hybrid improved): 48.7%
- V7 (corrected routing): 48.7%

**Only V3 (full LLM) achieved different result: 46.2% (worse)**

This suggests the pattern-based approach has hit its limits without better pattern coverage OR a fundamental change to how categories are returned.

---

## Next Steps

1. ✅ Document V7 findings (this file)
2. 🔄 **Investigate benchmark category extraction logic**
3. 🔄 **Add debug logging to V7 to trace "best museums" execution**
4. 📋 Based on findings, create V8 with appropriate fix:
   - If benchmark issue: Fix benchmark
   - If return type issue: Fix `_classify_entertainment()` and related methods
   - If pre-classification issue: Adjust pattern matching

---

## References

- V7 Implementation: `src/jetson/facade/airbnb_intent_classifier_v7_corrected_routing.py`
- V6 Analysis: `thoughts/shared/research/2025-11-08-v6-benchmark-analysis-speed-wins.md`
- Benchmark Script: `tests/facade/benchmark_intent_classifiers.py`
- Benchmark Results: `/tmp/intent_classifier_benchmark_v7.txt` (on Jetson)

---

## Lessons Learned

### What Worked

1. **Pre-classification routing fix:** Successfully calls `_classify_entertainment()` instead of returning `WEB_SEARCH`
2. **Speed optimization:** Maintained ~40ms average latency
3. **New patterns added:** Code is in place for "museums open today" and "find me" queries

### What Didn't Work

1. **Category return format:** `_classify_entertainment()` returns wrong tuple format for benchmark
2. **No accuracy gain:** Same 48.7% as V6 despite code fixes
3. **Worse routing for some queries:** "best museums" now routes to `time_date` instead of `general`

### Future Improvements (Post-V8)

1. **Standardize return tuples:** All `_classify_*()` methods should return consistent format
2. **Separation of concerns:** Classification (category) vs. response generation should be separate
3. **Better logging:** Add execution traces to understand classification flow
4. **Integration tests:** Test classification without benchmark to verify category extraction
