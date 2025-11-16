#!/usr/bin/env python3
"""
Populate routing configuration database directly via SQLAlchemy.

This script migrates hardcoded intent patterns, routing configurations, and
provider mappings from the orchestrator code to the admin database.

Usage:
    python3 populate_routing_db.py [--dry-run]

Environment:
    DATABASE_URL: PostgreSQL connection string (optional)
"""

import os
import sys
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import IntentPattern, IntentRouting, ProviderRouting


# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena_admin"
)


class RoutingConfigPopulator:
    """Populates routing configuration directly in database."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            "patterns_created": 0,
            "routing_created": 0,
            "providers_created": 0,
            "errors": []
        }

        if not dry_run:
            self.engine = create_engine(DATABASE_URL)
            SessionLocal = sessionmaker(bind=self.engine)
            self.session = SessionLocal()

    def create_pattern(self, category: str, pattern_type: str, keyword: str,
                      weight: float = 1.0) -> bool:
        """Create an intent pattern."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would create pattern: {category}/{pattern_type}/{keyword}")
            return True

        try:
            pattern = IntentPattern(
                intent_category=category,
                pattern_type=pattern_type,
                keyword=keyword,
                confidence_weight=weight,
                enabled=True
            )
            self.session.add(pattern)
            self.session.flush()
            self.stats["patterns_created"] += 1
            return True

        except IntegrityError:
            # Already exists - rollback and continue
            self.session.rollback()
            return True
        except Exception as e:
            self.stats["errors"].append(f"Error creating pattern {keyword}: {e}")
            self.session.rollback()
            return False

    def create_routing(self, category: str, use_rag: bool = False,
                      rag_url: str = None, use_web: bool = False,
                      use_llm: bool = True, priority: int = 100) -> bool:
        """Create intent routing configuration."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would create routing: {category} (RAG={use_rag}, Web={use_web})")
            return True

        try:
            routing = IntentRouting(
                intent_category=category,
                use_rag=use_rag,
                rag_service_url=rag_url,
                use_web_search=use_web,
                use_llm=use_llm,
                priority=priority,
                enabled=True
            )
            self.session.add(routing)
            self.session.flush()
            self.stats["routing_created"] += 1
            return True

        except IntegrityError:
            self.session.rollback()
            return True
        except Exception as e:
            self.stats["errors"].append(f"Error creating routing {category}: {e}")
            self.session.rollback()
            return False

    def create_provider(self, category: str, provider: str, priority: int) -> bool:
        """Create provider routing configuration."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would create provider: {category} → {provider} (pri={priority})")
            return True

        try:
            provider_routing = ProviderRouting(
                intent_category=category,
                provider_name=provider,
                priority=priority,
                enabled=True
            )
            self.session.add(provider_routing)
            self.session.flush()
            self.stats["providers_created"] += 1
            return True

        except IntegrityError:
            self.session.rollback()
            return True
        except Exception as e:
            self.stats["errors"].append(f"Error creating provider {category}/{provider}: {e}")
            self.session.rollback()
            return False

    def populate_control_patterns(self):
        """Populate control intent patterns."""
        print("\n📝 Populating control intent patterns...")

        # Basic control keywords
        basic_keywords = [
            "turn on", "turn off", "switch on", "switch off", "activate",
            "deactivate", "enable", "disable"
        ]
        for kw in basic_keywords:
            self.create_pattern("control", "basic_control", kw, 1.2)

        # Dimming keywords
        dimming_keywords = [
            "dim", "brighten", "set brightness", "brightness", "darker",
            "brighter", "50%", "100%"
        ]
        for kw in dimming_keywords:
            self.create_pattern("control", "dimming", kw, 1.1)

        # Temperature keywords
        temp_keywords = [
            "set temperature", "temperature", "degrees", "warmer", "cooler",
            "heat", "cool", "thermostat", "hvac"
        ]
        for kw in temp_keywords:
            self.create_pattern("control", "temperature", kw, 1.1)

        # Scene keywords
        scene_keywords = [
            "scene", "good morning", "good night", "movie time", "dinner time",
            "party mode", "relax"
        ]
        for kw in scene_keywords:
            self.create_pattern("control", "scene", kw, 1.3)

        # Lock keywords
        lock_keywords = ["lock", "unlock", "secure", "arm", "disarm"]
        for kw in lock_keywords:
            self.create_pattern("control", "lock", kw, 1.2)

        # Cover keywords
        cover_keywords = [
            "open", "close", "raise", "lower", "blinds", "shades",
            "curtains", "garage door"
        ]
        for kw in cover_keywords:
            self.create_pattern("control", "cover", kw, 1.1)

        # Fan keywords
        fan_keywords = ["fan", "ceiling fan", "fan speed"]
        for kw in fan_keywords:
            self.create_pattern("control", "fan", kw, 1.1)

        # Media keywords
        media_keywords = [
            "play", "pause", "stop", "volume", "mute", "unmute",
            "next track", "previous track", "music"
        ]
        for kw in media_keywords:
            self.create_pattern("control", "media", kw, 1.1)

    def populate_sports_patterns(self):
        """Populate sports intent patterns."""
        print("\n📝 Populating sports intent patterns...")

        keywords = [
            "ravens", "orioles", "score", "game", "touchdown", "field goal",
            "home run", "inning", "quarter", "half", "final score",
            "win", "lose", "tied", "leading", "trailing", "baseball", "football"
        ]

        for kw in keywords:
            self.create_pattern("sports", "team_or_game", kw, 1.2)

    def populate_weather_patterns(self):
        """Populate weather intent patterns."""
        print("\n📝 Populating weather intent patterns...")

        keywords = [
            "weather", "temperature", "rain", "snow", "forecast", "sunny",
            "cloudy", "humid", "wind", "storm", "precipitation", "conditions",
            "today's weather", "tomorrow's weather", "this week", "degrees",
            "feels like", "humidity"
        ]

        for kw in keywords:
            self.create_pattern("weather", "weather_query", kw, 1.2)

    def populate_airport_patterns(self):
        """Populate airport intent patterns."""
        print("\n📝 Populating airport intent patterns...")

        keywords = [
            "airport", "bwi", "flight", "gate", "terminal", "departure",
            "arrival", "delay", "on time", "baggage", "check-in", "security",
            "airline", "boarding", "cancelled", "diverted", "runway", "tsa"
        ]

        for kw in keywords:
            self.create_pattern("airports", "airport_query", kw, 1.2)

    def populate_transit_patterns(self):
        """Populate transit intent patterns."""
        print("\n📝 Populating transit intent patterns...")

        keywords = [
            "bus", "train", "marc", "metro", "light rail", "subway",
            "schedule", "next train", "next bus", "arrival time", "station",
            "route", "stop", "fare", "ticket", "transit", "mta"
        ]

        for kw in keywords:
            self.create_pattern("transit", "transit_query", kw, 1.1)

    def populate_food_patterns(self):
        """Populate food intent patterns."""
        print("\n📝 Populating food intent patterns...")

        # General food keywords
        general_keywords = [
            "restaurant", "food", "eat", "hungry", "dinner", "lunch",
            "breakfast", "takeout", "delivery", "menu", "reservations"
        ]
        for kw in general_keywords:
            self.create_pattern("food", "dining", kw, 1.1)

        # Baltimore-specific (higher weight)
        baltimore_keywords = [
            "fells point", "canton", "federal hill", "inner harbor",
            "mt vernon", "hampden", "crabs", "old bay", "natty boh",
            "bertha's", "thames street"
        ]
        for kw in baltimore_keywords:
            self.create_pattern("food", "local_dining", kw, 1.3)

    def populate_emergency_patterns(self):
        """Populate emergency intent patterns."""
        print("\n📝 Populating emergency intent patterns...")

        keywords = [
            "emergency", "911", "hospital", "urgent", "critical", "help",
            "ambulance", "police", "fire", "danger", "injured", "medical",
            "nearest hospital", "emergency room", "urgent care", "crisis"
        ]

        for kw in keywords:
            self.create_pattern("emergency", "emergency_query", kw, 1.5)

    def populate_event_patterns(self):
        """Populate event intent patterns."""
        print("\n📝 Populating event intent patterns...")

        keywords = [
            "concert", "show", "festival", "event", "tickets", "performance",
            "theater", "comedy", "music", "live", "venue", "tonight",
            "this weekend", "upcoming", "schedule"
        ]

        for kw in keywords:
            self.create_pattern("events", "event_query", kw, 1.2)

    def populate_location_patterns(self):
        """Populate location intent patterns."""
        print("\n📝 Populating location intent patterns...")

        keywords = [
            "where", "directions", "nearby", "closest", "nearest", "distance",
            "how far", "location", "address", "map", "navigate", "route",
            "driving", "walking", "find"
        ]

        for kw in keywords:
            self.create_pattern("location", "location_query", kw, 1.2)

    def populate_complex_indicators(self):
        """Populate complex query indicators for general_info routing."""
        print("\n📝 Populating complex query indicators...")

        keywords = [
            "why", "how", "explain", "tell me about", "what is", "what are",
            "describe", "compare", "difference between", "history of",
            "definition", "meaning", "etymology", "origin", "background"
        ]

        for kw in keywords:
            self.create_pattern("general_info", "complex_query", kw, 1.3)

    def populate_routing_configs(self):
        """Populate intent routing configurations."""
        print("\n📝 Populating intent routing configurations...")

        # RAG-enabled intents
        self.create_routing("weather", use_rag=True,
                          rag_url="http://localhost:8010",
                          use_web=False, use_llm=True, priority=90)

        self.create_routing("sports", use_rag=True,
                          rag_url="http://localhost:8012",
                          use_web=False, use_llm=True, priority=90)

        self.create_routing("airports", use_rag=True,
                          rag_url="http://localhost:8011",
                          use_web=False, use_llm=True, priority=90)

        # Direct control (no RAG, no web search)
        self.create_routing("control", use_rag=False,
                          use_web=False, use_llm=False, priority=100)

        # Web search enabled intents
        self.create_routing("transit", use_rag=False,
                          use_web=True, use_llm=True, priority=80)

        self.create_routing("food", use_rag=False,
                          use_web=True, use_llm=True, priority=80)

        self.create_routing("events", use_rag=False,
                          use_web=True, use_llm=True, priority=80)

        self.create_routing("location", use_rag=False,
                          use_web=True, use_llm=True, priority=80)

        self.create_routing("emergency", use_rag=False,
                          use_web=True, use_llm=True, priority=100)

        self.create_routing("general_info", use_rag=False,
                          use_web=True, use_llm=True, priority=70)

        self.create_routing("unknown", use_rag=False,
                          use_web=True, use_llm=True, priority=50)

    def populate_provider_mappings(self):
        """Populate web search provider mappings."""
        print("\n📝 Populating provider routing mappings...")

        # Event search providers
        self.create_provider("events", "ticketmaster", 1)
        self.create_provider("events", "eventbrite", 2)
        self.create_provider("events", "duckduckgo", 3)
        self.create_provider("events", "brave", 4)

        # General search providers
        self.create_provider("general_info", "duckduckgo", 1)
        self.create_provider("general_info", "brave", 2)

        # Transit search providers
        self.create_provider("transit", "brave", 1)
        self.create_provider("transit", "duckduckgo", 2)

        # Local business search
        self.create_provider("food", "brave", 1)
        self.create_provider("food", "duckduckgo", 2)

        self.create_provider("location", "brave", 1)
        self.create_provider("location", "duckduckgo", 2)

        self.create_provider("emergency", "duckduckgo", 1)
        self.create_provider("emergency", "brave", 2)

    def populate_all(self):
        """Populate all routing configuration."""
        print(f"\n{'='*60}")
        print(f"Routing Configuration Population (Direct DB)")
        print(f"{'='*60}")
        print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
        print(f"Dry Run: {self.dry_run}")
        print(f"{'='*60}")

        try:
            # Populate patterns
            self.populate_control_patterns()
            self.populate_sports_patterns()
            self.populate_weather_patterns()
            self.populate_airport_patterns()
            self.populate_transit_patterns()
            self.populate_food_patterns()
            self.populate_emergency_patterns()
            self.populate_event_patterns()
            self.populate_location_patterns()
            self.populate_complex_indicators()

            # Populate routing configs
            self.populate_routing_configs()

            # Populate provider mappings
            self.populate_provider_mappings()

            # Commit all changes
            if not self.dry_run:
                self.session.commit()
                print("\n✓ All changes committed to database")

        except Exception as e:
            if not self.dry_run:
                self.session.rollback()
            print(f"\n✗ Error during population: {e}")
            raise

        finally:
            if not self.dry_run:
                self.session.close()

        # Print summary
        print(f"\n{'='*60}")
        print(f"Population Summary")
        print(f"{'='*60}")
        print(f"Patterns created: {self.stats['patterns_created']}")
        print(f"Routing configs created: {self.stats['routing_created']}")
        print(f"Provider mappings created: {self.stats['providers_created']}")
        print(f"Errors: {len(self.stats['errors'])}")

        if self.stats['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in self.stats['errors'][:10]:
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")

        print(f"{'='*60}\n")

        return len(self.stats['errors']) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Populate routing configuration database directly"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - don't actually create anything"
    )

    args = parser.parse_args()

    populator = RoutingConfigPopulator(args.dry_run)
    success = populator.populate_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
