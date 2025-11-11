# Post-Marathon: Guest Experience Validation Plan

**Date:** 2025-01-08
**Status:** PLANNED - Execute after marathon challenge complete
**Priority:** HIGH

## Context

After completing the marathon challenge (90%+ on 3 consecutive test suites), we need to pivot from edge-case accuracy to **real guest experience validation**.

## Key Insight

**Flat 90% accuracy is not the right metric for guest experience.**

### What Actually Matters

1. **Error Impact > Error Rate**
   - Critical errors (home automation misclassification): 0% tolerance
   - Acceptable errors (falls back to LLM): Guest never notices

2. **Real Query Distribution**
   - 40%: TIME/DATE + WEATHER
   - 30%: LOCATION + DINING
   - 15%: ENTERTAINMENT
   - 10%: HOME AUTOMATION (not yet tested!)
   - 5%: SPORTS/RECIPE/OUT_OF_AREA/GENERAL

3. **Response Quality**
   - Does guest get useful answer even if category wrong?
   - LLM fallback quality not yet measured

## Post-Marathon Validation Plan

### Phase A: Measure What Matters (1-2 hours)

1. **LLM Fallback Quality Test**
   - Take 100 "failed" classifications from suite #3
   - Run through full LLM pipeline
   - Measure: Did guest get correct/useful answer?
   - Expected: 90%+ of "failures" still get good answers

2. **Critical Error Analysis**
   - Review all suite #2 failures (90.5% = 101 failures)
   - Identify any home automation misclassifications
   - Identify local resource → general misses
   - Target: Zero critical errors

3. **Category-Weighted Scoring**
   - Re-score suite #2 with real-world weights:
     - TIME/DATE: 2x weight (20% of queries)
     - WEATHER: 2x weight (20% of queries)
     - LOCATION: 2x weight (15% of queries)
     - DINING: 2x weight (15% of queries)
     - ENTERTAINMENT: 1.5x weight (15% of queries)
     - SPORTS: 1x weight (5% of queries)
     - RECIPE: 1x weight (5% of queries)
     - OUT_OF_AREA: 0.5x weight (2.5% of queries)
     - GENERAL: 0.5x weight (2.5% of queries)
   - Expected: V38 scores 93%+ weighted

### Phase B: Real Guest Query Suite (2-3 hours)

4. **Suite #5: Actual Airbnb Guest Patterns**
   - Research: What do Airbnb guests actually ask?
   - Categories:
     - Morning: "what time is it", "weather", "coffee nearby"
     - Planning: "things to do", "restaurants", "how to get to X"
     - Evening: "nightlife", "late night food", "uber to BWI"
     - In-rental: "how to use thermostat", "wifi password", "checkout time"
   - 500 queries weighted toward high-frequency categories

5. **Home Automation Query Suite**
   - NEW category: HOME_CONTROL
   - "turn on bedroom lights"
   - "set thermostat to 68"
   - "close the blinds"
   - "dim the living room"
   - Target: 100% accuracy (zero tolerance for errors)

### Phase C: Production Readiness (1-2 hours)

6. **Integration Testing**
   - Test with actual voice pipeline (STT → Intent → LLM → TTS)
   - Measure end-to-end latency
   - Validate Home Assistant integration
   - Test in real environment (office)

7. **Deployment Validation**
   - Deploy to test zone
   - Real-world usage for 24-48 hours
   - Log all queries and classifications
   - Measure guest satisfaction (if testable)

## Success Criteria (Post-Marathon)

### Minimum Viable Product
- ✅ 95%+ accuracy on high-frequency queries (time/weather/local)
- ✅ 100% accuracy on home automation (zero critical errors)
- ✅ <100ms end-to-end response time
- ✅ LLM fallback handles 90%+ of edge cases gracefully

### Production Ready
- ✅ All MV criteria met
- ✅ Real-world testing validates performance
- ✅ No critical errors in 48-hour test period
- ✅ Guest feedback positive (if available)

## Implementation Notes

**After marathon complete:**
1. Save all suite results (1, 2, 3, 4+) for comparison
2. Pick best version (likely V38 or final marathon version)
3. Run validation plan phases A, B, C
4. If validation passes → deploy to production
5. If validation fails → iterate on critical issues only

## Expected Outcome

**Hypothesis:** V38 (90.5% on suite #2) is already production-ready for real guest experience, even though it only scores 68-70% on edge-case suite #3.

**Test:** Post-marathon validation will prove or disprove this hypothesis.

**Timeline:** 4-6 hours total for full validation after marathon complete.

---

**Status:** Ready to execute after marathon challenge completion
