"""
Database connection management for the Job Fair Integration System.

Handles connections to:
1. Local SQLite database for operational data
2. Master PostgreSQL database on raspibig for employer extraction

Provides database initialization, connection management, and session handling.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional, Any, Dict, List
from contextlib import contextmanager
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from config import get_config

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager for both SQLite and PostgreSQL."""

    def __init__(self):
        self.config = get_config()
        self._sqlite_engine: Optional[Engine] = None
        self._postgres_engine: Optional[Engine] = None
        self._sqlite_session_factory: Optional[sessionmaker] = None
        self._postgres_session_factory: Optional[sessionmaker] = None
        self._initialized = False

    @property
    def sqlite_engine(self) -> Engine:
        """Get SQLite engine, creating if necessary."""
        if self._sqlite_engine is None:
            self._create_sqlite_engine()
        return self._sqlite_engine

    @property
    def postgres_engine(self) -> Engine:
        """Get PostgreSQL engine, creating if necessary."""
        if self._postgres_engine is None:
            self._create_postgres_engine()
        return self._postgres_engine

    def _create_sqlite_engine(self) -> None:
        """Create SQLite engine with proper configuration."""
        # Ensure data directory exists
        db_path = Path(self.config.database.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # SQLite-specific configuration for better performance and safety
        self._sqlite_engine = create_engine(
            self.config.database.sqlite_url,
            echo=self.config.debug,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20,
                # Enable foreign key constraints
                "isolation_level": None
            },
            # Connection pool settings
            pool_pre_ping=True,
            pool_recycle=3600
        )

        # Enable foreign key constraints and other pragmas
        @sa.event.listens_for(self._sqlite_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA temp_store=memory")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            cursor.close()

        self._sqlite_session_factory = sessionmaker(
            bind=self._sqlite_engine,
            expire_on_commit=False
        )

    def _create_postgres_engine(self) -> None:
        """Create PostgreSQL engine for master database access."""
        self._postgres_engine = create_engine(
            self.config.database.postgres_url,
            echo=self.config.debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600
        )

        self._postgres_session_factory = sessionmaker(
            bind=self._postgres_engine,
            expire_on_commit=False
        )

    @contextmanager
    def get_session(self, use_postgres: bool = False):
        """
        Get database session context manager.

        Args:
            use_postgres: If True, use PostgreSQL session for master database access
        """
        if use_postgres:
            session_factory = self._postgres_session_factory
            if session_factory is None:
                self._create_postgres_engine()
                session_factory = self._postgres_session_factory
        else:
            session_factory = self._sqlite_session_factory
            if session_factory is None:
                self._create_sqlite_engine()
                session_factory = self._sqlite_session_factory

        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def initialize_database(self) -> bool:
        """
        Initialize the SQLite database with all tables.

        Returns:
            True if initialization was successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Import models to ensure they're registered
            from .models import Base

            # Create all tables
            Base.metadata.create_all(bind=self.sqlite_engine)

            # Create indexes for performance
            self._create_indexes()

            # Verify table creation
            inspector = inspect(self.sqlite_engine)
            tables = inspector.get_table_names()
            expected_tables = {
                'employers', 'anofm_events', 'workers', 'worker_employer_matches',
                'legal_compliance', 'communications', 'financial_tracking'
            }

            if not expected_tables.issubset(set(tables)):
                missing = expected_tables - set(tables)
                logger.error(f"Missing tables after initialization: {missing}")
                return False

            logger.info(f"Database initialized successfully with tables: {tables}")
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def _create_indexes(self) -> None:
        """Create additional indexes for better performance."""
        index_queries = [
            # Employers indexes
            "CREATE INDEX IF NOT EXISTS idx_employers_country ON employers(country)",
            "CREATE INDEX IF NOT EXISTS idx_employers_sector ON employers(sector)",
            "CREATE INDEX IF NOT EXISTS idx_employers_status ON employers(status)",
            "CREATE INDEX IF NOT EXISTS idx_employers_email ON employers(contact_email)",

            # Events indexes
            "CREATE INDEX IF NOT EXISTS idx_anofm_events_date ON anofm_events(date)",
            "CREATE INDEX IF NOT EXISTS idx_anofm_events_region ON anofm_events(region)",
            "CREATE INDEX IF NOT EXISTS idx_anofm_events_status ON anofm_events(status)",

            # Workers indexes
            "CREATE INDEX IF NOT EXISTS idx_workers_region ON workers(region)",
            "CREATE INDEX IF NOT EXISTS idx_workers_sector ON workers(sector_experience)",
            "CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)",
            "CREATE INDEX IF NOT EXISTS idx_workers_consent ON workers(gdpr_consent)",

            # Matches indexes
            "CREATE INDEX IF NOT EXISTS idx_matches_worker ON worker_employer_matches(worker_id)",
            "CREATE INDEX IF NOT EXISTS idx_matches_employer ON worker_employer_matches(employer_id)",
            "CREATE INDEX IF NOT EXISTS idx_matches_event ON worker_employer_matches(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_matches_stage ON worker_employer_matches(match_stage)",

            # Communications indexes
            "CREATE INDEX IF NOT EXISTS idx_comm_recipient ON communications(recipient_type, recipient_id)",
            "CREATE INDEX IF NOT EXISTS idx_comm_sent_date ON communications(sent_date)",
            "CREATE INDEX IF NOT EXISTS idx_comm_status ON communications(status)",

            # Legal compliance indexes
            "CREATE INDEX IF NOT EXISTS idx_legal_event ON legal_compliance(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_legal_type ON legal_compliance(compliance_type)",
            "CREATE INDEX IF NOT EXISTS idx_legal_status ON legal_compliance(status)",

            # Financial tracking indexes
            "CREATE INDEX IF NOT EXISTS idx_financial_event ON financial_tracking(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_financial_type ON financial_tracking(transaction_type)",
            "CREATE INDEX IF NOT EXISTS idx_financial_status ON financial_tracking(payment_status)"
        ]

        with self.sqlite_engine.connect() as conn:
            for query in index_queries:
                try:
                    conn.execute(sa.text(query))
                except Exception as e:
                    logger.warning(f"Failed to create index: {query}, Error: {e}")

    def test_connections(self) -> Dict[str, bool]:
        """
        Test both database connections.

        Returns:
            Dictionary with connection test results
        """
        results = {}

        # Test SQLite connection
        try:
            with self.get_session() as session:
                session.execute(sa.text("SELECT 1"))
            results['sqlite'] = True
        except Exception as e:
            logger.error(f"SQLite connection test failed: {e}")
            results['sqlite'] = False

        # Test PostgreSQL connection
        try:
            with self.get_session(use_postgres=True) as session:
                session.execute(sa.text("SELECT 1"))
            results['postgres'] = True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            results['postgres'] = False

        return results

    def get_database_info(self) -> Dict[str, Any]:
        """Get information about database status and configuration."""
        info = {
            'sqlite_path': self.config.database.sqlite_path,
            'postgres_host': self.config.database.postgres_host,
            'postgres_database': self.config.database.postgres_database,
            'initialized': self._initialized,
            'connections': self.test_connections()
        }

        # Get table counts from SQLite
        try:
            with self.get_session() as session:
                inspector = inspect(self.sqlite_engine)
                tables = inspector.get_table_names()
                info['tables'] = tables

                table_counts = {}
                for table in tables:
                    try:
                        result = session.execute(sa.text(f"SELECT COUNT(*) FROM {table}"))
                        table_counts[table] = result.scalar()
                    except Exception:
                        table_counts[table] = "Error"

                info['table_counts'] = table_counts
        except Exception as e:
            info['tables'] = []
            info['table_counts'] = {}
            logger.error(f"Failed to get database info: {e}")

        return info

    def close_connections(self) -> None:
        """Close all database connections."""
        if self._sqlite_engine:
            self._sqlite_engine.dispose()
            self._sqlite_engine = None

        if self._postgres_engine:
            self._postgres_engine.dispose()
            self._postgres_engine = None

        self._sqlite_session_factory = None
        self._postgres_session_factory = None
        self._initialized = False


# Global database instance
_database: Optional[Database] = None


def get_database() -> Database:
    """Get the global database instance."""
    global _database
    if _database is None:
        _database = Database()
    return _database


def init_database() -> bool:
    """Initialize the database and return success status."""
    db = get_database()
    return db.initialize_database()