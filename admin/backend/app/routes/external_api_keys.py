"""
External API key management routes.

Stores encrypted API credentials for external providers (e.g., sports APIs)
and exposes a public, service-to-service endpoint for retrieval.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import structlog

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, ExternalAPIKey
from app.utils.encryption import encrypt_value, decrypt_value

logger = structlog.get_logger()

router = APIRouter(prefix="/api/external-api-keys", tags=["external-api-keys"])


class ExternalAPIKeyCreate(BaseModel):
    """Request model for creating/updating an external API key."""
    service_name: str = Field(..., description="Unique service identifier (e.g., api-football)")
    api_name: str = Field(..., description="Human-readable API name")
    api_key: str = Field(..., description="API key (will be encrypted)")
    endpoint_url: str = Field(..., description="Base API endpoint URL")
    enabled: bool = Field(default=True, description="Enable/disable API")
    description: Optional[str] = Field(None, description="Admin notes")
    rate_limit_per_minute: Optional[int] = Field(None, description="Rate limit")


class ExternalAPIKeyResponse(BaseModel):
    """Response model for external API key (masked)."""
    id: int
    service_name: str
    api_name: str
    api_key_masked: str
    endpoint_url: str
    enabled: bool
    description: Optional[str]
    rate_limit_per_minute: Optional[int]
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime]

    class Config:
        from_attributes = True


def _mask_key(encrypted: str) -> str:
    """Mask decrypted API key to last 4 characters."""
    try:
        decrypted = decrypt_value(encrypted)
        return f"{'*' * max(len(decrypted) - 4, 0)}{decrypted[-4:]}"
    except Exception:
        return "****"


def _to_response(key: ExternalAPIKey) -> ExternalAPIKeyResponse:
    """Convert DB model to response payload."""
    return ExternalAPIKeyResponse(
        id=key.id,
        service_name=key.service_name,
        api_name=key.api_name,
        api_key_masked=_mask_key(key.api_key_encrypted),
        endpoint_url=key.endpoint_url,
        enabled=key.enabled,
        description=key.description,
        rate_limit_per_minute=key.rate_limit_per_minute,
        created_at=key.created_at,
        updated_at=key.updated_at,
        last_used=key.last_used
    )


@router.post("", response_model=ExternalAPIKeyResponse, status_code=201)
async def create_external_api_key(
    key_data: ExternalAPIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new external API key (encrypted at rest)."""
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    existing = db.query(ExternalAPIKey).filter_by(service_name=key_data.service_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"API key for '{key_data.service_name}' already exists")

    encrypted_key = encrypt_value(key_data.api_key)

    new_key = ExternalAPIKey(
        service_name=key_data.service_name,
        api_name=key_data.api_name,
        api_key_encrypted=encrypted_key,
        endpoint_url=key_data.endpoint_url,
        enabled=key_data.enabled,
        description=key_data.description,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        created_by_id=current_user.id
    )

    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    logger.info(
        "external_api_key_created",
        service_name=new_key.service_name,
        user=current_user.username
    )
    return _to_response(new_key)


@router.get("", response_model=List[ExternalAPIKeyResponse])
async def list_external_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all external API keys (masked)."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    keys = db.query(ExternalAPIKey).order_by(ExternalAPIKey.service_name).all()
    return [_to_response(key) for key in keys]


@router.get("/{service_name}", response_model=ExternalAPIKeyResponse)
async def get_external_api_key(
    service_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a specific external API key by service name (masked)."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    key = db.query(ExternalAPIKey).filter_by(service_name=service_name).first()
    if not key:
        raise HTTPException(status_code=404, detail=f"API key '{service_name}' not found")

    return _to_response(key)


@router.put("/{service_name}", response_model=ExternalAPIKeyResponse)
async def update_external_api_key(
    service_name: str,
    key_data: ExternalAPIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing external API key."""
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    key = db.query(ExternalAPIKey).filter_by(service_name=service_name).first()
    if not key:
        raise HTTPException(status_code=404, detail=f"API key '{service_name}' not found")

    key.api_name = key_data.api_name
    key.endpoint_url = key_data.endpoint_url
    key.enabled = key_data.enabled
    key.description = key_data.description
    key.rate_limit_per_minute = key_data.rate_limit_per_minute
    if key_data.api_key:
        key.api_key_encrypted = encrypt_value(key_data.api_key)

    db.commit()
    db.refresh(key)

    logger.info(
        "external_api_key_updated",
        service_name=key.service_name,
        user=current_user.username
    )
    return _to_response(key)


@router.delete("/{service_name}")
async def delete_external_api_key(
    service_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an external API key."""
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    key = db.query(ExternalAPIKey).filter_by(service_name=service_name).first()
    if not key:
        raise HTTPException(status_code=404, detail=f"API key '{service_name}' not found")

    db.delete(key)
    db.commit()

    logger.info(
        "external_api_key_deleted",
        service_name=service_name,
        user=current_user.username
    )
    return {"message": f"API key '{service_name}' deleted"}


@router.get("/public/{service_name}/key", include_in_schema=False)
async def get_api_key_for_service(
    service_name: str,
    db: Session = Depends(get_db)
):
    """
    Public (service-to-service) endpoint to fetch decrypted API key.
    Intended for internal services; no authentication enforced here.
    """
    key = db.query(ExternalAPIKey).filter_by(
        service_name=service_name,
        enabled=True
    ).first()

    if not key:
        raise HTTPException(status_code=404, detail=f"Enabled API key '{service_name}' not found")

    key.last_used = datetime.utcnow()
    db.commit()

    try:
        decrypted_key = decrypt_value(key.api_key_encrypted)
    except Exception as e:
        logger.error("external_api_key_decrypt_failed", service_name=service_name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to decrypt API key")

    return {
        "api_key": decrypted_key,
        "endpoint_url": key.endpoint_url,
        "rate_limit_per_minute": key.rate_limit_per_minute
    }

