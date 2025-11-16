# LLM Backend System - Overview

> **Last Updated:** November 15, 2025
> **Status:** Production Ready
> **Version:** 1.0.0

## Quick Links

- [Admin API Reference](./llm-backend-admin-api)
- [Router Technical Docs](./llm-backend-router)
- [Configuration Guide](./llm-backend-config)
- [Deployment Guide](./llm-backend-deployment)

## What is the LLM Backend System?

The **LLM Backend System** provides flexible, per-model backend selection for Large Language Models in Project Athena. It enables dynamic routing between different LLM inference engines (Ollama, MLX, etc.) without code changes - all configuration is managed through the Admin UI.

### Key Features

✅ **Per-Model Backend Selection** - Each model can use a different backend
✅ **Zero Code Changes** - Switch backends via Admin API/UI only
✅ **Automatic Fallback** - Auto mode tries faster backend, falls back on failure
✅ **Performance Tracking** - Built-in metrics for tokens/sec and latency
✅ **Configuration Caching** - 60-second cache reduces database queries
✅ **Multiple Backend Support** - Ollama, MLX, and extensible for future backends

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Orchestrator                         │
│  (Intent Classification, Response Synthesis, etc.)       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │      LLM Router          │
         │  (Unified Interface)     │
         └─────┬────────────┬──────┘
               │            │
       ┌───────▼──────┐ ┌──▼──────────┐
       │    Ollama    │ │     MLX      │
       │  (Metal GPU) │ │  (Apple M)   │
       │ phi3:mini-q8 │ │  phi3:mini   │
       └──────────────┘ └──────────────┘
               │            │
         Configuration via Admin API
               │
         ┌─────▼────────────┐
         │ LLM Backend DB    │
         │ (PostgreSQL)      │
         └───────────────────┘
```

### Components

1. **LLM Router** (`src/shared/llm_router.py`)
   - Unified interface for all LLM backends
   - Fetches configuration from Admin API
   - Caches configs for 60 seconds
   - Handles fallback logic

2. **Admin API** (`admin/backend/app/routes/llm_backends.py`)
   - REST API for managing backend configurations
   - CRUD operations for backend configs
   - Service-to-service lookup endpoint

3. **Database** (`admin/backend/alembic/versions/93bea4659785_*.py`)
   - `llm_backends` table stores configurations
   - Performance metrics tracking
   - Model-to-backend mappings

## Supported Backends

### Ollama
- **Type:** GGUF quantized models
- **Acceleration:** Metal GPU (macOS), CUDA (Linux)
- **Format:** Ollama format models
- **API:** Custom Ollama API (`/api/generate`)
- **Use Case:** Default, broad model support

### MLX
- **Type:** Apple Silicon optimized
- **Acceleration:** Unified Memory Architecture
- **Format:** MLX format models
- **API:** OpenAI-compatible (`/v1/completions`)
- **Use Case:** 2-3x faster on Apple Silicon

### Auto (Hybrid)
- **Type:** Automatic fallback
- **Strategy:** Try MLX first → fall back to Ollama
- **Use Case:** Maximum performance with reliability

## Performance Comparison

Based on benchmarks on Mac Studio M4:

| Model | Backend | Avg Time | Tokens/sec | Speedup |
|-------|---------|----------|------------|---------|
| phi3:mini | Ollama | ~7s | ~14 t/s | 1.0x |
| phi3:mini | MLX | ~3s | ~33 t/s | 2.3x |
| llama3.1:8b | Ollama | ~15s | ~6.7 t/s | 1.0x |
| llama3.1:8b | MLX | ~6s | ~16.7 t/s | 2.5x |

## Configuration Example

### Via Admin API

```bash
# Create backend configuration for phi3:mini using Ollama
curl -X POST http://localhost:8080/api/llm-backends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434",
    "enabled": true,
    "max_tokens": 2048,
    "temperature_default": 0.7,
    "timeout_seconds": 60,
    "description": "Phi-3 Mini via Ollama for fast classification"
  }'
```

### Switch to MLX

```bash
# Update the same model to use MLX
curl -X PUT http://localhost:8080/api/llm-backends/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backend_type": "mlx",
    "endpoint_url": "http://localhost:8080"
  }'
```

**No code changes or service restart required!**

## Use Cases

### 1. Development → Production Migration
- **Development:** Use Ollama (easy setup, CPU/GPU)
- **Production:** Switch to MLX (2-3x faster, optimized)
- Change via Admin UI, no deployment needed

### 2. Per-Model Optimization
- **Fast models (phi3:mini):** Use MLX for sub-second responses
- **Large models (llama3.1:70b):** Use Ollama with quantization
- Configure once, works automatically

### 3. A/B Testing
- **Control group:** phi3:mini on Ollama
- **Test group:** phi3:mini on MLX
- Track performance metrics via database

### 4. Graceful Degradation
- **Primary:** MLX for speed
- **Fallback:** Ollama if MLX unavailable
- Use `auto` backend type for automatic switching

## Migration from OllamaClient

The system has been migrated from direct `OllamaClient` usage to the new `LLMRouter`:

**Before:**
```python
from shared.ollama_client import OllamaClient

ollama_client = OllamaClient(url="http://localhost:11434")
response = await ollama_client.chat(
    model="phi3:mini",
    messages=[...],
    temperature=0.7
)
```

**After:**
```python
from shared.llm_router import get_llm_router

llm_router = get_llm_router()  # Singleton
result = await llm_router.generate(
    model="phi3:mini",
    prompt="Your prompt here",
    temperature=0.7
)
response_text = result["response"]
```

**Key Differences:**
- Router uses admin-configured backends (Ollama, MLX, or Auto)
- Single `generate()` method instead of `chat()` and `generate()`
- Non-streaming responses (streaming support planned)
- Backend selection is transparent to the caller

## System Requirements

### Ollama Backend
- Ollama server installed and running
- Models pulled: `ollama pull phi3:mini`
- Port 11434 accessible

### MLX Backend
- Apple Silicon Mac (M1/M2/M3/M4)
- MLX server running: `mlx_lm.server --model <path> --port 8080`
- Models in MLX format (convert with `mlx_lm.convert`)
- Port 8080 accessible

### Admin System
- PostgreSQL database (postgres-01.xmojo.net)
- Admin backend running (port 8080)
- Kubernetes cluster for orchestrator

## Quick Start

1. **Install Ollama** (default backend):
   ```bash
   brew install ollama
   ollama serve
   ollama pull phi3:mini
   ```

2. **Configure backend via Admin API**:
   ```bash
   curl -X POST http://localhost:8080/api/llm-backends \
     -H "Content-Type: application/json" \
     -d '{"model_name": "phi3:mini", "backend_type": "ollama", ...}'
   ```

3. **Use in orchestrator** (automatic):
   ```python
   # Orchestrator automatically uses LLMRouter
   # Backend selection handled transparently
   ```

4. **Optional: Add MLX for 2-3x speedup**:
   - Deploy MLX server
   - Update config: `backend_type: "mlx"`
   - Instant performance boost!

## Next Steps

- **Read:** [Configuration Guide](./llm-backend-config) - Step-by-step setup
- **Read:** [Admin API Reference](./llm-backend-admin-api) - Complete API docs
- **Read:** [Deployment Guide](./llm-backend-deployment) - Production deployment
- **Explore:** [Router Technical Docs](./llm-backend-router) - Internal architecture

## Related Documentation

- [Project Athena Overview](../project-athena) - Main project documentation (DEPRECATED)
- [Orchestrator Architecture](../orchestrator) - How orchestrator uses LLM Router
- [Admin Configuration System](../../admin/config-system) - Overall admin system

---

**Status:** ✅ Production Ready
**Last Updated:** November 15, 2025
**Maintained By:** Jay Stuart
