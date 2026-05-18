import json
from urllib.parse import unquote
from uuid import uuid4

import pytest

import app as app_module

app = app_module.app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sent_otps(monkeypatch):
    sent = []

    def fake_send_otp_sms(phone_number, otp):
        sent.append({"phone_number": phone_number, "otp": otp})
        return {"success": True, "responseText": "SMS(es) have been queued for delivery"}

    monkeypatch.setattr(app_module, "send_otp_sms", fake_send_otp_sms)
    return sent


@pytest.fixture
def auth_token(client, sent_otps):
    """Register a user, request an OTP, and return a valid JWT token."""
    unique = uuid4().hex
    phone_number = f"097{unique[:7]}"
    client.post(
        "/api/register",
        json={
            "full_name": f"Test User {unique}",
            "email": f"test_{unique}@example.com",
            "phone_number": phone_number,
            "password": "testpass123",
        },
    )
    client.post("/api/login", json={"phone_number": phone_number})
    resp = client.post(
        "/api/login/otp",
        json={
            "phone_number": phone_number,
            "otp": sent_otps[-1]["otp"],
        },
    )
    data = json.loads(resp.data)
    return data["token"]


def _create_user_direct(role="borrower"):
    unique = uuid4().hex
    connection = app_module.get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (
                    full_name, email, phone_number, role, password_hash,
                    is_active, is_verified, failed_attempts
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    f"Direct {unique}",
                    f"direct_{unique}@example.com",
                    f"2609{unique[:8]}",
                    role,
                    app_module.generate_password_hash("password123"),
                    1,
                    1,
                    0,
                )
            )
            user_id = cursor.lastrowid
        connection.commit()
    finally:
        connection.close()

    return {
        "id": user_id,
        "full_name": f"Direct {unique}",
        "email": f"direct_{unique}@example.com",
        "phone_number": f"2609{unique[:8]}",
        "role": role,
    }


@pytest.fixture
def admin_token():
    admin = _create_user_direct(role="admin")
    return app_module.generate_token(admin)


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


class TestHealth:

    def test_root(self, client):
        resp = client.get("/")
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert "JWT API running" in data["message"]


class TestAuth:

    def test_register_success(self, client):
        unique = uuid4().hex
        resp = client.post(
            "/api/register",
            json={
                "full_name": f"New User {unique}",
                "email": f"new_{unique}@example.com",
                "phone_number": f"096{unique[:7]}",
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
        unique = uuid4().hex
        payload = {
            "full_name": f"Dup {unique}",
            "email": f"dup_{unique}@example.com",
            "phone_number": f"095{unique[:7]}",
            "password": "pass",
        }
        client.post("/api/register", json=payload)
        resp = client.post("/api/register", json=payload)
        assert resp.status_code == 409

    def test_login_sends_otp_and_saves_it(self, client, sent_otps):
        unique = uuid4().hex
        phone_number = f"094{unique[:7]}"
        client.post(
            "/api/register",
            json={
                "full_name": f"Login {unique}",
                "email": f"login_{unique}@example.com",
                "phone_number": phone_number,
                "password": "pass123",
            },
        )
        resp = client.post("/api/login", json={"phone_number": phone_number})
        data = json.loads(resp.data)

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["message"] == "OTP sent successfully"
        assert sent_otps[-1]["phone_number"] == phone_number

        connection = app_module.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT otp_code
                    FROM login_otps
                    WHERE phone_number = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (phone_number,)
                )
                otp_record = cursor.fetchone()
        finally:
            connection.close()

        assert otp_record["otp_code"] == sent_otps[-1]["otp"]

    def test_login_requires_phone_number_only(self, client):
        resp = client.post("/api/login", json={})
        data = json.loads(resp.data)

        assert resp.status_code == 400
        assert data["message"] == "Phone number required"

    def test_login_otp_success_returns_token_and_user(self, client, sent_otps):
        unique = uuid4().hex
        phone_number = f"093{unique[:7]}"
        client.post(
            "/api/register",
            json={
                "full_name": f"OTP {unique}",
                "email": f"otp_{unique}@example.com",
                "phone_number": phone_number,
                "password": "pass123",
            },
        )
        client.post("/api/login", json={"phone_number": phone_number})

        resp = client.post(
            "/api/login/otp",
            json={
                "phone_number": phone_number,
                "otp": sent_otps[-1]["otp"],
            },
        )
        data = json.loads(resp.data)

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["message"] == "Login successful"
        assert "token" in data
        assert data["user"]["phone_number"] == phone_number

    def test_login_otp_validation_error(self, client):
        resp = client.post(
            "/api/login/otp",
            json={
                "phone_number": "0970000000",
                "otp": "000000",
            },
        )
        data = json.loads(resp.data)

        assert resp.status_code == 401
        assert data["message"] == "OTP validation failed"

    def test_send_otp_sms_uses_zamtel_api(self, monkeypatch):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"success": true, "responseText": "queued"}'

        def fake_urlopen(request_obj, timeout):
            captured["url"] = request_obj.full_url
            captured["method"] = request_obj.get_method()
            captured["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setenv("ZAMTEL_API_KEY", "test-key")
        monkeypatch.setenv("ZAMTEL_SENDER_ID", "HelsBCredit")
        monkeypatch.setenv("ZAMTEL_BASE_URL", "https://bulksms.zamtel.co.zm/api/v2.1/action/send/")
        monkeypatch.setattr(app_module, "urlopen", fake_urlopen)

        response = app_module.send_otp_sms("0970000000", "123456")

        assert response["success"] is True
        assert captured["method"] == "POST"
        assert captured["timeout"] == 10
        assert "/api_key/test-key/" in captured["url"]
        assert "/contacts/260970000000/" in captured["url"]
        assert "/senderId/HelsBCredit/" in captured["url"]
        assert "Your HelsB Credit login OTP is 123456" in unquote(captured["url"])

    def test_normalize_phone_number_for_zamtel(self):
        assert app_module.normalize_phone_number("0970000000") == "260970000000"
        assert app_module.normalize_phone_number("+260970000000") == "260970000000"
        assert app_module.normalize_phone_number("260970000000") == "260970000000"

    def test_protected_no_token(self, client):
        resp = client.get("/api/protected")
        assert resp.status_code == 401

    def test_me(self, client, auth_token):
        resp = client.get("/api/me", headers=_headers(auth_token))
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert "user" in data


class TestUsersCRUD:

    def test_create_user(self, client, auth_token):
        unique = uuid4().hex
        resp = client.post(
            "/api/users",
            headers=_headers(auth_token),
            json={
                "full_name": f"Created {unique}",
                "email": f"created_{unique}@example.com",
                "phone_number": f"092{unique[:7]}",
                "password": "p",
                "role": "lender",
            },
        )
        data = json.loads(resp.data)
        assert resp.status_code == 201
        assert data["success"] is True
        assert "id" in data["data"]

    def test_create_user_invalid_role(self, client, auth_token):
        unique = uuid4().hex
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
        unique = uuid4().hex
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
        unique = uuid4().hex
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


class TestAdminUsers:

    def test_admin_routes_require_admin_role(self, client, auth_token):
        resp = client.get("/api/admin/users", headers=_headers(auth_token))
        data = json.loads(resp.data)

        assert resp.status_code == 403
        assert data["message"] == "Admin access required"

    def test_admin_create_and_get_user(self, client, admin_token):
        unique = uuid4().hex
        payload = {
            "full_name": f"Managed {unique}",
            "email": f"managed_{unique}@example.com",
            "phone_number": f"26097{unique[:7]}",
            "password": "password123",
            "role": "lender",
            "is_verified": 1,
        }

        create_resp = client.post(
            "/api/admin/users",
            headers=_headers(admin_token),
            json=payload,
        )
        create_data = json.loads(create_resp.data)

        assert create_resp.status_code == 201
        assert create_data["success"] is True

        get_resp = client.get(
            f"/api/admin/users/{create_data['user_id']}",
            headers=_headers(admin_token),
        )
        get_data = json.loads(get_resp.data)

        assert get_resp.status_code == 200
        assert get_data["data"]["email"] == payload["email"]
        assert get_data["data"]["role"] == "lender"
        assert get_data["data"]["is_verified"] is True

    def test_admin_list_users_with_filters(self, client, admin_token):
        managed = _create_user_direct(role="agent")

        resp = client.get(
            f"/api/admin/users?search={managed['email']}&role=agent&is_active=1",
            headers=_headers(admin_token),
        )
        data = json.loads(resp.data)

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["pagination"]["total"] >= 1
        assert any(user["id"] == managed["id"] for user in data["data"])

    def test_admin_update_user(self, client, admin_token):
        managed = _create_user_direct(role="borrower")

        resp = client.patch(
            f"/api/admin/users/{managed['id']}",
            headers=_headers(admin_token),
            json={"university": "UNZA", "role": "rep"},
        )
        data = json.loads(resp.data)

        assert resp.status_code == 200
        assert data["message"] == "User updated successfully"

        get_resp = client.get(
            f"/api/admin/users/{managed['id']}",
            headers=_headers(admin_token),
        )
        get_data = json.loads(get_resp.data)

        assert get_data["data"]["university"] == "UNZA"
        assert get_data["data"]["role"] == "rep"

    def test_admin_update_user_status(self, client, admin_token):
        managed = _create_user_direct(role="borrower")

        resp = client.patch(
            f"/api/admin/users/{managed['id']}/status",
            headers=_headers(admin_token),
            json={"is_active": 0},
        )
        data = json.loads(resp.data)

        assert resp.status_code == 200
        assert data["message"] == "User status updated successfully"

        get_resp = client.get(
            f"/api/admin/users/{managed['id']}",
            headers=_headers(admin_token),
        )
        get_data = json.loads(get_resp.data)

        assert get_data["data"]["is_active"] is False

    def test_admin_reset_user_password(self, client, admin_token):
        managed = _create_user_direct(role="borrower")

        resp = client.patch(
            f"/api/admin/users/{managed['id']}/reset-password",
            headers=_headers(admin_token),
            json={"password": "newpassword123"},
        )
        data = json.loads(resp.data)

        assert resp.status_code == 200
        assert data["message"] == "Password reset successfully"

    def test_admin_rejects_invalid_role(self, client, admin_token):
        resp = client.post(
            "/api/admin/users",
            headers=_headers(admin_token),
            json={
                "full_name": "Invalid Role",
                "email": f"invalid_{uuid4().hex}@example.com",
                "password": "password123",
                "role": "user",
            },
        )
        data = json.loads(resp.data)

        assert resp.status_code == 400
        assert "Invalid role" in data["message"]
