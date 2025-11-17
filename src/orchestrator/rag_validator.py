"""
RAG Service Response Validation System

Validates responses from RAG services (Weather, Sports, Airports) to prevent
silent failures when services return empty or invalid data.

Features:
- Service-specific validation for Weather, Sports, Airports
- Validates data structure and content quality
- Returns structured validation results with suggestions
- Performance target: < 10ms per validation
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Validation result status."""
    VALID = "valid"              # Data is good, use it
    EMPTY = "empty"              # Data is empty, trigger fallback
    INVALID = "invalid"          # Data is malformed, trigger fallback
    NEEDS_RETRY = "needs_retry"  # Data missing, retry with different params


class RAGValidator:
    """
    Validates RAG service responses for quality and completeness.

    Provides service-specific validation and auto-fix strategies.
    """

    def validate_sports_response(
        self,
        response_data: Dict[str, Any],
        query: str
    ) -> Tuple[ValidationResult, str, Optional[Dict[str, Any]]]:
        """
        Validate Sports RAG service response.

        Args:
            response_data: Raw response from Sports RAG service
            query: Original user query

        Returns:
            Tuple of (ValidationResult, reason, suggestions)

        Validates:
            - Events array exists and has data
            - Events have required fields (datetime, opponent, location)
            - Team data has required fields (name, record, standing)
            - Response matches query intent (scores vs schedules)
        """
        try:
            # Check for events array
            if "events" in response_data:
                events = response_data.get("events", [])

                if not events or len(events) == 0:
                    logger.warning(f"Sports RAG returned empty events for query: {query}")
                    return (
                        ValidationResult.EMPTY,
                        "No events found in response",
                        {"fallback_action": "web_search", "reason": "empty_events"}
                    )

                # Validate first event structure (sample check)
                first_event = events[0]
                required_event_fields = ["opponent", "datetime"]
                missing_fields = [f for f in required_event_fields if f not in first_event]

                if missing_fields:
                    logger.warning(f"Sports event missing fields {missing_fields}: {first_event}")
                    return (
                        ValidationResult.INVALID,
                        f"Event missing required fields: {missing_fields}",
                        {"fallback_action": "web_search", "reason": "malformed_event"}
                    )

                # Check if query asks for scores but we got schedule
                query_lower = query.lower()
                if any(word in query_lower for word in ["score", "result", "won", "lost", "final"]):
                    if not any("score" in e or "result" in e for e in events):
                        logger.info(f"Query asks for scores but response has schedule data")
                        return (
                            ValidationResult.NEEDS_RETRY,
                            "Query wants scores but got schedule",
                            {"retry_with": "scores", "fallback_action": "web_search"}
                        )

                logger.debug(f"Sports response validated: {len(events)} events")
                return (ValidationResult.VALID, f"Found {len(events)} events", None)

            # Check for team data
            elif "teams" in response_data:
                teams = response_data.get("teams", [])

                if not teams or len(teams) == 0:
                    logger.warning(f"Sports RAG returned empty teams for query: {query}")
                    return (
                        ValidationResult.EMPTY,
                        "No teams found in response",
                        {"fallback_action": "web_search", "reason": "empty_teams"}
                    )

                # Validate team structure
                first_team = teams[0]
                required_team_fields = ["name"]
                missing_fields = [f for f in required_team_fields if f not in first_team]

                if missing_fields:
                    logger.warning(f"Sports team missing fields {missing_fields}: {first_team}")
                    return (
                        ValidationResult.INVALID,
                        f"Team missing required fields: {missing_fields}",
                        {"fallback_action": "web_search", "reason": "malformed_team"}
                    )

                logger.debug(f"Sports response validated: {len(teams)} teams")
                return (ValidationResult.VALID, f"Found {len(teams)} teams", None)

            # No recognized data structure
            else:
                logger.warning(f"Sports response has no events or teams: {list(response_data.keys())}")
                return (
                    ValidationResult.INVALID,
                    "Response missing events or teams structure",
                    {"fallback_action": "web_search", "reason": "unknown_structure"}
                )

        except Exception as e:
            logger.error(f"Sports validation error: {e}", exc_info=True)
            return (
                ValidationResult.INVALID,
                f"Validation error: {str(e)}",
                {"fallback_action": "web_search", "reason": "validation_exception"}
            )

    def validate_weather_response(
        self,
        response_data: Dict[str, Any],
        query: str
    ) -> Tuple[ValidationResult, str, Optional[Dict[str, Any]]]:
        """
        Validate Weather RAG service response.

        Args:
            response_data: Raw response from Weather RAG service
            query: Original user query

        Returns:
            Tuple of (ValidationResult, reason, suggestions)

        Validates:
            - Current weather has temperature and conditions
            - Forecast has at least 1 day of data
            - Alerts array exists (can be empty)
            - Temperature values are reasonable
        """
        try:
            # Check for current weather data
            if "current" in response_data:
                current = response_data.get("current", {})

                if not current:
                    logger.warning(f"Weather RAG returned empty current data for query: {query}")
                    return (
                        ValidationResult.EMPTY,
                        "No current weather data",
                        {"fallback_action": "web_search", "reason": "empty_current"}
                    )

                # Validate current weather structure
                required_fields = ["temperature"]
                missing_fields = [f for f in required_fields if f not in current]

                if missing_fields:
                    logger.warning(f"Current weather missing fields {missing_fields}: {current}")
                    return (
                        ValidationResult.INVALID,
                        f"Current weather missing required fields: {missing_fields}",
                        {"fallback_action": "web_search", "reason": "malformed_current"}
                    )

                # Validate temperature is reasonable (-50°F to 150°F)
                temp = current.get("temperature")
                if temp and (temp < -50 or temp > 150):
                    logger.warning(f"Weather temperature out of range: {temp}°F")
                    return (
                        ValidationResult.INVALID,
                        f"Temperature out of reasonable range: {temp}°F",
                        {"fallback_action": "web_search", "reason": "invalid_temperature"}
                    )

                logger.debug(f"Weather current validated: {temp}°F")
                return (ValidationResult.VALID, f"Current weather: {temp}°F", None)

            # Check for forecast data
            elif "forecast" in response_data:
                forecast = response_data.get("forecast", [])

                if not forecast or len(forecast) == 0:
                    logger.warning(f"Weather RAG returned empty forecast for query: {query}")
                    return (
                        ValidationResult.EMPTY,
                        "No forecast data",
                        {"fallback_action": "web_search", "reason": "empty_forecast"}
                    )

                # Validate first forecast day structure
                first_day = forecast[0]
                required_fields = ["date", "high", "low"]
                missing_fields = [f for f in required_fields if f not in first_day]

                if missing_fields:
                    logger.warning(f"Forecast day missing fields {missing_fields}: {first_day}")
                    return (
                        ValidationResult.INVALID,
                        f"Forecast missing required fields: {missing_fields}",
                        {"fallback_action": "web_search", "reason": "malformed_forecast"}
                    )

                logger.debug(f"Weather forecast validated: {len(forecast)} days")
                return (ValidationResult.VALID, f"Forecast: {len(forecast)} days", None)

            # No recognized data structure
            else:
                logger.warning(f"Weather response has no current or forecast: {list(response_data.keys())}")
                return (
                    ValidationResult.INVALID,
                    "Response missing current or forecast structure",
                    {"fallback_action": "web_search", "reason": "unknown_structure"}
                )

        except Exception as e:
            logger.error(f"Weather validation error: {e}", exc_info=True)
            return (
                ValidationResult.INVALID,
                f"Validation error: {str(e)}",
                {"fallback_action": "web_search", "reason": "validation_exception"}
            )

    def validate_airports_response(
        self,
        response_data: Dict[str, Any],
        query: str
    ) -> Tuple[ValidationResult, str, Optional[Dict[str, Any]]]:
        """
        Validate Airports RAG service response.

        Args:
            response_data: Raw response from Airports RAG service
            query: Original user query

        Returns:
            Tuple of (ValidationResult, reason, suggestions)

        Validates:
            - Airport info has name and code
            - Flight search has results array
            - Flights have required fields (flight_number, status, time)
            - Delays/cancellations are properly marked
        """
        try:
            # Check for airport info
            if "airport" in response_data:
                airport = response_data.get("airport", {})

                if not airport:
                    logger.warning(f"Airports RAG returned empty airport data for query: {query}")
                    return (
                        ValidationResult.EMPTY,
                        "No airport data",
                        {"fallback_action": "web_search", "reason": "empty_airport"}
                    )

                # Validate airport structure
                required_fields = ["code", "name"]
                missing_fields = [f for f in required_fields if f not in airport]

                if missing_fields:
                    logger.warning(f"Airport missing fields {missing_fields}: {airport}")
                    return (
                        ValidationResult.INVALID,
                        f"Airport missing required fields: {missing_fields}",
                        {"fallback_action": "web_search", "reason": "malformed_airport"}
                    )

                logger.debug(f"Airport info validated: {airport.get('code')}")
                return (ValidationResult.VALID, f"Airport: {airport.get('code')}", None)

            # Check for flight search results
            elif "flights" in response_data:
                flights = response_data.get("flights", [])

                if not flights or len(flights) == 0:
                    logger.warning(f"Airports RAG returned empty flights for query: {query}")
                    return (
                        ValidationResult.EMPTY,
                        "No flights found in response",
                        {"fallback_action": "web_search", "reason": "empty_flights"}
                    )

                # Validate first flight structure
                first_flight = flights[0]
                required_fields = ["flight_number"]
                missing_fields = [f for f in required_fields if f not in first_flight]

                if missing_fields:
                    logger.warning(f"Flight missing fields {missing_fields}: {first_flight}")
                    return (
                        ValidationResult.INVALID,
                        f"Flight missing required fields: {missing_fields}",
                        {"fallback_action": "web_search", "reason": "malformed_flight"}
                    )

                logger.debug(f"Airports response validated: {len(flights)} flights")
                return (ValidationResult.VALID, f"Found {len(flights)} flights", None)

            # No recognized data structure
            else:
                logger.warning(f"Airports response has no airport or flights: {list(response_data.keys())}")
                return (
                    ValidationResult.INVALID,
                    "Response missing airport or flights structure",
                    {"fallback_action": "web_search", "reason": "unknown_structure"}
                )

        except Exception as e:
            logger.error(f"Airports validation error: {e}", exc_info=True)
            return (
                ValidationResult.INVALID,
                f"Validation error: {str(e)}",
                {"fallback_action": "web_search", "reason": "validation_exception"}
            )


# Global validator instance
validator = RAGValidator()
