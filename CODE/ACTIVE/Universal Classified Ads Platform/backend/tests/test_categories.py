import pytest


def test_list_categories_seeded(client):
    resp = client.get("/api/categories/")
    assert resp.status_code == 200
    cats = resp.json()
    assert len(cats) >= 7
    slugs = [c["slug"] for c in cats]
    assert "real-estate" in slugs
    assert "jobs" in slugs


def test_admin_create_category(client, admin_headers):
    resp = client.post("/api/categories/", headers=admin_headers, json={
        "name": "TestCat", "slug": "test-cat"
    })
    assert resp.status_code == 201
    assert resp.json()["slug"] == "test-cat"


def test_non_admin_create_category_403(client, user_headers):
    resp = client.post("/api/categories/", headers=user_headers, json={
        "name": "Nope", "slug": "nope"
    })
    assert resp.status_code == 403
