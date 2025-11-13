"""
OIDC (OpenID Connect) authentication with Authentik.

Provides SSO integration for Athena Admin interface using Authentik
as the identity provider.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
import structlog

from app.database import get_db
from app.models import User

logger = structlog.get_logger()

# OIDC configuration from environment
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "https://auth.xmojo.net/application/o/athena-admin/")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "https://athena-admin.xmojo.net/auth/callback")
OIDC_SCOPES = os.getenv("OIDC_SCOPES", "openid profile email")

# Session configuration
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "")  # Must be set in production
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", str(60 * 60 * 8)))  # 8 hours default

# JWT configuration for internal tokens
JWT_SECRET = os.getenv("JWT_SECRET", SESSION_SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", str(60 * 60 * 8)))  # 8 hours

# Security
security = HTTPBearer()

# OAuth client configuration
oauth = OAuth()

# Configure Authentik OIDC provider
oauth.register(
    name='authentik',
    client_id=OIDC_CLIENT_ID,
    client_secret=OIDC_CLIENT_SECRET,
    server_metadata_url=f'{OIDC_ISSUER}.well-known/openid-configuration',
    client_kwargs={
        'scope': OIDC_SCOPES,
    }
)


async def get_authentik_userinfo(access_token: str) -> Dict[str, Any]:
    """
    Get user information from Authentik using access token.

    Args:
        access_token: OAuth2 access token from Authentik

    Returns:
        Dict containing user information (sub, email, name, groups, etc.)

    Raises:
        HTTPException: If token is invalid or userinfo request fails
    """
    try:
        async with httpx.AsyncClient() as client:
            # Authentik userinfo endpoint is shared across all applications
            userinfo_url = "https://auth.xmojo.net/application/o/userinfo/"
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error("authentik_userinfo_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to fetch user information from Authentik"
        )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for internal use.

    Args:
        data: Dictionary of claims to include in token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(seconds=JWT_EXPIRATION))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Dictionary of decoded claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_or_create_user(db: Session, userinfo: Dict[str, Any]) -> User:
    """
    Get existing user or create new user from Authentik userinfo.

    Args:
        db: Database session
        userinfo: User information from Authentik

    Returns:
        User object

    Note:
        Default role is 'viewer'. Admins should manually promote users to
        'operator' or 'owner' roles through database or future UI.
    """
    authentik_id = userinfo.get('sub')
    email = userinfo.get('email')
    username = userinfo.get('preferred_username') or email.split('@')[0]
    full_name = userinfo.get('name', '')

    # Check if user exists
    user = db.query(User).filter(User.authentik_id == authentik_id).first()

    if user:
        # Update last login
        user.last_login = datetime.utcnow()
        user.email = email  # Update email in case it changed
        user.full_name = full_name
        db.commit()
        db.refresh(user)
        logger.info("user_login", user_id=user.id, username=user.username)
    else:
        # Create new user with viewer role
        user = User(
            authentik_id=authentik_id,
            username=username,
            email=email,
            full_name=full_name,
            role='viewer',  # Default role
            active=True,
            last_login=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("user_created", user_id=user.id, username=user.username, role=user.role)

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token from request
        db: Database session

    Returns:
        Current authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found

    Usage:
        @app.get("/api/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.username}
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.query(User).filter(User.id == user_id, User.active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user


def require_role(required_role: str):
    """
    Decorator factory for requiring specific role.

    Args:
        required_role: Required role ('owner', 'operator', 'viewer', 'support')

    Returns:
        FastAPI dependency function

    Usage:
        @app.post("/api/policies")
        def create_policy(
            current_user: User = Depends(require_role('operator'))
        ):
            ...
    """
    role_hierarchy = {
        'viewer': 0,
        'support': 1,
        'operator': 2,
        'owner': 3,
    }

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            logger.warning(
                "authorization_failed",
                user_id=current_user.id,
                user_role=current_user.role,
                required_role=required_role
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )

        return current_user

    return role_checker


def require_permission(permission: str):
    """
    Decorator factory for requiring specific permission.

    Args:
        permission: Required permission ('read', 'write', 'delete', 'manage_users', etc.)

    Returns:
        FastAPI dependency function

    Usage:
        @app.delete("/api/policies/{policy_id}")
        def delete_policy(
            policy_id: int,
            current_user: User = Depends(require_permission('delete'))
        ):
            ...
    """
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_permission(permission):
            logger.warning(
                "permission_denied",
                user_id=current_user.id,
                user_role=current_user.role,
                required_permission=permission
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}"
            )

        return current_user

    return permission_checker


# Export public API
__all__ = [
    'oauth',
    'get_authentik_userinfo',
    'create_access_token',
    'decode_access_token',
    'get_or_create_user',
    'get_current_user',
    'require_role',
    'require_permission',
]
