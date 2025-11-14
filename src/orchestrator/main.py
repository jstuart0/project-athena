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
from typing import Dict, Any, Optional, List, Literal
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
from shared.ollama_client import OllamaClient
from shared.cache import CacheClient

# Parallel search imports
from orchestrator.search_providers.parallel_search import ParallelSearchEngine
from orchestrator.search_providers.result_fusion import ResultFusion

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
ollama_client: Optional[OllamaClient] = None
cache_client: Optional[CacheClient] = None
rag_clients: Dict[str, httpx.AsyncClient] = {}

# Configuration
WEATHER_SERVICE_URL = os.getenv("RAG_WEATHER_URL", "http://localhost:8010")
AIRPORTS_SERVICE_URL = os.getenv("RAG_AIRPORTS_URL", "http://localhost:8011")
SPORTS_SERVICE_URL = os.getenv("RAG_SPORTS_URL", "http://localhost:8012")
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
    global ha_client, ollama_client, cache_client, rag_clients, parallel_search_engine, result_fusion

    # Startup
    logger.info("Starting Orchestrator service")

    # Initialize clients
    ha_client = HomeAssistantClient()
    ollama_client = OllamaClient(url=OLLAMA_URL)
    cache_client = CacheClient()

    # Initialize parallel search engine
    parallel_search_engine = ParallelSearchEngine.from_environment()
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
    if ollama_client:
        await ollama_client.close()
    if cache_client:
        await cache_client.close()
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
# Node Implementations
# ============================================================================

async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """
    Classify user intent using LLM.
    Determines: control vs info, specific category, entities.
    """
    start = time.time()

    try:
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
        messages = [
            {"role": "system", "content": "You are an intent classifier. Respond only with valid JSON."},
            {"role": "user", "content": classification_prompt}
        ]

        response_text = ""
        async for chunk in ollama_client.chat(
            model=ModelTier.SMALL.value,
            messages=messages,
            temperature=0.3,  # Lower temperature for consistent classification
            stream=False
        ):
            if chunk.get("done"):
                response_text = chunk.get("message", {}).get("content", "")
                break

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

        logger.info(f"Classified query as {state.intent} with confidence {state.confidence}")

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
    if any(p in query_lower for p in ["game", "score", "ravens", "orioles", "team"]):
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

async def retrieve_node(state: OrchestratorState) -> OrchestratorState:
    """
    Retrieve information from appropriate RAG service.
    """
    start = time.time()

    try:
        if state.intent == IntentCategory.WEATHER:
            # Call weather service
            location = state.entities.get("location", "Baltimore, MD")
            client = rag_clients["weather"]

            response = await client.get(
                "/weather/current",
                params={"location": location}
            )
            response.raise_for_status()

            state.retrieved_data = response.json()
            state.data_source = "OpenWeatherMap"
            state.citations.append(f"Weather data from OpenWeatherMap for {location}")

        elif state.intent == IntentCategory.AIRPORTS:
            # Call airports service
            airport = state.entities.get("airport", "BWI")
            client = rag_clients["airports"]

            response = await client.get(f"/airports/{airport}")
            response.raise_for_status()

            state.retrieved_data = response.json()
            state.data_source = "FlightAware"
            state.citations.append(f"Flight data from FlightAware for {airport}")

        elif state.intent == IntentCategory.SPORTS:
            # Call sports service
            team = state.entities.get("team", "Ravens")
            client = rag_clients["sports"]

            # Search for team
            search_response = await client.get(
                "/sports/teams/search",
                params={"query": team}
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            if search_data.get("teams"):
                team_id = search_data["teams"][0]["idTeam"]

                # Get next event
                events_response = await client.get(f"/sports/events/{team_id}/next")
                events_response.raise_for_status()

                state.retrieved_data = events_response.json()
                state.data_source = "TheSportsDB"
                state.citations.append(f"Sports data from TheSportsDB for {team}")

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

    except httpx.HTTPStatusError as e:
        logger.error(f"RAG service error: {e}")
        state.error = f"Failed to retrieve data: {str(e)}"
    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        state.error = f"Retrieval failed: {str(e)}"

    state.node_timings["retrieve"] = time.time() - start
    return state

async def synthesize_node(state: OrchestratorState) -> OrchestratorState:
    """
    Generate natural language response using LLM with retrieved data.
    """
    start = time.time()

    try:
        # Build synthesis prompt with retrieved data
        if state.retrieved_data:
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
            # No data retrieved - must be explicit about lack of information
            synthesis_prompt = f"""Question: {state.query}

CRITICAL: You do NOT have access to current or specific information to answer this question.

You must respond with:
1. Acknowledge you don't have current/specific information
2. Suggest where the user can find this information
3. NEVER make up specific facts, dates, names, numbers, or events

Respond honestly about your limitations.

Response:"""

        # Use selected model tier
        messages = [
            {"role": "system", "content": "You are Athena, a helpful home assistant. Provide clear, concise answers."},
            {"role": "user", "content": synthesis_prompt}
        ]

        response_text = ""
        async for chunk in ollama_client.chat(
            model=state.model_tier.value if state.model_tier else ModelTier.MEDIUM.value,
            messages=messages,
            temperature=state.temperature,
            stream=False
        ):
            if chunk.get("done"):
                response_text = chunk.get("message", {}).get("content", "")
                break

        state.answer = response_text

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

            messages = [
                {"role": "system", "content": "You are a precise fact-checking assistant. Always respond with valid JSON."},
                {"role": "user", "content": fact_check_prompt}
            ]

            fact_check_response = ""
            async for chunk in ollama_client.chat(
                model=ModelTier.FAST.value,  # Use fast model for validation
                messages=messages,
                temperature=0.1,  # Low temperature for consistent checking
                stream=False
            ):
                if chunk.get("done"):
                    fact_check_response = chunk.get("message", {}).get("content", "")
                    break

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

class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str = Field(..., description="Generated response")
    intent: str = Field(..., description="Detected intent category")
    confidence: float = Field(..., description="Classification confidence")
    citations: List[str] = Field(default_factory=list, description="Data sources")
    request_id: str = Field(..., description="Request tracking ID")
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
        # Create initial state
        initial_state = OrchestratorState(
            query=request.query,
            mode=request.mode,
            room=request.room,
            temperature=request.temperature
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

        # Build response
        model_tier = final_state.get("model_tier")
        model_tier_str = model_tier.value if model_tier and hasattr(model_tier, "value") else model_tier

        return QueryResponse(
            answer=final_state.get("answer") or "I couldn't process that request.",
            intent=intent_str if intent_str != "unknown" else IntentCategory.UNKNOWN.value,
            confidence=final_state.get("confidence"),
            citations=final_state.get("citations"),
            request_id=final_state.get("request_id"),
            processing_time=time.time() - final_state.get("start_time", time.time()),
            metadata={
                "model_used": model_tier_str,
                "data_source": final_state.get("data_source"),
                "validation_passed": final_state.get("validation_passed"),
                "node_timings": final_state.get("node_timings")
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

    # Check Ollama
    try:
        models = await ollama_client.list_models() if ollama_client else {}
        health["components"]["ollama"] = len(models.get("models", [])) > 0
    except:
        health["components"]["ollama"] = False

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
    critical_components = ["ollama", "redis"]
    if not all(health["components"].get(c, False) for c in critical_components):
        health["status"] = "unhealthy"
    elif not all(health["components"].values()):
        health["status"] = "degraded"

    return health

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)