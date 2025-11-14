"""
Provider routing based on query intent.

Routes queries to appropriate search provider sets based on classified intent.
"""

from typing import Dict, List, Optional
import logging
import os

from .base import SearchProvider
from .duckduckgo import DuckDuckGoProvider
from .brave import BraveSearchProvider
from .ticketmaster import TicketmasterProvider
from .eventbrite import EventbriteProvider

logger = logging.getLogger(__name__)


class ProviderRouter:
    """
    Routes queries to appropriate provider sets based on intent.

    Intent-based routing ensures:
    - Event queries use event-specific APIs (Ticketmaster, Eventbrite)
    - General queries use general web search (DuckDuckGo, Brave)
    - No wasted API calls to irrelevant providers
    """

    # Intent-to-provider mapping
    # Each intent gets a list of provider names to use
    INTENT_PROVIDER_SETS: Dict[str, List[str]] = {
        "event_search": [
            "ticketmaster",    # Official event data
            "eventbrite",      # Local community events
            "duckduckgo",      # General web search backup
            "brave"            # Additional web search coverage
        ],
        "general": [
            "duckduckgo",      # Free unlimited
            "brave"            # 2,000/month free
        ],
        "news": [
            "brave",           # Excellent news search
            "duckduckgo"       # General news coverage
        ],
        "local_business": [
            "brave",           # Good local search
            "duckduckgo"       # General search
        ]
    }

    # Intents that should be handled by RAG services, not web search
    RAG_INTENTS = {"weather", "sports"}

    def __init__(
        self,
        ticketmaster_api_key: Optional[str] = None,
        eventbrite_api_key: Optional[str] = None,
        brave_api_key: Optional[str] = None,
        enable_ticketmaster: bool = True,
        enable_eventbrite: bool = True,
        enable_brave: bool = True,
        enable_duckduckgo: bool = True
    ):
        """
        Initialize provider router.

        Args:
            ticketmaster_api_key: Ticketmaster API key
            eventbrite_api_key: Eventbrite API key
            brave_api_key: Brave Search API key
            enable_ticketmaster: Enable Ticketmaster provider
            enable_eventbrite: Enable Eventbrite provider
            enable_brave: Enable Brave Search provider
            enable_duckduckgo: Enable DuckDuckGo provider
        """
        self.all_providers: Dict[str, SearchProvider] = {}

        # Initialize DuckDuckGo (no API key needed)
        if enable_duckduckgo:
            try:
                self.all_providers["duckduckgo"] = DuckDuckGoProvider()
                logger.info("Initialized DuckDuckGo provider")
            except Exception as e:
                logger.error(f"Failed to initialize DuckDuckGo provider: {e}")

        # Initialize Brave Search
        if enable_brave and brave_api_key:
            try:
                self.all_providers["brave"] = BraveSearchProvider(api_key=brave_api_key)
                logger.info("Initialized Brave Search provider")
            except Exception as e:
                logger.error(f"Failed to initialize Brave Search provider: {e}")
        elif enable_brave and not brave_api_key:
            logger.warning("Brave Search enabled but no API key provided")

        # Initialize Ticketmaster
        if enable_ticketmaster and ticketmaster_api_key:
            try:
                self.all_providers["ticketmaster"] = TicketmasterProvider(api_key=ticketmaster_api_key)
                logger.info("Initialized Ticketmaster provider")
            except Exception as e:
                logger.error(f"Failed to initialize Ticketmaster provider: {e}")
        elif enable_ticketmaster and not ticketmaster_api_key:
            logger.warning("Ticketmaster enabled but no API key provided")

        # Initialize Eventbrite
        if enable_eventbrite and eventbrite_api_key:
            try:
                self.all_providers["eventbrite"] = EventbriteProvider(api_key=eventbrite_api_key)
                logger.info("Initialized Eventbrite provider")
            except Exception as e:
                logger.error(f"Failed to initialize Eventbrite provider: {e}")
        elif enable_eventbrite and not eventbrite_api_key:
            logger.warning("Eventbrite enabled but no API key provided")

        logger.info(f"Provider router initialized with {len(self.all_providers)} providers: {list(self.all_providers.keys())}")

    def get_providers_for_intent(self, intent: str) -> List[SearchProvider]:
        """
        Get provider instances for given intent.

        Args:
            intent: Query intent type

        Returns:
            List of SearchProvider instances appropriate for this intent
        """
        # Get provider names for this intent
        provider_names = self.INTENT_PROVIDER_SETS.get(intent, ["duckduckgo"])

        # Filter to only available providers
        providers = []
        for name in provider_names:
            if name in self.all_providers:
                providers.append(self.all_providers[name])
            else:
                logger.warning(f"Provider '{name}' requested for intent '{intent}' but not available")

        if not providers:
            # Fallback to DuckDuckGo if no providers available
            logger.warning(f"No providers available for intent '{intent}', falling back to DuckDuckGo")
            if "duckduckgo" in self.all_providers:
                providers = [self.all_providers["duckduckgo"]]
            else:
                logger.error("DuckDuckGo provider not available - no search providers!")

        logger.info(f"Selected {len(providers)} providers for intent '{intent}': {[p.name for p in providers]}")
        return providers

    def should_use_rag(self, intent: str) -> bool:
        """
        Check if intent should be handled by RAG service instead of web search.

        Args:
            intent: Classified intent

        Returns:
            True if RAG should handle, False if web search should handle
        """
        is_rag = intent in self.RAG_INTENTS
        if is_rag:
            logger.info(f"Intent '{intent}' should be handled by RAG service")
        return is_rag

    def get_available_providers(self) -> List[str]:
        """
        Get list of available provider names.

        Returns:
            List of provider names that were successfully initialized
        """
        return list(self.all_providers.keys())

    @classmethod
    def from_environment(cls) -> "ProviderRouter":
        """
        Create ProviderRouter from environment variables.

        Environment variables:
        - TICKETMASTER_API_KEY: Ticketmaster API key
        - EVENTBRITE_API_KEY: Eventbrite API key
        - BRAVE_SEARCH_API_KEY: Brave Search API key
        - ENABLE_TICKETMASTER: Enable Ticketmaster (default: true)
        - ENABLE_EVENTBRITE: Enable Eventbrite (default: true)
        - ENABLE_BRAVE_SEARCH: Enable Brave Search (default: true)
        - ENABLE_DUCKDUCKGO: Enable DuckDuckGo (default: true)

        Returns:
            Configured ProviderRouter instance
        """
        return cls(
            ticketmaster_api_key=os.getenv("TICKETMASTER_API_KEY"),
            eventbrite_api_key=os.getenv("EVENTBRITE_API_KEY"),
            brave_api_key=os.getenv("BRAVE_SEARCH_API_KEY"),
            enable_ticketmaster=os.getenv("ENABLE_TICKETMASTER", "true").lower() == "true",
            enable_eventbrite=os.getenv("ENABLE_EVENTBRITE", "true").lower() == "true",
            enable_brave=os.getenv("ENABLE_BRAVE_SEARCH", "true").lower() == "true",
            enable_duckduckgo=os.getenv("ENABLE_DUCKDUCKGO", "true").lower() == "true"
        )

    async def close_all(self):
        """Close all provider HTTP clients."""
        for provider in self.all_providers.values():
            try:
                await provider.close()
            except Exception as e:
                logger.error(f"Error closing provider {provider.name}: {e}")
