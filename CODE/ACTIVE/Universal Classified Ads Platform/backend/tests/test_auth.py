import pytest


def test_register_201(client):
    resp = client.post("/api/auth/register", json={
        "name": "New User", "email": "new@test.com", "password": "pass123456"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@test.com"


def test_register_duplicate_email(client, user_headers):
    resp = client.post("/api/auth/register", json={
        "name": "Dup", "email": "user@test.com", "password": "pass123456"
    })
    assert resp.status_code == 400


def test_register_invalid_email(client):
    resp = client.post("/api/auth/register", json={
        "name": "Bad", "email": "not-an-email", "password": "pass123456"
    })
    assert resp.status_code == 422


def test_login_returns_token(client, user_headers):
    # user_headers already logs in successfully; just verify structure
    resp = client.post("/api/auth/login", data={
        "username": "user@test.com", "password": "testpass123"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_me_with_token(client, user_headers):
    resp = client.get("/api/users/me", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@test.com"


def test_me_without_token_401(client):
    resp = client.get("/api/users/me")
    assert resp.status_code == 401
