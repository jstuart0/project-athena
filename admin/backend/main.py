"""
Project Athena - Admin Interface Backend

Provides REST API for monitoring and managing Athena services.
Deploys to thor Kubernetes cluster.
"""

import os
import httpx
import socket
import subprocess
import base64
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import structlog

from app.database import get_db, check_db_connection, init_db
from app.auth.oidc import (
    oauth,
    get_authentik_userinfo,
    create_access_token,
    get_or_create_user,
    get_current_user,
)
from app.models import User

# Import API route modules
from app.routes import (
    policies, secrets, devices, audit, users, servers, services, rag_connectors, voice_tests,
    hallucination_checks, multi_intent, validation_models, conversation, llm_backends, settings,
    intent_routing, features, external_api_keys
)

logger = structlog.get_logger()

# Configuration
MAC_STUDIO_IP = os.getenv("MAC_STUDIO_IP", "192.168.10.167")
MAC_MINI_IP = os.getenv("MAC_MINI_IP", "192.168.10.181")

# Mac Studio services
SERVICE_PORTS = {
    "gateway": 8000,
    "orchestrator": 8001,
    "weather": 8010,
    "airports": 8011,
    "flights": 8012,
    "events": 8013,
    "streaming": 8014,
    "news": 8015,
    "stocks": 8016,
    "sports": 8017,
    "websearch": 8018,
    "dining": 8019,
    "recipes": 8020,
    "validators": 8030,
    "ollama": 11434,
    "piper": 10200,
    "whisper": 10300,
}

# Mac mini services (data layer)
MAC_MINI_PORTS = {
    "qdrant": 6333,
    "redis": 6379,
}

app = FastAPI(
    title="Project Athena Admin API",
    description="Admin interface for monitoring and managing Athena services",
    version="2.0.0",  # Version 2 with authentication
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

# Session middleware (must be added BEFORE CORS)
SESSION_SECRET = os.getenv("SESSION_SECRET_KEY", "dev-secret-change-in-production")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API route modules
app.include_router(policies.router)
app.include_router(secrets.router)
app.include_router(devices.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(servers.router)
app.include_router(services.router)
app.include_router(rag_connectors.router)
app.include_router(voice_tests.router)
app.include_router(hallucination_checks.router)
app.include_router(multi_intent.router)
app.include_router(validation_models.router)
app.include_router(conversation.router)
app.include_router(llm_backends.router)
app.include_router(settings.router)
app.include_router(intent_routing.router)
app.include_router(features.router)
app.include_router(external_api_keys.router)


# Startup event: Initialize database and check connections
@app.on_event("startup")
async def startup_event():
    """Initialize database and verify connections on startup."""
    logger.info("athena_admin_startup", version="2.0.0")

    # Check database connection
    if check_db_connection():
        logger.info("database_connection_healthy")

        # Initialize database schema (creates tables if they don't exist)
        try:
            init_db()
            logger.info("database_schema_initialized")
        except Exception as e:
            logger.error("database_schema_init_failed", error=str(e))

        # Configure OAuth/OIDC from database
        try:
            from app.auth.oidc import configure_oauth_client
            configure_oauth_client()
            logger.info("oidc_configuration_loaded")
        except Exception as e:
            logger.error("oidc_configuration_failed", error=str(e))
    else:
        logger.error("database_connection_failed")

    logger.info("athena_admin_ready")


# Authentication routes
@app.get("/auth/login")
@app.get("/api/auth/login")
async def auth_login(request: Request, db: Session = Depends(get_db)):
    """Initiate OIDC login flow with Authentik."""
    # Demo mode bypass for development/testing
    if os.getenv("DEMO_MODE", "false").lower() == "true" or os.getenv("OIDC_CLIENT_ID") == "demo-mode":
        # Create demo userinfo dictionary
        demo_userinfo = {
            "sub": "demo-admin",
            "email": "admin@demo.local",
            "preferred_username": "admin",
            "name": "Demo Admin",
            "groups": ["admin"]
        }

        # Create or get demo user using the proper function signature
        demo_user = get_or_create_user(db=db, userinfo=demo_userinfo)

        # Create demo token with proper data structure
        demo_token = create_access_token(
            data={
                "sub": demo_user.authentik_id,
                "user_id": demo_user.id,  # Required by get_current_user
                "email": demo_user.email,
                "username": demo_user.username,
                "full_name": demo_user.full_name,
                "groups": ["admin"]
            }
        )

        frontend_url = os.getenv("FRONTEND_URL", "https://athena-admin.xmojo.net")
        return RedirectResponse(url=f"{frontend_url}?token={demo_token}")

    # Normal OAuth flow
    # Use explicit HTTPS redirect URI from environment (not request.url_for which returns HTTP)
    redirect_uri = os.getenv("OIDC_REDIRECT_URI", "https://athena-admin.xmojo.net/auth/callback")
    logger.info("auth_login_redirect", redirect_uri=redirect_uri)
    return await oauth.authentik.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
@app.get("/api/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """
    OIDC callback endpoint.

    Exchanges authorization code for tokens, fetches user info,
    creates/updates user in database, and returns JWT token.
    """
    logger.info("auth_callback_received", query_params=str(request.query_params))
    try:
        # Exchange authorization code for tokens
        # Skip ID token validation - we fetch userinfo directly
        token = await oauth.authentik.authorize_access_token(
            request,
            claims_options={
                "iss": {"essential": False},
                "aud": {"essential": False},
                "exp": {"essential": False}
            }
        )
        access_token = token.get('access_token')

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        # Get user info from Authentik
        userinfo = await get_authentik_userinfo(access_token)

        # Create or update user in database
        user = get_or_create_user(db, userinfo)

        # Create internal JWT token
        jwt_token = create_access_token({
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
        })

        # Store token in session
        request.session['access_token'] = jwt_token
        request.session['user_id'] = user.id

        logger.info("user_authenticated", user_id=user.id, username=user.username)

        # Redirect to frontend with token
        frontend_url = os.getenv("FRONTEND_URL", "https://athena-admin.xmojo.net")
        return RedirectResponse(url=f"{frontend_url}?token={jwt_token}")

    except Exception as e:
        logger.error("auth_callback_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Authentication failed")


@app.get("/auth/logout")
@app.get("/api/auth/logout")
async def auth_logout(request: Request):
    """Logout user and clear session."""
    request.session.clear()
    logger.info("user_logged_out")

    frontend_url = os.getenv("FRONTEND_URL", "https://athena-admin.xmojo.net")
    return RedirectResponse(url=frontend_url)


@app.get("/auth/me")
@app.get("/api/auth/me")
async def auth_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }


class ServiceStatus(BaseModel):
    """Service status model."""
    name: str
    port: int
    healthy: bool
    status: str
    version: str = "unknown"
    error: str = None


class SystemStatus(BaseModel):
    """Overall system status model."""
    healthy_services: int
    total_services: int
    overall_health: str
    services: List[ServiceStatus]


@app.get("/health")
async def health_check():
    """Health check for admin API itself."""
    return {
        "status": "healthy",
        "service": "athena-admin",
        "version": "1.0.0"
    }


@app.get("/status", response_model=SystemStatus)
@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """Get status of all Athena services."""
    service_statuses = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check Mac Studio services
        for service_name, port in SERVICE_PORTS.items():
            status = ServiceStatus(
                name=f"{service_name} (studio)",
                port=port,
                healthy=False,
                status="unknown"
            )

            try:
                # Special handling for different service types
                if service_name == "whisper" or service_name == "piper":
                    # Whisper and Piper use Wyoming protocol (TCP), check via socket
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((MAC_STUDIO_IP, port))
                        sock.close()

                        if result == 0:
                            status.healthy = True
                            status.status = "running"
                        else:
                            status.status = "error"
                            status.error = f"Connection failed: {result}"
                        service_statuses.append(status)
                        continue  # Skip HTTP check
                    except Exception as e:
                        status.status = "error"
                        status.error = str(e)
                        service_statuses.append(status)
                        continue

                # HTTP-based health checks
                if service_name == "ollama":
                    url = f"http://{MAC_STUDIO_IP}:{port}/api/tags"
                else:
                    url = f"http://{MAC_STUDIO_IP}:{port}/health"

                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    status.healthy = True
                    status.status = "running"
                    status.version = data.get("version", "unknown")
                elif response.status_code == 401:
                    # Gateway returns 401 for unauthenticated health checks
                    status.healthy = True
                    status.status = "running (auth required)"
                else:
                    status.status = f"error: HTTP {response.status_code}"
                    status.error = f"Unexpected status code: {response.status_code}"

            except httpx.TimeoutException:
                status.status = "timeout"
                status.error = "Service did not respond within timeout"
            except Exception as e:
                status.status = "error"
                status.error = str(e)

            service_statuses.append(status)

        # Check Mac mini services (optional - graceful degradation)
        for service_name, port in MAC_MINI_PORTS.items():
            status = ServiceStatus(
                name=f"{service_name} (mini)",
                port=port,
                healthy=False,
                status="not deployed"
            )

            try:
                if service_name == "redis":
                    # Redis uses binary protocol, check via TCP socket
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((MAC_MINI_IP, port))
                        sock.close()

                        if result == 0:
                            status.healthy = True
                            status.status = "running"
                        else:
                            status.status = "not deployed (optional)"
                            status.error = "Service not yet deployed - system works without this"
                    except Exception as e:
                        status.status = "not deployed (optional)"
                        status.error = "Service not yet deployed - system works without this"
                else:
                    # HTTP-based health checks for other services
                    if service_name == "qdrant":
                        url = f"http://{MAC_MINI_IP}:{port}/healthz"
                    else:
                        url = f"http://{MAC_MINI_IP}:{port}/health"

                    response = await client.get(url)

                    if response.status_code == 200:
                        status.healthy = True
                        status.status = "running"
                    else:
                        status.status = f"error: HTTP {response.status_code}"
                        status.error = f"Unexpected status code: {response.status_code}"

            except httpx.ConnectError:
                status.status = "not deployed (optional)"
                status.error = "Service not yet deployed - system works without this"
            except httpx.TimeoutException:
                status.status = "not deployed (optional)"
                status.error = "Service not yet deployed - system works without this"
            except Exception as e:
                status.status = "not deployed (optional)"
                status.error = "Service not yet deployed - system works without this"

            service_statuses.append(status)

        # Check SearXNG (cluster-local service)
        searxng_status = ServiceStatus(
            name="searxng (search)",
            port=8080,
            healthy=False,
            status="unknown"
        )

        try:
            url = "http://searxng.athena-admin.svc.cluster.local:8080/healthz"
            response = await client.get(url)

            if response.status_code == 200:
                searxng_status.healthy = True
                searxng_status.status = "running"
            else:
                searxng_status.status = f"error: HTTP {response.status_code}"
                searxng_status.error = f"Unexpected status code: {response.status_code}"

        except httpx.ConnectError:
            searxng_status.status = "not deployed"
            searxng_status.error = "SearXNG service not accessible"
        except httpx.TimeoutException:
            searxng_status.status = "timeout"
            searxng_status.error = "Service did not respond within timeout"
        except Exception as e:
            searxng_status.status = "error"
            searxng_status.error = str(e)

        service_statuses.append(searxng_status)

    healthy_count = sum(1 for s in service_statuses if s.healthy)
    total_count = len(service_statuses)

    overall_health = "healthy" if healthy_count == total_count else \
                    "degraded" if healthy_count > total_count * 0.5 else "critical"

    return SystemStatus(
        healthy_services=healthy_count,
        total_services=total_count,
        overall_health=overall_health,
        services=service_statuses
    )


@app.get("/services")
async def list_services():
    """List all configured services."""
    return {
        "services": [
            {"name": name, "port": port, "url": f"http://{MAC_STUDIO_IP}:{port}"}
            for name, port in SERVICE_PORTS.items()
        ]
    }


@app.post("/test-query")
async def test_query(query: str = "what is 2+2?"):
    """Test a query against the orchestrator."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"http://{MAC_STUDIO_IP}:8001/v1/chat/completions",
                json={"messages": [{"role": "user", "content": query}]}
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data["choices"][0]["message"]["content"],
                    "metadata": data.get("athena_metadata", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "details": response.text
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
