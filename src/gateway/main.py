"""
Project Athena Gateway Service

OpenAI-compatible API that routes requests to the orchestrator for
Athena-specific queries or falls back to Ollama for general queries.
"""

import os
import json
import time
import uuid
from typing import AsyncIterator, Dict, Any, List, Optional
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

# Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8001")
OLLAMA_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:11434")
API_KEY = os.getenv("GATEWAY_API_KEY", "dummy-key")  # Optional for Phase 1

# Model mapping (OpenAI -> Ollama)
MODEL_MAPPING = {
    "gpt-3.5-turbo": "phi3:mini",
    "gpt-4": "llama3.1:8b",
    "gpt-4-32k": "llama3.1:8b",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global orchestrator_client, ollama_client

    # Startup
    logger.info("Starting Gateway service")
    orchestrator_client = httpx.AsyncClient(
        base_url=ORCHESTRATOR_URL,
        timeout=60.0
    )
    ollama_client = OllamaClient(url=OLLAMA_URL)

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
    if orchestrator_client:
        await orchestrator_client.aclose()
    if ollama_client:
        await ollama_client.close()

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

def is_athena_query(messages: List[ChatMessage]) -> bool:
    """
    Determine if this query should be routed to Athena orchestrator.

    Athena handles:
    - Home automation control (lights, switches, climate)
    - Weather queries
    - Airport/flight information
    - Sports information
    - Location-specific queries (Baltimore context)
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
        # Sports
        "game", "score", "ravens", "orioles", "team",
        # Location context
        "baltimore", "home", "office", "bedroom", "kitchen",
        # Recipes and cooking (RAG + web search)
        "recipe", "cook", "how to make", "ingredients", "cooking",
        # Entertainment and events (web search)
        "concert", "perform", "tour", "show", "event", "when does",
        "who is", "what is", "tell me about"
    ]

    return any(pattern in last_user_msg for pattern in athena_patterns)

async def route_to_orchestrator(
    request: ChatCompletionRequest
) -> ChatCompletionResponse:
    """Route request to Athena orchestrator."""
    try:
        # Extract user message
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content

        # Call orchestrator
        with request_duration.labels(endpoint="orchestrator").time():
            response = await orchestrator_client.post(
                "/query",
                json={
                    "query": user_message,
                    "mode": "owner",  # Default to owner mode
                    "room": "unknown",  # Could be enriched later
                    "temperature": request.temperature,
                    "model": MODEL_MAPPING.get(request.model, "phi3:mini")
                }
            )
            response.raise_for_status()

        result = response.json()

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

    except httpx.HTTPStatusError as e:
        logger.error(f"Orchestrator error: {e}")
        raise HTTPException(status_code=502, detail="Orchestrator error")
    except Exception as e:
        logger.error(f"Failed to route to orchestrator: {e}", exc_info=True)
        # Fall back to Ollama
        return await route_to_ollama(request)

async def route_to_ollama(
    request: ChatCompletionRequest
) -> ChatCompletionResponse:
    """Route request directly to Ollama."""
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
            async for chunk in ollama_client.chat(
                model=ollama_model,
                messages=messages,
                temperature=request.temperature,
                stream=False
            ):
                if chunk.get("done"):
                    response_text = chunk.get("message", {}).get("content", "")
                    break

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

        # Route based on query type
        if is_athena_query(request.messages):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)