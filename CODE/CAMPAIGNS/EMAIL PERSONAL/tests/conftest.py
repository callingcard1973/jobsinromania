"""
Pytest configuration and shared fixtures for ANOFM tests.

Provides:
- Database connection management
- Test data fixtures
- Cleanup hooks
- Performance markers
"""

import pytest
import psycopg2
import os
import logging
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.getenv("POSTGRES_PORT", 5433)),
    "database": os.getenv("POSTGRES_DB", "interjob_master"),
    "user": os.getenv("POSTGRES_USER", "tudor"),
    "password": os.getenv("POSTGRES_PASSWORD", "tudor"),
    "connect_timeout": 5,
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# SESSION HOOKS
# ============================================================================

def pytest_configure(config):
    """Initialize test session."""
    logger.info(f"ANOFM PostgreSQL Migration Tests")
    logger.info(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")

    # Verify database connection
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        logger.info(f"Connected: {version[:50]}")
        cur.close()
        conn.close()
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        pytest.exit(f"Cannot connect to database: {e}")


def pytest_sessionstart(session):
    """Create audit log table if missing."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Create audit table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS anofm_audit_log (
                id SERIAL PRIMARY KEY,
                action TEXT,
                table_name TEXT,
                record_id INT,
                email_masked VARCHAR(255),
                timestamp TIMESTAMP DEFAULT now(),
                user_name TEXT
            )
        """)

        # Create backup table structure
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies_clean_anofm_backup (
                id INTEGER,
                name TEXT,
                cui TEXT,
                country CHAR(2),
                city TEXT,
                address TEXT,
                phone TEXT,
                email TEXT,
                website TEXT,
                sector TEXT,
                sector_name TEXT,
                employees_count INTEGER,
                revenue NUMERIC,
                source TEXT,
                source_file TEXT,
                lead_score INTEGER,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                ted_wins INTEGER,
                is_insolvent BOOLEAN,
                is_agency BOOLEAN,
                enriched_email VARCHAR(255),
                enriched_phone VARCHAR(50),
                standard_sector TEXT,
                last_ted_year INTEGER,
                size_segment TEXT
            )
        """)

        conn.commit()
        logger.info("Audit log table ready")

        cur.close()
        conn.close()
    except psycopg2.Error as e:
        logger.warning(f"Could not create audit table: {e}")


def pytest_sessionfinish(session, exitstatus):
    """Cleanup test session."""
    if exitstatus == 0:
        logger.info("All tests passed!")
    else:
        logger.error(f"Tests failed with status {exitstatus}")


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def db_config():
    """Provide database configuration."""
    return DB_CONFIG


@pytest.fixture(scope="session")
def pg_conn_session(db_config):
    """Session-scoped database connection."""
    conn = psycopg2.connect(**db_config)
    yield conn
    conn.close()


@pytest.fixture
def pg_conn(db_config):
    """Function-scoped database connection (fresh for each test)."""
    conn = psycopg2.connect(**db_config)
    yield conn
    conn.close()


@pytest.fixture
def pg_cursor(pg_conn):
    """Provide a cursor with auto-close."""
    cur = pg_conn.cursor()
    yield cur
    cur.close()


@pytest.fixture
def db_cleanup(pg_conn):
    """Auto-cleanup test records from companies_clean."""
    yield

    # Cleanup after test
    cur = pg_conn.cursor()
    try:
        cur.execute("""
            DELETE FROM companies_clean
            WHERE source IN ('ANOFM_TEST', 'ANOFM_BACKUP_TEST')
            OR email LIKE 'test-%@test.ro'
            OR email LIKE 'bulk_%@test.ro'
            OR email LIKE 'concurrent_%@test.ro'
            OR email LIKE 'recovery_%@test.ro'
            OR email LIKE 'gdpr_%@test.ro'
            OR email LIKE 'update_test_%@test.ro'
        """)
        pg_conn.commit()
    except psycopg2.Error as e:
        logger.warning(f"Cleanup failed: {e}")
        pg_conn.rollback()
    finally:
        cur.close()


@pytest.fixture
def audit_cleanup(pg_conn):
    """Auto-cleanup audit log test records."""
    yield

    # Cleanup after test
    cur = pg_conn.cursor()
    try:
        cur.execute("""
            DELETE FROM anofm_audit_log
            WHERE timestamp > now() - interval '1 hour'
        """)
        pg_conn.commit()
    except psycopg2.Error as e:
        logger.warning(f"Audit cleanup failed: {e}")
        pg_conn.rollback()
    finally:
        cur.close()


# ============================================================================
# MARKERS & PARAMETRIZATION
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Add markers based on test characteristics."""
    for item in items:
        # Slow tests
        if "concurrent" in item.nodeid or "load" in item.nodeid:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.load)

        # Integration tests (all tests here are integration)
        item.add_marker(pytest.mark.integration)

        # Category markers
        if "Connection" in item.nodeid:
            item.add_marker(pytest.mark.connection)
        elif "Integrity" in item.nodeid:
            item.add_marker(pytest.mark.integrity)
        elif "Idempotency" in item.nodeid:
            item.add_marker(pytest.mark.idempotency)
        elif "Send" in item.nodeid:
            item.add_marker(pytest.mark.send)
        elif "Audit" in item.nodeid:
            item.add_marker(pytest.mark.audit)
        elif "Recovery" in item.nodeid:
            item.add_marker(pytest.mark.recovery)
        elif "GDPR" in item.nodeid:
            item.add_marker(pytest.mark.gdpr)


# ============================================================================
# REPORTING
# ============================================================================

@pytest.fixture(autouse=True)
def test_logger(request):
    """Auto-log test names."""
    logger.info(f"Starting: {request.node.name}")
    yield
    logger.info(f"Completed: {request.node.name}")


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

@pytest.fixture
def performance_tracker(request):
    """Track test execution time."""
    import time
    start_time = time.time()

    yield

    elapsed = time.time() - start_time
    if elapsed > 5.0:
        logger.warning(f"{request.node.name} took {elapsed:.2f}s (slow)")
    else:
        logger.debug(f"{request.node.name} took {elapsed:.2f}s")
