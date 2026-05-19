"""Auth API tests — register, login, refresh, logout."""
import time

from flask_jwt_extended import create_access_token


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Pass1234",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["user"]["username"] == "newuser"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        # password_hash should NOT be in response
        assert "password_hash" not in data["data"]["user"]

    def test_register_duplicate_username(self, client, user_token):
        resp = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "Pass1234",
        })
        assert resp.status_code == 409
        assert "用户名已存在" in resp.get_json()["message"]

    def test_register_duplicate_email(self, client, user_token):
        resp = client.post("/api/v1/auth/register", json={
            "username": "otheruser",
            "email": "test@example.com",
            "password": "Pass1234",
        })
        assert resp.status_code == 409
        assert "邮箱已被注册" in resp.get_json()["message"]

    def test_register_weak_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "12345678",
        })
        assert resp.status_code == 422

    def test_register_missing_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "partial",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "badmail",
            "email": "not-an-email",
            "password": "Pass1234",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_by_username(self, client, user_token):
        resp = client.post("/api/v1/auth/login", json={
            "login": "testuser",
            "password": "Test1234",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["user"]["username"] == "testuser"
        assert "access_token" in data["data"]

    def test_login_by_email(self, client, user_token):
        resp = client.post("/api/v1/auth/login", json={
            "login": "test@example.com",
            "password": "Test1234",
        })
        assert resp.status_code == 200

    def test_login_wrong_password(self, client, user_token):
        resp = client.post("/api/v1/auth/login", json={
            "login": "testuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401
        assert resp.get_json()["message"] == "密码错误"

    def test_login_user_not_found(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "login": "nobody",
            "password": "Test1234",
        })
        assert resp.status_code == 401
        assert "不存在" in resp.get_json()["message"]

    def test_login_disabled_user(self, client, app, auth_header):
        """Disable user, attempt login."""
        with app.app_context():
            from app.extensions import db
            from app.models.user import User
            u = User.query.filter_by(username="testuser").first()
            u.is_active = False
            db.session.commit()

        resp = client.post("/api/v1/auth/login", json={
            "login": "testuser",
            "password": "Test1234",
        })
        assert resp.status_code == 401
        assert "禁用" in resp.get_json()["message"]

        # Restore
        with app.app_context():
            from app.extensions import db
            u = User.query.filter_by(username="testuser").first()
            u.is_active = True
            db.session.commit()

    def test_login_missing_fields(self, client):
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422


class TestRefresh:
    def test_refresh_success(self, client, user_token):
        _, refresh = user_token
        resp = client.post("/api/v1/auth/refresh", headers={
            "Authorization": f"Bearer {refresh}",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()["data"]

    def test_refresh_with_access_token_fails(self, client, user_token):
        access, _ = user_token
        resp = client.post("/api/v1/auth/refresh", headers={
            "Authorization": f"Bearer {access}",
        })
        assert resp.status_code == 422

    def test_refresh_no_token(self, client):
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_fake_token(self, client):
        resp = client.post("/api/v1/auth/refresh", headers={
            "Authorization": "Bearer this.is.a.fake.jwt",
        })
        # JWT extension returns 422 for invalid/malformed tokens
        assert resp.status_code in (401, 422)


class TestLogout:
    def test_logout_success(self, client, auth_header):
        resp = client.post("/api/v1/auth/logout", headers=auth_header)
        assert resp.status_code == 200

    def test_logout_no_auth(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401
