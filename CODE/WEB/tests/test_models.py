import pytest
from dashboard import models as models_module
from dashboard.models import init_db
import os


@pytest.fixture(autouse=True)
def test_db():
    """Create in-memory test database for each test"""
    os.environ['DATABASE_PATH'] = ':memory:'
    # Reload module to use in-memory database
    import importlib
    importlib.reload(models_module)
    from dashboard.models import db, Site, HealthCheck
    init_db()
    yield
    # Clean up
    db.close()


def test_create_site():
    """Test creating a site record"""
    from dashboard.models import Site
    site = Site.create(
        name='oipa.ro',
        domain='https://oipa.ro',
        host='gazduire',
        type='wordpress',
        access_method='rest'
    )
    assert site.id is not None
    assert site.domain == 'https://oipa.ro'


def test_create_health_check():
    """Test creating a health check record"""
    from dashboard.models import Site, HealthCheck
    site = Site.create(
        name='test.ro',
        domain='https://test.ro',
        host='gazduire',
        type='wordpress',
        access_method='rest'
    )
    check = HealthCheck.create(
        site=site,
        http_status=200,
        response_time_ms=145,
        ssl_valid=True,
        ssl_expires_at='2025-12-31'
    )
    assert check.id is not None
    assert check.http_status == 200


def test_get_latest_check():
    """Test retrieving latest health check for a site"""
    from dashboard.models import Site, HealthCheck
    site = Site.create(
        name='example.ro',
        domain='https://example.ro',
        host='gazduire',
        type='wordpress',
        access_method='rest'
    )
    HealthCheck.create(site=site, http_status=200, response_time_ms=100, ssl_valid=True)

    latest = HealthCheck.select().where(HealthCheck.site == site).order_by(HealthCheck.timestamp.desc()).first()
    assert latest.http_status == 200
