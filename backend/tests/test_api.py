import json
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_token(client):
    """Register a user and return a valid JWT token."""
    import time
    unique = str(int(time.time() * 1000))
    client.post(
        "/api/register",
        json={
            "full_name": f"Test User {unique}",
            "email": f"test_{unique}@example.com",
            "password": "testpass123",
        },
    )
    resp = client.post(
        "/api/login",
        json={
            "email": f"test_{unique}@example.com",
            "password": "testpass123",
        },
    )
    data = json.loads(resp.data)
    return data["token"]


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# ── Health ──────────────────────────────────────────────────────────

class TestHealth:

    def test_root(self, client):
        resp = client.get("/")
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert "JWT API running" in data["message"]


# ── Auth ────────────────────────────────────────────────────────────

class TestAuth:

    def test_register_success(self, client):
        import time
        unique = str(int(time.time() * 1000))
        resp = client.post(
            "/api/register",
            json={
                "full_name": f"New User {unique}",
                "email": f"new_{unique}@example.com",
                "password": "pass123",
            },
        )
        data = json.loads(resp.data)
        assert resp.status_code == 201
        assert data["success"] is True

    def test_register_missing_fields(self, client):
        resp = client.post(
            "/api/register",
            json={"full_name": "Incomplete"},
        )
        assert resp.status_code == 400

    def test_register_duplicate_email(self, client):
        import time
        unique = str(int(time.time() * 1000))
        payload = {
            "full_name": f"Dup {unique}",
            "email": f"dup_{unique}@example.com",
            "password": "pass",
        }
        client.post("/api/register", json=payload)
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 409

    def test_login_success(self, client):
        import time
        unique = str(int(time.time() * 1000))
        client.post(
            "/api/register",
            json={
                "full_name": f"Login {unique}",
                "email": f"login_{unique}@example.com",
                "password": "pass123",
            },
        )
        resp = client.post(
            "/api/login",
            json={
                "email": f"login_{unique}@example.com",
                "password": "pass123",
            },
        )
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert "token" in data

    def test_login_wrong_password(self, client):
        import time
        unique = str(int(time.time() * 1000))
        client.post(
            "/api/register",
            json={
                "full_name": f"Wrong {unique}",
                "email": f"wrong_{unique}@example.com",
                "password": "correct",
            },
        )
        resp = client.post(
            "/api/login",
            json={
                "email": f"wrong_{unique}@example.com",
                "password": "incorrect",
            },
        )
        assert resp.status_code == 401

    def test_protected_no_token(self, client):
        resp = client.get("/api/protected")
        assert resp.status_code == 401

    def test_me(self, client, auth_token):
        resp = client.get("/api/me", headers=_headers(auth_token))
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert "user" in data


# ── Users CRUD ──────────────────────────────────────────────────────

class TestUsersCRUD:

    def test_create_user(self, client, auth_token):
        import time
        unique = str(int(time.time() * 1000))
        resp = client.post(
            "/api/users",
            headers=_headers(auth_token),
            json={
                "full_name": f"Created {unique}",
                "email": f"created_{unique}@example.com",
                "password": "p",
                "role": "lender",
            },
        )
        data = json.loads(resp.data)
        assert resp.status_code == 201
        assert data["success"] is True
        assert "id" in data["data"]

    def test_create_user_invalid_role(self, client, auth_token):
        import time
        unique = str(int(time.time() * 1000))
        resp = client.post(
            "/api/users",
            headers=_headers(auth_token),
            json={
                "full_name": f"Bad {unique}",
                "email": f"bad_{unique}@example.com",
                "password": "p",
                "role": "superadmin",
            },
        )
        assert resp.status_code == 400

    def test_list_users(self, client, auth_token):
        resp = client.get("/api/users", headers=_headers(auth_token))
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert "data" in data
        assert "pagination" in data

    def test_get_user_not_found(self, client, auth_token):
        resp = client.get("/api/users/999999", headers=_headers(auth_token))
        assert resp.status_code == 404

    def test_update_user(self, client, auth_token):
        import time
        unique = str(int(time.time() * 1000))
        create_resp = client.post(
            "/api/users",
            headers=_headers(auth_token),
            json={
                "full_name": f"Upd {unique}",
                "email": f"upd_{unique}@example.com",
                "password": "p",
            },
        )
        user_id = json.loads(create_resp.data)["data"]["id"]

        resp = client.put(
            f"/api/users/{user_id}",
            headers=_headers(auth_token),
            json={"university": "UNZA"},
        )
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True

    def test_delete_user(self, client, auth_token):
        import time
        unique = str(int(time.time() * 1000))
        create_resp = client.post(
            "/api/users",
            headers=_headers(auth_token),
            json={
                "full_name": f"Del {unique}",
                "email": f"del_{unique}@example.com",
                "password": "p",
            },
        )
        user_id = json.loads(create_resp.data)["data"]["id"]

        resp = client.delete(
            f"/api/users/{user_id}",
            headers=_headers(auth_token),
        )
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True

        resp2 = client.get(
            f"/api/users/{user_id}",
            headers=_headers(auth_token),
        )
        assert resp2.status_code == 404
