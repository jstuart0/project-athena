"""
Intent and Provider Routing API routes.

Provides endpoints for configurable intent classification and routing.
Replaces hardcoded patterns in orchestrator with database-driven configuration.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, Field
import structlog

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, IntentPattern, IntentRouting, ProviderRouting

logger = structlog.get_logger()

router = APIRouter(prefix="/api/intent-routing", tags=["intent-routing"])


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class IntentPatternRequest(BaseModel):
    """Request model for creating/updating intent patterns."""
    intent_category: str = Field(..., max_length=50)
    pattern_type: str = Field(..., max_length=50)
    keyword: str = Field(..., max_length=100)
    confidence_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    enabled: bool = True


class IntentPatternResponse(BaseModel):
    """Response model for intent patterns."""
    id: int
    intent_category: str
    pattern_type: str
    keyword: str
    confidence_weight: float
    enabled: bool
    created_at: str
    updated_at: str


class IntentRoutingRequest(BaseModel):
    """Request model for creating/updating intent routing."""
    intent_category: str = Field(..., max_length=50)
    use_rag: bool = False
    rag_service_url: Optional[str] = Field(None, max_length=255)
    use_web_search: bool = False
    use_llm: bool = True
    priority: int = Field(default=100, ge=1, le=1000)
    enabled: bool = True


class IntentRoutingResponse(BaseModel):
    """Response model for intent routing."""
    id: int
    intent_category: str
    use_rag: bool
    rag_service_url: Optional[str]
    use_web_search: bool
    use_llm: bool
    priority: int
    enabled: bool
    created_at: str
    updated_at: str


class ProviderRoutingRequest(BaseModel):
    """Request model for creating/updating provider routing."""
    intent_category: str = Field(..., max_length=50)
    provider_name: str = Field(..., max_length=50)
    priority: int = Field(..., ge=1, le=100)
    enabled: bool = True


class ProviderRoutingResponse(BaseModel):
    """Response model for provider routing."""
    id: int
    intent_category: str
    provider_name: str
    priority: int
    enabled: bool
    created_at: str
    updated_at: str


# ============================================================================
# Intent Pattern Endpoints
# ============================================================================

@router.get("/patterns", response_model=List[IntentPatternResponse])
async def get_intent_patterns(
    intent_category: Optional[str] = Query(None),
    pattern_type: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all intent patterns with optional filtering.

    Query Parameters:
    - intent_category: Filter by intent category
    - pattern_type: Filter by pattern type
    - enabled: Filter by enabled status
    """
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        query = db.query(IntentPattern)

        # Apply filters
        if intent_category:
            query = query.filter(IntentPattern.intent_category == intent_category)
        if pattern_type:
            query = query.filter(IntentPattern.pattern_type == pattern_type)
        if enabled is not None:
            query = query.filter(IntentPattern.enabled == enabled)

        patterns = query.order_by(
            IntentPattern.intent_category,
            IntentPattern.pattern_type,
            IntentPattern.keyword
        ).all()

        logger.info(
            "intent_patterns_retrieved",
            user=current_user.username,
            count=len(patterns),
            filters={
                "intent_category": intent_category,
                "pattern_type": pattern_type,
                "enabled": enabled
            }
        )

        return [IntentPatternResponse(**pattern.to_dict()) for pattern in patterns]

    except Exception as e:
        logger.error("failed_to_retrieve_intent_patterns", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve intent patterns: {str(e)}")


@router.post("/patterns", response_model=IntentPatternResponse, status_code=201)
async def create_intent_pattern(
    pattern: IntentPatternRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new intent pattern.

    Requires manage_secrets permission (admin-level operation).
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Check for duplicate
        existing = db.query(IntentPattern).filter(
            and_(
                IntentPattern.intent_category == pattern.intent_category,
                IntentPattern.pattern_type == pattern.pattern_type,
                IntentPattern.keyword == pattern.keyword
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Pattern already exists for {pattern.intent_category}/{pattern.pattern_type}/{pattern.keyword}"
            )

        # Create new pattern
        new_pattern = IntentPattern(
            intent_category=pattern.intent_category,
            pattern_type=pattern.pattern_type,
            keyword=pattern.keyword,
            confidence_weight=pattern.confidence_weight,
            enabled=pattern.enabled
        )

        db.add(new_pattern)
        db.commit()
        db.refresh(new_pattern)

        logger.info(
            "intent_pattern_created",
            user=current_user.username,
            pattern_id=new_pattern.id,
            intent_category=pattern.intent_category,
            keyword=pattern.keyword
        )

        return IntentPatternResponse(**new_pattern.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_create_intent_pattern", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to create intent pattern: {str(e)}")


@router.put("/patterns/{pattern_id}", response_model=IntentPatternResponse)
async def update_intent_pattern(
    pattern_id: int,
    pattern: IntentPatternRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing intent pattern.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        existing_pattern = db.query(IntentPattern).filter(IntentPattern.id == pattern_id).first()

        if not existing_pattern:
            raise HTTPException(status_code=404, detail="Intent pattern not found")

        # Update fields
        existing_pattern.intent_category = pattern.intent_category
        existing_pattern.pattern_type = pattern.pattern_type
        existing_pattern.keyword = pattern.keyword
        existing_pattern.confidence_weight = pattern.confidence_weight
        existing_pattern.enabled = pattern.enabled

        db.commit()
        db.refresh(existing_pattern)

        logger.info(
            "intent_pattern_updated",
            user=current_user.username,
            pattern_id=pattern_id
        )

        return IntentPatternResponse(**existing_pattern.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_update_intent_pattern", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to update intent pattern: {str(e)}")


@router.delete("/patterns/{pattern_id}", status_code=204)
async def delete_intent_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an intent pattern.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        pattern = db.query(IntentPattern).filter(IntentPattern.id == pattern_id).first()

        if not pattern:
            raise HTTPException(status_code=404, detail="Intent pattern not found")

        db.delete(pattern)
        db.commit()

        logger.info(
            "intent_pattern_deleted",
            user=current_user.username,
            pattern_id=pattern_id
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_delete_intent_pattern", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to delete intent pattern: {str(e)}")


# ============================================================================
# Intent Routing Endpoints
# ============================================================================

@router.get("/routing", response_model=List[IntentRoutingResponse])
async def get_intent_routing(
    intent_category: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all intent routing configurations with optional filtering.

    Query Parameters:
    - intent_category: Filter by intent category
    - enabled: Filter by enabled status
    """
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        query = db.query(IntentRouting)

        # Apply filters
        if intent_category:
            query = query.filter(IntentRouting.intent_category == intent_category)
        if enabled is not None:
            query = query.filter(IntentRouting.enabled == enabled)

        routes = query.order_by(IntentRouting.priority.desc(), IntentRouting.intent_category).all()

        logger.info(
            "intent_routing_retrieved",
            user=current_user.username,
            count=len(routes),
            filters={"intent_category": intent_category, "enabled": enabled}
        )

        return [IntentRoutingResponse(**route.to_dict()) for route in routes]

    except Exception as e:
        logger.error("failed_to_retrieve_intent_routing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve intent routing: {str(e)}")


@router.post("/routing", response_model=IntentRoutingResponse, status_code=201)
async def create_intent_routing(
    routing: IntentRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new intent routing configuration.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Check for duplicate
        existing = db.query(IntentRouting).filter(
            IntentRouting.intent_category == routing.intent_category
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Routing already exists for intent category: {routing.intent_category}"
            )

        # Create new routing
        new_routing = IntentRouting(
            intent_category=routing.intent_category,
            use_rag=routing.use_rag,
            rag_service_url=routing.rag_service_url,
            use_web_search=routing.use_web_search,
            use_llm=routing.use_llm,
            priority=routing.priority,
            enabled=routing.enabled
        )

        db.add(new_routing)
        db.commit()
        db.refresh(new_routing)

        logger.info(
            "intent_routing_created",
            user=current_user.username,
            routing_id=new_routing.id,
            intent_category=routing.intent_category
        )

        return IntentRoutingResponse(**new_routing.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_create_intent_routing", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to create intent routing: {str(e)}")


@router.put("/routing/{routing_id}", response_model=IntentRoutingResponse)
async def update_intent_routing(
    routing_id: int,
    routing: IntentRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing intent routing configuration.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        existing_routing = db.query(IntentRouting).filter(IntentRouting.id == routing_id).first()

        if not existing_routing:
            raise HTTPException(status_code=404, detail="Intent routing not found")

        # Update fields
        existing_routing.intent_category = routing.intent_category
        existing_routing.use_rag = routing.use_rag
        existing_routing.rag_service_url = routing.rag_service_url
        existing_routing.use_web_search = routing.use_web_search
        existing_routing.use_llm = routing.use_llm
        existing_routing.priority = routing.priority
        existing_routing.enabled = routing.enabled

        db.commit()
        db.refresh(existing_routing)

        logger.info(
            "intent_routing_updated",
            user=current_user.username,
            routing_id=routing_id
        )

        return IntentRoutingResponse(**existing_routing.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_update_intent_routing", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to update intent routing: {str(e)}")


@router.delete("/routing/{routing_id}", status_code=204)
async def delete_intent_routing(
    routing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an intent routing configuration.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        routing = db.query(IntentRouting).filter(IntentRouting.id == routing_id).first()

        if not routing:
            raise HTTPException(status_code=404, detail="Intent routing not found")

        db.delete(routing)
        db.commit()

        logger.info(
            "intent_routing_deleted",
            user=current_user.username,
            routing_id=routing_id
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_delete_intent_routing", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to delete intent routing: {str(e)}")


# ============================================================================
# Provider Routing Endpoints
# ============================================================================

@router.get("/providers", response_model=List[ProviderRoutingResponse])
async def get_provider_routing(
    intent_category: Optional[str] = Query(None),
    provider_name: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all provider routing configurations with optional filtering.

    Query Parameters:
    - intent_category: Filter by intent category
    - provider_name: Filter by provider name
    - enabled: Filter by enabled status
    """
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        query = db.query(ProviderRouting)

        # Apply filters
        if intent_category:
            query = query.filter(ProviderRouting.intent_category == intent_category)
        if provider_name:
            query = query.filter(ProviderRouting.provider_name == provider_name)
        if enabled is not None:
            query = query.filter(ProviderRouting.enabled == enabled)

        providers = query.order_by(
            ProviderRouting.intent_category,
            ProviderRouting.priority
        ).all()

        logger.info(
            "provider_routing_retrieved",
            user=current_user.username,
            count=len(providers),
            filters={
                "intent_category": intent_category,
                "provider_name": provider_name,
                "enabled": enabled
            }
        )

        return [ProviderRoutingResponse(**provider.to_dict()) for provider in providers]

    except Exception as e:
        logger.error("failed_to_retrieve_provider_routing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve provider routing: {str(e)}")


@router.post("/providers", response_model=ProviderRoutingResponse, status_code=201)
async def create_provider_routing(
    provider: ProviderRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new provider routing configuration.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Check for duplicate
        existing = db.query(ProviderRouting).filter(
            and_(
                ProviderRouting.intent_category == provider.intent_category,
                ProviderRouting.provider_name == provider.provider_name
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Provider routing already exists for {provider.intent_category}/{provider.provider_name}"
            )

        # Create new provider routing
        new_provider = ProviderRouting(
            intent_category=provider.intent_category,
            provider_name=provider.provider_name,
            priority=provider.priority,
            enabled=provider.enabled
        )

        db.add(new_provider)
        db.commit()
        db.refresh(new_provider)

        logger.info(
            "provider_routing_created",
            user=current_user.username,
            provider_id=new_provider.id,
            intent_category=provider.intent_category,
            provider_name=provider.provider_name
        )

        return ProviderRoutingResponse(**new_provider.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_create_provider_routing", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to create provider routing: {str(e)}")


@router.put("/providers/{provider_id}", response_model=ProviderRoutingResponse)
async def update_provider_routing(
    provider_id: int,
    provider: ProviderRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing provider routing configuration.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        existing_provider = db.query(ProviderRouting).filter(ProviderRouting.id == provider_id).first()

        if not existing_provider:
            raise HTTPException(status_code=404, detail="Provider routing not found")

        # Update fields
        existing_provider.intent_category = provider.intent_category
        existing_provider.provider_name = provider.provider_name
        existing_provider.priority = provider.priority
        existing_provider.enabled = provider.enabled

        db.commit()
        db.refresh(existing_provider)

        logger.info(
            "provider_routing_updated",
            user=current_user.username,
            provider_id=provider_id
        )

        return ProviderRoutingResponse(**existing_provider.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_update_provider_routing", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to update provider routing: {str(e)}")


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider_routing(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a provider routing configuration.

    Requires manage_secrets permission.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        provider = db.query(ProviderRouting).filter(ProviderRouting.id == provider_id).first()

        if not provider:
            raise HTTPException(status_code=404, detail="Provider routing not found")

        db.delete(provider)
        db.commit()

        logger.info(
            "provider_routing_deleted",
            user=current_user.username,
            provider_id=provider_id
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("failed_to_delete_provider_routing", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to delete provider routing: {str(e)}")
