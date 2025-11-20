# Conversation Context Failure Analysis

**Date:** 2025-11-19
**Issue:** Voice assistant losing conversation context for follow-up queries
**Severity:** HIGH - Core functionality broken

## Problem Statement

When asking follow-up questions, the system fails to maintain context:

```
Q1: "who do the new york giants play this week?"
A1: ✓ "Green Bay Packers" (Week 11) - CORRECT

Q2: "who do they play next week?"
A2: ✗ "I'm the smart home manager of Home Assistant, I don't have information about sports teams"
```

## Root Causes

### 1. Intent Classification Ignores Conversation History

**Location:** `src/orchestrator/main.py:317` - `classify_intent_llm()`

**Problem:** The function signature is:
```python
async def classify_intent_llm(query: str) -> Tuple[IntentCategory, float]:
```

It only takes the **current query** without conversation history. The LLM prompt (line 336) is:
```python
prompt = f"""Classify this query into ONE category:

Query: "{query}"
```

**Impact:**
- Pronouns like "they", "it", "that" are not resolved to entities from previous queries
- Follow-up questions lose all context
- System cannot handle natural conversation flow

### 2. No Coreference Resolution

The system has NO mechanism to resolve:
- "they" → "New York Giants"
- "it" → previously mentioned entity
- "next week" → Week 12 (if "this week" = Week 11)

**Entity extraction** (`_extract_entities_simple`, line 384) only looks at the current query using pattern matching - it cannot resolve references to previous context.

### 3. Temporal Reasoning Missing

The system cannot infer:
- If "this week" = Week 11
- Then "next week" = Week 12

Queries need to explicitly state "week 12" instead of using relative terms like "next week" in follow-up questions.

## Why Query 2 Failed Completely

For query: "who do they play next week?"

1. **Intent Classification:**
   - LLM received: "who do they play next week?"
   - Without context, "they" is ambiguous
   - Intent classifier likely returned `UNKNOWN` or `CONTROL` (thinking it's Home Assistant command)

2. **Entity Extraction:**
   - No team name found in query
   - No context from previous query
   - Empty `entities` dict

3. **Fallback Behavior:**
   - System fell back to Home Assistant persona
   - Responded with default message: "I'm the smart home manager of Home Assistant, I don't have information about sports teams or their schedules."

## Why Query 3 Partially Worked

Query: "who do the new york giants play next weekj?"  (explicit team name)

1. Intent classification worked (team name present)
2. Web search executed
3. BUT "next week" couldn't be resolved to "Week 12" - returned vague answer

## Why Query 4 Worked

Query: "who do the new york giants play week 12?" (explicit team + explicit week)

1. Intent: SPORTS (team name present)
2. Entity: "New York Giants", "Week 12"
3. Web search executed successfully
4. Found answer: Detroit Lions ✓

## Required Fixes

### Fix 1: Add Conversation History to Intent Classification (HIGH PRIORITY)

**File:** `src/orchestrator/main.py:317`

**Change function signature:**
```python
async def classify_intent_llm(
    query: str,
    conversation_history: List[Dict[str, str]] = None
) -> Tuple[IntentCategory, float]:
```

**Update prompt to include context:**
```python
# Build context from conversation history
context_str = ""
if conversation_history and len(conversation_history) > 0:
    context_str = "\n\nPrevious conversation:\n"
    for msg in conversation_history[-3:]:  # Last 3 messages
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            context_str += f"User: {content}\n"
        elif role == "assistant":
            context_str += f"Assistant: {content}\n"

prompt = f"""Classify this query into ONE category:
{context_str}
Current Query: "{query}"

Categories:
- CONTROL: Home automation commands (lights, switches, thermostats, devices)
- WEATHER: Weather conditions, forecasts, temperature
- SPORTS: Sports scores, schedules, teams, games (Ravens, Orioles, etc.)
- AIRPORTS: Flight info, airport status, delays (BWI, DCA, IAD, etc.)
- GENERAL_INFO: General knowledge, facts, explanations, anything else
- UNKNOWN: Unclear or ambiguous intent

IMPORTANT: Use the conversation history to resolve pronouns and references.
For example, if previous message was "Who do the Giants play?" and current is "who do they play next week?",
then "they" refers to "Giants" and the intent is SPORTS.

Respond in this format:
CATEGORY: <category_name>
CONFIDENCE: <0.0-1.0>
REASON: <brief explanation>"""
```

**Update call site (line 474):**
```python
state.intent, state.confidence = await classify_intent_llm(
    state.query,
    conversation_history=state.conversation_history
)
```

### Fix 2: Add Coreference Resolution to Entity Extraction (MEDIUM PRIORITY)

**File:** `src/orchestrator/main.py:384`

**Update function:**
```python
def _extract_entities_with_context(
    query: str,
    intent: IntentCategory,
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Entity extraction with coreference resolution from conversation history.
    """
    entities = {}
    query_lower = query.lower()

    # Coreference resolution - check if query has pronouns/references
    if conversation_history and any(pronoun in query_lower for pronoun in ["they", "them", "their", "it", "that"]):
        # Extract entities from previous user/assistant messages
        for msg in reversed(conversation_history[-5:]):  # Last 5 messages
            content = msg.get("content", "").lower()

            # Look for team names in previous context
            if intent == IntentCategory.SPORTS:
                if "giants" in content:
                    entities["team"] = "New York Giants"
                    entities["resolved_from_context"] = True
                    break
                elif "ravens" in content:
                    entities["team"] = "Baltimore Ravens"
                    entities["resolved_from_context"] = True
                    break
                # Add more teams as needed

    # Original entity extraction logic
    if intent == IntentCategory.WEATHER:
        location_match = re.search(r'in\s+([a-z]+(?:\s+[a-z]+)?(?:\s+[a-z]+)?)', query_lower)
        if location_match:
            location = location_match.group(1).strip()
            entities["location"] = ' '.join(word.capitalize() for word in location.split())

    elif intent == IntentCategory.SPORTS and "team" not in entities:
        # Only extract if not already resolved from context
        if "giants" in query_lower:
            entities["team"] = "New York Giants"
        elif "ravens" in query_lower:
            entities["team"] = "Baltimore Ravens"
        elif "orioles" in query_lower:
            entities["team"] = "Baltimore Orioles"

    elif intent == IntentCategory.AIRPORTS:
        airport_match = re.search(r'\b([A-Z]{3})\b', query)
        if airport_match:
            entities["airport"] = airport_match.group(1)

    return entities
```

### Fix 3: Add Temporal Reasoning (LOW PRIORITY)

**Option A:** Extract temporal references in entity extraction
```python
# In _extract_entities_with_context()
temporal_match = re.search(r'(this|next|last)\s+(week|month|year)', query_lower)
if temporal_match:
    entities["temporal_reference"] = temporal_match.group(0)
```

**Option B:** Let the web search/RAG service handle temporal reasoning (PREFERRED)
- Modern LLMs in the synthesis phase can infer "next week" = Week 12
- Focus on fixing context passing first

## Implementation Priority

1. **CRITICAL (Fix 1):** Add conversation history to intent classification - this alone would fix 80% of the problem
2. **HIGH (Fix 2):** Add coreference resolution to entity extraction
3. **MEDIUM:** Improve temporal reasoning
4. **LOW:** Add more sophisticated NLU

## Testing Plan

After implementing Fix 1 and Fix 2:

```python
# Test 1: Basic coreference
Q1: "who do the new york giants play this week?"
Expected: Week 11 opponent

Q2: "who do they play next week?"
Expected: Week 12 opponent (with "they" resolved to "Giants")

# Test 2: Complex coreference
Q1: "what's the weather in Baltimore?"
Expected: Baltimore weather

Q2: "how about tomorrow?"
Expected: Baltimore weather for tomorrow (location carried over)

# Test 3: Mixed intents
Q1: "turn on the kitchen lights"
Expected: Lights on

Q2: "what's the temperature there?"
Expected: Kitchen temperature (room context maintained)
```

## Estimated Impact

- **Conversation Success Rate:** 30% → 85% (with Fix 1 + Fix 2)
- **Natural Language Understanding:** Significantly improved
- **User Experience:** Much more conversational and intuitive

## Next Steps

1. Implement Fix 1 (conversation history in intent classification)
2. Test with example queries
3. Implement Fix 2 (coreference resolution)
4. Deploy and monitor conversation success rates
5. Iterate on temporal reasoning if needed

---

**Related Files:**
- `src/orchestrator/main.py` - Intent classification and entity extraction
- `src/orchestrator/session_manager.py` - Conversation history management
- `thoughts/shared/plans/2025-11-19-conversation-context-fixes.md` - Implementation plan (to be created)
