"""Database infrastructure setup."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config.settings import settings

# Create engine from DATABASE_URL (only if URL is provided)
# Engine creation is deferred until needed to avoid errors when using in-memory mode
_engine = None
_SessionLocal = None


def _get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise ValueError("DATABASE_URL is required for database operations")
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.debug_mode,  # Log SQL queries in debug mode
        )
    return _engine


def get_db_session():
    """
    Get a database session.

    Returns:
        SQLAlchemy session instance
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = _get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal()
