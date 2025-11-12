"""
Project Athena - Admin Interface Backend

Provides REST API for monitoring and managing Athena services.
Deploys to thor Kubernetes cluster.
"""

import os
import httpx
import socket
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

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
    "whisper": 10300,
}

# Mac mini services (data layer)
MAC_MINI_PORTS = {
    "qdrant": 6333,
    "redis": 6379,
}

app = FastAPI(
    title="Project Athena Admin API",
    description="Admin interface for monitoring Athena services",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
                if service_name == "whisper":
                    # Whisper uses Wyoming protocol (TCP), check via socket
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


@app.get("/api/services")
async def list_services():
    """List all configured services."""
    return {
        "services": [
            {"name": name, "port": port, "url": f"http://{MAC_STUDIO_IP}:{port}"}
            for name, port in SERVICE_PORTS.items()
        ]
    }


@app.post("/api/test-query")
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
