"""
Admin Configuration Client

Allows services to fetch configuration and secrets from the admin API.
Uses service-to-service authentication with API key.
"""
import os
import time
import httpx
from typing import Optional, Dict, Any, List
import structlog

logger = structlog.get_logger()


class AdminConfigClient:
    """Client for fetching configuration from admin API."""

    def __init__(
        self,
        admin_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize admin configuration client.

        Args:
            admin_url: Admin API URL (defaults to ADMIN_API_URL env var)
            api_key: Service API key (defaults to SERVICE_API_KEY env var)
        """
        self.admin_url = admin_url or os.getenv(
            "ADMIN_API_URL",
            "http://localhost:8080"  # Default for local development
        )
        self.api_key = api_key or os.getenv(
            "SERVICE_API_KEY",
            "dev-service-key-change-in-production"
        )
        self.client = httpx.AsyncClient(timeout=10.0)

        # Routing configuration cache (60-second TTL)
        self._cache_ttl = 60
        self._patterns_cache: Optional[Dict[str, List[str]]] = None
        self._patterns_cache_time = 0.0
        self._routing_cache: Optional[Dict[str, Dict]] = None
        self._routing_cache_time = 0.0
        self._providers_cache: Optional[Dict[str, List[str]]] = None
        self._providers_cache_time = 0.0

        # LLM backends and features cache
        self._llm_backends_cache: Optional[List[Dict[str, Any]]] = None
        self._llm_backends_cache_time = 0.0
        self._features_cache: Optional[Dict[str, bool]] = None
        self._features_cache_time = 0.0

    async def get_secret(self, service_name: str) -> Optional[str]:
        """
        Fetch a secret value from the admin API.

        Args:
            service_name: Name of the service/secret to fetch

        Returns:
            Secret value, or None if not found

        Raises:
            Exception: If API call fails
        """
        try:
            url = f"{self.admin_url}/api/secrets/service/{service_name}"
            headers = {"X-API-Key": self.api_key}

            response = await self.client.get(url, headers=headers)

            if response.status_code == 404:
                logger.warning(
                    "secret_not_found",
                    service_name=service_name,
                    admin_url=self.admin_url
                )
                return None

            response.raise_for_status()
            data = response.json()
            return data.get("value")

        except httpx.HTTPStatusError as e:
            logger.error(
                "admin_api_error",
                service_name=service_name,
                status_code=e.response.status_code,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "admin_api_connection_failed",
                service_name=service_name,
                error=str(e)
            )
            raise

    async def get_config(self, key: str, default: Any = None) -> Any:
        """
        Fetch a configuration value.

        For now, this falls back to environment variables. In the future,
        this could fetch from a dedicated configuration store in the admin API.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        # TODO: Implement admin API endpoint for general config
        # For now, use environment variables
        return os.getenv(key, default)

    async def get_intent_patterns(self) -> Dict[str, List[str]]:
        """
        Fetch intent patterns from Admin API with caching.

        Returns:
            Dict mapping intent_category -> list of keywords
            Returns empty dict if API unavailable (allows hardcoded fallback)
        """
        # Check cache
        if self._patterns_cache and (time.time() - self._patterns_cache_time < self._cache_ttl):
            return self._patterns_cache

        # Fetch from API
        try:
            url = f"{self.admin_url}/api/intent-routing/patterns"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()

                # Transform API response to Dict[category, List[keywords]]
                patterns: Dict[str, List[str]] = {}
                for item in data:
                    category = item["intent_category"]
                    keyword = item["keyword"]

                    if category not in patterns:
                        patterns[category] = []
                    patterns[category].append(keyword)

                # Cache successful result
                self._patterns_cache = patterns
                self._patterns_cache_time = time.time()

                logger.info(
                    "intent_patterns_loaded_from_db",
                    categories=len(patterns),
                    total_keywords=sum(len(kws) for kws in patterns.values())
                )
                return patterns
            else:
                logger.warning(
                    "intent_patterns_fetch_failed",
                    status_code=response.status_code
                )

        except Exception as e:
            logger.warning(
                "intent_patterns_db_error",
                error=str(e),
                admin_url=self.admin_url
            )

        # Return empty dict to trigger hardcoded fallback
        return {}

    async def get_intent_routing(self) -> Dict[str, Dict]:
        """
        Fetch intent routing configuration with caching.

        Returns:
            Dict mapping intent_category -> {use_rag, rag_service_url, use_web_search, use_llm}
            Returns empty dict if API unavailable (allows hardcoded fallback)
        """
        # Check cache
        if self._routing_cache and (time.time() - self._routing_cache_time < self._cache_ttl):
            return self._routing_cache

        # Fetch from API
        try:
            url = f"{self.admin_url}/api/intent-routing/routing"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()

                # Transform API response to Dict[category, config_dict]
                routing: Dict[str, Dict] = {}
                for item in data:
                    category = item["intent_category"]
                    routing[category] = {
                        "use_rag": item.get("use_rag", False),
                        "rag_service_url": item.get("rag_service_url"),
                        "use_web_search": item.get("use_web_search", False),
                        "use_llm": item.get("use_llm", True),
                        "priority": item.get("priority", 100)
                    }

                # Cache successful result
                self._routing_cache = routing
                self._routing_cache_time = time.time()

                logger.info(
                    "intent_routing_loaded_from_db",
                    categories=len(routing)
                )
                return routing
            else:
                logger.warning(
                    "intent_routing_fetch_failed",
                    status_code=response.status_code
                )

        except Exception as e:
            logger.warning(
                "intent_routing_db_error",
                error=str(e),
                admin_url=self.admin_url
            )

        # Return empty dict to trigger hardcoded fallback
        return {}

    async def get_provider_routing(self) -> Dict[str, List[str]]:
        """
        Fetch provider routing with caching (ordered by priority).

        Returns:
            Dict mapping intent_category -> ordered list of provider names
            Returns empty dict if API unavailable (allows hardcoded fallback)
        """
        # Check cache
        if self._providers_cache and (time.time() - self._providers_cache_time < self._cache_ttl):
            return self._providers_cache

        # Fetch from API
        try:
            url = f"{self.admin_url}/api/intent-routing/providers"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()

                # Group by category and sort by priority
                providers: Dict[str, List[str]] = {}
                for item in data:
                    category = item["intent_category"]
                    provider = item["provider_name"]
                    priority = item.get("priority", 100)

                    if category not in providers:
                        providers[category] = []
                    providers[category].append((provider, priority))

                # Sort by priority and extract provider names
                for category in providers:
                    providers[category] = [
                        p[0] for p in sorted(providers[category], key=lambda x: x[1])
                    ]

                # Cache successful result
                self._providers_cache = providers
                self._providers_cache_time = time.time()

                logger.info(
                    "provider_routing_loaded_from_db",
                    categories=len(providers)
                )
                return providers
            else:
                logger.warning(
                    "provider_routing_fetch_failed",
                    status_code=response.status_code
                )

        except Exception as e:
            logger.warning(
                "provider_routing_db_error",
                error=str(e),
                admin_url=self.admin_url
            )

        # Return empty dict to trigger hardcoded fallback
        return {}

    async def get_llm_backends(self) -> List[Dict[str, Any]]:
        """
        Fetch enabled LLM backends from Admin API with caching.

        Returns:
            List of LLM backend configurations sorted by priority
            Returns empty list if API unavailable (allows env var fallback)
        """
        # Check cache
        if self._llm_backends_cache and (time.time() - self._llm_backends_cache_time < self._cache_ttl):
            return self._llm_backends_cache

        # Fetch from API
        try:
            url = f"{self.admin_url}/api/llm-backends/public"
            response = await self.client.get(url)

            if response.status_code == 200:
                backends = response.json()

                # Filter to only enabled backends and sort by priority
                enabled_backends = [b for b in backends if b.get("enabled", False)]
                enabled_backends.sort(key=lambda x: x.get("priority", 999))

                # Cache successful result
                self._llm_backends_cache = enabled_backends
                self._llm_backends_cache_time = time.time()

                logger.info(
                    "llm_backends_loaded_from_db",
                    count=len(enabled_backends),
                    backends=[b.get("model_name") for b in enabled_backends]
                )
                return enabled_backends
            else:
                logger.warning(
                    "llm_backends_fetch_failed",
                    status_code=response.status_code
                )

        except Exception as e:
            logger.warning(
                "llm_backends_db_error",
                error=str(e),
                admin_url=self.admin_url
            )

        # Return empty list to trigger env var fallback
        return []

    async def get_feature_flags(self) -> Dict[str, bool]:
        """
        Fetch feature flags from Admin API with caching.

        Returns:
            Dict mapping feature_name -> enabled status
            Returns empty dict if API unavailable (allows hardcoded defaults)
        """
        # Check cache
        if self._features_cache and (time.time() - self._features_cache_time < self._cache_ttl):
            return self._features_cache

        # Fetch from API
        try:
            url = f"{self.admin_url}/api/features/public?enabled_only=false"
            response = await self.client.get(url)

            if response.status_code == 200:
                features = response.json()

                # Transform to dict of name -> enabled
                flags = {f["name"]: f.get("enabled", False) for f in features}

                # Cache successful result
                self._features_cache = flags
                self._features_cache_time = time.time()

                logger.info(
                    "feature_flags_loaded_from_db",
                    count=len(flags),
                    enabled_count=sum(1 for v in flags.values() if v)
                )
                return flags
            else:
                logger.warning(
                    "feature_flags_fetch_failed",
                    status_code=response.status_code
                )

        except Exception as e:
            logger.warning(
                "feature_flags_db_error",
                error=str(e),
                admin_url=self.admin_url
            )

        # Return empty dict to trigger hardcoded defaults
        return {}

    async def is_feature_enabled(self, feature_name: str) -> Optional[bool]:
        """
        Check if a specific feature is enabled.

        Args:
            feature_name: Name of the feature to check

        Returns:
            True if enabled, False if disabled, None if not found in DB (use default)
        """
        flags = await self.get_feature_flags()
        return flags.get(feature_name)

    async def get_external_api_key(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch external API key from Admin API (decrypted).

        Args:
            service_name: Service identifier (e.g., "brave-search", "api-football")

        Returns:
            Dict with api_key, endpoint_url, rate_limit_per_minute, or None if not found
        """
        try:
            url = f"{self.admin_url}/api/external-api-keys/public/{service_name}/key"
            response = await self.client.get(url)

            if response.status_code == 404:
                logger.debug(
                    "external_api_key_not_found",
                    service_name=service_name
                )
                return None

            response.raise_for_status()
            data = response.json()

            logger.info(
                "external_api_key_fetched",
                service_name=service_name,
                endpoint_url=data.get("endpoint_url")
            )
            return data

        except httpx.HTTPStatusError as e:
            logger.warning(
                "external_api_key_fetch_error",
                service_name=service_name,
                status_code=e.response.status_code,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.warning(
                "external_api_key_connection_failed",
                service_name=service_name,
                error=str(e)
            )
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance for convenience
_admin_client: Optional[AdminConfigClient] = None


def get_admin_client() -> AdminConfigClient:
    """
    Get or create admin configuration client singleton.

    Returns:
        AdminConfigClient instance
    """
    global _admin_client
    if _admin_client is None:
        _admin_client = AdminConfigClient()
    return _admin_client


async def get_secret(service_name: str) -> Optional[str]:
    """
    Convenience function to fetch a secret.

    Args:
        service_name: Name of the service/secret

    Returns:
        Secret value or None
    """
    client = get_admin_client()
    return await client.get_secret(service_name)


async def get_config(key: str, default: Any = None) -> Any:
    """
    Convenience function to fetch configuration.

    Args:
        key: Configuration key
        default: Default value

    Returns:
        Configuration value
    """
    client = get_admin_client()
    return await client.get_config(key, default)


if __name__ == "__main__":
    import asyncio

    async def test():
        """Test the admin configuration client."""
        client = AdminConfigClient()

        # Test fetching a secret
        print("Testing secret fetch...")
        try:
            ha_token = await client.get_secret("home-assistant")
            if ha_token:
                print(f"✓ Home Assistant token: {ha_token[:20]}...")
            else:
                print("✗ Home Assistant token not found")
        except Exception as e:
            print(f"✗ Error fetching secret: {e}")

        await client.close()

    asyncio.run(test())
