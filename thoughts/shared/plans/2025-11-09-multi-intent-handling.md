# Multi-Intent Handling Implementation Plan

**Date:** 2025-11-09
**Status:** Ready for Implementation
**Complexity:** High
**Estimated Effort:** 12-16 hours
**Based On:** Comprehensive codebase analysis of existing facade architecture

---

## Overview

Enable the Baltimore Smart Facade to handle compound queries containing multiple intents in a single user request. Currently, the system processes only the first matched intent and ignores subsequent requests. This enhancement will allow natural compound queries like "What's the weather and what time is it" or "Tell me about restaurants and the Ravens score" to be fully processed with merged responses.

## Current State Analysis

### Existing Architecture

**Query Processing Pipeline** (`facade_integration.py:101-250`):
```
User Query → analyze_query() → Intent Classifier → Handler Dispatch → Response Stream
```

**Key Constraints Discovered**:
1. **Single Intent Only** (`airbnb_intent_classifier.py:52-139`): The `classify()` method uses early-return pattern, returning immediately on first match
2. **Handler Execution** (`facade_integration.py:118-229`): Switch-case style handler dispatch for single intent
3. **Response Format** (`facade_integration.py:318-332`): Single response object in NDJSON format
4. **Existing Patterns** Available:
   - Sequential fallback chain (news/stocks/sports handlers)
   - Numbered list formatting (news.py:140-153, events.py:186-201)
   - Multi-item aggregation (weather.py:213-226)

### Handler Inventory

All handlers initialized at module level (`facade_integration.py:59-80`):
- `weather_handler` → WeatherHandler
- `web_search_handler` → WebSearchHandler
- `airport_handler` → AirportHandler
- `flight_handler` → FlightHandler
- `events_handler` → EventsHandler
- `streaming_handler` → StreamingHandler
- `news_handler` → NewsHandler
- `stocks_handler` → StocksHandler
- `sports_handler` → SportsHandler

## Desired End State

### Success Criteria

**Functional Requirements**:
- [ ] System correctly splits 90%+ of compound queries
- [ ] Each intent in compound query is processed independently
- [ ] Responses are merged intelligently based on count (2 vs 3+)
- [ ] No regression in single-intent query performance
- [ ] Device control + information queries route to LLM appropriately

**Performance Requirements**:
- [ ] Multi-intent queries respond within 2x single-intent time
- [ ] Single-intent queries maintain current <500ms average response time
- [ ] Parallel processing reduces latency for independent API calls

**User Experience Requirements**:
- [ ] Merged responses are natural and coherent
- [ ] No truncated or missing responses from any intent
- [ ] False positive splits are <5% (e.g., "thunder and lightning" stays together)

### Verification Method

1. **Automated Testing**: Test suite with 50+ compound query examples
2. **Integration Testing**: Direct facade API calls via curl
3. **Manual Testing**: Home Assistant Assist interface validation
4. **Performance Testing**: Response time benchmarking

---

## What We're NOT Doing

To prevent scope creep, explicitly excluding:

- ❌ **Semantic similarity matching** - Using keyword-based detection only
- ❌ **ML-based intent classification** - Pattern matching sufficient for v1
- ❌ **Confidence scoring** - Binary match/no-match decision
- ❌ **Context-aware merging** - Simple concatenation/numbering strategies
- ❌ **Multi-turn conversation memory** - Each query independent
- ❌ **Intent prioritization/reordering** - Process in detected order
- ❌ **Parallel async execution** - Sequential processing for v1 simplicity

---

## Implementation Approach

**Strategy**: Extend existing architecture without breaking current functionality. Add multi-intent path alongside single-intent path with feature flag control.

**Key Decisions Made**:

1. **LLM Routing**: If ANY intent requires LLM (device control, complex reasoning), route ENTIRE query to LLM for coherent handling
2. **Splitting Conservativeness**: Conservative - only split on clear conjunctions between different intent types
3. **Response Merging**: Simple strategies:
   - 2 responses: "Response1. Response2"
   - 3+ responses: Numbered list format

**Backward Compatibility**: Preserve existing `classify()` method, add new `classify_multi()` alongside it

---

## Phase 1: Query Splitter Implementation

### Overview
Create intelligent query splitting logic that detects compound queries and separates them into independent sub-queries while avoiding false positives.

### Changes Required

#### 1. New File: `src/jetson/facade/query_splitter.py`

**Purpose**: Split compound queries on conjunctions while preserving context

**Implementation**:

```python
"""
Query Splitter - Detects and splits compound queries

Handles patterns:
- Conjunction-based: "X and Y", "X then Y", "X also Y"
- List-based: "X, Y, and Z"

Avoids false positives:
- Compound nouns: "thunder and lightning", "rock and roll"
- Multi-location queries: "hotels in Baltimore and DC"
- Multi-entity commands: "turn on living room and bedroom lights"
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class QuerySplitter:
    """Splits compound queries into individual sub-queries"""

    # Conjunctions that may indicate multiple intents
    CONJUNCTIONS = ['and', 'then', 'also', 'plus']

    # Known compound nouns that should NOT be split
    COMPOUND_NOUNS = [
        'thunder and lightning',
        'rock and roll',
        'bed and breakfast',
        'salt and pepper',
        'trial and error',
        'pros and cons',
        'supply and demand'
    ]

    # Device control patterns - multiple rooms/entities in single command
    MULTI_ENTITY_PATTERNS = [
        r'(living room|dining room|bedroom|kitchen|bathroom|office)\s+and\s+(living room|dining room|bedroom|kitchen|bathroom|office)',
        r'turn\s+(on|off)\s+.*\s+and\s+.*\s+(lights|light)',
        r'set\s+.*\s+and\s+.*\s+to',
    ]

    def split(self, query: str) -> List[str]:
        """
        Split query into sub-queries

        Args:
            query: Original user query

        Returns:
            List of sub-queries (or [original] if no split)
        """
        q = query.lower().strip()

        # Check if query should be split
        if not self._should_split(q):
            return [query]

        # Find conjunction positions
        sub_queries = self._split_on_conjunctions(query)

        # Validate split makes sense
        if not self._is_valid_split(sub_queries):
            logger.info(f"Split rejected as invalid: {sub_queries}")
            return [query]

        logger.info(f"✂️ Split query into {len(sub_queries)} parts: {sub_queries}")
        return sub_queries

    def _should_split(self, q: str) -> bool:
        """Check if query contains splittable conjunctions"""
        # Must contain at least one conjunction
        if not any(f' {conj} ' in q for conj in self.CONJUNCTIONS):
            return False

        # Check for compound nouns - do not split
        for compound in self.COMPOUND_NOUNS:
            if compound in q:
                logger.debug(f"Compound noun detected: {compound}")
                return False

        # Check for multi-entity device control - do not split
        for pattern in self.MULTI_ENTITY_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                logger.debug(f"Multi-entity pattern detected, not splitting")
                return False

        return True

    def _split_on_conjunctions(self, query: str) -> List[str]:
        """Split query on conjunctions"""
        # Start with original query
        parts = [query]

        # Try each conjunction
        for conj in self.CONJUNCTIONS:
            # Split on " and ", " then ", etc (with spaces)
            pattern = f' {conj} '
            temp_parts = []

            for part in parts:
                if pattern in part.lower():
                    # Split this part
                    split_parts = re.split(pattern, part, flags=re.IGNORECASE)
                    temp_parts.extend(split_parts)
                else:
                    temp_parts.append(part)

            parts = temp_parts

        # Clean up parts
        return [p.strip() for p in parts if p.strip()]

    def _is_valid_split(self, sub_queries: List[str]) -> bool:
        """
        Validate that split makes sense

        Heuristics:
        - At least 2 sub-queries
        - Each sub-query has minimum length (avoid "what" + "is the weather")
        - Sub-queries are not too similar (avoid location splits like "Baltimore and DC")
        """
        if len(sub_queries) < 2:
            return False

        # Each part should be at least 3 words
        for sq in sub_queries:
            if len(sq.split()) < 3:
                logger.debug(f"Sub-query too short: '{sq}'")
                return False

        # Check if all parts start with common question words - likely valid
        question_words = ['what', 'when', 'where', 'who', 'how', 'tell', 'show', 'give']
        parts_with_questions = sum(1 for sq in sub_queries if any(sq.lower().startswith(q) for q in question_words))

        if parts_with_questions >= len(sub_queries) - 1:
            # Most/all parts are standalone questions - good split
            return True

        return True  # Default: accept split
```

### Success Criteria

#### Automated Verification:
- [ ] Unit tests pass: `cd /Users/jaystuart/dev/project-athena && python3 -m pytest src/jetson/facade/tests/test_query_splitter.py`
- [ ] Test coverage >90%: `python3 -m pytest --cov=src/jetson/facade/query_splitter --cov-report=term-missing`
- [ ] No import errors: `python3 -c "from facade.query_splitter import QuerySplitter; print('OK')"`

**Test Cases to Pass**:
```python
# Should SPLIT
"what's the weather and what time is it" → ["what's the weather", "what time is it"]
"tell me about restaurants and the ravens score" → ["tell me about restaurants", "the ravens score"]
"weather tomorrow and events tonight" → ["weather tomorrow", "events tonight"]

# Should NOT split
"thunder and lightning forecast" → ["thunder and lightning forecast"]
"best hotels in Baltimore and DC" → ["best hotels in Baltimore and DC"]
"turn on living room and dining room lights" → ["turn on living room and dining room lights"]
"rock and roll concerts" → ["rock and roll concerts"]
```

#### Manual Verification:
- [ ] Test 20+ sample compound queries manually
- [ ] Verify <5% false positive rate on split decisions
- [ ] Confirm compound nouns correctly preserved

---

## Phase 2: Multi-Intent Classification

### Overview
Extend intent classifier to support multi-intent detection while maintaining backward compatibility with existing single-intent code.

### Changes Required

#### 1. Modify: `src/jetson/facade/airbnb_intent_classifier.py`

**Add new method after line 103** (after existing `classify()` method):

```python
def classify_multi(self, query: str) -> List[Tuple[str, str, Optional[Dict[str, Any]]]]:
    """
    Classify query and return ALL detected intents

    Args:
        query: User query (may be compound)

    Returns:
        List of (intent_type, handler_or_response, data) tuples
    """
    from facade.query_splitter import QuerySplitter

    # Split compound queries
    splitter = QuerySplitter()
    sub_queries = splitter.split(query)

    # Classify each sub-query
    intents = []
    for sub_query in sub_queries:
        intent = self.classify(sub_query)  # Reuse existing classify()
        intents.append(intent)

    logger.info(f"🎯 Classified {len(intents)} intents from query")
    return intents
```

**No changes to existing `classify()` method** - preserves backward compatibility

### Success Criteria

#### Automated Verification:
- [ ] Existing tests pass: `python3 -m pytest src/jetson/facade/tests/test_intent_classifier.py`
- [ ] New multi-intent tests pass: `python3 -m pytest src/jetson/facade/tests/test_multi_intent_classifier.py`
- [ ] No import errors: `python3 -c "from facade.airbnb_intent_classifier import AirbnbIntentClassifier; c = AirbnbIntentClassifier(); print('OK')"`
- [ ] Type checking passes: `python3 -m mypy src/jetson/facade/airbnb_intent_classifier.py` (if using type hints)

**Test Cases to Pass**:
```python
# Single intent (unchanged behavior)
classify("what's the weather") → 1 intent tuple

# Multi-intent
classify_multi("weather and time") → 2 intent tuples
classify_multi("restaurants, ravens score, and events tonight") → 3 intent tuples

# Device control detection
classify_multi("turn on lights and what's the weather") → 2 intents, first is LLM
```

#### Manual Verification:
- [ ] Verify all existing facade functionality unchanged
- [ ] Test 10+ compound queries through classifier
- [ ] Confirm each intent extracted correctly

---

## Phase 3: Intent Chain Processor

### Overview
Create processor that executes multiple intents sequentially and collects responses, extracted from existing handler dispatch logic.

### Changes Required

#### 1. New File: `src/jetson/facade/intent_processor.py`

**Purpose**: Process list of intents and execute appropriate handlers

**Implementation**:

```python
"""
Intent Chain Processor - Executes multiple intents sequentially

Extracted from facade_integration.py handler dispatch logic (lines 118-229)
"""

import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


class IntentChainProcessor:
    """Processes a chain of intents and collects responses"""

    def __init__(self, handlers: Dict[str, Any]):
        """
        Initialize with handler instances

        Args:
            handlers: Dict mapping handler names to instances
                Example: {
                    'weather': weather_handler,
                    'sports': sports_handler,
                    ...
                }
        """
        self.handlers = handlers

    def process_chain(self, intents: List[Tuple[str, str, Optional[Dict]]]) -> List[str]:
        """
        Process each intent and collect responses

        Args:
            intents: List of (intent_type, handler_name_or_response, data) tuples

        Returns:
            List of response strings
        """
        responses = []

        for intent_type, handler_or_response, data in intents:
            try:
                response = self._process_single_intent(intent_type, handler_or_response, data)

                if response and len(response.strip()) > 0:
                    responses.append(response)
                    logger.info(f"✅ Processed intent {handler_or_response}: {len(response)} chars")
                else:
                    logger.warning(f"⚠️ Empty response from {handler_or_response}")

            except Exception as e:
                logger.error(f"❌ Error processing intent {handler_or_response}: {e}", exc_info=True)
                # Continue processing other intents despite error

        return responses

    def _process_single_intent(self, intent_type: str, handler_or_response: str, data: Optional[Dict]) -> str:
        """
        Process a single intent (extracted from facade_integration.py:113-229)

        Args:
            intent_type: One of IntentType.QUICK|API_CALL|WEB_SEARCH|LLM
            handler_or_response: Handler name or pre-computed response
            data: Optional data dict for handler

        Returns:
            Response string
        """
        from facade.airbnb_intent_classifier import IntentType

        # QUICK responses - return immediately
        if intent_type == IntentType.QUICK:
            return handler_or_response

        # API_CALL - route to appropriate handler
        if intent_type == IntentType.API_CALL:
            return self._call_handler(handler_or_response, data)

        # WEB_SEARCH - call web search handler
        if intent_type == IntentType.WEB_SEARCH:
            search_query = data.get('query', '') if data else ''
            if 'web_search' in self.handlers:
                response = self.handlers['web_search'].search(search_query)
                if response and len(response.strip()) >= 20:
                    return response
            return ""  # Empty to signal need for LLM fallback

        # LLM - cannot process in multi-intent chain, return signal
        if intent_type == IntentType.LLM:
            return "[LLM_REQUIRED]"  # Special marker

        return ""

    def _call_handler(self, handler_name: str, data: Optional[Dict]) -> str:
        """
        Call appropriate handler based on name

        Extracted from facade_integration.py lines 120-226
        """
        data = data or {}

        if handler_name == "weather":
            timeframe = data.get('timeframe', 'current')
            query = data.get('query', '')
            if 'weather' in self.handlers:
                return self.handlers['weather'].get_weather(timeframe, query)

        elif handler_name == "airports":
            # Check if flight status query
            if data.get('type') == 'flight_status':
                flight_num = data.get('flight_number')
                if flight_num and 'flight' in self.handlers:
                    return self.handlers['flight'].get_flight_status(flight_num)
                return "Which flight number are you asking about?"

            # Static airport info
            airport_code = data.get('airport_code')
            if airport_code and 'airport' in self.handlers:
                return self.handlers['airport'].get_airport_info(airport_code)
            return "Which airport? I have info on BWI, DCA, IAD, PHL, JFK, EWR, and LGA"

        elif handler_name == "streaming":
            if data.get('type') == 'search' and 'streaming' in self.handlers:
                return self.handlers['streaming'].search_content(data.get('query', ''))
            return "Which streaming service are you asking about?"

        elif handler_name == "events":
            timeframe = data.get('timeframe', 'today')
            category = data.get('category')
            if 'events' in self.handlers:
                return self.handlers['events'].get_events(timeframe, category)

        elif handler_name == "news":
            news_type = data.get('type', 'national')
            topic = data.get('topic')
            if 'news' in self.handlers:
                response = self.handlers['news'].get_news(news_type, topic)
                # Fallback chain (from facade_integration.py:165-176)
                if not response or len(response.strip()) < 20:
                    if 'web_search' in self.handlers:
                        web_response = self.handlers['web_search'].search(data.get('query', ''))
                        if web_response and len(web_response.strip()) >= 20:
                            return web_response
                    return ""
                return response

        elif handler_name == "stocks":
            if 'stocks' in self.handlers:
                response = self.handlers['stocks'].get_stock_quote(data.get('query', ''))
                # Fallback chain (from facade_integration.py:184-195)
                if not response or len(response.strip()) < 20:
                    if 'web_search' in self.handlers:
                        web_response = self.handlers['web_search'].search(data.get('query', ''))
                        if web_response and len(web_response.strip()) >= 20:
                            return web_response
                    return ""
                return response

        elif handler_name == "sports":
            if 'sports' in self.handlers:
                response = self.handlers['sports'].get_team_score(data.get('query', ''))
                # Fallback chain (from facade_integration.py:203-214)
                if not response or len(response.strip()) < 20:
                    if 'web_search' in self.handlers:
                        web_response = self.handlers['web_search'].search(data.get('query', ''))
                        if web_response and len(web_response.strip()) >= 20:
                            return web_response
                    return ""
                return response

        logger.warning(f"⚠️ Unknown handler: {handler_name}")
        return ""
```

### Success Criteria

#### Automated Verification:
- [ ] Unit tests pass: `python3 -m pytest src/jetson/facade/tests/test_intent_processor.py`
- [ ] Integration test with real handlers: `python3 src/jetson/facade/tests/integration_test_processor.py`
- [ ] No import errors: `python3 -c "from facade.intent_processor import IntentChainProcessor; print('OK')"`

**Test Cases**:
```python
# Single intent
process_chain([(IntentType.QUICK, "It's 72°F", None)]) → ["It's 72°F"]

# Multiple intents
process_chain([
    (IntentType.QUICK, "It's 3:45 PM", None),
    (IntentType.API_CALL, "weather", {"timeframe": "current"})
]) → ["It's 3:45 PM", "Currently 72°F and sunny"]

# Error handling
process_chain([
    (IntentType.API_CALL, "broken_handler", {}),
    (IntentType.QUICK, "This should still work", None)
]) → ["This should still work"]  # Continues despite first error
```

#### Manual Verification:
- [ ] Test with all handler types (weather, sports, news, stocks, events, streaming, airports)
- [ ] Verify fallback chains work correctly
- [ ] Confirm error in one intent doesn't break others

---

## Phase 4: Response Merger

### Overview
Create intelligent response merging that combines multiple intent responses into coherent output using existing patterns from news/events handlers.

### Changes Required

#### 1. New File: `src/jetson/facade/response_merger.py`

**Purpose**: Merge multiple responses using simple, natural strategies

**Implementation**:

```python
"""
Response Merger - Combines multiple intent responses

Uses patterns from:
- news.py:140-153 (numbered list formatting)
- events.py:186-201 (enumeration with ellipsis)
"""

import logging

logger = logging.getLogger(__name__)


class ResponseMerger:
    """Merges multiple intent responses into coherent output"""

    def merge(self, responses: list[str], original_query: str = "") -> str:
        """
        Merge multiple responses intelligently

        Args:
            responses: List of response strings
            original_query: Original user query (for context)

        Returns:
            Merged response string
        """
        # Filter empty responses
        valid_responses = [r for r in responses if r and r.strip() and r != "[LLM_REQUIRED]"]

        # Check if LLM required
        if any(r == "[LLM_REQUIRED]" for r in responses):
            logger.info("🤖 LLM required marker detected, escalating to LLM")
            return None  # Signal to caller to use LLM

        if len(valid_responses) == 0:
            return ""

        if len(valid_responses) == 1:
            return valid_responses[0]

        if len(valid_responses) == 2:
            return self._merge_two(valid_responses)

        return self._merge_many(valid_responses)

    def _merge_two(self, responses: list[str]) -> str:
        """
        Merge two responses with simple connector

        Pattern: "Response1. Response2."

        Example:
            ["It's 72°F and sunny", "The time is 3:45 PM"]
            → "It's 72°F and sunny. The time is 3:45 PM."
        """
        return f"{responses[0]}. {responses[1]}"

    def _merge_many(self, responses: list[str]) -> str:
        """
        Merge 3+ responses with numbered list

        Pattern from news.py:140-153 and events.py:186-201

        Example:
            ["Weather: 72°F", "Restaurants: Koco's", "Events: 3 tonight"]
            → "Here's what I found:\n1) Weather: 72°F\n2) Restaurants: Koco's\n3) Events: 3 tonight"
        """
        merged = "Here's what I found:\n"

        for i, response in enumerate(responses, 1):
            # Use consistent numbering format with parenthesis (matching news.py pattern)
            merged += f"{i}) {response}\n"

        return merged.strip()
```

### Success Criteria

#### Automated Verification:
- [ ] Unit tests pass: `python3 -m pytest src/jetson/facade/tests/test_response_merger.py`
- [ ] No import errors: `python3 -c "from facade.response_merger import ResponseMerger; print('OK')"`

**Test Cases**:
```python
# Empty handling
merge([]) → ""
merge(["", "", ""]) → ""

# Single response
merge(["Only one"]) → "Only one"

# Two responses
merge(["First", "Second"]) → "First. Second."

# Three responses
merge(["One", "Two", "Three"]) → "Here's what I found:\n1) One\n2) Two\n3) Three"

# LLM marker
merge(["Weather", "[LLM_REQUIRED]"]) → None
```

#### Manual Verification:
- [ ] Test merged responses for natural readability
- [ ] Verify numbered lists are formatted correctly
- [ ] Confirm no weird punctuation issues

---

## Phase 5: Facade Integration

### Overview
Integrate all multi-intent components into main facade with feature flag for safe rollout.

### Changes Required

#### 1. Modify: `facade_integration.py`

**Add environment variable at top** (after line 48):

```python
# Multi-intent feature flag
MULTI_INTENT_ENABLED = os.environ.get('MULTI_INTENT_MODE', 'false').lower() == 'true'
```

**Add new function after analyze_query** (after line 250):

```python
def analyze_query_multi(query: str) -> Tuple[str, str]:
    """
    Analyze query with multi-intent support

    Returns: (query_type, response_content)
        query_type: 'quick' | 'llm'
        response_content: String response or 'general' for LLM
    """
    from facade.query_splitter import QuerySplitter
    from facade.intent_processor import IntentChainProcessor
    from facade.response_merger import ResponseMerger
    from facade.airbnb_intent_classifier import IntentType

    # Check if compound query
    splitter = QuerySplitter()
    if not splitter._should_split(query.lower()):
        # Single intent - use existing logic
        logger.info("Single intent query, using existing path")
        return analyze_query(query)

    # Multi-intent processing
    intents = intent_classifier.classify_multi(query)

    # Check if ANY intent requires LLM
    any_llm = any(intent[0] == IntentType.LLM for intent in intents)

    if any_llm:
        # Route entire query to LLM for coherent handling
        logger.info(f"🤖 Multi-intent with LLM required, routing to LLM")
        return ('llm', 'general')

    # Build handler dict for processor
    handler_dict = {
        'weather': weather_handler,
        'web_search': web_search_handler,
        'airport': airport_handler,
        'flight': flight_handler,
        'events': events_handler,
        'streaming': streaming_handler,
        'news': news_handler,
        'stocks': stocks_handler,
        'sports': sports_handler
    }

    # Process all intents
    processor = IntentChainProcessor(handler_dict)
    responses = processor.process_chain(intents)

    # Merge responses
    merger = ResponseMerger()
    merged_response = merger.merge(responses, query)

    # Check if LLM required from merger
    if merged_response is None:
        logger.info(f"🤖 Merger signaled LLM required")
        return ('llm', 'general')

    if not merged_response:
        # All handlers failed, fall back to LLM
        logger.warning(f"⚠️ All handlers returned empty, falling back to LLM")
        return ('llm', 'general')

    return ('quick', merged_response)
```

**Modify chat() function** (replace line 306):

```python
# OLD (line 306):
query_type, response = analyze_query(user_msg)

# NEW:
if MULTI_INTENT_ENABLED:
    query_type, response = analyze_query_multi(user_msg)
else:
    query_type, response = analyze_query(user_msg)
```

### Success Criteria

#### Automated Verification:
- [ ] Feature flag defaults to OFF: `MULTI_INTENT_MODE not set → single-intent path`
- [ ] Feature flag ON works: `MULTI_INTENT_MODE=true → multi-intent path`
- [ ] Existing tests still pass with flag OFF: `python3 -m pytest src/jetson/facade/tests/`
- [ ] No import errors: `python3 -c "import facade_integration; print('OK')"`
- [ ] Facade starts successfully: `cd /mnt/nvme/athena-lite && python3 facade_integration.py 2>&1 | head -20`

#### Manual Verification:
- [ ] Test facade with MULTI_INTENT_MODE=false → verify single-intent still works
- [ ] Test facade with MULTI_INTENT_MODE=true → verify multi-intent works
- [ ] No errors in logs during startup
- [ ] Home Assistant connection still works

**Implementation Note**: After automated verification passes, pause here for manual testing before enabling feature flag in production.

---

## Testing Strategy

### Unit Tests

**Files to Create**:
1. `src/jetson/facade/tests/test_query_splitter.py` - 50+ test cases
2. `src/jetson/facade/tests/test_multi_intent_classifier.py` - 30+ test cases
3. `src/jetson/facade/tests/test_intent_processor.py` - 40+ test cases
4. `src/jetson/facade/tests/test_response_merger.py` - 25+ test cases

**Key Test Categories**:
- **Positive Cases**: Valid compound queries that should split
- **Negative Cases**: Queries that should NOT split (false positives)
- **Edge Cases**: Empty, very long, special characters
- **Error Handling**: Handler failures, network errors, empty responses

### Integration Tests

**Direct Facade Testing**:

```bash
# Test 1: Simple compound query (weather + time)
curl -X POST http://192.168.10.62:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What time is it and weather today"}],"stream":false}' \
  | jq -r '.message.content'

# Expected: "It's [time]. Currently [weather]"

# Test 2: Three-part query
curl -X POST http://192.168.10.62:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"weather, restaurants, and events tonight"}],"stream":false}' \
  | jq -r '.message.content'

# Expected: Numbered list with 3 responses

# Test 3: False positive (should NOT split)
curl -X POST http://192.168.10.62:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"thunder and lightning forecast"}],"stream":false}' \
  | jq -r '.message.content'

# Expected: Single weather response about thunderstorms

# Test 4: Device control + info (should route to LLM)
curl -X POST http://192.168.10.62:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"turn on lights and what is the weather"}],"stream":false}' \
  | jq -r '.message.content'

# Expected: LLM handles both parts coherently
```

**Home Assistant Testing**:
1. Open HA Assist interface
2. Test 10+ compound queries
3. Verify responses are natural and complete
4. Check facade logs for multi-intent processing

### Performance Testing

**Benchmarking Script**: `src/jetson/facade/tests/benchmark_multi_intent.py`

```python
import requests
import time
import statistics

test_queries = [
    # Single intent (baseline)
    "what's the weather",
    "what time is it",

    # Two intents
    "weather and time",
    "restaurants and events",

    # Three intents
    "weather, restaurants, and ravens score"
]

results = {}

for query in test_queries:
    times = []
    for _ in range(10):
        start = time.time()
        response = requests.post(
            "http://192.168.10.62:11434/api/chat",
            json={"messages": [{"role": "user", "content": query}], "stream": False}
        )
        end = time.time()
        times.append(end - start)

    results[query] = {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times)
    }

# Print results
for query, stats in results.items():
    print(f"{query}: {stats['mean']:.2f}s avg (min: {stats['min']:.2f}s, max: {stats['max']:.2f}s)")
```

**Performance Targets**:
- Single intent: <500ms average
- Two intents: <1000ms average (2x overhead acceptable)
- Three intents: <1500ms average

---

## Deployment Plan

### Phase A: Development (MULTI_INTENT_MODE=false)

1. **Implement all components** (Phases 1-5)
2. **Run unit tests** for each component
3. **Integration test** with facade running locally

### Phase B: Testing (MULTI_INTENT_MODE=true on Jetson)

1. **Deploy to Jetson**:
```bash
# Copy files
scp src/jetson/facade/query_splitter.py jstuart@192.168.10.62:/mnt/nvme/athena-lite/facade/
scp src/jetson/facade/intent_processor.py jstuart@192.168.10.62:/mnt/nvme/athena-lite/facade/
scp src/jetson/facade/response_merger.py jstuart@192.168.10.62:/mnt/nvme/athena-lite/facade/
scp facade_integration.py jstuart@192.168.10.62:/mnt/nvme/athena-lite/
scp src/jetson/facade/airbnb_intent_classifier.py jstuart@192.168.10.62:/mnt/nvme/athena-lite/facade/
```

2. **Enable feature flag**:
```bash
ssh jstuart@192.168.10.62 'echo "export MULTI_INTENT_MODE=true" >> ~/.bashrc'
```

3. **Restart facade**:
```bash
ssh jstuart@192.168.10.62 'ps aux | grep facade_integration | grep -v grep | awk "{print \$2}" | xargs kill -9 && cd /mnt/nvme/athena-lite && MULTI_INTENT_MODE=true python3 facade_integration.py > logs/facade.log 2>&1 &'
```

4. **Monitor logs**:
```bash
ssh jstuart@192.168.10.62 'tail -f /mnt/nvme/athena-lite/logs/facade.log'
```

5. **Test 20+ queries** via curl and Home Assistant

### Phase C: Production (MULTI_INTENT_MODE=true permanently)

1. **Update systemd service** (if exists) with environment variable
2. **Create rollback plan**: Keep old facade_integration.py as backup
3. **Monitor for 24 hours** before declaring success

---

## Performance Considerations

### Expected Response Times

**Current (Single Intent)**:
- Time/Date: ~50ms (QUICK response)
- Weather: ~200-400ms (API call)
- Sports: ~300-600ms (API + fallback)

**Multi-Intent (Sequential)**:
- 2 intents: Sum of individual times + ~50ms overhead
- 3 intents: Sum of individual times + ~100ms overhead

**Optimization Opportunity (Future)**:
Parallel processing could reduce to: `max(individual_times) + overhead`

### Caching Strategy

All existing handler caching remains:
- Weather: 5min TTL (`weather.py:cache_ttl`)
- Events: 10min TTL (`events.py:cache_ttl`)
- News: 15min TTL (`news.py:cache_ttl`)
- Sports: 5min TTL (`sports.py:cache_ttl`)

Multi-intent queries benefit from cache if sub-queries match cached entries.

---

## Risk Mitigation

### Risk 1: False Positive Splits

**Mitigation**:
- Conservative splitting (compound noun detection)
- Multi-entity pattern filtering
- Minimum sub-query length validation
- Test suite with 50+ edge cases

**Fallback**: If split causes issues, user can rephrase or ask separately

### Risk 2: Response Merging Confusion

**Mitigation**:
- Simple, predictable merging strategies
- Numbered lists for 3+ responses
- LLM fallback if merging fails

**Fallback**: Feature flag allows instant disable if problems occur

### Risk 3: Performance Degradation

**Mitigation**:
- Sequential processing keeps latency predictable
- Existing caching reduces repeat API calls
- Feature flag OFF by default

**Monitoring**: Benchmark script tracks performance regression

### Risk 4: Handler Errors Breaking Entire Response

**Mitigation**:
- Try/except around each intent in processor
- Continue processing remaining intents on error
- Log errors but don't fail entire query

**Fallback**: LLM handles query if all handlers fail

---

## Related Documents

- **Original Plan**: `thoughts/shared/plans/2025-11-09-multi-intent-handling.md` (this file)
- **Research Output**: Sub-agent findings on facade architecture, intent classifier, and existing patterns
- **Facade Integration**: `facade_integration.py` (main routing logic)
- **Intent Classifier**: `src/jetson/facade/airbnb_intent_classifier.py`
- **Existing Handlers**: `src/jetson/facade/handlers/` directory

---

## Next Steps

1. **Begin Phase 1**: Implement QuerySplitter
2. **Run unit tests** after each phase completion
3. **Integration test** after Phase 5
4. **Deploy to Jetson** for manual testing
5. **Enable feature flag** after validation

**Estimated Completion**: 2025-11-10 (12-16 hours total)

---

**Status**: Ready for Implementation
**Approved By**: [Pending user approval]
**Implementation Start**: [After approval]
