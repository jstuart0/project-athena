"""
Conversation Configuration Loader.

Loads conversation context and clarification settings from the Admin Panel database
(postgres-01.xmojo.net) with optional Redis caching for performance.
"""

import os
import asyncpg
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = structlog.get_logger()

# Database connection details (always postgres-01.xmojo.net)
ADMIN_DB_HOST = os.getenv("ADMIN_DB_HOST", "postgres-01.xmojo.net")
ADMIN_DB_PORT = int(os.getenv("ADMIN_DB_PORT", "5432"))
ADMIN_DB_NAME = os.getenv("ADMIN_DB_NAME", "athena_admin")
ADMIN_DB_USER = os.getenv("ADMIN_DB_USER", "psadmin")
ADMIN_DB_PASSWORD = os.getenv("ADMIN_DB_PASSWORD", "Ibucej1!")

# Redis connection (optional - graceful degradation if not available)
REDIS_HOST = os.getenv("REDIS_HOST", "192.168.10.181")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
CACHE_TTL = 300  # 5 minutes

# In-memory fallback cache
_memory_cache: Dict[str, tuple[Any, datetime]] = {}


class ConversationConfig:
    """Configuration manager for conversation context and clarification features."""

    def __init__(self):
        """Initialize configuration manager."""
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client = None
        self._initialized = False

    async def initialize(self):
        """Initialize database connection pool and Redis client."""
        if self._initialized:
            return

        try:
            # Initialize PostgreSQL connection pool
            self.db_pool = await asyncpg.create_pool(
                host=ADMIN_DB_HOST,
                port=ADMIN_DB_PORT,
                database=ADMIN_DB_NAME,
                user=ADMIN_DB_USER,
                password=ADMIN_DB_PASSWORD,
                min_size=1,
                max_size=5,
                command_timeout=10
            )
            logger.info("config_loader_db_connected", host=ADMIN_DB_HOST, database=ADMIN_DB_NAME)

            # Initialize Redis if enabled
            if REDIS_ENABLED:
                try:
                    import redis.asyncio as redis
                    self.redis_client = redis.Redis(
                        host=REDIS_HOST,
                        port=REDIS_PORT,
                        decode_responses=True,
                        socket_connect_timeout=2
                    )
                    # Test connection
                    await self.redis_client.ping()
                    logger.info("config_loader_redis_connected", host=REDIS_HOST)
                except Exception as e:
                    logger.warning("config_loader_redis_unavailable", error=str(e))
                    self.redis_client = None

            self._initialized = True

        except Exception as e:
            logger.error("config_loader_init_failed", error=str(e))
            raise

    async def close(self):
        """Close database and Redis connections."""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
        self._initialized = False

    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis or memory fallback)."""
        # Try Redis first
        if self.redis_client:
            try:
                import json
                value = await self.redis_client.get(key)
                if value:
                    logger.debug("config_cache_hit", key=key, source="redis")
                    return json.loads(value)
            except Exception as e:
                logger.warning("config_redis_get_failed", key=key, error=str(e))

        # Fallback to memory cache
        if key in _memory_cache:
            cached_value, cached_time = _memory_cache[key]
            if datetime.utcnow() - cached_time < timedelta(seconds=CACHE_TTL):
                logger.debug("config_cache_hit", key=key, source="memory")
                return cached_value
            else:
                # Expired
                del _memory_cache[key]

        return None

    async def _set_to_cache(self, key: str, value: Any):
        """Set value in cache (Redis or memory fallback)."""
        # Try Redis first
        if self.redis_client:
            try:
                import json
                await self.redis_client.setex(
                    key,
                    CACHE_TTL,
                    json.dumps(value)
                )
                logger.debug("config_cached", key=key, source="redis")
                return
            except Exception as e:
                logger.warning("config_redis_set_failed", key=key, error=str(e))

        # Fallback to memory cache
        _memory_cache[key] = (value, datetime.utcnow())
        logger.debug("config_cached", key=key, source="memory")

    async def get_conversation_settings(self) -> Dict[str, Any]:
        """
        Get conversation context settings.

        Returns:
            Dictionary with conversation settings (enabled, max_messages, timeout, etc.)
        """
        cache_key = "conversation:settings"

        # Check cache first
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        # Load from database
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM conversation_settings LIMIT 1")

            if not row:
                logger.warning("conversation_settings_not_found")
                # Return defaults
                settings = {
                    "enabled": True,
                    "use_context": True,
                    "max_messages": 20,
                    "timeout_seconds": 1800,
                    "cleanup_interval_seconds": 60,
                    "session_ttl_seconds": 3600,
                    "max_llm_history_messages": 10
                }
            else:
                settings = dict(row)

        # Cache and return
        await self._set_to_cache(cache_key, settings)
        logger.info("conversation_settings_loaded", enabled=settings.get("enabled"))
        return settings

    async def get_clarification_settings(self) -> Dict[str, Any]:
        """
        Get global clarification settings.

        Returns:
            Dictionary with clarification settings (enabled, timeout_seconds)
        """
        cache_key = "clarification:settings"

        # Check cache first
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        # Load from database
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM clarification_settings LIMIT 1")

            if not row:
                logger.warning("clarification_settings_not_found")
                settings = {
                    "enabled": True,
                    "timeout_seconds": 300
                }
            else:
                settings = dict(row)

        # Cache and return
        await self._set_to_cache(cache_key, settings)
        logger.info("clarification_settings_loaded", enabled=settings.get("enabled"))
        return settings

    async def get_clarification_types(self) -> List[Dict[str, Any]]:
        """
        Get all clarification types with their configurations.

        Returns:
            List of dictionaries, each containing a clarification type configuration
        """
        cache_key = "clarification:types"

        # Check cache first
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        # Load from database
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM clarification_types
                WHERE enabled = true
                ORDER BY priority DESC
            """)

            types = [dict(row) for row in rows]

        # Cache and return
        await self._set_to_cache(cache_key, types)
        logger.info("clarification_types_loaded", count=len(types))
        return types

    async def get_sports_teams(self) -> List[Dict[str, Any]]:
        """
        Get sports team disambiguation rules.

        Returns:
            List of dictionaries with team names and disambiguation options
        """
        cache_key = "clarification:sports_teams"

        # Check cache first
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        # Load from database
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM sports_team_disambiguation
                WHERE requires_disambiguation = true
                ORDER BY team_name
            """)

            teams = [dict(row) for row in rows]

        # Cache and return
        await self._set_to_cache(cache_key, teams)
        logger.info("sports_teams_loaded", count=len(teams))
        return teams

    async def get_device_rules(self) -> List[Dict[str, Any]]:
        """
        Get device disambiguation rules.

        Returns:
            List of dictionaries with device types and disambiguation rules
        """
        cache_key = "clarification:device_rules"

        # Check cache first
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        # Load from database
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM device_disambiguation_rules
                WHERE requires_disambiguation = true
                ORDER BY device_type
            """)

            rules = [dict(row) for row in rows]

        # Cache and return
        await self._set_to_cache(cache_key, rules)
        logger.info("device_rules_loaded", count=len(rules))
        return rules

    async def log_analytics_event(
        self,
        session_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a conversation analytics event.

        Args:
            session_id: Conversation session ID
            event_type: Type of event (e.g., 'session_created', 'followup_detected')
            metadata: Optional event metadata
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversation_analytics (session_id, event_type, metadata)
                    VALUES ($1, $2, $3)
                """, session_id, event_type, metadata)

            logger.info("analytics_event_logged", session_id=session_id, event_type=event_type)

        except Exception as e:
            # Don't fail the request if analytics logging fails
            logger.warning("analytics_event_log_failed", error=str(e), event_type=event_type)

    async def reload_config(self):
        """
        Reload all configuration from database (bypass cache).

        Useful when configuration changes in Admin Panel.
        """
        logger.info("config_reload_requested")

        # Clear cache
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
                logger.info("redis_cache_cleared")
            except Exception as e:
                logger.warning("redis_cache_clear_failed", error=str(e))

        # Clear memory cache
        _memory_cache.clear()
        logger.info("memory_cache_cleared")

        # Reload all configs
        await self.get_conversation_settings()
        await self.get_clarification_settings()
        await self.get_clarification_types()
        await self.get_sports_teams()
        await self.get_device_rules()

        logger.info("config_reloaded")


# Global instance
_config: Optional[ConversationConfig] = None


async def get_config() -> ConversationConfig:
    """
    Get global configuration instance.

    Returns:
        ConversationConfig instance
    """
    global _config
    if _config is None:
        _config = ConversationConfig()
        await _config.initialize()
    return _config


async def reload_config():
    """Reload configuration from database."""
    config = await get_config()
    await config.reload_config()


# Convenience functions for common operations

async def is_conversation_enabled() -> bool:
    """Check if conversation context is enabled."""
    config = await get_config()
    settings = await config.get_conversation_settings()
    return settings.get("enabled", True)


async def is_clarification_enabled() -> bool:
    """Check if clarification system is enabled."""
    config = await get_config()
    settings = await config.get_clarification_settings()
    return settings.get("enabled", True)


async def get_max_messages() -> int:
    """Get maximum number of messages to keep in conversation history."""
    config = await get_config()
    settings = await config.get_conversation_settings()
    return settings.get("max_messages", 20)


async def get_session_timeout() -> int:
    """Get conversation session timeout in seconds."""
    config = await get_config()
    settings = await config.get_conversation_settings()
    return settings.get("timeout_seconds", 1800)
