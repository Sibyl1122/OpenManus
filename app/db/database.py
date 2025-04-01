"""
Database connection and session management.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create database directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"), exist_ok=True)

# Database URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'openmanus.db')}"

# Create SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for model declaration
Base = declarative_base()

def init_db():
    """Initialize the database by creating all tables."""
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    """
    Get a database session.
    Usage:
        with get_db() as db:
            db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
