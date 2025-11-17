"""
Project Athena Gateway Service

OpenAI-compatible API that routes requests to the orchestrator for
Athena-specific queries or falls back to Ollama for general queries.
"""

import os
import json
import time
import uuid
from typing import AsyncIterator, Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

# Add to Python path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.logging_config import configure_logging
from shared.ollama_client import OllamaClient
from shared.admin_config import get_admin_client
from gateway.device_session_manager import get_device_session_manager, DeviceSessionManager

# Configure logging
logger = configure_logging("gateway")

# Metrics
request_counter = Counter(
    'gateway_requests_total',
    'Total requests to gateway',
    ['endpoint', 'status']
)
request_duration = Histogram(
    'gateway_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint']
)

# Global clients
orchestrator_client: Optional[httpx.AsyncClient] = None
ollama_client: Optional[OllamaClient] = None
device_session_mgr: Optional[DeviceSessionManager] = None
admin_client = None  # Admin API client for configuration

# Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8001")
OLLAMA_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:11434")  # Fallback if DB empty
API_KEY = os.getenv("GATEWAY_API_KEY", "dummy-key")  # Optional for Phase 1
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://athena-admin-backend.athena-admin.svc.cluster.local:8080")

# Feature flag cache
_feature_cache = {}
_cache_expiry = 0
_cache_ttl = 60  # 60 seconds

# LLM backends cache (from database)
_llm_backends_cache = []
_llm_backends_cache_time = 0

# Model mapping (OpenAI -> Ollama) - Fallback if database is empty
MODEL_MAPPING = {
    "gpt-3.5-turbo": "phi3:mini",
    "gpt-4": "llama3.1:8b",
    "gpt-4-32k": "llama3.1:8b",
}

async def get_llm_backends():
    """
    Fetch enabled LLM backends from Admin API with caching.

    Returns list of backend configurations sorted by priority,
    or empty list if database is unavailable (triggers env var fallback).
    """
    global _llm_backends_cache, _llm_backends_cache_time

    now = time.time()
    if now > _llm_backends_cache_time + _cache_ttl:
        # Cache expired, refresh
        try:
            backends = await admin_client.get_llm_backends()
            if backends:
                _llm_backends_cache = backends
                _llm_backends_cache_time = now
                logger.info(f"LLM backends loaded from DB: {[b.get('model_name') for b in backends]}")
            else:
                logger.warning("No LLM backends found in database, using environment variable fallback")
        except Exception as e:
            logger.warning(f"Failed to load LLM backends from database: {e}")

    return _llm_backends_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global orchestrator_client, ollama_client, device_session_mgr, admin_client

    # Startup
    logger.info("Starting Gateway service")

    # Initialize admin config client for database-driven configuration
    admin_client = get_admin_client()
    logger.info("Admin config client initialized")

    orchestrator_client = httpx.AsyncClient(
        base_url=ORCHESTRATOR_URL,
        timeout=60.0
    )

    # Load LLM backends from database (with fallback to env var)
    backends = await get_llm_backends()
    if backends:
        # Use first backend as primary Ollama URL
        primary_backend = backends[0]
        ollama_url = primary_backend.get("endpoint_url", OLLAMA_URL)
        logger.info(f"Using LLM backend from database: {primary_backend.get('model_name')} @ {ollama_url}")
    else:
        ollama_url = OLLAMA_URL
        logger.info(f"Using fallback Ollama URL from environment: {ollama_url}")

    ollama_client = OllamaClient(url=ollama_url)
    device_session_mgr = await get_device_session_manager()
    logger.info("Device session manager initialized")

    # Check orchestrator health
    try:
        response = await orchestrator_client.get("/health")
        if response.status_code == 200:
            logger.info("Orchestrator is healthy")
        else:
            logger.warning(f"Orchestrator unhealthy: {response.status_code}")
    except Exception as e:
        logger.warning(f"Orchestrator not available: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Gateway service")
    if device_session_mgr:
        await device_session_mgr.close()
    if orchestrator_client:
        await orchestrator_client.aclose()
    if ollama_client:
        await ollama_client.close()
    if admin_client:
        await admin_client.close()

app = FastAPI(
    title="Athena Gateway",
    description="OpenAI-compatible API gateway for Project Athena",
    version="1.0.0",
    lifespan=lifespan
)

# Request/Response models (OpenAI-compatible)
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Optional name")

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model to use")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")
    top_p: float = Field(1.0, ge=0, le=1, description="Top-p sampling")
    n: int = Field(1, ge=1, le=10, description="Number of completions")
    stream: bool = Field(False, description="Stream response")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    max_tokens: Optional[int] = Field(None, description="Max tokens to generate")
    presence_penalty: float = Field(0, ge=-2, le=2)
    frequency_penalty: float = Field(0, ge=-2, le=2)
    user: Optional[str] = Field(None, description="User identifier")

class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Dict[str, int]

# Home Assistant Conversation API models
class HAConversationRequest(BaseModel):
    """
    Home Assistant conversation request from Voice PE devices.

    This matches the format that Home Assistant sends when a voice device
    (Wyoming protocol) triggers a conversation.
    """
    text: str = Field(..., description="User's voice query transcribed to text")
    language: str = Field("en", description="Language code (default: en)")
    conversation_id: Optional[str] = Field(None, description="HA conversation ID (optional)")
    device_id: Optional[str] = Field(None, description="Voice PE device identifier (e.g., 'office', 'kitchen')")
    agent_id: Optional[str] = Field(None, description="HA agent ID")

class HAConversationResponse(BaseModel):
    """
    Home Assistant conversation response format.

    This is returned to Home Assistant which then synthesizes it to speech
    and plays it back through the Voice PE device.
    """
    response: Dict[str, Any] = Field(..., description="Response structure")
    conversation_id: Optional[str] = Field(None, description="Session ID for conversation context")

# API key validation (optional for Phase 1)
async def validate_api_key(request: Request):
    """Validate API key if configured."""
    if API_KEY == "dummy-key":
        return True  # Skip validation in dev

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    token = auth_header.replace("Bearer ", "")
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True

async def is_feature_enabled(feature_name: str) -> bool:
    """
    Check if feature is enabled via Admin API with caching.

    Args:
        feature_name: Name of feature flag to check (e.g., 'llm_based_routing')

    Returns:
        True if feature is enabled, False otherwise

    Note:
        Uses 60-second TTL cache to avoid hitting Admin API on every request.
        If Admin API is unavailable, returns False (safe default).
    """
    global _feature_cache, _cache_expiry

    now = time.time()
    if now > _cache_expiry:
        # Refresh cache
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Use public endpoint (no auth required)
                response = await client.get(f"{ADMIN_API_URL}/api/features/public")
                if response.status_code == 200:
                    features = response.json()
                    _feature_cache = {f["name"]: f["enabled"] for f in features}
                    _cache_expiry = now + _cache_ttl
                    logger.debug(f"Feature cache refreshed: {len(_feature_cache)} features")
                else:
                    logger.warning(f"Failed to fetch features: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to fetch features from Admin API: {e}")

    return _feature_cache.get(feature_name, False)


async def _log_metric_to_db(
    timestamp: float,
    model: str,
    backend: str,
    latency_seconds: float,
    tokens: int,
    tokens_per_second: float,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    zone: Optional[str] = None,
    intent: Optional[str] = None,
    source: Optional[str] = None
):
    """
    Log LLM performance metric to admin database (fire-and-forget).

    Args:
        timestamp: Unix timestamp of request start
        model: Model name used
        backend: Backend type (ollama, mlx, auto)
        latency_seconds: Total request latency
        tokens: Number of tokens generated
        tokens_per_second: Token generation speed
        request_id: Optional request ID
        session_id: Optional session ID
        user_id: Optional user ID
        zone: Optional zone/location
        intent: Optional intent classification
        source: Optional source service (gateway, orchestrator, etc.)

    Note:
        Failures are logged but don't raise exceptions to avoid
        impacting the main LLM request flow.
    """
    try:
        metric_payload = {
            "timestamp": timestamp,
            "model": model,
            "backend": backend,
            "latency_seconds": latency_seconds,
            "tokens": tokens,
            "tokens_per_second": tokens_per_second,
            "request_id": request_id,
            "session_id": session_id,
            "user_id": user_id,
            "zone": zone,
            "intent": intent,
            "source": source
        }

        url = f"{ADMIN_API_URL}/api/llm-backends/metrics"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=metric_payload, timeout=5.0)
            if response.status_code == 201:
                logger.info(
                    "metric_logged_to_db",
                    model=model,
                    backend=backend,
                    tokens_per_sec=round(tokens_per_second, 2)
                )
            else:
                logger.warning(
                    "failed_to_log_metric",
                    status_code=response.status_code,
                    error=response.text[:200]
                )
    except Exception as e:
        logger.error(f"Metric logging error: {e}", exc_info=False)


async def classify_intent_llm(query: str) -> bool:
    """
    Use LLM to classify if query should route to orchestrator.

    Uses phi3:mini-q8 model for fast, accurate intent classification.
    Classifies queries into two categories:
    - athena: Home control, weather, sports, airports, local info (Baltimore context)
    - general: General knowledge, math, coding, explanations

    Args:
        query: User query to classify

    Returns:
        True if orchestrator should handle (athena), False for Ollama (general)

    Note:
        Falls back to keyword matching if LLM call fails.
        Target latency: 50-200ms
    """
    prompt = f"""Classify this query into ONE category:

Query: "{query}"

Categories:
- athena: Home control, weather, sports, airports, local info (Baltimore context)
- general: General knowledge, math, coding, explanations

Respond with ONLY the category name (athena or general)."""

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "phi3:mini",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent classification
                        "num_predict": 10     # Only need one word response
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            classification = result.get("response", "").strip().lower()

            is_athena = "athena" in classification
            logger.info(f"LLM classified '{query}' as {'athena' if is_athena else 'general'}")
            return is_athena

    except Exception as e:
        logger.error(f"LLM classification failed: {e}, falling back to keyword matching")
        # Fallback to keyword matching
        # Create a temporary ChatMessage for keyword matching
        from pydantic import BaseModel
        temp_messages = [ChatMessage(role="user", content=query)]
        return is_athena_query_keywords(temp_messages)


def is_athena_query_keywords(messages: List[ChatMessage]) -> bool:
    """
    Keyword-based classification (fast, 0ms overhead).

    Used as fallback when LLM is disabled or fails.
    Matches queries against predefined keyword patterns for:
    - Home automation control (lights, switches, climate)
    - Weather queries
    - Airport/flight information
    - Sports information (all major leagues and teams)
    - Location-specific queries (Baltimore context)
    - Recipes and cooking
    - Entertainment and events

    Args:
        messages: Chat messages list

    Returns:
        True if orchestrator should handle, False for Ollama
    """
    # Get the last user message
    last_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            last_user_msg = msg.content.lower()
            break

    if not last_user_msg:
        return False

    # Athena-specific patterns
    athena_patterns = [
        # Home control
        "turn on", "turn off", "set", "dim", "brighten",
        "lights", "switch", "temperature", "thermostat",
        # Weather
        "weather", "forecast", "rain", "snow", "temperature outside",
        # Airports/flights
        "airport", "flight", "delay", "departure", "arrival",
        "bwi", "dca", "iad", "phl", "jfk", "lga", "ewr",
        # Sports - General
        "game", "score", "team", "schedule", "match", "vs", "versus",
        "playoff", "championship", "tournament", "season", "league",
        # Sports - Types
        "football", "soccer", "basketball", "baseball", "hockey", "olympics",
        # Sports - Leagues
        "nfl", "nba", "mlb", "nhl", "mls", "ncaa", "fifa", "ufc", "pga",
        # NFL Teams
        "ravens", "steelers", "browns", "bengals", "cowboys", "eagles",
        "giants", "commanders", "packers", "bears", "vikings", "lions",
        "saints", "falcons", "panthers", "buccaneers", "49ers", "seahawks",
        "rams", "cardinals", "patriots", "bills", "dolphins", "jets",
        "chiefs", "broncos", "raiders", "chargers", "colts", "texans",
        "jaguars", "titans",
        # MLB Teams
        "orioles", "yankees", "red sox", "blue jays", "rays", "white sox",
        "guardians", "tigers", "royals", "twins", "astros", "angels",
        "athletics", "mariners", "rangers", "braves", "marlins", "mets",
        "phillies", "nationals", "cubs", "reds", "brewers", "pirates",
        "cardinals", "diamondbacks", "rockies", "dodgers", "padres", "giants",
        # NBA Teams
        "celtics", "nets", "knicks", "76ers", "raptors", "bulls", "cavaliers",
        "pistons", "pacers", "bucks", "hawks", "hornets", "heat", "magic",
        "wizards", "nuggets", "timberwolves", "thunder", "trail blazers",
        "jazz", "warriors", "clippers", "lakers", "suns", "kings",
        "mavericks", "rockets", "grizzlies", "pelicans", "spurs",
        # NHL Teams
        "bruins", "sabres", "red wings", "panthers", "canadiens", "senators",
        "lightning", "maple leafs", "hurricanes", "blue jackets", "devils",
        "islanders", "rangers", "flyers", "penguins", "capitals", "blackhawks",
        "avalanche", "stars", "wild", "predators", "blues", "jets",
        "ducks", "flames", "oilers", "kings", "sharks", "kraken", "canucks",
        "golden knights", "coyotes",
        # MLS Teams (Soccer)
        "atlanta united", "austin fc", "charlotte fc", "chicago fire", "fc cincinnati",
        "colorado rapids", "columbus crew", "dc united", "fc dallas", "houston dynamo",
        "la galaxy", "lafc", "inter miami", "minnesota united", "montreal", "nashville sc",
        "new england revolution", "new york red bulls", "new york city fc", "orlando city",
        "philadelphia union", "portland timbers", "real salt lake", "san jose earthquakes",
        "seattle sounders", "sporting kansas city", "toronto fc", "vancouver whitecaps",
        # Major International Soccer Teams
        "manchester united", "manchester city", "liverpool", "chelsea", "arsenal", "tottenham",
        "barcelona", "real madrid", "atletico madrid", "bayern munich", "borussia dortmund",
        "juventus", "ac milan", "inter milan", "psg", "paris saint-germain",
        # Location context
        "baltimore", "home", "office", "bedroom", "kitchen",
        # Recipes and cooking (RAG + web search)
        "recipe", "cook", "how to make", "ingredients", "cooking",
        # Entertainment and events (web search)
        "concert", "perform", "tour", "show", "event", "when does",
        "who is", "what is", "tell me about"
    ]

    return any(pattern in last_user_msg for pattern in athena_patterns)


async def is_athena_query(messages: List[ChatMessage]) -> bool:
    """
    Main routing decision function.

    Uses LLM or keywords based on feature flag configuration.
    Checks 'llm_based_routing' feature flag to determine routing method:
    - If enabled: Use LLM-based intent classification (more accurate, +50-200ms)
    - If disabled: Use keyword-based pattern matching (fast, 0ms overhead)

    Args:
        messages: Chat messages list

    Returns:
        True if orchestrator should handle, False for Ollama

    Note:
        Feature flag is cached for 60 seconds to avoid hitting Admin API on every request.
        LLM classification falls back to keyword matching if it fails.
    """
    # Get the last user message for LLM classification
    last_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            last_user_msg = msg.content
            break

    if not last_user_msg:
        return False

    # Check feature flag (cached for 60 seconds)
    use_llm = await is_feature_enabled("llm_based_routing")

    if use_llm:
        logger.info("Using LLM-based routing")
        return await classify_intent_llm(last_user_msg)
    else:
        logger.info("Using keyword-based routing")
        return is_athena_query_keywords(messages)


async def route_to_orchestrator(
    request: ChatCompletionRequest,
    device_id: Optional[str] = None,
    session_id: Optional[str] = None,
    return_session_id: bool = False
) -> Union[ChatCompletionResponse, tuple]:
    """
    Route request to Athena orchestrator.

    Args:
        request: OpenAI-compatible chat completion request
        device_id: Optional Voice PE device identifier for session management
        session_id: Optional session ID to continue conversation
        return_session_id: If True, returns tuple of (response, session_id)

    Returns:
        ChatCompletionResponse with orchestrator's answer, or tuple if return_session_id=True
    """
    try:
        # Extract user message
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content

        # Call orchestrator with session support
        with request_duration.labels(endpoint="orchestrator").time():
            payload = {
                "query": user_message,
                "mode": "owner",  # Default to owner mode
                "room": device_id or "unknown",  # Use device_id as room if available
                "temperature": request.temperature,
                "model": MODEL_MAPPING.get(request.model, "phi3:mini")
            }

            # Include session_id if provided (for conversation context)
            if session_id:
                payload["session_id"] = session_id

            response = await orchestrator_client.post("/query", json=payload)
            response.raise_for_status()

        result = response.json()

        # Format as OpenAI response
        chat_response = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=result.get("answer", "I couldn't process that request.")
                    ),
                    finish_reason="stop"
                )
            ],
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(result.get("answer", "").split()),
                "total_tokens": len(user_message.split()) + len(result.get("answer", "").split())
            }
        )

        # Return session_id if requested (for HA conversation endpoint)
        if return_session_id:
            orchestrator_session_id = result.get("session_id", f"session-{uuid.uuid4().hex[:8]}")
            return chat_response, orchestrator_session_id

        return chat_response

    except httpx.HTTPStatusError as e:
        logger.error(f"Orchestrator error: {e}")
        raise HTTPException(status_code=502, detail="Orchestrator error")
    except Exception as e:
        logger.error(f"Failed to route to orchestrator: {e}", exc_info=True)
        # Fall back to Ollama
        if return_session_id:
            fallback_response = await route_to_ollama(request)
            return fallback_response, f"session-{uuid.uuid4().hex[:8]}"
        return await route_to_ollama(request)

async def route_to_ollama(
    request: ChatCompletionRequest,
    device_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> ChatCompletionResponse:
    """Route request directly to Ollama with metric logging."""
    start_time = time.time()

    try:
        # Map model name
        ollama_model = MODEL_MAPPING.get(request.model, request.model)

        # Convert messages format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # Call Ollama
        with request_duration.labels(endpoint="ollama").time():
            response_text = ""
            eval_count = 0
            async for chunk in ollama_client.chat(
                model=ollama_model,
                messages=messages,
                temperature=request.temperature,
                stream=False
            ):
                if chunk.get("done"):
                    response_text = chunk.get("message", {}).get("content", "")
                    eval_count = chunk.get("eval_count", 0)
                    break

        # Calculate metrics
        latency_seconds = time.time() - start_time
        tokens = eval_count or len(response_text.split())  # Fallback to word count
        tokens_per_second = tokens / latency_seconds if latency_seconds > 0 and tokens > 0 else 0

        # Log metrics to database (fire-and-forget)
        import asyncio
        asyncio.create_task(_log_metric_to_db(
            timestamp=start_time,
            model=ollama_model,
            backend="ollama",
            latency_seconds=latency_seconds,
            tokens=tokens,
            tokens_per_second=tokens_per_second,
            request_id=f"gateway-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            user_id=user_id,
            zone=device_id,
            intent=None,
            source="gateway"
        ))

        # Format as OpenAI response
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response_text
                    ),
                    finish_reason="stop"
                )
            ],
            usage={
                "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
                "completion_tokens": len(response_text.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(response_text.split())
            }
        )

    except Exception as e:
        logger.error(f"Ollama error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="LLM service error")

async def stream_response(request: ChatCompletionRequest) -> AsyncIterator[str]:
    """Stream response from Ollama (orchestrator doesn't support streaming yet)."""
    try:
        # Only Ollama supports streaming for now
        ollama_model = MODEL_MAPPING.get(request.model, request.model)
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # Stream from Ollama
        async for chunk in ollama_client.chat(
            model=ollama_model,
            messages=messages,
            temperature=request.temperature,
            stream=True
        ):
            if not chunk.get("done"):
                # Format as OpenAI streaming chunk
                data = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": chunk.get("message", {}).get("content", "")
                        },
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"

        # Send final chunk
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    _: bool = Depends(validate_api_key)
):
    """
    OpenAI-compatible chat completions endpoint.
    Routes to orchestrator for Athena queries, Ollama for general queries.
    """
    request_counter.labels(endpoint="chat_completions", status="started").inc()

    try:
        # Handle streaming
        if request.stream:
            request_counter.labels(endpoint="chat_completions", status="streaming").inc()
            return StreamingResponse(
                stream_response(request),
                media_type="text/event-stream"
            )

        # Route based on query type (LLM or keyword-based, controlled by feature flag)
        if await is_athena_query(request.messages):
            logger.info("Routing to orchestrator")
            response = await route_to_orchestrator(request)
        else:
            logger.info("Routing to Ollama")
            response = await route_to_ollama(request)

        request_counter.labels(endpoint="chat_completions", status="success").inc()
        return response

    except HTTPException:
        request_counter.labels(endpoint="chat_completions", status="error").inc()
        raise
    except Exception as e:
        request_counter.labels(endpoint="chat_completions", status="error").inc()
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "gateway",
        "version": "1.0.0"
    }

    # Check orchestrator
    try:
        response = await orchestrator_client.get("/health")
        health["orchestrator"] = response.status_code == 200
    except:
        health["orchestrator"] = False

    # Check Ollama
    try:
        models = await ollama_client.list_models()
        health["ollama"] = len(models.get("models", [])) > 0
    except:
        health["ollama"] = False

    # Overall health
    if not health["orchestrator"] and not health["ollama"]:
        health["status"] = "unhealthy"
    elif not health["orchestrator"] or not health["ollama"]:
        health["status"] = "degraded"

    return health

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "athena"},
            {"id": "gpt-4", "object": "model", "owned_by": "athena"}
        ]
    }

@app.post("/ha/conversation", response_model=HAConversationResponse)
async def ha_conversation(request: HAConversationRequest):
    """
    Home Assistant conversation endpoint for Voice PE devices.

    This endpoint receives voice queries from Home Assistant's conversation integration
    (Wyoming protocol). It manages device-to-session mapping to maintain conversation
    context across multiple interactions with the same Voice PE device.

    Flow:
    1. Voice PE device captures wake word + voice input
    2. Wyoming protocol sends audio to HA
    3. HA transcribes to text and calls this endpoint
    4. Gateway gets/creates session for device
    5. Routes to orchestrator with session_id for context
    6. Updates device session mapping
    7. Returns response to HA
    8. HA synthesizes to speech and plays on Voice PE device

    Args:
        request: HAConversationRequest with text, device_id, etc.

    Returns:
        HAConversationResponse with answer and session_id
    """
    request_counter.labels(endpoint="ha_conversation", status="started").inc()

    try:
        device_id = request.device_id or "unknown"
        logger.info(f"HA conversation request from device: {device_id}, query: {request.text}")

        # Get active session for this device (or None to create new)
        existing_session_id = await device_session_mgr.get_session_for_device(device_id)

        if existing_session_id:
            logger.info(f"Using existing session {existing_session_id} for device {device_id}")
        else:
            logger.info(f"Creating new session for device {device_id}")

        # Create OpenAI-compatible request for routing
        chat_request = ChatCompletionRequest(
            model="gpt-4",  # Default model
            messages=[
                ChatMessage(role="user", content=request.text)
            ],
            temperature=0.7
        )

        # Route to orchestrator with device and session info
        with request_duration.labels(endpoint="ha_conversation").time():
            chat_response, orchestrator_session_id = await route_to_orchestrator(
                request=chat_request,
                device_id=device_id,
                session_id=existing_session_id,
                return_session_id=True
            )

        # Extract answer from chat response
        answer = chat_response.choices[0].message.content if chat_response.choices else "I couldn't process that request."

        # Update device session mapping with the orchestrator's session_id
        await device_session_mgr.update_session_for_device(device_id, orchestrator_session_id)
        logger.info(f"Updated session mapping: device {device_id} → session {orchestrator_session_id}")

        # Format response for Home Assistant
        ha_response = HAConversationResponse(
            response={
                "speech": {
                    "plain": {
                        "speech": answer,
                        "extra_data": None
                    }
                },
                "card": {},
                "language": request.language,
                "response_type": "action_done",
                "data": {
                    "success": True,
                    "targets": []
                }
            },
            conversation_id=orchestrator_session_id
        )

        request_counter.labels(endpoint="ha_conversation", status="success").inc()
        logger.info(f"HA conversation completed: device {device_id}, session {orchestrator_session_id}")

        return ha_response

    except HTTPException:
        request_counter.labels(endpoint="ha_conversation", status="error").inc()
        raise
    except Exception as e:
        request_counter.labels(endpoint="ha_conversation", status="error").inc()
        logger.error(f"HA conversation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)