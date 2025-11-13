"""
Database connection and session management for Athena Admin.

Provides SQLAlchemy engine, session factory, and dependency injection
for FastAPI endpoints.
"""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
import structlog

from app.models import Base

logger = structlog.get_logger()

# Database configuration from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://psadmin:Ibucej1!@postgres-01.xmojo.net:5432/athena_admin"
)

# Database password from environment (for security)
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
if DB_PASSWORD and "@" in DATABASE_URL:
    # Insert password into connection string
    # postgresql://user@host -> postgresql://user:password@host
    parts = DATABASE_URL.split("@")
    user_part = parts[0].split("//")[1]  # Extract user
    DATABASE_URL = f"postgresql://{user_part}:{DB_PASSWORD}@{'@'.join(parts[1:])}"

# Connection pool settings
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=POOL_PRE_PING,  # Test connections before using them
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Log SQL queries if enabled
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Don't expire objects after commit
)


# SQLAlchemy event listeners for logging
@event.listens_for(Engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log database connections."""
    logger.debug("database_connection_established")


@event.listens_for(Engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Log database disconnections."""
    logger.debug("database_connection_closed")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage in FastAPI endpoints:
        @app.get("/api/policies")
        def get_policies(db: Session = Depends(get_db)):
            return db.query(Policy).all()

    Yields:
        Session: SQLAlchemy session

    Note:
        Session is automatically closed after request completes,
        even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions outside FastAPI.

    Usage:
        with get_db_context() as db:
            policy = db.query(Policy).first()

    Yields:
        Session: SQLAlchemy session

    Note:
        Session is automatically closed when context exits.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database schema.

    Creates all tables defined in models if they don't exist.
    Should only be called during initial setup or testing.

    For production, use Alembic migrations instead.
    """
    logger.info("initializing_database_schema")
    Base.metadata.create_all(bind=engine)
    logger.info("database_schema_initialized")


def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.debug("database_health_check_passed")
        return True
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return False


def get_db_stats() -> dict:
    """
    Get database connection pool statistics.

    Returns:
        dict: Pool statistics including size, checked out connections, etc.
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "recycle_time": POOL_RECYCLE,
    }
