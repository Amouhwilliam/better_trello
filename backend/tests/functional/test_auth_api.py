"""
Functional tests for POST /auth/login.
"""
import pytest


def register_user(client, email: str, password: str, fullname: str = "Test User") -> dict:
    r = client.post("/users", json={"fullname": fullname, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


class TestLogin:
    def test_valid_credentials_return_200(self, client):
        register_user(client, "login_ok@example.com", "secret123")
        r = client.post("/auth/login", json={"email": "login_ok@example.com", "password": "secret123"})
        assert r.status_code == 200

    def test_response_contains_access_token(self, client):
        register_user(client, "token@example.com", "secret123")
        r = client.post("/auth/login", json={"email": "token@example.com", "password": "secret123"})
        body = r.json()
        assert "access_token" in body
        assert isinstance(body["access_token"], str)
        assert len(body["access_token"]) > 0

    def test_response_contains_token_type(self, client):
        register_user(client, "tokentype@example.com", "secret123")
        r = client.post("/auth/login", json={"email": "tokentype@example.com", "password": "secret123"})
        assert r.json()["token_type"] == "bearer"

    def test_response_contains_user(self, client):
        register_user(client, "userfield@example.com", "secret123", fullname="Alice Dupont")
        r = client.post("/auth/login", json={"email": "userfield@example.com", "password": "secret123"})
        user = r.json()["user"]
        assert user["email"] == "userfield@example.com"
        assert user["fullname"] == "Alice Dupont"
        assert "id" in user

    def test_wrong_password_returns_401(self, client):
        register_user(client, "wrongpw@example.com", "correct_password")
        r = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "wrong_password"})
        assert r.status_code == 401

    def test_unknown_email_returns_401(self, client):
        r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "anything"})
        assert r.status_code == 401

    def test_missing_email_returns_422(self, client):
        r = client.post("/auth/login", json={"password": "secret123"})
        assert r.status_code == 422

    def test_missing_password_returns_422(self, client):
        r = client.post("/auth/login", json={"email": "a@b.com"})
        assert r.status_code == 422

    def test_password_not_exposed_in_response(self, client):
        register_user(client, "nopw@example.com", "secret123")
        r = client.post("/auth/login", json={"email": "nopw@example.com", "password": "secret123"})
        body = r.json()
        assert "password" not in body
        assert "password_hash" not in body
        assert "password" not in body.get("user", {})
