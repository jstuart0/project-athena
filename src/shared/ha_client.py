"""Home Assistant API client for Project Athena"""

import os
import httpx
from typing import Optional, Dict, Any


class HomeAssistantClient:
    """Client for interacting with Home Assistant API"""
    
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        self.url = url or os.getenv("HA_URL", "https://192.168.10.168:8123")
        self.token = token or os.getenv("HA_TOKEN")
        
        if not self.token:
            raise ValueError("HA_TOKEN must be provided or set in environment")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=self.url,
            headers=self.headers,
            verify=False,  # Self-signed cert
            timeout=30.0
        )
    
    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of an entity"""
        response = await self.client.get(f"/api/states/{entity_id}")
        response.raise_for_status()
        return response.json()
    
    async def call_service(
        self, 
        domain: str, 
        service: str, 
        service_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Call a Home Assistant service"""
        url = f"/api/services/{domain}/{service}"
        response = await self.client.post(url, json=service_data or {})
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> bool:
        """Check if Home Assistant is reachable"""
        try:
            response = await self.client.get("/api/")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
