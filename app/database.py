"""
database.py - Database Setup

Configures SQLAlchemy engine, session factory, and base model.
Uses SQLite for local dev; easily swappable for PostgreSQL in production.
"""

import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings

# Create SQLAlchemy engine
# check_same_thread=False is required for SQLite with FastAPI
sqlite_connect_args = {}
if "sqlite" in settings.database_url:
    sqlite_connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }

engine = create_engine(
    settings.database_url,
    connect_args=sqlite_connect_args,
    echo=settings.debug,  # Log SQL queries in debug mode
)

if "sqlite" in settings.database_url:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        except sqlite3.OperationalError:
            # Database may already be locked by another connection.
            pass
        finally:
            cursor.close()

# Session factory - each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    Ensures the session is properly closed after each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined in models."""
    # Import all models to register them with Base
    from app.models import user, article, password_reset  # noqa: F401
    Base.metadata.create_all(bind=engine)
