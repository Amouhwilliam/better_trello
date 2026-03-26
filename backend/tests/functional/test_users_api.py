"""
Functional tests for /users endpoints.
All requests go through the full HTTP stack: routing → dependency injection
→ application service → domain → SQLite.
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_user(
    client: TestClient,
    fullname: str = "Alice Dupont",
    email: str | None = None,
    password: str = "secret123",
    suffix: str = "",
) -> dict:
    if email is None:
        email = f"alice{suffix}@example.com"
    payload = {"fullname": fullname, "email": email, "password": password}
    r = client.post("/users", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

class TestGetMe:
    def test_returns_own_user(self, client: TestClient):
        """Create a user, override auth to that user's ID, then call /me."""
        import uuid
        from unittest.mock import patch

        from api.dependencies import get_current_user_id
        from main import app

        u = create_user(client, email="me_test@x.com")
        user_uuid = uuid.UUID(u["id"])

        # Only works in in-process mode (TestClient); in live-server mode skip.
        if not hasattr(app, "dependency_overrides"):
            return

        original = app.dependency_overrides.get(get_current_user_id)
        app.dependency_overrides[get_current_user_id] = lambda: user_uuid
        try:
            r = client.get("/users/me")
            assert r.status_code == 200
            body = r.json()
            assert body["id"] == u["id"]
            assert body["email"] == "me_test@x.com"
            assert "password" not in body
            assert "password_hash" not in body
        finally:
            if original is None:
                app.dependency_overrides.pop(get_current_user_id, None)
            else:
                app.dependency_overrides[get_current_user_id] = original

    def test_returns_404_for_unknown_auth_id(self, client: TestClient):
        """When the JWT points to a non-existent user, /me returns 404."""
        r = client.get("/users/me")
        # TEST_USER_ID has no matching row → 404
        assert r.status_code == 404
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_returns_201(self, client: TestClient):
        r = client.post("/users", json={"fullname": "Alice", "email": "u_create_201@x.com", "password": "pass123"})
        assert r.status_code == 201

    def test_response_shape(self, client: TestClient):
        r = client.post("/users", json={"fullname": "Alice", "email": "u_shape@x.com", "password": "pass123"})
        body = r.json()
        assert "id" in body
        assert body["fullname"] == "Alice"
        assert body["email"] == "u_shape@x.com"
        assert "password" not in body
        assert "password_hash" not in body

    def test_missing_fullname_returns_422(self, client: TestClient):
        r = client.post("/users", json={"email": "u@x.com", "password": "pass123"})
        assert r.status_code == 422

    def test_missing_email_returns_422(self, client: TestClient):
        r = client.post("/users", json={"fullname": "Alice", "password": "pass123"})
        assert r.status_code == 422

    def test_invalid_email_returns_422(self, client: TestClient):
        r = client.post("/users", json={"fullname": "Alice", "email": "not-an-email", "password": "pass123"})
        assert r.status_code == 422

    def test_short_password_returns_422(self, client: TestClient):
        r = client.post("/users", json={"fullname": "Alice", "email": "u@x.com", "password": "123"})
        assert r.status_code == 422

    def test_duplicate_email_returns_409(self, client: TestClient):
        create_user(client, email="u_dup@x.com")
        r = client.post("/users", json={"fullname": "Bob", "email": "u_dup@x.com", "password": "pass123"})
        assert r.status_code == 409
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_returns_200(self, client: TestClient):
        r = client.get("/users")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert "has_more" in body

    def test_includes_created_user(self, client: TestClient):
        u = create_user(client, email="u_list@x.com")
        ids = [x["id"] for x in client.get("/users").json()["items"]]
        assert u["id"] in ids


# ---------------------------------------------------------------------------
# GET /users — pagination
# ---------------------------------------------------------------------------

class TestListUsersPaginated:
    def test_default_page_is_1(self, client: TestClient):
        assert client.get("/users").json()["page"] == 1

    def test_default_page_size_is_6(self, client: TestClient):
        assert client.get("/users").json()["page_size"] == 6

    def test_total_reflects_all_users(self, client: TestClient):
        for i in range(3):
            create_user(client, email=f"u_pag_total{i}@x.com")
        assert client.get("/users").json()["total"] >= 3

    def test_page_size_limits_items(self, client: TestClient):
        for i in range(5):
            create_user(client, email=f"u_pag_size{i}@x.com")
        items = client.get("/users?page_size=2").json()["items"]
        assert len(items) <= 2

    def test_second_page_returns_next_items(self, client: TestClient):
        for i in range(4):
            create_user(client, email=f"u_pag_page{i}@x.com")
        p1 = {x["id"] for x in client.get("/users?page=1&page_size=2").json()["items"]}
        p2 = {x["id"] for x in client.get("/users?page=2&page_size=2").json()["items"]}
        assert p1.isdisjoint(p2)

    def test_has_more_true_when_more_pages_exist(self, client: TestClient):
        for i in range(3):
            create_user(client, email=f"u_has_more{i}@x.com")
        body = client.get("/users?page=1&page_size=1").json()
        assert body["has_more"] is True

    def test_has_more_false_on_last_page(self, client: TestClient):
        create_user(client, email="u_last_page@x.com")
        total = client.get("/users").json()["total"]
        body = client.get(f"/users?page=1&page_size={total}").json()
        assert body["has_more"] is False

    def test_invalid_page_returns_422(self, client: TestClient):
        assert client.get("/users?page=0").status_code == 422

    def test_invalid_page_size_returns_422(self, client: TestClient):
        assert client.get("/users?page_size=0").status_code == 422


# ---------------------------------------------------------------------------
# GET /users/{id}
# ---------------------------------------------------------------------------

class TestGetUser:
    def test_returns_user(self, client: TestClient):
        u = create_user(client, email="u_get@x.com")
        r = client.get(f"/users/{u['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == u["id"]

    def test_returns_404_for_unknown_id(self, client: TestClient):
        r = client.get("/users/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_404_body_has_detail(self, client: TestClient):
        r = client.get("/users/00000000-0000-0000-0000-000000000001")
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# PUT /users/{id}
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_updates_fullname(self, client: TestClient):
        u = create_user(client, email="u_upd_name@x.com")
        r = client.put(f"/users/{u['id']}", json={"fullname": "Alicia"})
        assert r.status_code == 200
        assert r.json()["fullname"] == "Alicia"

    def test_updates_email(self, client: TestClient):
        u = create_user(client, email="u_upd_email_old@x.com")
        r = client.put(f"/users/{u['id']}", json={"email": "u_upd_email_new@x.com"})
        assert r.status_code == 200
        assert r.json()["email"] == "u_upd_email_new@x.com"

    def test_duplicate_email_update_returns_409(self, client: TestClient):
        create_user(client, email="u_taken@x.com")
        u2 = create_user(client, email="u_upd_dup@x.com")
        r = client.put(f"/users/{u2['id']}", json={"email": "u_taken@x.com"})
        assert r.status_code == 409

    def test_password_not_exposed_in_response(self, client: TestClient):
        u = create_user(client, email="u_pw_resp@x.com")
        r = client.put(f"/users/{u['id']}", json={"password": "newpass123"})
        assert r.status_code == 200
        assert "password" not in r.json()
        assert "password_hash" not in r.json()

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.put("/users/00000000-0000-0000-0000-000000000000", json={"fullname": "Ghost"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /users/{id}
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_returns_204(self, client: TestClient):
        u = create_user(client, email="u_del@x.com")
        r = client.delete(f"/users/{u['id']}")
        assert r.status_code == 204

    def test_user_no_longer_retrievable(self, client: TestClient):
        u = create_user(client, email="u_del2@x.com")
        client.delete(f"/users/{u['id']}")
        assert client.get(f"/users/{u['id']}").status_code == 404

    def test_returns_404_for_unknown(self, client: TestClient):
        r = client.delete("/users/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404
