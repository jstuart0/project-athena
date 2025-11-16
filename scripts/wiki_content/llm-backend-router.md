# LLM Backend System - Router Technical Documentation

> **Last Updated:** November 15, 2025
> **Status:** Production Ready
> **File:** `src/shared/llm_router.py`

## Overview

The **LLM Router** is the central routing component that provides a unified interface for accessing multiple LLM backends (Ollama, MLX, etc.). It abstracts backend differences, manages configuration caching, and handles automatic fallback logic.

**Quick Links:**
- [Overview](./llm-backend-overview) - System overview
- [Admin API Reference](./llm-backend-admin-api) - Configuration API
- [Configuration Guide](./llm-backend-config) - Setup guide

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Orchestrator / Application              │
│                                                 │
│   result = await llm_router.generate(           │
│       model="phi3:mini",                        │
│       prompt="Your prompt here"                 │
│   )                                             │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│              LLM Router                         │
│                                                 │
│  1. Fetch config from Admin API                │
│  2. Cache config (60s TTL)                      │
│  3. Route to appropriate backend                │
│  4. Handle fallback (if Auto mode)              │
└─────────┬──────────────┬────────────────────────┘
          │              │
    ┌─────▼─────┐  ┌─────▼─────┐
    │  Ollama   │  │    MLX     │
    │  Backend  │  │  Backend   │
    └───────────┘  └────────────┘
          │              │
    Configuration fetched from:
    GET /api/llm-backends/model/{model_name}
```

## Class: LLMRouter

**Location:** `src/shared/llm_router.py`

**Purpose:** Route LLM requests to configured backends based on per-model configuration.

### Initialization

```python
from shared.llm_router import LLMRouter

# Create instance
router = LLMRouter(
    admin_url="http://localhost:8080",  # Admin API URL
    cache_ttl=60                         # Cache TTL in seconds
)

# Or use singleton pattern
from shared.llm_router import get_llm_router
router = get_llm_router()
```

**Constructor Parameters:**
- `admin_url` (str, optional) - Admin API base URL. Defaults to `ADMIN_API_URL` env var or `http://localhost:8080`
- `cache_ttl` (int, optional) - Configuration cache TTL in seconds. Default: 60

**Instance Variables:**
- `admin_url` - Admin API URL
- `client` - httpx.AsyncClient with 120s timeout
- `_backend_cache` - Dict storing cached backend configs
- `_cache_expiry` - Dict storing cache expiration timestamps
- `_cache_ttl` - Cache TTL in seconds

### Primary Method: generate()

**Purpose:** Generate text using the configured backend for a given model.

**Signature:**
```python
async def generate(
    self,
    model: str,
    prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]
```

**Parameters:**
- `model` (str, required) - Model identifier (e.g., "phi3:mini", "llama3.1:8b")
- `prompt` (str, required) - Input prompt text
- `temperature` (float, optional) - Sampling temperature (0.0-1.0). Uses config default if not provided
- `max_tokens` (int, optional) - Maximum tokens to generate. Uses config default if not provided
- `**kwargs` - Additional backend-specific parameters (future use)

**Returns:**
```python
{
    "response": str,           # Generated text
    "backend": str,            # Backend used ("ollama", "mlx")
    "model": str,              # Model name
    "done": bool,              # Generation complete flag
    "total_duration": int,     # Total time in nanoseconds (Ollama only)
    "eval_count": int          # Tokens generated
}
```

**Example Usage:**
```python
# Initialize router
from shared.llm_router import get_llm_router
llm_router = get_llm_router()

# Generate response
result = await llm_router.generate(
    model="phi3:mini",
    prompt="Classify the intent of: 'What's the weather in Baltimore?'",
    temperature=0.3,
    max_tokens=512
)

response_text = result["response"]
backend_used = result["backend"]  # "ollama" or "mlx"
```

### Internal Methods

#### _get_backend_config()

**Purpose:** Fetch backend configuration from Admin API with caching.

**Signature:**
```python
async def _get_backend_config(self, model: str) -> Dict[str, Any]
```

**Flow:**
1. Check if config is in cache and not expired
2. If cached: return cached config
3. If not cached: fetch from Admin API endpoint `/api/llm-backends/model/{model_name}`
4. If 404 response: use default Ollama config
5. If error: log and fall back to default Ollama config
6. Cache config with expiry timestamp
7. Return config

**Configuration Structure:**
```python
{
    "backend_type": "ollama",              # or "mlx", "auto"
    "endpoint_url": "http://localhost:11434",
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "timeout_seconds": 60
}
```

**Caching Behavior:**
- Cache TTL: 60 seconds (configurable)
- Cache key: Model name (e.g., "phi3:mini")
- Cache invalidation: Time-based only (no manual invalidation)

**Fallback Behavior:**
- If Admin API unreachable: Use default Ollama config
- If model not found (404): Use default Ollama config
- Default config:
  ```python
  {
      "backend_type": "ollama",
      "endpoint_url": "http://localhost:11434",
      "max_tokens": 2048,
      "temperature_default": 0.7,
      "timeout_seconds": 60
  }
  ```

#### _generate_ollama()

**Purpose:** Generate text using Ollama backend.

**Signature:**
```python
async def _generate_ollama(
    self,
    endpoint_url: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int
) -> Dict[str, Any]
```

**Implementation:**
```python
async def _generate_ollama(...):
    client = httpx.AsyncClient(base_url=endpoint_url, timeout=timeout)

    try:
        response = await client.post("/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        })

        response.raise_for_status()
        data = response.json()

        return {
            "response": data.get("response"),
            "backend": "ollama",
            "model": model,
            "done": data.get("done", True),
            "total_duration": data.get("total_duration"),
            "eval_count": data.get("eval_count")
        }
    finally:
        await client.aclose()
```

**Ollama API Endpoint:** `POST /api/generate`
**Request Format:**
```json
{
  "model": "phi3:mini",
  "prompt": "Your prompt here",
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 2048
  }
}
```

**Response Format:**
```json
{
  "model": "phi3:mini",
  "response": "Generated text here...",
  "done": true,
  "total_duration": 4850000000,
  "eval_count": 95
}
```

#### _generate_mlx()

**Purpose:** Generate text using MLX backend (OpenAI-compatible API).

**Signature:**
```python
async def _generate_mlx(
    self,
    endpoint_url: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int
) -> Dict[str, Any]
```

**Implementation:**
```python
async def _generate_mlx(...):
    client = httpx.AsyncClient(base_url=endpoint_url, timeout=timeout)

    try:
        # MLX server uses OpenAI-compatible API
        response = await client.post("/v1/completions", json={
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        })

        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]

        return {
            "response": choice["text"],
            "backend": "mlx",
            "model": model,
            "done": True,
            "total_duration": None,  # MLX doesn't provide this
            "eval_count": data.get("usage", {}).get("completion_tokens")
        }
    finally:
        await client.aclose()
```

**MLX API Endpoint:** `POST /v1/completions` (OpenAI-compatible)
**Request Format:**
```json
{
  "model": "phi3:mini",
  "prompt": "Your prompt here",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**Response Format:**
```json
{
  "id": "completion-123",
  "object": "text_completion",
  "created": 1700000000,
  "model": "phi3:mini",
  "choices": [
    {
      "text": "Generated text here...",
      "index": 0,
      "finish_reason": "length"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 95,
    "total_tokens": 107
  }
}
```

### Backend Type: Auto (Hybrid Fallback)

**Purpose:** Try MLX backend first, automatically fall back to Ollama on any error.

**Logic:**
```python
if backend_type == BackendType.AUTO:
    try:
        # Try MLX first (faster)
        return await self._generate_mlx(
            endpoint_url, model, prompt, temperature, max_tokens, timeout
        )
    except Exception as e:
        logger.warning("mlx_failed_falling_back_to_ollama", error=str(e))

        # Fall back to Ollama
        ollama_url = "http://localhost:11434"
        return await self._generate_ollama(
            ollama_url, model, prompt, temperature, max_tokens, timeout
        )
```

**Use Case:**
- Development: MLX may be running on Mac Studio, but not always available
- Production: Try MLX for 2-3x speed, fall back to Ollama for reliability
- Configuration: Set `backend_type: "auto"` and `endpoint_url` to MLX server URL

**Example Auto Config:**
```json
{
  "model_name": "phi3:mini",
  "backend_type": "auto",
  "endpoint_url": "http://localhost:8080",
  "enabled": true
}
```

**Behavior:**
1. Router fetches config, sees `backend_type: "auto"`
2. Attempts MLX generation at `http://localhost:8080/v1/completions`
3. If MLX fails (timeout, 500 error, connection refused):
   - Logs warning
   - Switches to Ollama at `http://localhost:11434/api/generate`
4. Returns result from whichever backend succeeded

## Enum: BackendType

**Purpose:** Supported backend types as string enum.

**Definition:**
```python
class BackendType(str, Enum):
    OLLAMA = "ollama"
    MLX = "mlx"
    AUTO = "auto"  # Try MLX first, fall back to Ollama
```

**Validation:** Admin API validates `backend_type` must be one of these values.

## Singleton Pattern: get_llm_router()

**Purpose:** Get or create a single LLMRouter instance (singleton).

**Implementation:**
```python
_router: Optional[LLMRouter] = None

def get_llm_router() -> LLMRouter:
    """Get or create LLM router singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
```

**Usage:**
```python
# Always returns same instance
from shared.llm_router import get_llm_router

router1 = get_llm_router()
router2 = get_llm_router()
assert router1 is router2  # True
```

**Benefits:**
- Single HTTP client shared across application
- Single configuration cache
- Reduced memory footprint

## Logging

**Structured Logging:** Uses `structlog` for JSON-formatted logs.

**Log Events:**

1. **Routing decision:**
```python
logger.info(
    "routing_llm_request",
    model=model,
    backend_type=backend_type,
    endpoint=endpoint_url
)
```

2. **Request completion:**
```python
logger.info(
    "llm_request_completed",
    model=model,
    backend_type=backend_type,
    duration=duration
)
```

3. **Configuration not found (fallback):**
```python
logger.warning(
    "no_backend_config_found",
    model=model,
    falling_back="ollama"
)
```

4. **MLX failure (auto mode):**
```python
logger.warning(
    "mlx_failed_falling_back_to_ollama",
    error=str(e)
)
```

5. **Config fetch error:**
```python
logger.error(
    "failed_to_fetch_backend_config",
    model=model,
    error=str(e)
)
```

**Example Log Output:**
```json
{
  "event": "routing_llm_request",
  "model": "phi3:mini",
  "backend_type": "mlx",
  "endpoint": "http://localhost:8080",
  "timestamp": "2025-11-15T15:30:00.123456Z"
}
{
  "event": "llm_request_completed",
  "model": "phi3:mini",
  "backend_type": "mlx",
  "duration": 2.98,
  "timestamp": "2025-11-15T15:30:03.105234Z"
}
```

## Error Handling

**Configuration Fetch Errors:**
- Network errors → Fall back to default Ollama config
- 404 Not Found → Fall back to default Ollama config
- Other errors → Fall back to default Ollama config

**Generation Errors:**
- Network timeout → Propagated to caller
- HTTP 500 errors → Propagated to caller
- Auto mode: MLX errors trigger Ollama fallback

**HTTP Client Cleanup:**
- Each backend method creates temporary client
- Client closed in `finally` block
- Prevents connection leaks

## Performance Characteristics

**Configuration Cache:**
- Hit rate: ~99% for repeated model queries
- Cache duration: 60 seconds
- Memory overhead: Minimal (~1KB per model)

**Request Latency:**
- Configuration fetch (cache miss): ~10-20ms
- Configuration fetch (cache hit): <1ms
- Ollama generation: ~5-7s (phi3:mini, 100 tokens)
- MLX generation: ~2-3s (phi3:mini, 100 tokens)

**Throughput:**
- Limited by LLM backend throughput, not router
- Router overhead: <1ms per request

## Integration Examples

### Example 1: Intent Classification (Orchestrator)

**Location:** `src/orchestrator/main.py:260`

```python
from shared.llm_router import get_llm_router

llm_router = get_llm_router()

# Intent classification with small model
full_prompt = f"""You are an intent classifier...

Query: {user_query}
"""

result = await llm_router.generate(
    model="phi3:mini",  # Small, fast model
    prompt=full_prompt,
    temperature=0.3      # Low temperature for deterministic classification
)

response_text = result["response"]
# Parse JSON response from LLM
```

### Example 2: Response Synthesis (Orchestrator)

**Location:** `src/orchestrator/main.py:563`

```python
# Response synthesis with larger model
full_prompt = system_context + synthesis_prompt

result = await llm_router.generate(
    model="llama3.1:8b",  # Larger model for better responses
    prompt=full_prompt,
    temperature=0.7       # Higher temperature for creativity
)

state.answer = result["response"]
```

### Example 3: Health Check

```python
from shared.llm_router import get_llm_router

async def health_check():
    llm_router = get_llm_router()

    # Router is always available (falls back to Ollama)
    if llm_router is not None:
        return {"status": "healthy"}
    else:
        return {"status": "unhealthy"}
```

## Migration from OllamaClient

**Before (streaming chat API):**
```python
from shared.ollama_client import OllamaClient

ollama_client = OllamaClient(url="http://localhost:11434")

response = await ollama_client.chat(
    model="phi3:mini",
    messages=[
        {"role": "system", "content": "You are a classifier"},
        {"role": "user", "content": "Classify this query"}
    ],
    temperature=0.3,
    stream=False
)

# Streaming chunks even with stream=False
text = ""
async for chunk in response:
    text += chunk
```

**After (unified router):**
```python
from shared.llm_router import get_llm_router

llm_router = get_llm_router()

# Concatenate system + user into single prompt
full_prompt = "You are a classifier\n\nClassify this query"

result = await llm_router.generate(
    model="phi3:mini",
    prompt=full_prompt,
    temperature=0.3
)

text = result["response"]
```

**Key Differences:**
- No streaming support (returns complete response)
- Messages array → single prompt string
- Configuration managed via Admin API (not code)
- Automatic backend selection (Ollama, MLX, or Auto)

## Testing

**Unit Testing:**
```python
import pytest
from shared.llm_router import LLMRouter

@pytest.mark.asyncio
async def test_router_ollama():
    router = LLMRouter(admin_url="http://localhost:8080")

    result = await router.generate(
        model="phi3:mini",
        prompt="Test prompt",
        temperature=0.7
    )

    assert "response" in result
    assert result["backend"] in ["ollama", "mlx"]
    assert result["model"] == "phi3:mini"
```

**Integration Testing:**
```bash
# Configure test backend
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "test-model",
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434",
    "enabled": true
  }'

# Test router
python3 -c "
from shared.llm_router import get_llm_router
import asyncio

async def test():
    router = get_llm_router()
    result = await router.generate(
        model='test-model',
        prompt='Hello world'
    )
    print(result)

asyncio.run(test())
"
```

## Limitations and Future Work

**Current Limitations:**

1. **No streaming support** - Returns complete response only
2. **No conversation history** - Single prompt, no message array support
3. **No performance metrics collection** - Tokens/sec and latency not tracked yet
4. **No backend health monitoring** - No automatic failover based on health
5. **No retry logic** - Single attempt per backend
6. **Cache invalidation** - Time-based only, no manual cache clear

**Planned Enhancements:**

1. Add streaming support for real-time responses
2. Implement message array formatting for conversation history
3. Track performance metrics (tokens/sec, latency) and report to Admin API
4. Add backend health checks with automatic failover
5. Implement exponential backoff retry logic
6. Add cache invalidation endpoint

## Security Considerations

**Admin API Access:**
- Service-to-service endpoint (`/model/{model_name}`) has no authentication
- Intentional design for internal service access
- Should not be exposed to public internet

**Credential Management:**
- No credentials stored in router code
- Backend URLs configurable via Admin API
- No hardcoded API keys or tokens

**Network Security:**
- All backend communication over HTTP (internal network)
- HTTPS not required for internal services
- Timeout protection (120s default)

## Next Steps

- **[Configuration Guide](./llm-backend-config)** - Step-by-step setup
- **[Deployment Guide](./llm-backend-deployment)** - Production deployment
- **[Admin API Reference](./llm-backend-admin-api)** - API documentation
- **[Overview](./llm-backend-overview)** - Back to system overview

---

**Last Updated:** November 15, 2025
**File:** `src/shared/llm_router.py`
**Maintained By:** Jay Stuart
