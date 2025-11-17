# RAG Service Validation and Auto-Fix System

**Date:** 2025-11-17
**Status:** Planned
**Priority:** High
**Estimated Effort:** 6-8 hours

## Problem Statement

RAG services (Weather, Sports, Airports) can return empty or invalid data while reporting HTTP 200 status. This causes two critical problems:

1. **Silent Failures**: Empty RAG responses don't trigger fallback to web search, resulting in unhelpful "check the website" responses from the LLM
2. **Poor User Experience**: Users receive generic responses instead of actual data

**Recent Example:**
- Query: "football schedule"
- Sports RAG returned: `{"events": []}`  (empty array, HTTP 200)
- Expected: Trigger web search fallback
- Actual: LLM responded "check Ravens website" (unhelpful)
- Root cause: No validation that events array contained data

## Current State

**Existing Validation** (src/orchestrator/validator.py):
- Two-layer anti-hallucination validation system
- Layer 1: Self-validation (entity checks, pattern matching)
- Layer 2: Cross-model validation (confidence scoring)
- Used for final LLM responses, not RAG data

**Current RAG Services:**
- Weather (8010): Returns weather data or HTTP errors
- Sports (8011): Returns events/teams or empty arrays
- Airports (8012): Returns flight/airport data or HTTP errors

**Current Orchestrator RAG Handling:**
- Makes HTTP request to RAG service
- Checks for HTTP exceptions (raise_for_status)
- Stores response.json() directly to state
- No validation of response content
- Fallback only triggers on HTTP exceptions

## Goals

1. **Validate RAG responses** before accepting them as valid data
2. **Detect empty or insufficient data** (empty arrays, missing fields)
3. **Auto-fix** when possible (retry with different parameters)
4. **Trigger fallback** when validation fails and auto-fix doesn't help
5. **Lightweight validation** (< 10ms overhead per RAG call)
6. **Service-specific validation** (each RAG service has different data structure)

## Technical Approach

### 1. Create RAG Validation Module

Create `src/orchestrator/rag_validator.py`:

```python
"""
RAG Service Validation and Auto-Fix System

Validates RAG service responses for completeness and quality.
Provides auto-fix strategies and fallback recommendations.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Validation result status."""
    VALID = "valid"              # Data is good, use it
    EMPTY = "empty"              # Data is empty, trigger fallback
    INVALID = "invalid"          # Data is malformed, trigger fallback
    NEEDS_RETRY = "needs_retry"  # Data missing, retry with different params


class RAGValidator:
    """
    Validates RAG service responses for quality and completeness.

    Provides service-specific validation and auto-fix strategies.
    """

    def validate_sports_response(
        self,
        response_data: Dict[str, Any],
        query: str
    ) -> Tuple[ValidationResult, str, Optional[Dict[str, Any]]]:
        """
        Validate Sports RAG response.

        Args:
            response_data: JSON response from Sports RAG
            query: Original user query

        Returns:
            Tuple of (result, reason, fix_suggestion)
            - result: ValidationResult enum
            - reason: Human-readable explanation
            - fix_suggestion: Dict with retry parameters if needs_retry
        """
        # Check for events array
        if "events" in response_data:
            events = response_data.get("events", [])

            # Empty events array
            if not events or len(events) == 0:
                logger.warning(f"Sports RAG returned empty events array")
                return (
                    ValidationResult.EMPTY,
                    "No events found",
                    None
                )

            # Validate event structure
            required_fields = ["strEvent", "dateEvent"]
            for event in events:
                missing_fields = [f for f in required_fields if f not in event]
                if missing_fields:
                    logger.warning(
                        f"Sports event missing fields: {missing_fields}"
                    )
                    return (
                        ValidationResult.INVALID,
                        f"Event missing required fields: {missing_fields}",
                        None
                    )

            logger.info(f"Sports RAG response valid: {len(events)} events")
            return (ValidationResult.VALID, f"Found {len(events)} events", None)

        # Check for team data
        elif "teams" in response_data:
            teams = response_data.get("teams", [])

            if not teams or len(teams) == 0:
                logger.warning(f"Sports RAG returned empty teams array")
                return (
                    ValidationResult.EMPTY,
                    "No teams found",
                    None
                )

            logger.info(f"Sports RAG response valid: {len(teams)} teams")
            return (ValidationResult.VALID, f"Found {len(teams)} teams", None)

        # Unknown response structure
        else:
            logger.warning(
                f"Sports RAG response missing 'events' or 'teams': "
                f"{list(response_data.keys())}"
            )
            return (
                ValidationResult.INVALID,
                "Response missing expected data structure",
                None
            )

    def validate_weather_response(
        self,
        response_data: Dict[str, Any],
        query: str
    ) -> Tuple[ValidationResult, str, Optional[Dict[str, Any]]]:
        """
        Validate Weather RAG response.

        Args:
            response_data: JSON response from Weather RAG
            query: Original user query

        Returns:
            Tuple of (result, reason, fix_suggestion)
        """
        # Check for current weather
        if "current" in response_data:
            current = response_data.get("current", {})

            # Validate required fields
            required_fields = ["temp_f", "condition"]
            missing_fields = [f for f in required_fields if f not in current]

            if missing_fields:
                logger.warning(
                    f"Weather RAG missing fields: {missing_fields}"
                )
                return (
                    ValidationResult.INVALID,
                    f"Weather data missing: {missing_fields}",
                    None
                )

            logger.info(f"Weather RAG response valid")
            return (ValidationResult.VALID, "Current weather found", None)

        # Check for forecast
        elif "forecast" in response_data:
            forecast = response_data.get("forecast", {})
            forecastday = forecast.get("forecastday", [])

            if not forecastday or len(forecastday) == 0:
                logger.warning(f"Weather RAG returned empty forecast")
                return (
                    ValidationResult.EMPTY,
                    "No forecast data",
                    None
                )

            logger.info(f"Weather RAG response valid: {len(forecastday)} days")
            return (
                ValidationResult.VALID,
                f"Found {len(forecastday)} day forecast",
                None
            )

        # Unknown structure
        else:
            logger.warning(
                f"Weather RAG response missing 'current' or 'forecast': "
                f"{list(response_data.keys())}"
            )
            return (
                ValidationResult.INVALID,
                "Response missing expected data structure",
                None
            )

    def validate_airports_response(
        self,
        response_data: Dict[str, Any],
        query: str
    ) -> Tuple[ValidationResult, str, Optional[Dict[str, Any]]]:
        """
        Validate Airports RAG response.

        Args:
            response_data: JSON response from Airports RAG
            query: Original user query

        Returns:
            Tuple of (result, reason, fix_suggestion)
        """
        # Check for airport search results
        if "results" in response_data:
            results = response_data.get("results", [])

            if not results or len(results) == 0:
                logger.warning(f"Airports RAG returned empty results")
                return (
                    ValidationResult.EMPTY,
                    "No airports found",
                    None
                )

            logger.info(f"Airports RAG response valid: {len(results)} results")
            return (
                ValidationResult.VALID,
                f"Found {len(results)} airports",
                None
            )

        # Check for single airport data
        elif "airport_code" in response_data or "icao" in response_data:
            required_fields = ["name"]
            missing_fields = [
                f for f in required_fields if f not in response_data
            ]

            if missing_fields:
                logger.warning(
                    f"Airports RAG missing fields: {missing_fields}"
                )
                return (
                    ValidationResult.INVALID,
                    f"Airport data missing: {missing_fields}",
                    None
                )

            logger.info(f"Airports RAG response valid: single airport")
            return (ValidationResult.VALID, "Airport data found", None)

        # Check for flight data
        elif "flights" in response_data:
            flights = response_data.get("flights", [])

            if not flights or len(flights) == 0:
                logger.warning(f"Airports RAG returned empty flights")
                return (
                    ValidationResult.EMPTY,
                    "No flights found",
                    None
                )

            logger.info(f"Airports RAG response valid: {len(flights)} flights")
            return (
                ValidationResult.VALID,
                f"Found {len(flights)} flights",
                None
            )

        # Unknown structure
        else:
            logger.warning(
                f"Airports RAG response missing expected structure: "
                f"{list(response_data.keys())}"
            )
            return (
                ValidationResult.INVALID,
                "Response missing expected data structure",
                None
            )


# Global validator instance
validator = RAGValidator()
```

### 2. Integration with Orchestrator

Modify `src/orchestrator/main.py` to use validator:

```python
# Add import
from .rag_validator import validator, ValidationResult

async def retrieve_sports_data(state: ConversationState) -> ConversationState:
    """
    Retrieve sports data with validation and fallback.
    """
    query = state.query
    logger.info(f"Retrieving sports data for: {query}")

    try:
        # Get team from query
        team = None
        for team_name in ["Ravens", "Orioles"]:
            if team_name.lower() in query.lower():
                team = team_name
                break

        if not team:
            logger.warning("No recognized sports team found")
            await _fallback_to_web_search(state, "Sports", "team not recognized")
            return state

        # Search for team
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{SPORTS_RAG_URL}/sports/teams/search",
                params={"query": team}
            )
            response.raise_for_status()
            team_data = response.json()
            teams = team_data.get("teams", [])

            if not teams:
                logger.warning(f"No teams found for: {team}")
                await _fallback_to_web_search(state, "Sports", "team not found")
                return state

            team_id = teams[0]["idTeam"]
            logger.info(f"Found team ID: {team_id}")

            # Get next events
            events_response = await client.get(
                f"{SPORTS_RAG_URL}/sports/events/{team_id}/next"
            )
            events_response.raise_for_status()
            events_data = events_response.json()

            # NEW: Validate RAG response
            result, reason, fix_suggestion = validator.validate_sports_response(
                events_data,
                query
            )

            if result == ValidationResult.VALID:
                # Data is good, use it
                state.retrieved_data = events_data
                state.data_source = "TheSportsDB"
                logger.info(f"Sports RAG validation passed: {reason}")

            elif result == ValidationResult.EMPTY:
                # Empty data, trigger fallback
                logger.warning(
                    f"Sports RAG validation failed: {reason}, "
                    "triggering web search fallback"
                )
                await _fallback_to_web_search(state, "Sports", reason)

            elif result == ValidationResult.INVALID:
                # Invalid data structure, trigger fallback
                logger.error(
                    f"Sports RAG validation failed: {reason}, "
                    "triggering web search fallback"
                )
                await _fallback_to_web_search(state, "Sports", reason)

            elif result == ValidationResult.NEEDS_RETRY:
                # Retry with different parameters
                logger.info(
                    f"Sports RAG needs retry: {reason}, "
                    f"suggestion: {fix_suggestion}"
                )
                # TODO: Implement retry logic with fix_suggestion
                # For now, fall back to web search
                await _fallback_to_web_search(state, "Sports", reason)

    except httpx.HTTPStatusError as e:
        logger.error(f"Sports RAG HTTP error: {e}")
        await _fallback_to_web_search(state, "Sports", f"HTTP {e.response.status_code}")

    except Exception as e:
        logger.error(f"Sports RAG error: {e}", exc_info=True)
        await _fallback_to_web_search(state, "Sports", str(e))

    return state
```

### 3. Apply to All RAG Services

**Weather RAG Integration:**

```python
async def retrieve_weather_data(state: ConversationState) -> ConversationState:
    """
    Retrieve weather data with validation and fallback.
    """
    location = state.metadata.get("location", "Baltimore, MD")
    logger.info(f"Retrieving weather for: {location}")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{WEATHER_RAG_URL}/weather/current",
                params={"location": location}
            )
            response.raise_for_status()
            weather_data = response.json()

            # Validate response
            result, reason, fix_suggestion = validator.validate_weather_response(
                weather_data,
                state.query
            )

            if result == ValidationResult.VALID:
                state.retrieved_data = weather_data
                state.data_source = "WeatherAPI"
                logger.info(f"Weather RAG validation passed: {reason}")
            else:
                logger.warning(
                    f"Weather RAG validation failed: {reason}, "
                    "triggering web search fallback"
                )
                await _fallback_to_web_search(state, "Weather", reason)

    except Exception as e:
        logger.error(f"Weather RAG error: {e}", exc_info=True)
        await _fallback_to_web_search(state, "Weather", str(e))

    return state
```

**Airports RAG Integration:**

```python
async def retrieve_airports_data(state: ConversationState) -> ConversationState:
    """
    Retrieve airport data with validation and fallback.
    """
    # ... existing logic ...

    # Validate response
    result, reason, fix_suggestion = validator.validate_airports_response(
        airport_data,
        state.query
    )

    if result == ValidationResult.VALID:
        state.retrieved_data = airport_data
        state.data_source = "FlightAware"
    else:
        await _fallback_to_web_search(state, "Airports", reason)

    return state
```

### 4. Enhanced Fallback Helper

Improve `_fallback_to_web_search()` with more context:

```python
async def _fallback_to_web_search(
    state: ConversationState,
    rag_type: str,
    failure_reason: str
):
    """
    Fall back to web search when RAG fails.

    Args:
        state: Current conversation state
        rag_type: Type of RAG that failed (Weather, Sports, Airports)
        failure_reason: Why RAG failed (for logging)
    """
    logger.warning(
        f"{rag_type} RAG failed ({failure_reason}), "
        "falling back to web search"
    )

    # Mark for web search
    state.retrieved_data = None
    state.data_source = "web_search_fallback"
    state.metadata["rag_failure_reason"] = failure_reason
    state.metadata["original_intent"] = state.intent

    # Perform web search with force_search=True
    try:
        intent, search_results = await parallel_search_engine.search(
            query=state.query,
            location="Baltimore, MD",
            limit_per_provider=5,
            force_search=True  # Bypass RAG intent blocking
        )

        if search_results:
            # Format search results for LLM
            search_context = "\n".join([
                f"- {r.title}: {r.snippet} ({r.url})"
                for r in search_results[:5]
            ])

            state.retrieved_data = {
                "type": "web_search",
                "query": state.query,
                "results": search_context,
                "fallback_from": rag_type,
                "reason": failure_reason
            }
            state.data_source = f"web_search (fallback from {rag_type})"
            logger.info(
                f"Web search fallback successful: {len(search_results)} results"
            )
        else:
            logger.warning("Web search fallback returned no results")
            state.retrieved_data = None

    except Exception as e:
        logger.error(f"Web search fallback failed: {e}", exc_info=True)
        state.retrieved_data = None
```

## Performance Considerations

**Validation Overhead:**
- Simple field checks: < 1ms
- Array validation: < 5ms for typical responses
- Total overhead: 5-10ms per RAG call (negligible)

**Error Recovery:**
- Validation fails fast (no retries unless NEEDS_RETRY)
- Fallback is asynchronous (doesn't block)
- Total latency impact: < 10ms

**Resource Usage:**
- No additional HTTP calls (validates existing response)
- Minimal memory (only validates JSON structure)
- No external dependencies

## Testing Strategy

### Unit Tests

```python
# tests/test_rag_validator.py
import pytest
from orchestrator.rag_validator import validator, ValidationResult

def test_sports_valid_events():
    """Test valid sports events response."""
    response_data = {
        "events": [
            {
                "strEvent": "Ravens vs Steelers",
                "dateEvent": "2025-11-18",
                "strTime": "13:00:00"
            }
        ]
    }

    result, reason, fix = validator.validate_sports_response(
        response_data,
        "When do Ravens play?"
    )

    assert result == ValidationResult.VALID
    assert "1 events" in reason
    assert fix is None


def test_sports_empty_events():
    """Test empty sports events array."""
    response_data = {"events": []}

    result, reason, fix = validator.validate_sports_response(
        response_data,
        "Ravens schedule"
    )

    assert result == ValidationResult.EMPTY
    assert "No events found" in reason


def test_sports_invalid_structure():
    """Test malformed sports response."""
    response_data = {"unknown_key": "value"}

    result, reason, fix = validator.validate_sports_response(
        response_data,
        "Sports query"
    )

    assert result == ValidationResult.INVALID
    assert "missing expected data structure" in reason


def test_weather_valid_current():
    """Test valid current weather response."""
    response_data = {
        "current": {
            "temp_f": 65.0,
            "condition": {"text": "Partly cloudy"}
        }
    }

    result, reason, fix = validator.validate_weather_response(
        response_data,
        "What's the weather?"
    )

    assert result == ValidationResult.VALID
    assert "Current weather found" in reason


def test_airports_empty_results():
    """Test empty airports search."""
    response_data = {"results": []}

    result, reason, fix = validator.validate_airports_response(
        response_data,
        "Find airport XYZ"
    )

    assert result == ValidationResult.EMPTY
    assert "No airports found" in reason
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_sports_rag_with_validation():
    """Test full sports RAG retrieval with validation."""
    state = ConversationState(
        session_id="test-123",
        query="When do the Ravens play?",
        intent=IntentCategory.SPORTS,
        conversation_history=[]
    )

    # Mock empty response
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {"events": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Should trigger fallback
        state = await retrieve_sports_data(state)

        # Verify fallback was triggered
        assert state.data_source == "web_search (fallback from Sports)"
        assert "rag_failure_reason" in state.metadata
        assert state.metadata["rag_failure_reason"] == "No events found"
```

### Manual Testing

```bash
# Test Sports RAG validation
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3:mini",
    "messages": [{"role": "user", "content": "When do the Ravens play?"}],
    "stream": false
  }'

# Check logs for validation messages
ssh jstuart@192.168.10.167 'tail -50 ~/dev/project-athena/orchestrator.log | grep -E "(validation|fallback)"'
```

## Deployment Plan

### Phase 1: Implementation (3-4 hours)
1. Create `rag_validator.py` module
2. Implement validation for all three RAG services
3. Add unit tests
4. Update Orchestrator to use validator

### Phase 2: Integration Testing (2-3 hours)
1. Test with real RAG services
2. Test with mocked empty responses
3. Test with malformed responses
4. Verify fallback behavior

### Phase 3: Deployment (1 hour)
1. Deploy to Mac Studio
2. Monitor logs for validation messages
3. Verify fallback triggers correctly
4. Test end-to-end with real queries

### Phase 4: Monitoring (ongoing)
1. Track validation failure rates
2. Identify common failure patterns
3. Tune validation rules if needed
4. Add more sophisticated validation

## Success Criteria

1. **Zero Silent Failures**: All RAG failures trigger fallback or retry
2. **Fast Validation**: < 10ms overhead per RAG call
3. **Comprehensive Coverage**: All RAG services validated
4. **Clear Logging**: All validation failures logged with reason
5. **Better UX**: Users get actual data instead of "check website" responses

## Risks and Mitigations

**Risk 1: False Positives (Valid data marked invalid)**
- Mitigation: Conservative validation (only check critical fields)
- Mitigation: Extensive testing with real RAG responses
- Mitigation: Logging allows quick identification

**Risk 2: Performance Overhead**
- Mitigation: Simple validation logic (no complex processing)
- Mitigation: No additional HTTP calls
- Mitigation: Benchmarking before deployment

**Risk 3: Breaking Changes in RAG APIs**
- Mitigation: Service-specific validators can be updated independently
- Mitigation: Validation failures don't break the system (trigger fallback)
- Mitigation: Comprehensive logging for debugging

## Future Enhancements

1. **Auto-Retry Logic**: When `ValidationResult.NEEDS_RETRY`, retry with adjusted parameters
2. **Confidence Scoring**: Similar to response validator, score data quality (0.0-1.0)
3. **Caching**: Cache validation results to avoid re-validating same data
4. **Metrics**: Track validation success/failure rates per service
5. **Adaptive Validation**: Learn from user feedback to improve validation rules

## References

- Existing validator: `src/orchestrator/validator.py`
- Sports RAG: `src/rag/sports/main.py`
- Weather RAG: `src/rag/weather/main.py`
- Airports RAG: `src/rag/airports/main.py`
- Parallel search: `src/orchestrator/search_providers/parallel_search.py`
- Orchestrator main: `src/orchestrator/main.py`

## Implementation Checklist

- [ ] Create `rag_validator.py` module
- [ ] Implement `validate_sports_response()`
- [ ] Implement `validate_weather_response()`
- [ ] Implement `validate_airports_response()`
- [ ] Write unit tests for all validators
- [ ] Update `retrieve_sports_data()` to use validator
- [ ] Update `retrieve_weather_data()` to use validator
- [ ] Update `retrieve_airports_data()` to use validator
- [ ] Enhance `_fallback_to_web_search()` with context
- [ ] Write integration tests
- [ ] Manual testing with real RAG services
- [ ] Deploy to Mac Studio
- [ ] Monitor validation logs for 24 hours
- [ ] Tune validation rules if needed
- [ ] Document results in Wiki
