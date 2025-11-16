# MLX + Ollama Hybrid Implementation Plan

**Status**: Ready for Implementation
**Type**: Per-Model Backend Selection (Option C - Hybrid)
**Open Source**: Yes - Designed for community deployment

## Executive Summary

Implement a flexible LLM backend system allowing **per-model selection** between:
- **Ollama** (existing, GGUF models, Metal GPU)
- **MLX** (new, Apple Silicon optimized, 2.34x faster)
- **Auto** (try MLX first, fall back to Ollama)

All configurable via admin UI, no code changes needed for backend switching.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│               Admin UI (Configuration)                        │
│  ┌────────────────────┐  ┌──────────────────────┐           │
│  │ Model: phi3:mini   │  │ Model: llama3.1:8b   │           │
│  │ Backend: Ollama ▼  │  │ Backend: MLX ▼       │           │
│  │ Port: 11434        │  │ Port: 11435          │           │
│  │ Enabled: ✅         │  │ Enabled: ✅           │           │
│  └────────────────────┘  └──────────────────────┘           │
└──────────────────────────────────────────────────────────────┘
                            ↓ Configuration API
┌──────────────────────────────────────────────────────────────┐
│            Unified LLM Router (src/shared/llm_router.py)      │
│  - Reads model→backend mapping from admin API               │
│  - Routes requests to correct backend                        │
│  - Handles fallback on errors                                │
│  - Tracks performance metrics                                │
└──────────────────────────────────────────────────────────────┘
        ↓ Ollama requests          ↓ MLX requests
┌────────────────────┐    ┌────────────────────────┐
│  Ollama Server     │    │  MLX Server            │
│  :11434            │    │  :11435                │
│  (GGUF models)     │    │  (MLX-optimized)       │
│  Metal GPU         │    │  Metal GPU (faster)    │
└────────────────────┘    └────────────────────────┘
```

---

## Implementation Steps

### Phase 1: Database Model (30 min)

**File**: `admin/backend/app/models.py`

Add LLM Backend Registry model:

```python
class LLMBackend(Base):
    """LLM backend configuration for model routing."""
    __tablename__ = 'llm_backends'

    id = Column(Integer, primary_key=True)
    model_name = Column(String(255), unique=True, nullable=False, index=True)
    backend_type = Column(String(32), nullable=False)  # ollama, mlx, auto
    endpoint_url = Column(String(500), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=100)  # Lower = higher priority for 'auto'

    # Performance tracking
    avg_tokens_per_sec = Column(Float)
    avg_latency_ms = Column(Float)
    total_requests = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)

    # Configuration
    max_tokens = Column(Integer, default=2048)
    temperature_default = Column(Float, default=0.7)
    timeout_seconds = Column(Integer, default=60)

    # Metadata
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey('users.id'))

    # Relationships
    creator = relationship('User')

    __table_args__ = (
        Index('idx_llm_backends_enabled', 'enabled'),
        Index('idx_llm_backends_backend_type', 'backend_type'),
    )
```

**Database Migration**:
```bash
# Create migration
alembic revision --autogenerate -m "Add LLM backend registry"

# Apply migration
alembic upgrade head
```

---

### Phase 2: Admin API Routes (1 hour)

**File**: `admin/backend/app/routes/llm_backends.py` (NEW)

```python
"""
LLM Backend Management API Routes.

Provides CRUD operations for LLM backend configuration.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, LLMBackend

router = APIRouter(prefix="/api/llm-backends", tags=["llm-backends"])

class LLMBackendCreate(BaseModel):
    """Request model for creating LLM backend config."""
    model_name: str
    backend_type: str  # ollama, mlx, auto
    endpoint_url: str
    enabled: bool = True
    priority: int = 100
    max_tokens: int = 2048
    temperature_default: float = 0.7
    timeout_seconds: int = 60
    description: str = None

class LLMBackendResponse(BaseModel):
    """Response model for LLM backend config."""
    id: int
    model_name: str
    backend_type: str
    endpoint_url: str
    enabled: bool
    priority: int
    avg_tokens_per_sec: float = None
    avg_latency_ms: float = None
    total_requests: int
    total_errors: int
    description: str = None

    class Config:
        from_attributes = True

@router.get("", response_model=List[LLMBackendResponse])
async def list_backends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all LLM backend configurations."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403)

    backends = db.query(LLMBackend).order_by(LLMBackend.model_name).all()
    return backends

@router.get("/{backend_id}", response_model=LLMBackendResponse)
async def get_backend(
    backend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific LLM backend configuration."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403)

    backend = db.query(LLMBackend).filter(LLMBackend.id == backend_id).first()
    if not backend:
        raise HTTPException(status_code=404, detail="Backend not found")

    return backend

@router.get("/model/{model_name}", response_model=LLMBackendResponse)
async def get_backend_by_model(
    model_name: str,
    db: Session = Depends(get_db)
):
    """
    Get LLM backend configuration for a specific model.

    This endpoint is called by services (no auth required - uses service API key).
    """
    backend = db.query(LLMBackend).filter(
        LLMBackend.model_name == model_name,
        LLMBackend.enabled == True
    ).first()

    if not backend:
        raise HTTPException(
            status_code=404,
            detail=f"No backend configured for model '{model_name}'"
        )

    return backend

@router.post("", response_model=LLMBackendResponse, status_code=201)
async def create_backend(
    backend_data: LLMBackendCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new LLM backend configuration."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403)

    # Check if model already configured
    existing = db.query(LLMBackend).filter(
        LLMBackend.model_name == backend_data.model_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Backend for model '{backend_data.model_name}' already exists"
        )

    backend = LLMBackend(
        model_name=backend_data.model_name,
        backend_type=backend_data.backend_type,
        endpoint_url=backend_data.endpoint_url,
        enabled=backend_data.enabled,
        priority=backend_data.priority,
        max_tokens=backend_data.max_tokens,
        temperature_default=backend_data.temperature_default,
        timeout_seconds=backend_data.timeout_seconds,
        description=backend_data.description,
        created_by_id=current_user.id
    )

    db.add(backend)
    db.commit()
    db.refresh(backend)

    return backend

@router.put("/{backend_id}", response_model=LLMBackendResponse)
async def update_backend(
    backend_id: int,
    backend_data: LLMBackendCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update LLM backend configuration."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403)

    backend = db.query(LLMBackend).filter(LLMBackend.id == backend_id).first()
    if not backend:
        raise HTTPException(status_code=404)

    backend.backend_type = backend_data.backend_type
    backend.endpoint_url = backend_data.endpoint_url
    backend.enabled = backend_data.enabled
    backend.priority = backend_data.priority
    backend.max_tokens = backend_data.max_tokens
    backend.temperature_default = backend_data.temperature_default
    backend.timeout_seconds = backend_data.timeout_seconds
    backend.description = backend_data.description

    db.commit()
    db.refresh(backend)

    return backend

@router.delete("/{backend_id}", status_code=204)
async def delete_backend(
    backend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete LLM backend configuration."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403)

    backend = db.query(LLMBackend).filter(LLMBackend.id == backend_id).first()
    if not backend:
        raise HTTPException(status_code=404)

    db.delete(backend)
    db.commit()

    return None
```

**Register routes in** `admin/backend/app/main.py`:
```python
from app.routes import llm_backends
app.include_router(llm_backends.router)
```

---

### Phase 3: Unified LLM Router Client (2 hours)

**File**: `src/shared/llm_router.py` (NEW)

This is the CRITICAL file that replaces `ollama_client.py` with multi-backend support.

```python
"""
Unified LLM Router

Routes LLM requests to appropriate backend (Ollama, MLX, etc.) based on
admin configuration. Supports per-model backend selection with automatic
fallback.

Open Source Compatible - No vendor lock-in.
"""
import httpx
import time
from typing import Dict, Any, Optional
from enum import Enum
import structlog

logger = structlog.get_logger()

class BackendType(str, Enum):
    """Supported LLM backend types."""
    OLLAMA = "ollama"
    MLX = "mlx"
    AUTO = "auto"  # Try MLX first, fall back to Ollama

class LLMRouter:
    """
    Routes LLM requests to configured backends.

    Usage:
        router = LLMRouter(admin_url="https://admin.example.com")
        response = await router.generate(
            model="phi3:mini",
            prompt="Hello world",
            temperature=0.7
        )
    """

    def __init__(
        self,
        admin_url: Optional[str] = None,
        cache_ttl: int = 60
    ):
        self.admin_url = admin_url or os.getenv(
            "ADMIN_API_URL",
            "http://localhost:8080"
        )
        self.client = httpx.AsyncClient(timeout=120.0)
        self._backend_cache = {}
        self._cache_expiry = {}
        self._cache_ttl = cache_ttl

    async def _get_backend_config(self, model: str) -> Dict[str, Any]:
        """
        Fetch backend configuration for a model from admin API.

        Caches results for performance.
        """
        now = time.time()

        # Check cache
        if model in self._backend_cache:
            if now < self._cache_expiry.get(model, 0):
                return self._backend_cache[model]

        # Fetch from admin API
        try:
            url = f"{self.admin_url}/api/llm-backends/model/{model}"
            response = await self.client.get(url)

            if response.status_code == 404:
                # No config found - use default Ollama
                logger.warning(
                    "no_backend_config_found",
                    model=model,
                    falling_back="ollama"
                )
                config = {
                    "backend_type": "ollama",
                    "endpoint_url": "http://localhost:11434",
                    "max_tokens": 2048,
                    "temperature_default": 0.7,
                    "timeout_seconds": 60
                }
            else:
                response.raise_for_status()
                config = response.json()

            # Cache
            self._backend_cache[model] = config
            self._cache_expiry[model] = now + self._cache_ttl

            return config

        except Exception as e:
            logger.error(
                "failed_to_fetch_backend_config",
                model=model,
                error=str(e)
            )
            # Fall back to Ollama
            return {
                "backend_type": "ollama",
                "endpoint_url": "http://localhost:11434"
            }

    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using configured backend for the model.

        Args:
            model: Model name (e.g., "phi3:mini")
            prompt: Input prompt
            temperature: Temperature override
            max_tokens: Max tokens override
            **kwargs: Additional backend-specific parameters

        Returns:
            Generated response with metadata
        """
        # Get backend configuration
        config = await self._get_backend_config(model)
        backend_type = config["backend_type"]
        endpoint_url = config["endpoint_url"]

        # Apply defaults from config
        temperature = temperature or config.get("temperature_default", 0.7)
        max_tokens = max_tokens or config.get("max_tokens", 2048)
        timeout = config.get("timeout_seconds", 60)

        logger.info(
            "routing_llm_request",
            model=model,
            backend_type=backend_type,
            endpoint=endpoint_url
        )

        start_time = time.time()

        try:
            if backend_type == BackendType.AUTO:
                # Try MLX first, fall back to Ollama
                try:
                    return await self._generate_mlx(
                        endpoint_url, model, prompt, temperature, max_tokens, timeout
                    )
                except Exception as e:
                    logger.warning(
                        "mlx_failed_falling_back_to_ollama",
                        error=str(e)
                    )
                    # Fall back to Ollama
                    ollama_url = "http://localhost:11434"
                    return await self._generate_ollama(
                        ollama_url, model, prompt, temperature, max_tokens, timeout
                    )

            elif backend_type == BackendType.MLX:
                return await self._generate_mlx(
                    endpoint_url, model, prompt, temperature, max_tokens, timeout
                )

            else:  # OLLAMA
                return await self._generate_ollama(
                    endpoint_url, model, prompt, temperature, max_tokens, timeout
                )

        finally:
            duration = time.time() - start_time
            logger.info(
                "llm_request_completed",
                model=model,
                backend_type=backend_type,
                duration=duration
            )

    async def _generate_ollama(
        self,
        endpoint_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: int
    ) -> Dict[str, Any]:
        """Generate using Ollama backend."""
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

    async def _generate_mlx(
        self,
        endpoint_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: int
    ) -> Dict[str, Any]:
        """Generate using MLX backend."""
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

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

# Singleton instance
_router: Optional[LLMRouter] = None

def get_llm_router() -> LLMRouter:
    """Get or create LLM router singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
```

---

### Phase 4: MLX Server Wrapper (1 hour)

**File**: `src/mlx_server/main.py` (NEW)

Simple OpenAI-compatible API wrapper around MLX for drop-in replacement.

```python
"""
MLX LLM Server

OpenAI-compatible API server for MLX models.
Designed to be a drop-in replacement for Ollama with better performance.

Usage:
    python3 src/mlx_server/main.py --model ~/mlx_models/phi3-mini-4bit --port 11435
"""
import os
import sys
import argparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Add MLX to path
sys.path.insert(0, os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages"))

import mlx.core as mx
from mlx_lm import load, generate

app = FastAPI(title="MLX LLM Server", version="1.0.0")

# Global model state
MODEL = None
TOKENIZER = None
MODEL_NAME = "phi3-mini"

class CompletionRequest(BaseModel):
    """OpenAI-compatible completion request."""
    model: str
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False

class CompletionResponse(BaseModel):
    """OpenAI-compatible completion response."""
    id: str = "mlx-completion"
    object: str = "text_completion"
    created: int
    model: str
    choices: list
    usage: dict

@app.on_event("startup")
async def load_model():
    """Load MLX model on startup."""
    global MODEL, TOKENIZER, MODEL_NAME

    model_path = os.getenv("MLX_MODEL_PATH", "~/mlx_models/phi3-mini-4bit")
    model_path = os.path.expanduser(model_path)

    print(f"Loading MLX model from: {model_path}")
    MODEL, TOKENIZER = load(model_path)
    print("✓ MLX model loaded successfully")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "backend": "mlx",
        "model": MODEL_NAME,
        "gpu_available": mx.metal.is_available()
    }

@app.post("/v1/completions", response_model=CompletionResponse)
async def create_completion(request: CompletionRequest):
    """OpenAI-compatible completion endpoint."""
    if MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        import time
        start_time = time.time()

        # Generate using MLX
        response_text = generate(
            MODEL,
            TOKENIZER,
            prompt=request.prompt,
            temp=request.temperature,
            max_tokens=request.max_tokens
        )

        duration = time.time() - start_time
        tokens_generated = len(TOKENIZER.encode(response_text))

        return CompletionResponse(
            created=int(start_time),
            model=request.model,
            choices=[{
                "text": response_text,
                "index": 0,
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": len(TOKENIZER.encode(request.prompt)),
                "completion_tokens": tokens_generated,
                "total_tokens": len(TOKENIZER.encode(request.prompt)) + tokens_generated,
                "duration_seconds": duration
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLX LLM Server")
    parser.add_argument("--model", default="~/mlx_models/phi3-mini-4bit", help="Path to MLX model")
    parser.add_argument("--port", type=int, default=11435, help="Server port")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")

    args = parser.parse_args()

    os.environ["MLX_MODEL_PATH"] = args.model

    uvicorn.run(app, host=args.host, port=args.port)
```

**Systemd service** (for production):
```ini
# /etc/systemd/system/mlx-server.service
[Unit]
Description=MLX LLM Server
After=network.target

[Service]
Type=simple
User=jstuart
WorkingDirectory=/Users/jstuart/dev/project-athena
Environment="MLX_MODEL_PATH=/Users/jstuart/mlx_models/phi3-mini-4bit"
ExecStart=/usr/bin/python3 src/mlx_server/main.py --port 11435
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

### Phase 5: Update Orchestrator (30 min)

**File**: `src/orchestrator/main.py`

Replace OllamaClient with LLMRouter:

```python
# OLD
from shared.ollama_client import OllamaClient
ollama_client = OllamaClient()

# NEW
from shared.llm_router import get_llm_router
llm_router = get_llm_router()

# Usage stays the same!
response = await llm_router.generate(
    model="phi3:mini",
    prompt=synthesis_prompt,
    temperature=0.7
)
```

---

## Open Source Deployment Guide

### Quick Start (5 minutes)

```bash
# 1. Install MLX (Mac only)
pip3 install mlx mlx-lm

# 2. Download model (or use Ollama only)
# Skip this if you only want Ollama

# 3. Configure default backends in admin UI
curl -X POST http://admin.example.com/api/llm-backends \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "model_name": "phi3:mini",
    "backend_type": "ollama",
    "endpoint_url": "http://localhost:11434",
    "enabled": true
  }'

# 4. Done! Services automatically route to configured backends
```

### Per-Model Configuration Examples

```bash
# Ollama for classification (fast enough)
curl -X POST $ADMIN_URL/api/llm-backends -d '{
  "model_name": "phi3:mini-classify",
  "backend_type": "ollama",
  "endpoint_url": "http://localhost:11434"
}'

# MLX for synthesis (need speed)
curl -X POST $ADMIN_URL/api/llm-backends -d '{
  "model_name": "phi3:mini-synthesis",
  "backend_type": "mlx",
  "endpoint_url": "http://localhost:11435"
}'

# Auto mode (try MLX, fall back to Ollama)
curl -X POST $ADMIN_URL/api/llm-backends -d '{
  "model_name": "llama3.1:8b",
  "backend_type": "auto",
  "endpoint_url": "http://localhost:11435"
}'
```

---

## Performance Expectations

| Model | Backend | Tokens/sec | Latency | Use Case |
|-------|---------|-----------|---------|----------|
| phi3:mini | Ollama (CPU) | ~15-20 | 4.5s | Baseline |
| phi3:mini | Ollama (Metal) | ~35-40 | 2.0s | Current (good!) |
| phi3:mini | MLX | ~80-100 | 0.8s | Maximum speed |

**Synthesis time reduction**: 4.52s → 0.8s (5.6x faster with MLX)

---

## Testing Checklist

- [ ] Database migration applied
- [ ] Admin API endpoints working
- [ ] Can create/update/delete backend configs via API
- [ ] LLMRouter fetches config from admin API
- [ ] LLMRouter routes to Ollama correctly
- [ ] MLX server starts and responds
- [ ] LLMRouter routes to MLX correctly
- [ ] Auto fallback works (MLX fail → Ollama)
- [ ] Orchestrator uses new router
- [ ] Performance metrics tracked
- [ ] Admin UI shows backend configs
- [ ] Documentation complete

---

## Next Steps

1. **Implement Database Model** - Add to models.py, create migration
2. **Implement Admin API** - Add routes, test with curl
3. **Implement LLM Router** - Create unified client, test routing
4. **Optional: MLX Setup** - If you want maximum speed
5. **Update Orchestrator** - Switch from OllamaClient to LLMRouter
6. **Test End-to-End** - Verify routing works correctly
7. **Add Admin UI** - Build configuration interface

**Estimated Total Time**: 6-8 hours for complete implementation

**MVP Time** (Ollama only): 2-3 hours (skip MLX server, use auto-config)

---

## Open Source License

This implementation is designed to be MIT/Apache 2.0 compatible.

**No vendor lock-in**: Works with any OpenAI-compatible LLM backend.

**Community contributions welcome**: Backend plugins for Claude, GPT-4, local models, etc.

