"""
Project Athena Orchestrator Service

LangGraph-based state machine that coordinates between:
- Intent classification
- Home Assistant control
- RAG services for information retrieval
- LLM synthesis
- Response validation
"""

import os
import json
import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Literal, Tuple
from contextlib import asynccontextmanager
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# Add to Python path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.logging_config import configure_logging
from shared.ha_client import HomeAssistantClient
from shared.llm_router import get_llm_router, LLMRouter
from shared.cache import CacheClient
from shared.admin_config import get_admin_client

# Parallel search imports
from orchestrator.search_providers.parallel_search import ParallelSearchEngine
from orchestrator.search_providers.result_fusion import ResultFusion

# Session manager imports
from orchestrator.session_manager import get_session_manager, SessionManager
from orchestrator.config_loader import get_config

# RAG validation imports
from orchestrator.rag_validator import validator, ValidationResult

# Configure logging
logger = configure_logging("orchestrator")

# Metrics
request_counter = Counter(
    'orchestrator_requests_total',
    'Total requests to orchestrator',
    ['intent', 'status']
)
request_duration = Histogram(
    'orchestrator_request_duration_seconds',
    'Request duration in seconds',
    ['intent']
)
node_duration = Histogram(
    'orchestrator_node_duration_seconds',
    'Node execution duration in seconds',
    ['node']
)

# Global clients
ha_client: Optional[HomeAssistantClient] = None
llm_router: Optional[LLMRouter] = None
cache_client: Optional[CacheClient] = None
session_manager: Optional[SessionManager] = None
rag_clients: Dict[str, httpx.AsyncClient] = {}

# Configuration
WEATHER_SERVICE_URL = os.getenv("RAG_WEATHER_URL", "http://localhost:8010")
SPORTS_SERVICE_URL = os.getenv("RAG_SPORTS_URL", "http://localhost:8011")
AIRPORTS_SERVICE_URL = os.getenv("RAG_AIRPORTS_URL", "http://localhost:8012")
OLLAMA_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:11434")

# Intent categories
class IntentCategory(str, Enum):
    CONTROL = "control"  # Home Assistant control
    WEATHER = "weather"  # Weather information
    AIRPORTS = "airports"  # Airport/flight info
    SPORTS = "sports"  # Sports information
    GENERAL_INFO = "general_info"  # General knowledge
    UNKNOWN = "unknown"  # Unclear intent

# Model tiers
class ModelTier(str, Enum):
    SMALL = "phi3:mini"  # Quick responses
    MEDIUM = "llama3.1:8b"  # Standard queries
    LARGE = "llama3.1:8b"  # Complex reasoning (same as medium for Phase 1)

# Orchestrator state
class OrchestratorState(BaseModel):
    """State that flows through the LangGraph state machine."""

    # Input
    query: str = Field(..., description="User's query")
    mode: Literal["owner", "guest"] = Field("owner", description="User mode")
    room: str = Field("unknown", description="Room/zone identifier")
    temperature: float = Field(0.7, description="LLM temperature")
    session_id: Optional[str] = Field(None, description="Conversation session ID")

    # Conversation context
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Previous conversation messages")

    # Classification
    intent: Optional[IntentCategory] = None
    confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)

    # Model selection
    model_tier: Optional[ModelTier] = None

    # Retrieved data
    retrieved_data: Dict[str, Any] = Field(default_factory=dict)
    data_source: Optional[str] = None

    # Response
    answer: Optional[str] = None
    citations: List[str] = Field(default_factory=list)

    # Validation
    validation_passed: bool = True
    validation_reason: Optional[str] = None
    validation_details: List[str] = Field(default_factory=list)

    # Metadata
    request_id: str = Field(default_factory=lambda: hashlib.md5(str(time.time()).encode()).hexdigest()[:8])
    start_time: float = Field(default_factory=time.time)
    node_timings: Dict[str, float] = Field(default_factory=dict)
    error: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global ha_client, llm_router, cache_client, session_manager, rag_clients, parallel_search_engine, result_fusion

    # Startup
    logger.info("Starting Orchestrator service")

    # Initialize clients
    # Home Assistant client - optional, gracefully handle if unavailable
    try:
        # TODO: Get HA token from admin API instead of environment
        admin_client = get_admin_client()
        ha_token = await admin_client.get_secret("home-assistant")
        if ha_token:
            ha_client = HomeAssistantClient(token=ha_token)
            logger.info("Home Assistant client initialized from database")
        else:
            logger.warning("HA token not in database, trying environment")
            ha_token_env = os.getenv("HA_TOKEN")
            if ha_token_env:
                ha_client = HomeAssistantClient(token=ha_token_env)
                logger.info("Home Assistant client initialized from environment")
            else:
                ha_client = None
                logger.warning("Home Assistant not configured (token unavailable)")
    except Exception as e:
        ha_client = None
        logger.warning(f"Home Assistant client initialization failed: {e}")

    # Initialize LLM router with database-driven backend configuration
    llm_router = get_llm_router()
    logger.info(f"LLM Router initialized with admin API: {llm_router.admin_url}")

    cache_client = CacheClient()

    # Initialize session manager
    session_manager = await get_session_manager()
    logger.info("Session manager initialized")

    # Initialize parallel search engine (async to fetch API keys from database)
    parallel_search_engine = await ParallelSearchEngine.from_environment()
    logger.info("Parallel search engine initialized")

    # Initialize result fusion
    result_fusion = ResultFusion(
        similarity_threshold=0.7,
        min_confidence=0.5
    )
    logger.info("Result fusion initialized")

    # Initialize RAG service clients
    rag_clients = {
        "weather": httpx.AsyncClient(base_url=WEATHER_SERVICE_URL, timeout=30.0),
        "airports": httpx.AsyncClient(base_url=AIRPORTS_SERVICE_URL, timeout=30.0),
        "sports": httpx.AsyncClient(base_url=SPORTS_SERVICE_URL, timeout=30.0),
    }

    # Check service health
    for name, client in rag_clients.items():
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                logger.info(f"RAG service {name} is healthy")
            else:
                logger.warning(f"RAG service {name} unhealthy: {response.status_code}")
        except Exception as e:
            logger.warning(f"RAG service {name} not available: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Orchestrator service")
    if ha_client:
        await ha_client.close()
    if llm_router:
        await llm_router.close()
    if cache_client:
        await cache_client.close()
    if session_manager:
        await session_manager.close()
    if parallel_search_engine:
        await parallel_search_engine.close_all()
    for client in rag_clients.values():
        await client.aclose()

app = FastAPI(
    title="Athena Orchestrator",
    description="LangGraph-based request coordination for Project Athena",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# Helper Functions
# ============================================================================

async def get_rag_service_url(intent: str) -> Optional[str]:
    """
    Get RAG service URL for intent from database configuration.
    Falls back to environment variables if database unavailable.

    Args:
        intent: Intent category (e.g., "weather", "sports", "airports")

    Returns:
        RAG service URL or None
    """
    try:
        client = get_admin_client()
        routing_config = await client.get_intent_routing()

        if routing_config and intent in routing_config:
            url = routing_config[intent].get("rag_service_url")
            if url:
                logger.info(f"Using database RAG URL for '{intent}': {url}")
                return url
    except Exception as e:
        logger.warning(f"Failed to get RAG URL from database for '{intent}': {e}")

    # Fallback to environment variables
    url_map = {
        "weather": WEATHER_SERVICE_URL,
        "airports": AIRPORTS_SERVICE_URL,
        "sports": SPORTS_SERVICE_URL
    }
    fallback_url = url_map.get(intent)
    if fallback_url:
        logger.info(f"Using environment variable RAG URL for '{intent}': {fallback_url}")
    return fallback_url

# ============================================================================
# Node Implementations
# ============================================================================

def _parse_classification_response(response: str) -> Tuple[IntentCategory, float]:
    """
    Parse LLM classification response into category and confidence.

    Expected format:
        CATEGORY: <category_name>
        CONFIDENCE: <0.0-1.0>
        REASON: <brief explanation>

    Returns:
        Tuple of (IntentCategory, confidence_score)
    """
    try:
        # Extract category
        category_match = re.search(r'CATEGORY:\s*(\w+)', response, re.IGNORECASE)
        category_str = category_match.group(1).upper() if category_match else None

        # Extract confidence
        confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5

        # Map to IntentCategory enum
        category_map = {
            "CONTROL": IntentCategory.CONTROL,
            "WEATHER": IntentCategory.WEATHER,
            "AIRPORTS": IntentCategory.AIRPORTS,
            "SPORTS": IntentCategory.SPORTS,
            "GENERAL_INFO": IntentCategory.GENERAL_INFO,
            "GENERAL": IntentCategory.GENERAL_INFO,  # Alias
            "UNKNOWN": IntentCategory.UNKNOWN,
        }

        category = category_map.get(category_str, IntentCategory.GENERAL_INFO)

        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))

        return (category, confidence)

    except Exception as e:
        logger.warning(f"Failed to parse LLM response: {e}")
        return (IntentCategory.GENERAL_INFO, 0.3)  # Low confidence fallback


async def classify_intent_llm(query: str, conversation_history: List[Dict[str, str]] = None) -> Tuple[IntentCategory, float]:
    """
    Use LLM (phi3:mini) to classify query intent with confidence scoring.

    This is a simplified Gateway-style LLM classification that directly
    calls Ollama API for fast, structured intent classification.

    Args:
        query: User query to classify
        conversation_history: Previous conversation messages for context

    Returns:
        Tuple of (IntentCategory, confidence_score)

    Confidence levels:
        - 1.0: High confidence (explicit intent)
        - 0.7-0.9: Medium confidence (contextual clues)
        - 0.3-0.6: Low confidence (ambiguous)
        - Falls back to pattern matching if < 0.3
    """
    # Build context from conversation history
    context_str = ""
    if conversation_history and len(conversation_history) > 0:
        context_str = "\n\nPrevious conversation:\n"
        # Include last 3 messages for context
        for msg in conversation_history[-3:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                context_str += f"User: {content}\n"
            elif role == "assistant":
                context_str += f"Assistant: {content}\n"
        logger.info(f"Using conversation context with {len(conversation_history[-3:])} previous messages")

    prompt = f"""Classify this query into ONE category:
{context_str}
Current Query: "{query}"

Categories:
- CONTROL: Home automation commands (lights, switches, thermostats, devices)
- WEATHER: Weather conditions, forecasts, temperature
- SPORTS: Sports scores, schedules, teams, games (Ravens, Orioles, Giants, etc.)
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

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "phi3:mini",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistency
                        "num_predict": 50   # Need ~50 tokens for structured response
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
        category = _pattern_based_classification(query)
        return (category, 0.5)  # Medium confidence for fallback


def _extract_entities_simple(query: str, intent: IntentCategory) -> Dict[str, Any]:
    """
    Simple pattern-based entity extraction for simplified mode.
    Extracts location, team, airport, etc. based on intent.
    """
    entities = {}
    query_lower = query.lower()

    if intent == IntentCategory.WEATHER:
        # Extract location from "in <city>" pattern
        location_match = re.search(r'in\s+([a-z]+(?:\s+[a-z]+)?(?:\s+[a-z]+)?)', query_lower)
        if location_match:
            location = location_match.group(1).strip()
            # Title case the location
            entities["location"] = ' '.join(word.capitalize() for word in location.split())

    elif intent == IntentCategory.SPORTS:
        # Extract team names (simple heuristics)
        if "ravens" in query_lower:
            entities["team"] = "Baltimore Ravens"
        elif "orioles" in query_lower:
            entities["team"] = "Baltimore Orioles"

    elif intent == IntentCategory.AIRPORTS:
        # Extract airport codes
        airport_match = re.search(r'\b([A-Z]{3})\b', query)
        if airport_match:
            entities["airport"] = airport_match.group(1)

    return entities


def _extract_entities_with_context(
    query: str,
    intent: IntentCategory,
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Entity extraction with coreference resolution from conversation history.

    Resolves pronouns and references by looking back through conversation history.
    Falls back to pattern-based extraction if no context available.

    Args:
        query: Current user query
        intent: Classified intent
        conversation_history: Previous conversation messages

    Returns:
        Dictionary of extracted entities
    """
    entities = {}
    query_lower = query.lower()

    # Coreference resolution - check if query has pronouns/references
    has_pronouns = any(pronoun in query_lower for pronoun in ["they", "them", "their", "it", "that", "those"])

    if conversation_history and has_pronouns:
        logger.info("Detected pronouns in query, attempting coreference resolution")

        # Look back through last 5 messages for entity references
        for msg in reversed(conversation_history[-5:]):
            content = msg.get("content", "").lower()
            role = msg.get("role", "")

            # Look for team names in previous context (SPORTS intent)
            if intent == IntentCategory.SPORTS and "team" not in entities:
                team_keywords = [
                    ("giants", "New York Giants"),
                    ("ravens", "Baltimore Ravens"),
                    ("orioles", "Baltimore Orioles"),
                    ("yankees", "New York Yankees"),
                    ("jets", "New York Jets"),
                    ("cowboys", "Dallas Cowboys"),
                    ("patriots", "New England Patriots"),
                    ("bills", "Buffalo Bills"),
                    ("chiefs", "Kansas City Chiefs"),
                    ("packers", "Green Bay Packers"),
                    ("eagles", "Philadelphia Eagles"),
                    ("steelers", "Pittsburgh Steelers"),
                    ("49ers", "San Francisco 49ers"),
                ]

                for keyword, full_name in team_keywords:
                    if keyword in content:
                        entities["team"] = full_name
                        entities["resolved_from_context"] = True
                        logger.info(f"Resolved 'they' → '{full_name}' from conversation history")
                        break

                if "team" in entities:
                    break  # Stop searching once we find a team

            # Look for locations in previous context (WEATHER intent)
            elif intent == IntentCategory.WEATHER and "location" not in entities:
                # Extract location from "in <city>" pattern in previous messages
                location_match = re.search(r'in\s+([a-z]+(?:\s+[a-z]+)?(?:\s+[a-z]+)?)', content)
                if location_match:
                    location = location_match.group(1).strip()
                    entities["location"] = ' '.join(word.capitalize() for word in location.split())
                    entities["resolved_from_context"] = True
                    logger.info(f"Resolved location from conversation history: {entities['location']}")
                    break

    # Standard entity extraction (same as _extract_entities_simple)
    if intent == IntentCategory.WEATHER and "location" not in entities:
        # Extract location from "in <city>" pattern
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
        elif "yankees" in query_lower:
            entities["team"] = "New York Yankees"
        elif "jets" in query_lower:
            entities["team"] = "New York Jets"

    elif intent == IntentCategory.AIRPORTS:
        # Extract airport codes
        airport_match = re.search(r'\b([A-Z]{3})\b', query)
        if airport_match:
            entities["airport"] = airport_match.group(1)

    return entities


async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """
    Classify user intent using LLM with Redis caching.
    Determines: control vs info, specific category, entities.

    Supports two classification modes via feature flag:
    - Simplified LLM mode: Fast, direct Ollama API calls (Gateway-style)
    - Standard LLM mode: JSON-based classification via llm_router
    """
    start = time.time()

    # OPTIMIZATION: Check cache first
    cache_key = f"intent_v4:{hashlib.md5(state.query.lower().encode()).hexdigest()}"

    def _heuristic_sports_team(query: str) -> Optional[str]:
        team_tokens = [
            "ravens", "giants", "jets", "cowboys", "patriots", "bills", "chiefs", "lions",
            "packers", "eagles", "49ers", "dolphins", "steelers", "chargers", "browns",
            "texans", "bears", "saints", "buccaneers", "vikings", "falcons", "colts",
            "broncos", "commanders", "jaguars", "panthers", "raiders", "rams", "titans",
            "cardinals", "seahawks", "bengals"
        ]
        q_lower = query.lower()
        return next((t.title() for t in team_tokens if t in q_lower), None)

    try:
        cached = await cache_client.get(cache_key)
        if cached:
            state.intent = IntentCategory(cached["intent"])
            state.confidence = cached.get("confidence", 0.9)
            state.entities = cached.get("entities", {})
            state.node_timings["classify"] = time.time() - start
            # If sports intent cached without a team, attempt heuristic; if still empty, continue to reclassify
            if state.intent == IntentCategory.SPORTS and not state.entities.get("team"):
                found = _heuristic_sports_team(state.query)
                if found:
                    state.entities["team"] = found
                    logger.info(f"Heuristic sports team extraction (cache path): {found}")
                else:
                    logger.info(f"Intent cache HIT for '{state.query}' but missing team; continuing to reclassify")
            else:
                logger.info(f"Intent cache HIT for '{state.query}': {state.intent}")
                return state
    except Exception as e:
        logger.warning(f"Intent cache lookup failed: {e}")

    # Check feature flag for simplified LLM classification
    admin_client = get_admin_client()
    use_simplified_llm = await admin_client.is_feature_enabled("enable_llm_intent_classification")

    # Default to False if feature not found in database
    if use_simplified_llm is None:
        use_simplified_llm = False

    try:
        if use_simplified_llm:
            # Use simplified Gateway-style LLM classification with conversation context
            logger.info("Using simplified LLM classification (Gateway-style)")
            state.intent, state.confidence = await classify_intent_llm(
                state.query,
                conversation_history=state.conversation_history
            )
            # Extract entities with coreference resolution
            state.entities = _extract_entities_with_context(
                state.query,
                state.intent,
                conversation_history=state.conversation_history
            )

        else:
            # Use existing JSON-based LLM classification via llm_router
            logger.info("Using standard JSON-based LLM classification")

            # Build classification prompt
            classification_prompt = f"""Classify the following user query into a category and extract entities.

Categories:
- control: Home automation commands (lights, switches, thermostats, scenes)
- weather: Weather information requests
- airports: Airport or flight information
- sports: Sports scores, games, teams
- general_info: Other information requests
- unknown: Unclear or ambiguous

Query: "{state.query}"

Respond in JSON format:
{{
    "intent": "category_name",
    "confidence": 0.0-1.0,
    "entities": {{
        "device": "optional device name",
        "location": "optional location",
        "team": "optional sports team",
        "airport": "optional airport code"
    }}
}}"""

            # Use small model for classification
            # Combine system and user messages into a single prompt
            full_prompt = f"You are an intent classifier. Respond only with valid JSON.\n\n{classification_prompt}"

            result = await llm_router.generate(
                model=ModelTier.SMALL.value,
                prompt=full_prompt,
                temperature=0.3,  # Lower temperature for consistent classification
                request_id=state.request_id,
                session_id=state.session_id,
                user_id=state.mode,
                zone=state.room
            )

            response_text = result.get("response", "")

            # Parse classification result
            try:
                result = json.loads(response_text)
                state.intent = IntentCategory(result.get("intent", "unknown"))
                state.confidence = float(result.get("confidence", 0.5))
                state.entities = result.get("entities", {})
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse classification: {e}")
                # Fallback to pattern matching
                state.intent = _pattern_based_classification(state.query)
                state.confidence = 0.7
                # Extract entities using pattern-based extraction in fallback path
                state.entities = _extract_entities_simple(state.query, state.intent)

        # Heuristic sports team extraction when entities are empty (useful in simplified mode)
        if state.intent == IntentCategory.SPORTS and not state.entities.get("team"):
            found = _heuristic_sports_team(state.query)
            if found:
                state.entities["team"] = found
                logger.info(f"Heuristic sports team extraction: {state.entities['team']}")

        if state.intent == IntentCategory.SPORTS:
            logger.info(f"Sports classification entities: {state.entities}")

        # DEBUG: Log entities for all intents to trace extraction
        logger.info(f"Classified query as {state.intent} with confidence {state.confidence}, entities: {state.entities}")

        # OPTIMIZATION: Cache the result (5 minute TTL)
        try:
            await cache_client.set(cache_key, {
                "intent": state.intent.value,
                "confidence": state.confidence,
                "entities": state.entities
            }, ttl=300)
            logger.info(f"Intent classification cached for '{state.query}'")
        except Exception as e:
            logger.warning(f"Intent cache write failed: {e}")

    except Exception as e:
        logger.error(f"Classification error: {e}", exc_info=True)
        state.intent = IntentCategory.UNKNOWN
        state.confidence = 0.0
        state.error = f"Classification failed: {str(e)}"

    state.node_timings["classify"] = time.time() - start
    return state

def _pattern_based_classification(query: str) -> IntentCategory:
    """Fallback pattern-based classification."""
    query_lower = query.lower()

    # Control patterns
    control_patterns = [
        "turn on", "turn off", "set", "dim", "brighten",
        "lights", "switch", "temperature", "thermostat", "scene"
    ]
    if any(p in query_lower for p in control_patterns):
        return IntentCategory.CONTROL

    # Weather patterns
    if any(p in query_lower for p in ["weather", "forecast", "rain", "snow", "temperature outside"]):
        return IntentCategory.WEATHER

    # Airport patterns
    if any(p in query_lower for p in ["airport", "flight", "delay", "bwi", "dca", "iad"]):
        return IntentCategory.AIRPORTS

    # Sports patterns
    sports_patterns = [
        "game", "score", "ravens", "orioles", "team", "schedule",
        "football", "soccer", "basketball", "baseball", "hockey",
        "nfl", "nba", "mlb", "nhl", "mls", "ncaa",
        "playoff", "championship", "season", "match", "vs", "versus"
    ]
    if any(p in query_lower for p in sports_patterns):
        return IntentCategory.SPORTS

    return IntentCategory.GENERAL_INFO

async def route_control_node(state: OrchestratorState) -> OrchestratorState:
    """
    Handle home automation control commands via Home Assistant API.
    """
    start = time.time()

    try:
        # Extract device and action from entities or query
        device = state.entities.get("device")
        query_lower = state.query.lower()

        # Simple pattern matching for common commands
        if "turn on" in query_lower:
            action = "turn_on"
        elif "turn off" in query_lower:
            action = "turn_off"
        else:
            action = None

        if not device:
            # Try to extract device from query
            if "lights" in query_lower or "light" in query_lower:
                device = "light.office_ceiling"  # Default for demo
            elif "switch" in query_lower:
                device = "switch.office_fan"  # Default for demo

        if device and action:
            # Call Home Assistant service
            domain = device.split(".")[0]
            result = await ha_client.call_service(
                domain=domain,
                service=action,
                service_data={"entity_id": device}
            )

            state.answer = f"Done! I've turned {'on' if action == 'turn_on' else 'off'} the {device.replace('_', ' ').replace('.', ' ')}."
            state.retrieved_data = {"ha_response": result}

        else:
            # Need more information
            state.answer = "I understand you want to control something, but I need more details. Which device would you like to control?"

        logger.info(f"Control command executed: {device} - {action}")

    except Exception as e:
        logger.error(f"Control execution error: {e}", exc_info=True)
        state.answer = "I encountered an error while trying to control that device. Please try again."
        state.error = str(e)

    state.node_timings["route_control"] = time.time() - start
    return state

async def route_info_node(state: OrchestratorState) -> OrchestratorState:
    """
    Select appropriate model tier for information queries.
    """
    start = time.time()

    # Estimate complexity based on query length and intent
    query_length = len(state.query.split())

    if state.intent == IntentCategory.GENERAL_INFO and query_length > 20:
        state.model_tier = ModelTier.LARGE
    elif state.intent in [IntentCategory.WEATHER, IntentCategory.SPORTS]:
        state.model_tier = ModelTier.SMALL
    else:
        state.model_tier = ModelTier.MEDIUM

    logger.info(f"Selected model tier: {state.model_tier}")

    state.node_timings["route_info"] = time.time() - start
    return state

def _is_time_sensitive_query(query: str) -> bool:
    """
    Priority 3: Detect if query requires current/real-time information.

    Time-sensitive queries should trigger web search even if RAG succeeds.

    Args:
        query: User query

    Returns:
        True if query requires current data, False otherwise
    """
    query_lower = query.lower()

    # Time indicators (today, now, current, etc.)
    time_indicators = [
        "today", "tonight", "tomorrow", "yesterday",
        "this week", "this month", "this year",
        "now", "currently", "recent", "recently",
        "latest", "newest", "current", "present",
        "right now", "at the moment"
    ]

    # Current event indicators
    current_event_indicators = [
        "score", "scores", "result", "results",
        "won", "lost", "winning", "losing",
        "news", "headline", "headlines",
        "what happened", "what's happening",
        "update", "updates", "status",
        "delay", "delays", "delayed",
        "cancellation", "cancelled",
        "price", "stock", "market"
    ]

    # Check for time indicators
    has_time_indicator = any(indicator in query_lower for indicator in time_indicators)

    # Check for current event indicators
    has_current_event = any(indicator in query_lower for indicator in current_event_indicators)

    # If query has both time and event indicators, it's definitely time-sensitive
    if has_time_indicator and has_current_event:
        logger.info(f"Query is time-sensitive (time + event indicators): {query}")
        return True

    # Just current event indicators also make it time-sensitive
    if has_current_event:
        logger.info(f"Query is time-sensitive (event indicators): {query}")
        return True

    return False


async def _fallback_to_web_search(state: OrchestratorState, rag_service: str, error_msg: str):
    """
    Helper function to fall back to web search when RAG service fails.

    Args:
        state: Current orchestrator state
        rag_service: Name of the failed RAG service (for logging)
        error_msg: Error message from the failed service
    """
    logger.warning(f"{rag_service} RAG service failed ({error_msg}), falling back to web search")

    try:
        # Execute parallel search with automatic intent classification
        # force_search=True bypasses RAG intent check (since we're already in fallback mode)
        intent, search_results = await parallel_search_engine.search(
            query=state.query,
            location="Baltimore, MD",
            limit_per_provider=5,
            force_search=True  # CRITICAL: Force web search even for RAG intents
        )

        logger.info(f"Fallback search intent classified as: '{intent}'")

        if search_results:
            # Fuse and rank results based on classified intent
            fused_results = result_fusion.get_top_results(
                results=search_results,
                query=state.query,
                intent=intent,
                limit=5
            )

            logger.info(f"Fallback web search returned {len(fused_results)} fused results")

            # Convert to dict format for LLM
            search_data = {
                "intent": intent,
                "results": [r.to_dict() for r in fused_results],
                "sources": list(set(r.source for r in fused_results)),
                "total_results": len(search_results),
                "fused_results": len(fused_results),
                "fallback_note": f"Data retrieved from web search (primary {rag_service} service unavailable)"
            }

            state.retrieved_data = search_data
            state.data_source = f"Web Search Fallback ({intent}): {', '.join(search_data['sources'])}"
            state.citations.extend([f"Search result from {r.source}" for r in fused_results])
            state.citations.append(f"Note: {rag_service} service was unavailable, used web search instead")
            logger.info(f"Fallback web search successful: intent={intent}, sources={search_data['sources']}")
        else:
            # Even web search failed - use LLM knowledge
            state.retrieved_data = {}
            state.data_source = "LLM knowledge (RAG and web search unavailable)"
            logger.warning(f"Fallback web search returned no results, using LLM knowledge")

    except Exception as e:
        logger.error(f"Fallback web search failed: {e}", exc_info=True)
        state.retrieved_data = {}
        state.data_source = "LLM knowledge (RAG and web search failed)"


async def retrieve_node(state: OrchestratorState) -> OrchestratorState:
    """
    Retrieve information from appropriate RAG service.
    Falls back to web search if RAG service is unavailable.
    """
    start = time.time()

    try:
        if state.intent == IntentCategory.WEATHER:
            # Get dynamic RAG service URL
            service_url = await get_rag_service_url("weather")
            if not service_url:
                logger.error("Weather RAG service URL not configured")
                # Fall back to web search instead of failing
                await _fallback_to_web_search(state, "Weather", "service not configured")
            else:
                try:
                    # Call weather service with dynamic URL
                    location = state.entities.get("location", "Baltimore, MD")

                    # Check if forecast is needed (future timeframes)
                    needs_forecast = state.entities.get("forecast", False)

                    async with httpx.AsyncClient(base_url=service_url, timeout=30.0) as client:
                        if needs_forecast:
                            # Call forecast endpoint for future weather
                            logger.info(f"Fetching forecast for {location} (timeframe: {state.entities.get('timeframe', 'future')})")
                            response = await client.get(
                                "/weather/forecast",
                                params={"location": location, "days": 5}
                            )
                        else:
                            # Call current weather endpoint
                            logger.info(f"Fetching current weather for {location}")
                            response = await client.get(
                                "/weather/current",
                                params={"location": location}
                            )

                        response.raise_for_status()

                        weather_data = response.json()

                        # Validate Weather RAG response quality
                        validation_result, reason, suggestions = validator.validate_weather_response(
                            weather_data, state.query
                        )

                        if validation_result == ValidationResult.VALID:
                            # Response is good, use it
                            state.retrieved_data = weather_data
                            state.data_source = "OpenWeatherMap"
                            state.citations.append(f"Weather data from OpenWeatherMap for {location}")
                            logger.debug(f"Weather RAG validation passed: {reason}")

                        elif validation_result in [ValidationResult.EMPTY, ValidationResult.INVALID]:
                            # Data is empty or invalid, trigger web search fallback
                            logger.warning(
                                f"Weather RAG validation failed: {validation_result.value} - {reason}"
                            )
                            if suggestions:
                                logger.info(f"Fallback suggestion: {suggestions}")
                            await _fallback_to_web_search(state, "Weather", reason)

                        elif validation_result == ValidationResult.NEEDS_RETRY:
                            # Data structure mismatch or missing information
                            logger.info(
                                f"Weather RAG needs retry: {reason}. Suggestions: {suggestions}"
                            )
                            # For now, fall back to web search for retry scenarios
                            await _fallback_to_web_search(state, "Weather", reason)

                except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
                    # RAG service failed - fall back to web search
                    await _fallback_to_web_search(state, "Weather", str(e))

        elif state.intent == IntentCategory.AIRPORTS:
            # Get dynamic RAG service URL
            service_url = await get_rag_service_url("airports")
            if not service_url:
                logger.error("Airports RAG service URL not configured")
                await _fallback_to_web_search(state, "Airports", "service not configured")
            else:
                try:
                    # Call airports service with dynamic URL
                    airport = state.entities.get("airport", "BWI")
                    async with httpx.AsyncClient(base_url=service_url, timeout=30.0) as client:
                        response = await client.get(f"/airports/{airport}")
                        response.raise_for_status()

                        airports_data = response.json()

                        # Validate Airports RAG response quality
                        validation_result, reason, suggestions = validator.validate_airports_response(
                            airports_data, state.query
                        )

                        if validation_result == ValidationResult.VALID:
                            # Response is good, use it
                            state.retrieved_data = airports_data
                            state.data_source = "FlightAware"
                            state.citations.append(f"Flight data from FlightAware for {airport}")
                            logger.debug(f"Airports RAG validation passed: {reason}")

                        elif validation_result in [ValidationResult.EMPTY, ValidationResult.INVALID]:
                            # Data is empty or invalid, trigger web search fallback
                            logger.warning(
                                f"Airports RAG validation failed: {validation_result.value} - {reason}"
                            )
                            if suggestions:
                                logger.info(f"Fallback suggestion: {suggestions}")
                            await _fallback_to_web_search(state, "Airports", reason)

                        elif validation_result == ValidationResult.NEEDS_RETRY:
                            # Data structure mismatch or missing information
                            logger.info(
                                f"Airports RAG needs retry: {reason}. Suggestions: {suggestions}"
                            )
                            # For now, fall back to web search for retry scenarios
                            # Future: Could retry with different RAG parameters
                            await _fallback_to_web_search(state, "Airports", reason)

                except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
                    # RAG service failed - fall back to web search
                    await _fallback_to_web_search(state, "Airports", str(e))

        elif state.intent == IntentCategory.SPORTS:
            # Get dynamic RAG service URL
            service_url = await get_rag_service_url("sports")
            if not service_url:
                logger.error("Sports RAG service URL not configured")
                await _fallback_to_web_search(state, "Sports", "service not configured")
            else:
                try:
                    # Call sports service with dynamic URL
                    team = state.entities.get("team")
                    if not team:
                        # Lightweight heuristic extraction from query
                        team_tokens = [
                            "ravens", "giants", "jets", "cowboys", "patriots", "bills", "chiefs", "lions",
                            "packers", "eagles", "49ers", "dolphins", "steelers", "chargers", "browns",
                            "texans", "bears", "saints", "buccaneers", "vikings", "falcons", "colts",
                            "broncos", "commanders", "jaguars", "panthers", "raiders", "rams", "titans",
                            "cardinals", "seahawks", "bengals"
                        ]
                        q_lower = state.query.lower()
                        team = next((t.title() for t in team_tokens if t in q_lower), state.query)
                    logger.info(f"Sports query team resolved to: {team}")
                    query_lower = state.query.lower()
                    news_mode = any(word in query_lower for word in ["news", "headline", "update", "latest"])
                    olympics_mode = "olympic" in query_lower
                    async with httpx.AsyncClient(base_url=service_url, timeout=30.0) as client:
                        if olympics_mode:
                            olympics_q = state.query
                            olympics_resp = await client.get(
                                "/sports/olympics/events",
                                params={"query": olympics_q}
                            )
                            olympics_resp.raise_for_status()
                            olympics_data = olympics_resp.json()
                            state.retrieved_data = olympics_data
                            state.data_source = "olympics-news"
                            state.citations.append(f"Olympics coverage for {olympics_q}")
                            logger.debug("Olympics coverage fetched", extra={"count": olympics_data.get("count", 0)})
                            return state

                        if news_mode:
                            news_q = team if team else state.query
                            news_resp = await client.get(
                                "/sports/news",
                                params={"query": news_q, "limit": 5}
                            )
                            news_resp.raise_for_status()
                            news_data = news_resp.json()
                            state.retrieved_data = news_data
                            state.data_source = "sports-news"
                            state.citations.append(f"News headlines for {news_q}")
                            logger.debug("Sports news fetched", extra={"count": news_data.get("count", 0)})
                            return state

                        # Search for team
                        search_response = await client.get(
                            "/sports/teams/search",
                            params={"query": team}
                        )
                        search_response.raise_for_status()
                        search_data = search_response.json()

                        if search_data.get("teams"):
                            # Prefer NFL Giants vs MLB Giants when query mentions football
                            teams_list = search_data["teams"]
                            if team.lower() == "giants":
                                teams_list = sorted(
                                    teams_list,
                                    key=lambda t: 0 if "football" in (t.get("strLeague") or "") else 1
                                )
                            team_id = teams_list[0]["idTeam"]

                            # Get next event
                            events_response = await client.get(f"/sports/events/{team_id}/next")
                            events_response.raise_for_status()

                            events_data = events_response.json()

                            # If user asks for "this week/today/tomorrow", prune events to near-term
                            query_lower = state.query.lower()
                            if any(kw in query_lower for kw in ["this week", "today", "tonight", "tomorrow"]):
                                events = events_data.get("events", []) or []
                                now = datetime.utcnow().date()
                                week_end = now + timedelta(days=7)
                                filtered = []
                                for ev in events:
                                    date_str = ev.get("dateEvent") or ev.get("date")
                                    try:
                                        d = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                                    except Exception:
                                        try:
                                            d = datetime.strptime(date_str, "%Y-%m-%d").date()
                                        except Exception:
                                            continue
                                    if now <= d <= week_end:
                                        filtered.append(ev)
                                events_data["events"] = filtered
                                if not filtered:
                                    # No events in the requested window; return empty result gracefully
                                    provider = None
                                    events_list = events_data.get("events") or []
                                    if events_list:
                                        provider = events_list[0].get("source")
                                    state.retrieved_data = {"team_id": team_id, "events": []}
                                    state.data_source = provider or "sports-rag"
                                    state.citations.append(f"Sports data from {state.data_source} for {team}")
                                    return state

                            # Validate Sports RAG response quality
                            # Pass team name to detect TheSportsDB API data corruption
                            validation_result, reason, suggestions = validator.validate_sports_response(
                                events_data, state.query, requested_team=team
                            )

                            if validation_result == ValidationResult.VALID:
                                # Response is good, use it
                                state.retrieved_data = events_data
                                # Use provider from payload if available
                                provider = None
                                if events_data.get("events"):
                                    provider = events_data["events"][0].get("source")
                                elif events_data.get("teams"):
                                    provider = events_data["teams"][0].get("source")
                                state.data_source = provider or "sports-rag"
                                state.citations.append(f"Sports data from {state.data_source} for {team}")
                                logger.debug(f"Sports RAG validation passed: {reason}")

                            elif validation_result in [ValidationResult.EMPTY, ValidationResult.INVALID]:
                                # Data is empty or invalid, trigger web search fallback
                                logger.warning(
                                    f"Sports RAG validation failed: {validation_result.value} - {reason}"
                                )
                                if suggestions:
                                    logger.info(f"Fallback suggestion: {suggestions}")
                                await _fallback_to_web_search(state, "Sports", reason)

                            elif validation_result == ValidationResult.NEEDS_RETRY:
                                # Data structure mismatch (e.g., got schedule when query wants scores)
                                logger.info(
                                    f"Sports RAG needs retry: {reason}. Suggestions: {suggestions}"
                                )
                                # For now, fall back to web search for retry scenarios
                                # Future: Could retry with different RAG parameters
                                await _fallback_to_web_search(state, "Sports", reason)

                except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
                    # RAG service failed - fall back to web search
                    await _fallback_to_web_search(state, "Sports", str(e))

        else:
            # Use intent-based parallel web search for unknown/general queries
            logger.info("Attempting intent-based parallel search")

            # Execute parallel search with automatic intent classification
            intent, search_results = await parallel_search_engine.search(
                query=state.query,
                location="Baltimore, MD",
                limit_per_provider=5
            )

            logger.info(f"Search intent classified as: '{intent}'")

            if search_results:
                # Fuse and rank results based on classified intent
                fused_results = result_fusion.get_top_results(
                    results=search_results,
                    query=state.query,
                    intent=intent,
                    limit=5
                )

                logger.info(f"Parallel search returned {len(fused_results)} fused results (intent: {intent})")

                # Convert to dict format for LLM
                search_data = {
                    "intent": intent,
                    "results": [r.to_dict() for r in fused_results],
                    "sources": list(set(r.source for r in fused_results)),
                    "total_results": len(search_results),
                    "fused_results": len(fused_results)
                }

                state.retrieved_data = search_data
                state.data_source = f"Parallel Search ({intent}): {', '.join(search_data['sources'])}"
                state.citations.extend([f"Search result from {r.source}" for r in fused_results])
                logger.info(f"Parallel search completed: intent={intent}, sources={search_data['sources']}")
            else:
                # Fallback to LLM knowledge
                state.retrieved_data = {}
                state.data_source = "LLM knowledge"
                logger.info(f"Parallel search returned no results (intent: {intent}), using LLM knowledge")

        logger.info(f"Retrieved data from {state.data_source}")

    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        state.error = f"Retrieval failed: {str(e)}"

    state.node_timings["retrieve"] = time.time() - start
    return state

async def synthesize_node(state: OrchestratorState) -> OrchestratorState:
    """
    Generate natural language response using LLM with retrieved data and conversation history.
    """
    start = time.time()

    try:
        # Build synthesis prompt with retrieved data
        # Check if we have meaningful data (not just empty dict)
        has_data = state.retrieved_data and (
            isinstance(state.retrieved_data, dict) and len(state.retrieved_data) > 0 and
            any(v for v in state.retrieved_data.values() if v)  # Has non-empty values
        )

        if has_data:
            context = json.dumps(state.retrieved_data, indent=2)
            synthesis_prompt = f"""Answer the following question using ONLY the provided context.

Question: {state.query}

Context Data:
{context}

CRITICAL INSTRUCTIONS:
1. ONLY use facts from the Context Data above
2. If the context doesn't have the information, say "I don't have current information about that"
3. NEVER make up specific facts, dates, names, or numbers
4. Be concise but accurate
5. Cite your source when possible

Response:"""
        else:
            # No data retrieved - use general knowledge with caveats
            # This happens when web search failed/returned nothing
            synthesis_prompt = f"""Question: {state.query}

You don't have access to real-time or current information, but you can answer using your general knowledge.

IMPORTANT GUIDELINES:
1. Answer the question using your general knowledge if possible
2. If it requires current/real-time data (news, scores, weather, stocks, etc.), acknowledge the limitation and suggest checking authoritative sources
3. For factual/historical questions, provide accurate information from your training
4. For general knowledge, explanations, or how-to questions, provide helpful answers
5. NEVER make up specific current events, recent data, or time-sensitive facts
6. Be helpful - if you can answer even partially, do so
7. If you truly cannot answer, suggest alternative approaches

Response:"""

        # Build prompt with system context
        system_context = "You are Athena, a helpful home assistant. Provide clear, concise answers.\n\n"

        # Format conversation history for LLM context
        history_context = ""
        if state.conversation_history:
            logger.info(f"Including {len(state.conversation_history)} previous messages in context")
            history_context = "Previous conversation:\n"
            for msg in state.conversation_history:
                role = msg["role"].capitalize()
                content = msg["content"]
                history_context += f"{role}: {content}\n"
            history_context += "\n"

        # Combine system context, history, and synthesis prompt
        full_prompt = system_context + history_context + synthesis_prompt

        result = await llm_router.generate(
            model=state.model_tier.value if state.model_tier else ModelTier.MEDIUM.value,
            prompt=full_prompt,
            temperature=state.temperature,
            request_id=state.request_id,
            session_id=state.session_id,
            user_id=state.mode,
            zone=state.room,
            intent=state.intent.value if state.intent else None
        )

        state.answer = result.get("response", "")

        # Add data attribution
        if state.citations:
            state.answer += f"\n\n_Source: {', '.join(state.citations)}_"

        logger.info(f"Synthesized response using {state.model_tier}")

    except Exception as e:
        logger.error(f"Synthesis error: {e}", exc_info=True)
        state.answer = "I apologize, but I'm having trouble generating a response. Please try again."
        state.error = f"Synthesis failed: {str(e)}"

    state.node_timings["synthesize"] = time.time() - start
    return state

async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """
    Multi-layer anti-hallucination validation.

    Layer 1: Basic checks (length, error patterns)
    Layer 2: Pattern detection (specific facts without data)
    Layer 3: LLM-based fact checking
    Layer 4: Uncertainty marker detection
    """
    start = time.time()

    # Layer 1: Basic validation
    if not state.answer or len(state.answer) < 10:
        state.validation_passed = False
        state.validation_reason = "Response too short"
        logger.warning(f"Validation failed: {state.validation_reason}")
        state.node_timings["validate"] = time.time() - start
        return state

    if len(state.answer) > 2000:
        state.validation_passed = False
        state.validation_reason = "Response too long"
        logger.warning(f"Validation failed: {state.validation_reason}")
        state.node_timings["validate"] = time.time() - start
        return state

    # Layer 1.5: Answer Quality Validation (Priority 2 Fix) - RE-ENABLED with targeted patterns
    # Now uses VERY SPECIFIC patterns to catch only explicit admissions of ignorance:
    # - "i don't have the ability to access"
    # - "please check ESPN/CBS Sports"
    # - "consult official league"
    # This avoids the false positives from broad patterns like "i apologize", "i don't have"
    validation_result, reason, suggestions = validator.validate_answer_quality(
        answer=state.answer,
        query=state.query,
        intent=state.intent.value if state.intent else "unknown"
    )

    if validation_result != ValidationResult.VALID:
        logger.warning(f"Answer quality validation failed: {reason}")
        logger.info(f"Suggestions: {suggestions}")

        # If we haven't already retried with web search, trigger fallback
        if "web_search_retry_attempted" not in state.entities:
            logger.info("Triggering web search retry for unhelpful answer")
            state.entities["web_search_retry_attempted"] = True
            state.entities["answer_validation_failure"] = reason

            # Trigger web search fallback (will re-retrieve and re-synthesize)
            try:
                await _fallback_to_web_search(state, "Answer Quality", reason)

                # Re-synthesize with new data
                logger.info("Re-synthesizing answer with web search data")
                state = await synthesize_node(state)

                # Don't validate again - accept this answer to avoid infinite loop
                state.validation_passed = True
                state.validation_reason = "Passed after web search retry"
                logger.info(f"Answer after web search retry: {state.answer[:100]}...")
                state.node_timings["validate"] = time.time() - start
                return state

            except Exception as e:
                logger.error(f"Web search retry failed: {e}", exc_info=True)
                # Continue with original answer even though it's unhelpful
                state.validation_passed = True
                state.validation_reason = "Failed answer quality but retry failed"
        else:
            # Already retried, don't loop forever
            logger.warning("Answer still unhelpful after web search retry - accepting it to avoid loops")
            state.validation_passed = True
            state.validation_reason = "Accepted after failed retry"

    # Layer 2: Pattern detection for hallucinations
    # Look for specific patterns that indicate fabricated information
    import re

    # Detect specific dates (Month DD, YYYY or MM/DD/YYYY)
    date_patterns = re.findall(r'(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b)', state.answer)

    # Detect specific times (HH:MM AM/PM)
    time_patterns = re.findall(r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b', state.answer)

    # Detect specific dollar amounts
    money_patterns = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', state.answer)

    # Detect phone numbers
    phone_patterns = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', state.answer)

    has_specific_facts = bool(date_patterns or time_patterns or money_patterns or phone_patterns)

    # Layer 3: Check if we have data to support specific facts
    has_supporting_data = bool(state.retrieved_data)

    if has_specific_facts and not has_supporting_data:
        logger.warning(f"Response contains specific facts but no supporting data retrieved")
        logger.warning(f"Dates: {date_patterns}, Times: {time_patterns}, Money: {money_patterns}, Phones: {phone_patterns}")

        # Layer 4: LLM-based fact checking
        try:
            fact_check_prompt = f"""You are a fact-checking assistant. Analyze this response for hallucinations.

Original Query: {state.query}

Retrieved Data Available: {'Yes' if state.retrieved_data else 'No'}
{f"Retrieved Data: {json.dumps(state.retrieved_data, indent=2)}" if state.retrieved_data else "No data was retrieved from external sources."}

Generated Response:
{state.answer}

Question: Does this response contain specific factual claims (dates, times, names, phone numbers, prices, events) that are NOT present in the Retrieved Data?

IMPORTANT: If no Retrieved Data is available, ANY specific factual claims are likely hallucinations.

Respond ONLY with valid JSON:
{{"contains_hallucinations": true/false, "reason": "brief explanation", "specific_claims": ["list of suspicious claims"]}}"""

            # Combine system and user prompts
            full_fact_check_prompt = f"You are a precise fact-checking assistant. Always respond with valid JSON.\n\n{fact_check_prompt}"

            result = await llm_router.generate(
                model=ModelTier.SMALL.value,  # OPTIMIZATION: Fix bug - use SMALL model for validation
                prompt=full_fact_check_prompt,
                temperature=0.1,  # Low temperature for consistent checking
                request_id=state.request_id,
                session_id=state.session_id,
                user_id=state.mode,
                zone=state.room
            )

            fact_check_response = result.get("response", "")

            # Parse fact check response
            try:
                # Extract JSON from response (handle markdown code blocks)
                json_match = re.search(r'\{.*\}', fact_check_response, re.DOTALL)
                if json_match:
                    fact_check_result = json.loads(json_match.group())

                    if fact_check_result.get("contains_hallucinations", False):
                        state.validation_passed = False
                        state.validation_reason = f"Hallucination detected: {fact_check_result.get('reason', 'Unknown')}"
                        state.validation_details = fact_check_result.get("specific_claims", [])
                        logger.warning(f"Hallucination detected by LLM fact checker: {state.validation_reason}")
                        logger.warning(f"Suspicious claims: {state.validation_details}")
                    else:
                        state.validation_passed = True
                        logger.info("Response passed LLM fact checking")
                else:
                    logger.warning(f"Could not parse fact check response as JSON: {fact_check_response}")
                    # Default to failing validation if we can't parse
                    state.validation_passed = False
                    state.validation_reason = "Could not verify response accuracy"

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse fact check JSON: {e}")
                # Default to failing validation if we can't parse
                state.validation_passed = False
                state.validation_reason = "Could not verify response accuracy"

        except Exception as e:
            logger.error(f"Fact checking error: {e}", exc_info=True)
            # If fact checking fails, be conservative and fail validation
            state.validation_passed = False
            state.validation_reason = f"Validation error: {str(e)}"

    else:
        # No specific facts or we have supporting data
        state.validation_passed = True
        logger.info("Response passed validation (no specific facts or has supporting data)")

    state.node_timings["validate"] = time.time() - start
    return state

async def finalize_node(state: OrchestratorState) -> OrchestratorState:
    """
    Prepare final response with fallbacks for validation failures.
    """
    start = time.time()

    if not state.validation_passed:
        # Provide fallback response based on validation failure reason
        logger.warning(f"Validation failed, providing fallback response: {state.validation_reason}")

        if "hallucination" in state.validation_reason.lower():
            # Hallucination detected - provide helpful fallback
            state.answer = f"I don't have current information to answer that accurately. I recommend checking reliable sources for up-to-date information about {state.query.lower()}."
        elif state.error:
            state.answer = "I encountered an issue processing your request. Please try rephrasing your question."
        else:
            state.answer = "I'm not confident in my response. Could you please rephrase your question?"

    # Calculate total processing time
    total_time = time.time() - state.start_time
    logger.info(
        f"Request {state.request_id} completed in {total_time:.2f}s",
        extra={
            "request_id": state.request_id,
            "intent": state.intent,
            "total_time": total_time,
            "node_timings": state.node_timings
        }
    )

    # Cache conversation context for follow-ups
    await cache_client.set(
        f"conversation:{state.request_id}",
        {
            "query": state.query,
            "intent": state.intent.value if state.intent else None,
            "answer": state.answer,
            "timestamp": time.time()
        },
        ttl=3600  # 1 hour TTL
    )

    state.node_timings["finalize"] = time.time() - start
    return state

# ============================================================================
# LangGraph State Machine
# ============================================================================

def create_orchestrator_graph() -> StateGraph:
    """Create the LangGraph state machine."""

    # Initialize graph with state schema
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("route_control", route_control_node)
    graph.add_node("route_info", route_info_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("validate", validate_node)
    graph.add_node("finalize", finalize_node)

    # Define edges
    graph.set_entry_point("classify")

    # Conditional routing after classification
    def route_after_classify(state: OrchestratorState) -> str:
        if state.intent == IntentCategory.CONTROL:
            return "route_control"
        elif state.intent == IntentCategory.UNKNOWN:
            return "finalize"  # Skip to finalize for unknown intents
        else:
            return "route_info"

    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "route_control": "route_control",
            "route_info": "route_info",
            "finalize": "finalize"
        }
    )

    # Control path
    graph.add_edge("route_control", "finalize")

    # Info path
    graph.add_edge("route_info", "retrieve")
    graph.add_edge("retrieve", "synthesize")
    graph.add_edge("synthesize", "validate")
    graph.add_edge("validate", "finalize")

    # End
    graph.add_edge("finalize", END)

    return graph.compile()

# Create global graph instance
orchestrator_graph = None

# ============================================================================
# API Endpoints
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="User's query")
    mode: Literal["owner", "guest"] = Field("owner", description="User mode")
    room: str = Field("unknown", description="Room identifier")
    temperature: float = Field(0.7, ge=0, le=2, description="LLM temperature")
    model: Optional[str] = Field(None, description="Preferred model")
    session_id: Optional[str] = Field(None, description="Conversation session ID (optional, will create new if not provided)")

class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str = Field(..., description="Generated response")
    intent: str = Field(..., description="Detected intent category")
    confidence: float = Field(..., description="Classification confidence")
    citations: List[str] = Field(default_factory=list, description="Data sources")
    request_id: str = Field(..., description="Request tracking ID")
    session_id: str = Field(..., description="Conversation session ID")
    processing_time: float = Field(..., description="Total processing time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a user query through the orchestrator state machine.
    """
    global orchestrator_graph

    # Initialize graph if needed
    if orchestrator_graph is None:
        orchestrator_graph = create_orchestrator_graph()

    # Track request
    request_counter.labels(intent="unknown", status="started").inc()

    try:
        # Session management: get or create session
        session = await session_manager.get_or_create_session(
            session_id=request.session_id,
            user_id=request.mode,  # Use mode as user_id for now
            zone=request.room
        )

        logger.info(f"Processing query in session {session.session_id}")

        # Get conversation history for LLM context
        config = await get_config()
        conv_settings = await config.get_conversation_settings()

        # Only load history if conversation context is enabled
        conversation_history = []
        if conv_settings.get("enabled", True) and conv_settings.get("use_context", True):
            max_history = conv_settings.get("max_llm_history_messages", 10)
            conversation_history = session.get_llm_history(max_history)
            logger.info(f"Loaded {len(conversation_history)} previous messages from session")

        # Create initial state with conversation history
        initial_state = OrchestratorState(
            query=request.query,
            mode=request.mode,
            room=request.room,
            temperature=request.temperature,
            session_id=session.session_id,
            conversation_history=conversation_history
        )

        # Run through state machine
        with request_duration.labels(intent="processing").time():
            final_state = await orchestrator_graph.ainvoke(initial_state)

        # Track metrics
        intent_value = final_state.get("intent")
        if intent_value and hasattr(intent_value, "value"):
            intent_str = intent_value.value
        elif isinstance(intent_value, str):
            intent_str = intent_value
        else:
            intent_str = "unknown"

        request_counter.labels(
            intent=intent_str,
            status="success"
        ).inc()

        # Add messages to session history
        answer = final_state.get("answer") or "I couldn't process that request."

        # Extract model_tier for session metadata
        model_tier = final_state.get("model_tier")

        # Add user message to session
        session.add_message(
            role="user",
            content=request.query,
            metadata={
                "intent": intent_str,
                "confidence": final_state.get("confidence"),
                "room": request.room
            }
        )

        # Add assistant response to session
        session.add_message(
            role="assistant",
            content=answer,
            metadata={
                "model_tier": model_tier.value if model_tier and hasattr(model_tier, "value") else str(model_tier),
                "data_source": final_state.get("data_source"),
                "validation_passed": final_state.get("validation_passed")
            }
        )

        # Save session (with trimming based on config)
        await session_manager.add_message(
            session_id=session.session_id,
            role="user",
            content=request.query,
            metadata={"intent": intent_str, "confidence": final_state.get("confidence")}
        )
        await session_manager.add_message(
            session_id=session.session_id,
            role="assistant",
            content=answer,
            metadata={"model_tier": model_tier.value if model_tier and hasattr(model_tier, "value") else str(model_tier)}
        )

        logger.info(f"Session {session.session_id} updated with {len(session.messages)} total messages")

        # Build response
        model_tier_str = model_tier.value if model_tier and hasattr(model_tier, "value") else model_tier

        return QueryResponse(
            answer=answer,
            intent=intent_str if intent_str != "unknown" else IntentCategory.UNKNOWN.value,
            confidence=final_state.get("confidence"),
            citations=final_state.get("citations"),
            request_id=final_state.get("request_id"),
            session_id=session.session_id,
            processing_time=time.time() - final_state.get("start_time", time.time()),
            metadata={
                "model_used": model_tier_str,
                "data_source": final_state.get("data_source"),
                "validation_passed": final_state.get("validation_passed"),
                "node_timings": final_state.get("node_timings"),
                "conversation_turns": len(session.messages) // 2
            }
        )

    except Exception as e:
        logger.error(f"Query processing error: {e}", exc_info=True)
        request_counter.labels(intent="unknown", status="error").inc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0",
        "components": {}
    }

    # Check Home Assistant
    try:
        ha_healthy = await ha_client.health_check() if ha_client else False
        health["components"]["home_assistant"] = ha_healthy
    except:
        health["components"]["home_assistant"] = False

    # Check LLM Router (supports Ollama, MLX, etc.)
    try:
        health["components"]["llm_router"] = llm_router is not None
    except:
        health["components"]["llm_router"] = False

    # Check Redis
    try:
        await cache_client.client.ping() if cache_client else False
        health["components"]["redis"] = True
    except:
        health["components"]["redis"] = False

    # Check RAG services
    for name, client in rag_clients.items():
        try:
            response = await client.get("/health")
            health["components"][f"rag_{name}"] = response.status_code == 200
        except:
            health["components"][f"rag_{name}"] = False

    # Determine overall health
    critical_components = ["llm_router", "redis"]
    if not all(health["components"].get(c, False) for c in critical_components):
        health["status"] = "unhealthy"
    elif not all(health["components"].values()):
        health["status"] = "degraded"

    return health

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")

@app.get("/llm-metrics")
async def llm_metrics():
    """
    Get LLM performance metrics from the router.

    Returns aggregated metrics including:
    - Overall average latency and tokens/sec
    - Per-model breakdown
    - Per-backend breakdown
    """
    try:
        metrics_data = llm_router.report_metrics()
        return metrics_data
    except Exception as e:
        logger.error(f"Failed to retrieve LLM metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )

# ============================================================================
# Session Management Endpoints (Phase 2)
# ============================================================================

class SessionListResponse(BaseModel):
    """Response model for session list."""
    sessions: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = Field(..., description="Total number of sessions")

class SessionDetailResponse(BaseModel):
    """Response model for session details."""
    session_id: str
    user_id: Optional[str]
    zone: Optional[str]
    created_at: str
    last_activity: str
    message_count: int
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = 50,
    offset: int = 0
) -> SessionListResponse:
    """
    List all active conversation sessions.

    Query Parameters:
    - limit: Maximum number of sessions to return (default 50)
    - offset: Number of sessions to skip (default 0)
    """
    # Note: This is a simplified implementation
    # In production, you'd want to add pagination support to the session manager

    # For now, we'll return an empty list since session_manager stores sessions in Redis/memory
    # and doesn't have a built-in list_all method

    logger.info(f"Listing sessions (limit={limit}, offset={offset})")

    return SessionListResponse(
        sessions=[],
        total=0
    )

@app.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_details(session_id: str) -> SessionDetailResponse:
    """
    Get details of a specific session including message history.

    Path Parameters:
    - session_id: Session identifier
    """
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    logger.info(f"Retrieved session {session_id} with {len(session.messages)} messages")

    return SessionDetailResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        zone=session.zone,
        created_at=session.created_at.isoformat(),
        last_activity=session.last_activity.isoformat(),
        message_count=len(session.messages),
        messages=session.messages,
        metadata=session.metadata
    )

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a conversation session.

    Path Parameters:
    - session_id: Session identifier
    """
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    await session_manager.delete_session(session_id)

    logger.info(f"Deleted session {session_id}")

    return {"status": "success", "message": f"Session {session_id} deleted"}

@app.get("/sessions/{session_id}/export")
async def export_session_history(session_id: str, format: str = "json"):
    """
    Export session history in various formats.

    Path Parameters:
    - session_id: Session identifier

    Query Parameters:
    - format: Export format (json, text, markdown) - default: json
    """
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if format == "json":
        return {
            "session_id": session.session_id,
            "messages": session.messages,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }

    elif format == "text":
        lines = [f"Conversation Session: {session.session_id}"]
        lines.append(f"Created: {session.created_at.isoformat()}")
        lines.append(f"Last Activity: {session.last_activity.isoformat()}")
        lines.append("=" * 80)
        lines.append("")

        for msg in session.messages:
            role = msg["role"].upper()
            content = msg["content"]
            timestamp = msg.get("timestamp", "")
            lines.append(f"[{timestamp}] {role}:")
            lines.append(content)
            lines.append("")

        return Response(content="\n".join(lines), media_type="text/plain")

    elif format == "markdown":
        lines = [f"# Conversation Session: {session.session_id}"]
        lines.append(f"**Created:** {session.created_at.isoformat()}")
        lines.append(f"**Last Activity:** {session.last_activity.isoformat()}")
        lines.append("")

        for msg in session.messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            timestamp = msg.get("timestamp", "")
            lines.append(f"### {role} ({timestamp})")
            lines.append(content)
            lines.append("")

        return Response(content="\n".join(lines), media_type="text/markdown")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
