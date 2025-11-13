"""Structured logging configuration for Project Athena"""

import os
import sys
import logging
import structlog
from typing import Optional


def configure_logging(service_name: str, level: Optional[str] = None):
    """Configure structured logging for a service
    
    Args:
        service_name: Name of the service (e.g., "gateway", "orchestrator")
        level: Log level (default: INFO, from LOG_LEVEL env var)
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json")  # json or console
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    
    # Add service name to all logs
    structlog.contextvars.bind_contextvars(service=service_name)
    
    return structlog.get_logger()


def get_logger(name: Optional[str] = None):
    """Get a logger instance
    
    Args:
        name: Optional logger name (defaults to calling module)
    """
    return structlog.get_logger(name)
