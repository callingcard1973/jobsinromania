import pytest
from datetime import datetime, timezone, timedelta


def _create_ad(client, headers, **overrides):
    data = {
        "title": "Test Ad",
        "description": "A test description that is long enough",
        "category": "jobs",
        "location": "Bucharest",
    }
    data.update(overrides)
    return client.post("/api/ads/", headers=headers, json=data)


class TestAdWorkflow:
    def test_create_draft(self, client, user_headers):
        resp = _create_ad(client, user_headers)
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"

    def test_pay_to_publish_flow(self, client, user_headers, moderator_headers):
        # 1. create ad
        ad = _create_ad(client, user_headers).json()
        assert ad["status"] == "draft"

        # 2. checkout (sandbox)
        resp = client.post(f"/api/payments/ads/{ad['id']}/checkout", headers=user_headers)
        assert resp.status_code == 200
        pay = resp.json()
        assert pay["sandbox"] is True
        payment_id = pay["payment_id"]

        # 3. sandbox confirm
        resp = client.post(f"/api/payments/sandbox/{payment_id}/confirm", headers=user_headers)
        assert resp.status_code == 200

        # 4. verify ad is now pending_review
        ad_resp = client.get(f"/api/ads/{ad['id']}", headers=user_headers)
        assert ad_resp.json()["status"] == "pending_review"

        # 5. moderator approve
        resp = client.post(f"/api/ads/{ad['id']}/approve", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        # 6. moderator publish
        resp = client.post(f"/api/ads/{ad['id']}/publish", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

        # 7. anonymous can see it
        resp = client.get(f"/api/ads/{ad['id']}")
        assert resp.status_code == 200


class TestWorkflowGuards:
    def test_approve_non_pending_400(self, client, user_headers, moderator_headers):
        ad = _create_ad(client, user_headers).json()  # draft
        resp = client.post(f"/api/ads/{ad['id']}/approve", headers=moderator_headers)
        assert resp.status_code == 400

    def test_publish_non_approved_400(self, client, user_headers, moderator_headers):
        ad = _create_ad(client, user_headers).json()
        # pay to get to pending_review
        pay = client.post(f"/api/payments/ads/{ad['id']}/checkout", headers=user_headers).json()
        client.post(f"/api/payments/sandbox/{pay['payment_id']}/confirm", headers=user_headers)
        # skip approve, go straight to publish
        resp = client.post(f"/api/ads/{ad['id']}/publish", headers=moderator_headers)
        assert resp.status_code == 400


class TestPermissions:
    def test_normal_user_approve_403(self, client, user_headers):
        ad = _create_ad(client, user_headers).json()
        resp = client.post(f"/api/ads/{ad['id']}/approve", headers=user_headers)
        assert resp.status_code == 403

    def test_non_owner_update_403(self, client, user_headers, db_session):
        from tests.conftest import _create_user
        _create_user(db_session, email="other@test.com", name="Other")
        db_session.close()
        other = client.post("/api/auth/login", data={"username": "other@test.com", "password": "testpass123"})
        other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

        ad = _create_ad(client, user_headers).json()
        resp = client.put(f"/api/ads/{ad['id']}", headers=other_headers, json={"title": "Hacked"})
        assert resp.status_code == 403

    def test_anonymous_draft_403(self, client, user_headers):
        ad = _create_ad(client, user_headers).json()
        resp = client.get(f"/api/ads/{ad['id']}")
        assert resp.status_code == 403


class TestListingPrivilege:
    def test_anonymous_draft_filter_403(self, client, user_headers):
        resp = client.get("/api/ads/?status=draft")
        assert resp.status_code == 403

    def test_anonymous_list_only_published(self, client, user_headers, moderator_headers):
        # create and publish one ad
        ad = _create_ad(client, user_headers).json()
        pay = client.post(f"/api/payments/ads/{ad['id']}/checkout", headers=user_headers).json()
        client.post(f"/api/payments/sandbox/{pay['payment_id']}/confirm", headers=user_headers)
        client.post(f"/api/ads/{ad['id']}/approve", headers=moderator_headers)
        client.post(f"/api/ads/{ad['id']}/publish", headers=moderator_headers)

        # create a draft (not published)
        _create_ad(client, user_headers, title="Draft Only")

        resp = client.get("/api/ads/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1  # only published

    def test_x_total_count_header(self, client, user_headers, moderator_headers):
        ad = _create_ad(client, user_headers).json()
        pay = client.post(f"/api/payments/ads/{ad['id']}/checkout", headers=user_headers).json()
        client.post(f"/api/payments/sandbox/{pay['payment_id']}/confirm", headers=user_headers)
        client.post(f"/api/ads/{ad['id']}/approve", headers=moderator_headers)
        client.post(f"/api/ads/{ad['id']}/publish", headers=moderator_headers)

        resp = client.get("/api/ads/")
        assert "x-total-count" in resp.headers


class TestExpiry:
    def test_expired_ad_hidden_from_anonymous(self, client, user_headers, moderator_headers):
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        ad = _create_ad(client, user_headers, expires_at=past).json()
        pay = client.post(f"/api/payments/ads/{ad['id']}/checkout", headers=user_headers).json()
        client.post(f"/api/payments/sandbox/{pay['payment_id']}/confirm", headers=user_headers)
        client.post(f"/api/ads/{ad['id']}/approve", headers=moderator_headers)
        client.post(f"/api/ads/{ad['id']}/publish", headers=moderator_headers)

        # anonymous detail: 404
        resp = client.get(f"/api/ads/{ad['id']}")
        assert resp.status_code == 404

        # anonymous list: not included
        resp = client.get("/api/ads/")
        ids = [a["id"] for a in resp.json()]
        assert ad["id"] not in ids


class TestCategoryValidation:
    def test_bogus_category_400(self, client, user_headers):
        resp = _create_ad(client, user_headers, category="nonexistent-category")
        assert resp.status_code == 400


class TestPayments:
    def test_config(self, client):
        resp = client.get("/api/payments/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount_cents"] > 0
        assert data["currency"] == "usd"

    def test_double_checkout_400(self, client, user_headers):
        ad = _create_ad(client, user_headers).json()
        resp1 = client.post(f"/api/payments/ads/{ad['id']}/checkout", headers=user_headers)
        assert resp1.status_code == 200
        pay = resp1.json()
        client.post(f"/api/payments/sandbox/{pay['payment_id']}/confirm", headers=user_headers)
        # second checkout on already-paid ad
        resp2 = client.post(f"/api/payments/ads/{ad['id']}/checkout", headers=user_headers)
        assert resp2.status_code == 400
