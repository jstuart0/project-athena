"""
Settings management API routes.

Provides endpoints for managing application settings including OIDC configuration.
Settings are stored as encrypted secrets in the database.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import structlog

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, Secret
from app.utils.encryption import encrypt_value, decrypt_value

logger = structlog.get_logger()

router = APIRouter(prefix="/api/settings", tags=["settings"])


class OIDCSettings(BaseModel):
    """OIDC configuration settings."""
    provider_url: str
    client_id: str
    client_secret: Optional[str] = None  # Only included when saving
    redirect_uri: str


class OIDCSettingsResponse(BaseModel):
    """OIDC settings response (excludes client_secret)."""
    provider_url: str
    client_id: str
    redirect_uri: str


@router.get("/oidc", response_model=OIDCSettingsResponse)
async def get_oidc_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get OIDC authentication settings.

    Returns current OIDC configuration from database.
    Client secret is not included in response for security.
    """
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Load OIDC settings from secrets table
        provider_url_secret = db.query(Secret).filter(Secret.service_name == "oidc_provider_url").first()
        client_id_secret = db.query(Secret).filter(Secret.service_name == "oidc_client_id").first()
        redirect_uri_secret = db.query(Secret).filter(Secret.service_name == "oidc_redirect_uri").first()

        # Decrypt values
        provider_url = decrypt_value(provider_url_secret.encrypted_value) if provider_url_secret else ""
        client_id = decrypt_value(client_id_secret.encrypted_value) if client_id_secret else ""
        redirect_uri = decrypt_value(redirect_uri_secret.encrypted_value) if redirect_uri_secret else "https://athena-admin.xmojo.net/api/auth/callback"

        logger.info("oidc_settings_retrieved", user=current_user.username)

        return OIDCSettingsResponse(
            provider_url=provider_url,
            client_id=client_id,
            redirect_uri=redirect_uri
        )

    except Exception as e:
        logger.error("failed_to_retrieve_oidc_settings", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve OIDC settings")


@router.post("/oidc")
async def save_oidc_settings(
    settings: OIDCSettings,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save OIDC authentication settings.

    Stores OIDC configuration as encrypted secrets in database.
    Requires manage_secrets permission.

    Note: Backend must be restarted for changes to take effect.
    """
    if not current_user.has_permission('manage_secrets'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Save or update each OIDC setting as a secret
        def save_or_update_secret(service_name: str, value: str):
            """Helper to save or update a secret."""
            secret = db.query(Secret).filter(Secret.service_name == service_name).first()

            if secret:
                # Update existing
                secret.encrypted_value = encrypt_value(value)
            else:
                # Create new
                secret = Secret(
                    service_name=service_name,
                    encrypted_value=encrypt_value(value),
                    description=f"OIDC configuration - {service_name}",
                    created_by_id=current_user.id
                )
                db.add(secret)

        # Save provider URL
        save_or_update_secret("oidc_provider_url", settings.provider_url)

        # Save client ID
        save_or_update_secret("oidc_client_id", settings.client_id)

        # Save client secret (only if provided)
        if settings.client_secret:
            save_or_update_secret("oidc_client_secret", settings.client_secret)

        # Save redirect URI
        save_or_update_secret("oidc_redirect_uri", settings.redirect_uri)

        db.commit()

        logger.info(
            "oidc_settings_saved",
            user=current_user.username,
            provider_url=settings.provider_url,
            ip=request.client.host
        )

        return {
            "status": "success",
            "message": "OIDC settings saved successfully. Backend restart required for changes to take effect."
        }

    except Exception as e:
        db.rollback()
        logger.error("failed_to_save_oidc_settings", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to save OIDC settings: {str(e)}")
