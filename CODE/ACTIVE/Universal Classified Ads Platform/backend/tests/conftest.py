import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import Depends

# Must set env BEFORE importing app (Settings reads env at import time)
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long!!")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("POSTHOG_API_KEY", "")
os.environ.setdefault("POSTHOG_ENABLED", "false")

from app.core.database import Base, get_db
from app.core.ratelimit import login_rate_limit, register_rate_limit
from app.main import app
from app.models.user import User, UserRole
from app.models.category import Category, seed_default_categories
from app.core.security import get_password_hash

TEST_DB_URL = "sqlite://"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _setup_db():
    # Reset rate limiter state between tests
    login_rate_limit._hits.clear()
    register_rate_limit._hits.clear()

    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        seed_default_categories(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app=app)


@pytest.fixture
def db_session():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def _create_user(db, email="user@test.com", name="Test User", role="user", password="testpass123"):
    user = User(
        name=name,
        email=email,
        password_hash=get_password_hash(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_headers(client):
    db = TestSession()
    _create_user(db, email="user@test.com", name="Test User", role="user")
    db.close()
    resp = client.post("/api/auth/login", data={"username": "user@test.com", "password": "testpass123"})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def moderator_headers(client):
    db = TestSession()
    _create_user(db, email="mod@test.com", name="Moderator", role="moderator")
    db.close()
    resp = client.post("/api/auth/login", data={"username": "mod@test.com", "password": "testpass123"})
    assert resp.status_code == 200, f"Mod login failed: {resp.json()}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    db = TestSession()
    _create_user(db, email="admin@test.com", name="Admin", role="admin")
    db.close()
    resp = client.post("/api/auth/login", data={"username": "admin@test.com", "password": "testpass123"})
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
