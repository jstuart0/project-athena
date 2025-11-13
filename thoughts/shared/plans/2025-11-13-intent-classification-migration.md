# Intent Classification Migration Plan for LangGraph

## Overview

This plan migrates the sophisticated intent classification, multi-intent handling, and anti-hallucination validation systems from the Jetson facade implementations to the LangGraph orchestrator.

## Current State

### What We Have (Jetson)
- 30+ facade implementations with evolved intent patterns
- Two-layer anti-hallucination validation
- Fast-path/slow-path routing
- Comprehensive pattern matching for Baltimore-specific queries
- Caching with category-specific TTLs
- Confidence scoring system

### What's Missing (Orchestrator)
- Using basic pattern matching placeholder
- No confidence scoring
- No anti-hallucination validation
- No caching layer
- No multi-intent support

## Migration Architecture

### Component Overview
```
┌─────────────────────────────────────────┐
│         Enhanced Orchestrator           │
├─────────────────────────────────────────┤
│  IntentClassifier                       │
│    ├─> Pattern Matcher (Fast Path)     │
│    ├─> LLM Classifier (Slow Path)      │
│    └─> Entity Extractor                │
├─────────────────────────────────────────┤
│  QueryAnalyzer                          │
│    ├─> Compound Query Splitter         │
│    └─> Intent Chain Builder            │
├─────────────────────────────────────────┤
│  ResponseValidator                      │
│    ├─> Self-Validation (Layer 1)       │
│    ├─> Cross-Model Check (Layer 2)     │
│    └─> Confidence Scorer               │
├─────────────────────────────────────────┤
│  ResponseCache                          │
│    └─> TTL-based Category Cache        │
└─────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Intent Classification (Day 1)

#### 1.1 Create Intent Classifier Module
```python
# src/orchestrator/intent_classifier.py

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re

class IntentCategory(Enum):
    CONTROL = "control"
    WEATHER = "weather"
    SPORTS = "sports"
    AIRPORTS = "airports"
    TRANSIT = "transit"
    EMERGENCY = "emergency"
    FOOD = "food"
    EVENTS = "events"
    LOCATION = "location"
    GENERAL_INFO = "general_info"
    UNKNOWN = "unknown"

class IntentClassification:
    def __init__(self):
        self.category: IntentCategory = IntentCategory.UNKNOWN
        self.confidence: float = 0.0
        self.entities: Dict[str, Any] = {}
        self.requires_llm: bool = False
        self.cache_key: Optional[str] = None

class EnhancedIntentClassifier:
    """Sophisticated intent classification from Jetson facades"""

    def __init__(self):
        # Control patterns (from facades)
        self.control_patterns = {
            "basic": ["turn on", "turn off", "toggle", "switch"],
            "dimming": ["dim", "brighten", "set brightness", "darker", "lighter"],
            "temperature": ["set temperature", "warmer", "cooler", "heat", "cool"],
            "scenes": ["scene", "mood", "movie mode", "dinner mode", "goodnight"],
            "locks": ["lock", "unlock", "secure", "is locked"],
            "covers": ["open", "close", "raise", "lower", "blinds", "shades"]
        }

        # Information patterns (from Baltimore facades)
        self.info_patterns = {
            IntentCategory.SPORTS: [
                "ravens", "orioles", "score", "game", "won", "lost",
                "stadium", "m&t bank", "camden yards", "tickets"
            ],
            IntentCategory.WEATHER: [
                "weather", "temperature", "rain", "snow", "forecast",
                "humid", "cold", "hot", "storm", "sunny"
            ],
            IntentCategory.AIRPORTS: [
                "airport", "bwi", "flight", "delayed", "gate",
                "terminal", "tsa", "departure", "arrival"
            ],
            IntentCategory.TRANSIT: [
                "bus", "train", "marc", "light rail", "metro",
                "uber", "lyft", "taxi", "water taxi", "circulator"
            ],
            IntentCategory.FOOD: [
                "restaurant", "food", "eat", "hungry", "crab",
                "seafood", "coffee", "breakfast", "lunch", "dinner"
            ],
            IntentCategory.EMERGENCY: [
                "emergency", "911", "hospital", "doctor", "urgent",
                "police", "fire", "ambulance", "pharmacy", "medical"
            ],
            IntentCategory.EVENTS: [
                "event", "concert", "show", "museum", "tonight",
                "weekend", "things to do", "entertainment"
            ],
            IntentCategory.LOCATION: [
                "where", "address", "how far", "distance", "directions",
                "neighborhood", "nearby", "closest", "route"
            ]
        }

        # Complex indicators requiring LLM
        self.complex_indicators = [
            "explain", "why", "how does", "what is the difference",
            "should i", "recommend", "help me understand",
            "tell me about", "compare"
        ]

    async def classify(self, query: str) -> IntentClassification:
        """Classify intent using layered approach"""
        result = IntentClassification()
        query_lower = query.lower()

        # Layer 1: Fast path pattern matching
        pattern_result = self._pattern_match(query_lower)
        if pattern_result:
            result.category, result.confidence = pattern_result

            # High confidence pattern match
            if result.confidence >= 0.8:
                result.entities = self._extract_entities(query_lower, result.category)
                return result

        # Check if complex query needing LLM
        if self._is_complex(query_lower):
            result.requires_llm = True
            result.confidence = 0.5  # Medium confidence, needs LLM

        # Layer 2: Entity extraction regardless of classification
        result.entities = self._extract_entities(query_lower, result.category)

        return result

    def _pattern_match(self, query: str) -> Optional[Tuple[IntentCategory, float]]:
        """Pattern-based classification with confidence"""

        # Check control patterns first (highest priority)
        control_score = 0
        for pattern_type, patterns in self.control_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    control_score += 1

        if control_score > 0:
            # Higher score = higher confidence
            confidence = min(0.6 + (control_score * 0.2), 1.0)
            return (IntentCategory.CONTROL, confidence)

        # Check information patterns
        best_match = None
        best_score = 0

        for category, patterns in self.info_patterns.items():
            score = sum(1 for p in patterns if p in query)
            if score > best_score:
                best_score = score
                best_match = category

        if best_match and best_score > 0:
            # Calculate confidence based on match strength
            confidence = min(0.5 + (best_score * 0.15), 0.95)
            return (best_match, confidence)

        return None

    def _is_complex(self, query: str) -> bool:
        """Check if query requires complex LLM processing"""
        return any(indicator in query for indicator in self.complex_indicators)

    def _extract_entities(self, query: str, category: IntentCategory) -> Dict[str, Any]:
        """Extract relevant entities based on intent category"""
        entities = {}

        if category == IntentCategory.CONTROL:
            # Extract device/room entities
            rooms = ["bedroom", "kitchen", "office", "living room", "bathroom"]
            devices = ["lights", "fan", "tv", "thermostat", "lock", "blinds"]

            for room in rooms:
                if room in query:
                    entities["room"] = room

            for device in devices:
                if device in query:
                    entities["device"] = device

            # Extract actions
            if "turn on" in query:
                entities["action"] = "on"
            elif "turn off" in query:
                entities["action"] = "off"

            # Extract values
            temp_match = re.search(r'(\d+)\s*degrees?', query)
            if temp_match:
                entities["temperature"] = int(temp_match.group(1))

            bright_match = re.search(r'(\d+)\s*%|percent', query)
            if bright_match:
                entities["brightness"] = int(bright_match.group(1))

        elif category == IntentCategory.WEATHER:
            # Extract location if specified
            if "tomorrow" in query:
                entities["time"] = "tomorrow"
            elif "weekend" in query:
                entities["time"] = "weekend"
            elif "today" in query:
                entities["time"] = "today"

        elif category == IntentCategory.SPORTS:
            # Extract team names
            if "ravens" in query:
                entities["team"] = "ravens"
            elif "orioles" in query:
                entities["team"] = "orioles"

            # Extract time references
            if "last" in query or "yesterday" in query:
                entities["timeframe"] = "past"
            elif "next" in query or "upcoming" in query:
                entities["timeframe"] = "future"

        return entities
```

#### 1.2 Update Orchestrator classify_node

```python
# In src/orchestrator/main.py

from intent_classifier import EnhancedIntentClassifier, IntentCategory as EnhancedIntentCategory

# Initialize classifier
intent_classifier = EnhancedIntentClassifier()

async def enhanced_classify_node(state: OrchestratorState) -> OrchestratorState:
    """Enhanced classification using Jetson patterns"""

    # Use enhanced classifier
    classification = await intent_classifier.classify(state.query)

    # Map to orchestrator intent categories
    intent_mapping = {
        EnhancedIntentCategory.CONTROL: IntentCategory.CONTROL,
        EnhancedIntentCategory.WEATHER: IntentCategory.WEATHER,
        EnhancedIntentCategory.SPORTS: IntentCategory.SPORTS,
        EnhancedIntentCategory.AIRPORTS: IntentCategory.AIRPORTS,
        EnhancedIntentCategory.TRANSIT: IntentCategory.GENERAL_INFO,
        EnhancedIntentCategory.EMERGENCY: IntentCategory.GENERAL_INFO,
        EnhancedIntentCategory.FOOD: IntentCategory.GENERAL_INFO,
        EnhancedIntentCategory.EVENTS: IntentCategory.GENERAL_INFO,
        EnhancedIntentCategory.LOCATION: IntentCategory.GENERAL_INFO,
        EnhancedIntentCategory.GENERAL_INFO: IntentCategory.GENERAL_INFO,
        EnhancedIntentCategory.UNKNOWN: IntentCategory.UNKNOWN,
    }

    state.intent = intent_mapping.get(
        classification.category,
        IntentCategory.UNKNOWN
    )

    # Store additional metadata
    state.metadata["confidence"] = classification.confidence
    state.metadata["entities"] = classification.entities
    state.metadata["requires_llm"] = classification.requires_llm

    # If low confidence or requires LLM, use LLM classification
    if classification.confidence < 0.6 or classification.requires_llm:
        state = await _llm_classify(state)

    logger.info(
        f"Enhanced classification: {state.intent} "
        f"(confidence: {classification.confidence:.2f})"
    )

    return state
```

### Phase 2: Anti-Hallucination Validation (Day 1-2)

#### 2.1 Create Validator Module

```python
# src/orchestrator/validator.py

import asyncio
import re
from typing import Tuple, Dict, Any, Optional
import httpx

class ResponseValidator:
    """Two-layer anti-hallucination validation from Jetson"""

    def __init__(self, llm_client: httpx.AsyncClient):
        self.llm_client = llm_client

    async def validate_response(
        self,
        query: str,
        response: str,
        enable_cross_check: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Full validation pipeline
        Returns: (is_valid, final_response, metadata)
        """
        metadata = {
            'layer1': {'passed': False, 'modified': False},
            'layer2': {
                'enabled': enable_cross_check,
                'passed': False,
                'confidence': 0.0
            }
        }

        # Layer 1: Self-validation
        is_valid, validated = await self._self_validate(query, response)
        metadata['layer1']['passed'] = is_valid
        metadata['layer1']['modified'] = (validated != response)

        if not is_valid:
            return (False, validated, metadata)

        # Layer 2: Cross-model check (optional)
        if enable_cross_check:
            is_consistent, final, confidence = await self._cross_check(
                query,
                validated
            )
            metadata['layer2']['passed'] = is_consistent
            metadata['layer2']['confidence'] = confidence

            if confidence < 0.5:
                return (False, final, metadata)

            return (True, final, metadata)

        return (True, validated, metadata)

    async def _self_validate(
        self,
        query: str,
        response: str
    ) -> Tuple[bool, str]:
        """
        Layer 1: Validate answer addresses query
        Returns: (is_valid, possibly_modified_response)
        """

        # Check for specific requirements
        checks = {
            'score_check': (
                any(word in query.lower() for word in ['score', 'result', 'won', 'lost']),
                lambda r: any(char.isdigit() for char in r),
                "Response missing scores/numbers"
            ),
            'time_check': (
                any(word in query.lower() for word in ['when', 'what time', 'schedule']),
                lambda r: any(
                    indicator in r.lower()
                    for indicator in ['am', 'pm', ':', 'tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                ),
                "Response missing time/date"
            ),
            'location_check': (
                any(word in query.lower() for word in ['where', 'location', 'address']),
                lambda r: any(
                    indicator in r.lower()
                    for indicator in ['street', 'avenue', 'road', 'miles', 'blocks', 'near']
                ),
                "Response missing location"
            )
        }

        for check_name, (should_check, validator, error_msg) in checks.items():
            if should_check and not validator(response):
                # Try to get better answer with validation prompt
                validation_prompt = f"""
                User asked: "{query}"
                System answered: "{response}"

                Problem: {error_msg}

                Provide a corrected answer that includes the missing information.
                Be concise and direct.
                """

                try:
                    result = await self.llm_client.post(
                        "/v1/chat/completions",
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [
                                {"role": "system", "content": validation_prompt}
                            ],
                            "temperature": 0.1,
                            "max_tokens": 200
                        }
                    )

                    if result.status_code == 200:
                        data = result.json()
                        corrected = data["choices"][0]["message"]["content"]
                        return (True, corrected)

                except Exception as e:
                    logger.error(f"Validation correction failed: {e}")

                return (False, response)

        return (True, response)

    async def _cross_check(
        self,
        query: str,
        response: str
    ) -> Tuple[bool, str, float]:
        """
        Layer 2: Cross-model validation
        Returns: (is_consistent, final_response, confidence_score)
        """

        # Use smaller model for verification
        try:
            # Ask simpler model same question
            verify_result = await self.llm_client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",  # Could use smaller model
                    "messages": [
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100
                }
            )

            if verify_result.status_code == 200:
                verify_data = verify_result.json()
                verify_response = verify_data["choices"][0]["message"]["content"]

                # Calculate similarity/confidence
                confidence = self._calculate_confidence(
                    response,
                    verify_response
                )

                # If very different, use the verification response
                if confidence < 0.3:
                    return (False, verify_response, confidence)

                return (True, response, confidence)

        except Exception as e:
            logger.error(f"Cross-check failed: {e}")
            # Default to trusting original
            return (True, response, 0.7)

        return (True, response, 0.7)

    def _calculate_confidence(
        self,
        response1: str,
        response2: str
    ) -> float:
        """Calculate confidence score between two responses"""

        # Simple implementation - can be enhanced
        r1_lower = response1.lower()
        r2_lower = response2.lower()

        # Extract key facts
        r1_numbers = set(re.findall(r'\d+', r1_lower))
        r2_numbers = set(re.findall(r'\d+', r2_lower))

        r1_words = set(r1_lower.split())
        r2_words = set(r2_lower.split())

        # Calculate overlaps
        number_overlap = len(r1_numbers & r2_numbers) / max(
            len(r1_numbers | r2_numbers), 1
        )
        word_overlap = len(r1_words & r2_words) / max(
            len(r1_words | r2_words), 1
        )

        # Weighted confidence
        confidence = (number_overlap * 0.6) + (word_overlap * 0.4)

        return min(max(confidence, 0.0), 1.0)
```

#### 2.2 Update Orchestrator validate_node

```python
# In src/orchestrator/main.py

from validator import ResponseValidator

# Initialize validator
response_validator = ResponseValidator(llm_client)

async def enhanced_validate_node(state: OrchestratorState) -> OrchestratorState:
    """Enhanced validation with anti-hallucination"""

    # Skip validation for control commands (they don't hallucinate)
    if state.intent == IntentCategory.CONTROL:
        state.metadata["validation_skipped"] = True
        return state

    # Determine if high confidence needed
    requires_high_confidence = any([
        "emergency" in state.query.lower(),
        "urgent" in state.query.lower(),
        "critical" in state.query.lower(),
        state.metadata.get("requires_high_confidence", False)
    ])

    # Run validation
    is_valid, final_response, validation_metadata = await response_validator.validate_response(
        state.query,
        state.response,
        enable_cross_check=requires_high_confidence
    )

    # Update state
    state.response = final_response
    state.metadata["validation"] = validation_metadata

    if not is_valid:
        state.metadata["validation_failed"] = True
        logger.warning(
            f"Validation failed for query: {state.query[:50]}... "
            f"Confidence: {validation_metadata['layer2']['confidence']}"
        )

        # Could trigger retry or fallback here
        if state.metadata.get("retry_count", 0) < 2:
            state.metadata["retry_count"] = state.metadata.get("retry_count", 0) + 1
            state.metadata["needs_retry"] = True

    return state
```

### Phase 3: Response Caching (Day 2)

#### 3.1 Create Cache Module

```python
# src/orchestrator/response_cache.py

import time
from typing import Optional, Any, Dict
import json
import hashlib

class ResponseCache:
    """TTL-based response cache from Jetson facades"""

    def __init__(self, redis_client):
        self.redis = redis_client

        # Category-specific TTLs (in seconds)
        self.ttls = {
            "control": 0,        # Don't cache control commands
            "sports": 300,       # 5 minutes
            "weather": 600,      # 10 minutes
            "airports": 120,     # 2 minutes
            "transit": 60,       # 1 minute
            "events": 3600,      # 1 hour
            "static": 86400,     # 24 hours
            "default": 300       # 5 minutes default
        }

    def _generate_key(self, category: str, query: str) -> str:
        """Generate cache key from category and query"""
        # Normalize query
        normalized = query.lower().strip()
        # Create hash for consistent keys
        query_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
        return f"response:{category}:{query_hash}"

    async def get(
        self,
        category: str,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached response if not expired"""

        if category == "control":
            return None  # Never cache control commands

        key = self._generate_key(category, query)

        try:
            cached_json = await self.redis.get(key)
            if cached_json:
                cached = json.loads(cached_json)

                # Check if expired
                ttl = self.ttls.get(category, self.ttls["default"])
                if time.time() - cached["timestamp"] < ttl:
                    return cached["data"]
                else:
                    # Expired, delete it
                    await self.redis.delete(key)

        except Exception as e:
            logger.warning(f"Cache get error: {e}")

        return None

    async def set(
        self,
        category: str,
        query: str,
        response_data: Dict[str, Any]
    ):
        """Cache response with appropriate TTL"""

        if category == "control":
            return  # Never cache control commands

        key = self._generate_key(category, query)

        try:
            cache_data = {
                "data": response_data,
                "timestamp": time.time(),
                "category": category,
                "query": query
            }

            ttl = self.ttls.get(category, self.ttls["default"])

            await self.redis.setex(
                key,
                ttl,
                json.dumps(cache_data)
            )

        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    async def clear_category(self, category: str):
        """Clear all cached responses for a category"""
        pattern = f"response:{category}:*"

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)

        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
```

#### 3.2 Integrate Caching in Orchestrator

```python
# In src/orchestrator/main.py

from response_cache import ResponseCache

# Initialize cache
response_cache = ResponseCache(cache_client)

async def cached_retrieve_node(state: OrchestratorState) -> OrchestratorState:
    """Retrieve with caching"""

    # Check cache first
    cached_response = await response_cache.get(
        state.intent.value,
        state.query
    )

    if cached_response:
        state.rag_context = cached_response.get("rag_context", "")
        state.response = cached_response.get("response", "")
        state.metadata["cache_hit"] = True
        logger.info(f"Cache hit for {state.intent.value} query")
        return state

    # Original retrieve logic
    state = await original_retrieve_logic(state)

    # Cache the response
    if state.response:
        await response_cache.set(
            state.intent.value,
            state.query,
            {
                "rag_context": state.rag_context,
                "response": state.response,
                "metadata": state.metadata
            }
        )

    return state
```

### Phase 4: Multi-Intent Support (Day 2-3)

#### 4.1 Create Query Analyzer

```python
# src/orchestrator/query_analyzer.py

import re
from typing import List, Tuple
from intent_classifier import EnhancedIntentClassifier

class QueryAnalyzer:
    """Multi-intent query analysis"""

    def __init__(self):
        self.classifier = EnhancedIntentClassifier()

        # Compound query indicators
        self.compound_indicators = [
            " and ",
            " then ",
            " also ",
            " plus ",
            ", ",
            " after that "
        ]

    async def analyze(
        self,
        query: str
    ) -> List[Tuple[str, Any]]:
        """
        Split and analyze compound queries
        Returns list of (sub_query, classification) tuples
        """

        # Check for compound query
        if not any(ind in query.lower() for ind in self.compound_indicators):
            # Single intent
            classification = await self.classifier.classify(query)
            return [(query, classification)]

        # Split compound query
        parts = self._split_query(query)

        # Classify each part
        results = []
        for part in parts:
            classification = await self.classifier.classify(part)
            results.append((part, classification))

        return results

    def _split_query(self, query: str) -> List[str]:
        """Split compound query into parts"""

        # Start with simple split on "and"
        parts = []
        remaining = query

        for indicator in [" and ", " then ", " also "]:
            if indicator in remaining.lower():
                split_parts = remaining.split(indicator)
                parts.extend(split_parts[:-1])
                remaining = split_parts[-1]

        parts.append(remaining)

        # Clean up parts
        cleaned = []
        for part in parts:
            clean = part.strip()
            if clean and len(clean) > 3:  # Minimum viable query
                cleaned.append(clean)

        return cleaned if cleaned else [query]
```

#### 4.2 Update Orchestrator for Multi-Intent

```python
# In src/orchestrator/main.py

from query_analyzer import QueryAnalyzer

# Initialize analyzer
query_analyzer = QueryAnalyzer()

async def multi_intent_classify_node(state: OrchestratorState) -> OrchestratorState:
    """Handle multi-intent queries"""

    # Analyze for multiple intents
    intent_parts = await query_analyzer.analyze(state.query)

    if len(intent_parts) == 1:
        # Single intent - use existing flow
        _, classification = intent_parts[0]
        state.intent = classification.category
        state.metadata["confidence"] = classification.confidence
        state.metadata["entities"] = classification.entities
    else:
        # Multiple intents detected
        state.metadata["multi_intent"] = True
        state.metadata["intent_parts"] = []

        for sub_query, classification in intent_parts:
            state.metadata["intent_parts"].append({
                "query": sub_query,
                "intent": classification.category.value,
                "confidence": classification.confidence,
                "entities": classification.entities
            })

        # Set primary intent as first one
        _, primary_classification = intent_parts[0]
        state.intent = primary_classification.category

        logger.info(
            f"Multi-intent query detected: {len(intent_parts)} parts"
        )

    return state

# Add new node for processing multiple intents
async def process_multi_intent_node(state: OrchestratorState) -> OrchestratorState:
    """Process multiple intents sequentially"""

    if not state.metadata.get("multi_intent"):
        return state

    responses = []

    for intent_part in state.metadata["intent_parts"]:
        # Create sub-state for each intent
        sub_state = OrchestratorState(
            query=intent_part["query"],
            intent=IntentCategory(intent_part["intent"]),
            mode=state.mode,
            room=state.room
        )

        # Process based on intent type
        if sub_state.intent == IntentCategory.CONTROL:
            sub_state = await route_control_node(sub_state)
        else:
            sub_state = await route_info_node(sub_state)
            sub_state = await retrieve_node(sub_state)
            sub_state = await synthesize_node(sub_state)

        responses.append(sub_state.response)

    # Combine responses
    state.response = " ".join(responses)

    return state
```

## Testing Strategy

### Unit Tests

```python
# tests/test_intent_classifier.py

import pytest
from src.orchestrator.intent_classifier import EnhancedIntentClassifier

@pytest.mark.asyncio
async def test_control_intent_classification():
    classifier = EnhancedIntentClassifier()

    # Test control commands
    result = await classifier.classify("turn on the bedroom lights")
    assert result.category == IntentCategory.CONTROL
    assert result.confidence >= 0.8
    assert result.entities["device"] == "lights"
    assert result.entities["room"] == "bedroom"
    assert result.entities["action"] == "on"

@pytest.mark.asyncio
async def test_weather_intent_classification():
    classifier = EnhancedIntentClassifier()

    result = await classifier.classify("what's the weather tomorrow")
    assert result.category == IntentCategory.WEATHER
    assert result.entities["time"] == "tomorrow"

@pytest.mark.asyncio
async def test_complex_query_detection():
    classifier = EnhancedIntentClassifier()

    result = await classifier.classify("explain how the thermostat works")
    assert result.requires_llm == True
```

### Integration Tests

```python
# tests/integration/test_enhanced_orchestrator.py

@pytest.mark.asyncio
async def test_multi_intent_processing():
    """Test compound query handling"""

    response = await client.post(
        "/query",
        json={
            "query": "turn off the lights and what's the weather"
        }
    )

    assert response.status_code == 200
    result = response.json()

    # Should handle both intents
    assert "lights" in result["answer"].lower()
    assert "weather" in result["answer"].lower()

@pytest.mark.asyncio
async def test_anti_hallucination():
    """Test validation prevents hallucination"""

    response = await client.post(
        "/query",
        json={
            "query": "what was the Ravens score yesterday"
        }
    )

    result = response.json()

    # Should have actual numbers if answering about score
    assert any(char.isdigit() for char in result["answer"])
```

## Success Criteria

1. **Intent Classification Accuracy**
   - Pattern matching achieves >90% accuracy on known patterns
   - LLM fallback handles unknown patterns gracefully
   - Entity extraction works for control commands

2. **Anti-Hallucination**
   - Validation catches missing required elements (scores, times, etc.)
   - Cross-model check provides confidence scoring
   - Low confidence responses are flagged

3. **Performance**
   - Cached responses return in <100ms
   - Pattern matching completes in <50ms
   - Full classification pipeline <500ms

4. **Multi-Intent**
   - Compound queries are split correctly
   - Each intent is processed appropriately
   - Responses are combined coherently

## Rollout Plan

### Day 1
- [ ] Implement EnhancedIntentClassifier
- [ ] Update classify_node to use new classifier
- [ ] Deploy and test pattern matching

### Day 2
- [ ] Implement ResponseValidator
- [ ] Update validate_node with anti-hallucination
- [ ] Add ResponseCache
- [ ] Deploy and test validation

### Day 3
- [ ] Implement QueryAnalyzer
- [ ] Add multi-intent support
- [ ] Full integration testing
- [ ] Performance optimization

## Monitoring

Add metrics for:
- Intent classification confidence scores
- Cache hit rates by category
- Validation failure rates
- Multi-intent query frequency
- Response latencies by intent type

## Future Enhancements

1. **Learning System**
   - Track successful/failed classifications
   - Update patterns based on feedback
   - Personalization per user

2. **Advanced Multi-Intent**
   - Parallel intent processing
   - Intent dependency resolution
   - Context carrying between intents

3. **Enhanced Validation**
   - Multiple model ensemble validation
   - Fact checking against knowledge base
   - Temporal consistency checking