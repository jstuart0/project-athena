"""
LLM Backend Management API Routes.

Provides CRUD operations for LLM backend configuration to enable
per-model backend selection (Ollama, MLX, Auto) with performance tracking.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import structlog

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, LLMBackend, LLMPerformanceMetric
from datetime import datetime

logger = structlog.get_logger()

router = APIRouter(prefix="/api/llm-backends", tags=["llm-backends"])


# Pydantic models for request/response
class LLMBackendCreate(BaseModel):
    """Request model for creating LLM backend config."""
    model_name: str = Field(..., description="Model identifier (e.g., 'phi3:mini', 'llama3.1:8b')")
    backend_type: str = Field(..., description="Backend type: 'ollama', 'mlx', or 'auto'")
    endpoint_url: str = Field(..., description="Backend endpoint URL (e.g., 'http://localhost:11434')")
    enabled: bool = Field(default=True, description="Whether this backend is enabled")
    priority: int = Field(default=100, description="Priority for 'auto' mode (lower = higher priority)")
    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")
    temperature_default: float = Field(default=0.7, description="Default temperature for generation")
    timeout_seconds: int = Field(default=60, description="Request timeout in seconds")
    description: Optional[str] = Field(None, description="Optional description of this backend configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "phi3:mini",
                "backend_type": "ollama",
                "endpoint_url": "http://localhost:11434",
                "enabled": True,
                "priority": 100,
                "max_tokens": 2048,
                "temperature_default": 0.7,
                "timeout_seconds": 60,
                "description": "Phi-3 Mini via Ollama for fast classification"
            }
        }


class LLMBackendUpdate(BaseModel):
    """Request model for updating LLM backend config."""
    backend_type: Optional[str] = None
    endpoint_url: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature_default: Optional[float] = None
    timeout_seconds: Optional[int] = None
    description: Optional[str] = None


class LLMBackendResponse(BaseModel):
    """Response model for LLM backend config."""
    id: int
    model_name: str
    backend_type: str
    endpoint_url: str
    enabled: bool
    priority: int
    avg_tokens_per_sec: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    total_requests: int
    total_errors: int
    max_tokens: int
    temperature_default: float
    timeout_seconds: int
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class LLMMetricCreate(BaseModel):
    """Request model for creating LLM performance metric."""
    timestamp: float = Field(..., description="Unix timestamp of request start")
    model: str = Field(..., description="Model name used for generation")
    backend: str = Field(..., description="Backend type (ollama, mlx, auto)")
    latency_seconds: float = Field(..., description="Total request latency in seconds")
    tokens: int = Field(..., description="Number of tokens generated")
    tokens_per_second: float = Field(..., description="Token generation speed")
    request_id: Optional[str] = Field(None, description="Optional request ID for tracking")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation tracking")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    zone: Optional[str] = Field(None, description="Optional zone/location")
    intent: Optional[str] = Field(None, description="Optional intent classification")
    source: Optional[str] = Field(None, description="Source of the request (admin_voice_test, gateway, orchestrator, rag_*)")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 1700000000.123,
                "model": "phi3:mini",
                "backend": "ollama",
                "latency_seconds": 2.5,
                "tokens": 150,
                "tokens_per_second": 60.0,
                "request_id": "req_123abc",
                "session_id": "sess_xyz789",
                "intent": "weather_query",
                "source": "gateway"
            }
        }


# API Routes
@router.get("", response_model=List[LLMBackendResponse])
async def list_backends(
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all LLM backend configurations.

    Query params:
    - enabled_only: If true, only return enabled backends
    """
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    logger.info("list_llm_backends", user=current_user.username, enabled_only=enabled_only)

    query = db.query(LLMBackend)
    if enabled_only:
        query = query.filter(LLMBackend.enabled == True)

    backends = query.order_by(LLMBackend.model_name).all()

    return [
        LLMBackendResponse(
            **backend.to_dict()
        ) for backend in backends
    ]


class LLMMetricResponse(BaseModel):
    """Response model for LLM performance metric."""
    id: int
    timestamp: str
    model: str
    backend: str
    latency_seconds: float
    tokens_generated: int
    tokens_per_second: float
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    zone: Optional[str] = None
    intent: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/metrics", response_model=List[LLMMetricResponse])
async def get_metrics(
    model: Optional[str] = None,
    backend: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve LLM performance metrics.

    Query Parameters:
    - model: Filter by model name (optional)
    - backend: Filter by backend type (optional)
    - limit: Maximum number of metrics to return (default: 100, max: 1000)

    Returns:
        List of performance metrics ordered by timestamp (newest first)
    """
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Limit maximum to 1000 records
    if limit > 1000:
        limit = 1000

    query = db.query(LLMPerformanceMetric)

    if model:
        query = query.filter(LLMPerformanceMetric.model == model)
    if backend:
        query = query.filter(LLMPerformanceMetric.backend == backend)

    metrics = query.order_by(
        LLMPerformanceMetric.timestamp.desc()
    ).limit(limit).all()

    logger.info(
        "llm_metrics_retrieved",
        user=current_user.username,
        count=len(metrics),
        filters={"model": model, "backend": backend, "limit": limit}
    )

    return [
        LLMMetricResponse(
            id=m.id,
            timestamp=m.timestamp.isoformat(),
            model=m.model,
            backend=m.backend,
            latency_seconds=m.latency_seconds,
            tokens_generated=m.tokens_generated,
            tokens_per_second=m.tokens_per_second,
            request_id=m.request_id,
            session_id=m.session_id,
            user_id=m.user_id,
            zone=m.zone,
            intent=m.intent
        ) for m in metrics
    ]


@router.post("/metrics", status_code=201)
async def create_metric(
    metric: LLMMetricCreate,
    db: Session = Depends(get_db)
):
    """
    Store LLM performance metric in database.

    This endpoint is called internally by the LLM Router to persist metrics.
    No authentication required for internal service-to-service calls.

    Returns:
        201: Metric created successfully
        500: Database error
    """
    try:
        db_metric = LLMPerformanceMetric(
            timestamp=datetime.fromtimestamp(metric.timestamp),
            model=metric.model,
            backend=metric.backend,
            latency_seconds=metric.latency_seconds,
            tokens_generated=metric.tokens,
            tokens_per_second=metric.tokens_per_second,
            request_id=metric.request_id,
            session_id=metric.session_id,
            user_id=metric.user_id,
            zone=metric.zone,
            intent=metric.intent,
            source=metric.source
        )

        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)

        logger.info(
            "llm_metric_persisted",
            metric_id=db_metric.id,
            model=metric.model,
            backend=metric.backend,
            tokens_per_sec=metric.tokens_per_second
        )

        return {"id": db_metric.id, "status": "created"}

    except Exception as e:
        db.rollback()
        logger.error(
            "failed_to_persist_metric",
            error=str(e),
            model=metric.model
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist metric: {str(e)}"
        )

@router.get("/{backend_id}", response_model=LLMBackendResponse)
async def get_backend(
    backend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific LLM backend configuration by ID."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    backend = db.query(LLMBackend).filter(LLMBackend.id == backend_id).first()
    if not backend:
        raise HTTPException(status_code=404, detail="Backend not found")

    logger.info("get_llm_backend", backend_id=backend_id, user=current_user.username)

    return LLMBackendResponse(**backend.to_dict())


@router.get("/model/{model_name}", response_model=LLMBackendResponse)
async def get_backend_by_model(
    model_name: str,
    db: Session = Depends(get_db)
):
    """
    Get LLM backend configuration for a specific model.

    This endpoint is called by services and does not require authentication
    (uses service-to-service communication).
    """
    backend = db.query(LLMBackend).filter(
        LLMBackend.model_name == model_name,
        LLMBackend.enabled == True
    ).first()

    if not backend:
        logger.warning("backend_not_found", model_name=model_name)
        raise HTTPException(
            status_code=404,
            detail=f"No enabled backend configured for model '{model_name}'"
        )

    logger.debug("get_backend_by_model", model_name=model_name, backend_type=backend.backend_type)

    return LLMBackendResponse(**backend.to_dict())


@router.post("", response_model=LLMBackendResponse, status_code=201)
async def create_backend(
    backend_data: LLMBackendCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new LLM backend configuration."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate backend_type
    valid_types = ['ollama', 'mlx', 'auto']
    if backend_data.backend_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid backend_type. Must be one of: {', '.join(valid_types)}"
        )

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

    logger.info(
        "created_llm_backend",
        backend_id=backend.id,
        model_name=backend.model_name,
        backend_type=backend.backend_type,
        user=current_user.username
    )

    return LLMBackendResponse(**backend.to_dict())


@router.put("/{backend_id}", response_model=LLMBackendResponse)
async def update_backend(
    backend_id: int,
    backend_data: LLMBackendUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update LLM backend configuration."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    backend = db.query(LLMBackend).filter(LLMBackend.id == backend_id).first()
    if not backend:
        raise HTTPException(status_code=404, detail="Backend not found")

    # Validate backend_type if provided
    if backend_data.backend_type is not None:
        valid_types = ['ollama', 'mlx', 'auto']
        if backend_data.backend_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backend_type. Must be one of: {', '.join(valid_types)}"
            )

    # Update fields
    update_data = backend_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(backend, field, value)

    db.commit()
    db.refresh(backend)

    logger.info(
        "updated_llm_backend",
        backend_id=backend_id,
        model_name=backend.model_name,
        updated_fields=list(update_data.keys()),
        user=current_user.username
    )

    return LLMBackendResponse(**backend.to_dict())


@router.delete("/{backend_id}", status_code=204)
async def delete_backend(
    backend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete LLM backend configuration."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    backend = db.query(LLMBackend).filter(LLMBackend.id == backend_id).first()
    if not backend:
        raise HTTPException(status_code=404, detail="Backend not found")

    model_name = backend.model_name
    db.delete(backend)
    db.commit()

    logger.info(
        "deleted_llm_backend",
        backend_id=backend_id,
        model_name=model_name,
        user=current_user.username
    )

    return None


@router.post("/{backend_id}/toggle", response_model=LLMBackendResponse)
async def toggle_backend(
    backend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle enabled/disabled status of an LLM backend."""
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    backend = db.query(LLMBackend).filter(LLMBackend.id == backend_id).first()
    if not backend:
        raise HTTPException(status_code=404, detail="Backend not found")

    backend.enabled = not backend.enabled
    db.commit()
    db.refresh(backend)

    logger.info(
        "toggled_llm_backend",
        backend_id=backend_id,
        model_name=backend.model_name,
        enabled=backend.enabled,
        user=current_user.username
    )

    return LLMBackendResponse(**backend.to_dict())


