from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Determine if we're using SQLite
is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

logger.info(f"Database URL: {settings.DATABASE_URL}")
logger.info(f"Using SQLite: {is_sqlite}")

# Create engine with appropriate settings
if is_sqlite:
    # SQLite-specific settings for better concurrency
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL/other database settings
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=settings.DEBUG
        )
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL engine: {e}")
        # Fallback to SQLite
        logger.warning("Falling back to SQLite database")
        engine = create_engine(
            "sqlite:///./knowledge_assistant.db",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.DEBUG
        )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    """
    # Import all models to ensure they're registered
    # The models module handles import order
    from app import models
    
    logger.info(f"Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """
    Drop all database tables.
    """
    Base.metadata.drop_all(bind=engine)
