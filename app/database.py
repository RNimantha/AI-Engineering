"""
MySQL connection and session management for the Claude Agent SDK demo.

Uses SQLAlchemy 2.x ORM with the PyMySQL driver.

Place this file at: app/database.py

Quickstart:
    from database import get_db, Base
    from sqlalchemy.orm import Session

    @app.get("/example")
    def endpoint(db: Session = Depends(get_db)):
        ...
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

# ── Connection string ──────────────────────────────────────────────────────────
# Set DATABASE_URL in .env; fall back to a sensible local default.
# Format: mysql+pymysql://user:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/claude_agent_sdk",
)

# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    echo=False,          # Set True to log all SQL (useful during development)
    pool_size=10,        # Persistent connections kept open
    max_overflow=20,     # Extra connections when pool is exhausted
    pool_recycle=3600,   # Refresh connections after 1 h (avoids MySQL wait_timeout)
    pool_pre_ping=True,  # Test connection before use; auto-reconnect on stale conn
    connect_args={"charset": "utf8mb4"},  # Full Unicode + emoji support
)

# ── Session factory ────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models (SQLAlchemy 2.x API).

    All models must inherit from this class so that Base.metadata knows
    about every table before create_all() is called.
    """
    pass


# ── FastAPI dependency ─────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session for use in FastAPI endpoint dependencies.
    The session is closed automatically after the response completes,
    including after the SSE stream finishes.

    Usage:
        @app.post("/api/chat")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Context manager (scripts / tests) ─────────────────────────────────────────
@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for code that runs outside a FastAPI request (e.g., init scripts).

    Usage:
        with get_db_context() as db:
            db.add(User(username="seed_user"))
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Initialisation helpers ─────────────────────────────────────────────────────
def init_db() -> None:
    """
    Create all tables defined across the ORM models.

    Safe to call repeatedly — SQLAlchemy uses CREATE TABLE IF NOT EXISTS.
    Call this once on application startup.
    """
    # Lazy import so models register with Base.metadata before create_all.
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")


def check_connection() -> bool:
    """
    Ping the database and return True if reachable, False otherwise.
    Useful for /api/health checks.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connectivity check failed: %s", exc)
        return False
