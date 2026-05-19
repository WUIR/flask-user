"""Coverage gap tests — hit every missing code path for 100%."""
from datetime import timedelta

from flask import abort
from flask_jwt_extended import create_access_token
from marshmallow import ValidationError as MarshError
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models.user import User
from app.utils.response import error_response


class TestModelCoverage:
    """Cover missing lines in app/models/user.py"""

    def test_password_property_raises(self, db, app):
        """Line 30: accessing User.password raises AttributeError"""
        u = User(username="cov", email="cov@test.com")
        u.password = "Test1234"
        import pytest
        with pytest.raises(AttributeError, match="password is not a readable attribute"):
            _ = u.password

    def test_repr(self, db, app):
        """Line 55: __repr__ is callable"""
        u = User(username="repr_user", email="repr@test.com")
        u.password = "Test1234"
        db.session.add(u)
        db.session.commit()
        r = repr(u)
        assert "repr_user" in r
        assert "user" in r  # default role


class TestAppFactoryCoverage:
    """Cover missing lines in app/__init__.py"""

    def test_create_app_default(self, monkeypatch):
        """Line 13: create_app() with no args (config_name is None)"""
        import os
        monkeypatch.delenv("FLASK_ENV", raising=False)
        app = create_app()
        assert app is not None
        assert app.config["DEBUG"] is True

    def test_create_app_production_talisman(self, monkeypatch):
        """Line 26: production mode with USE_TALISMAN"""
        import os
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        app = create_app("production")
        assert app.config["USE_TALISMAN"] is True

    def test_health_endpoint(self, client):
        """Line 39: health check return"""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}


class TestUserAPIExceptions:
    """Cover exception branches in app/api/users.py"""

    def test_get_me_user_deleted_before_fetch(self, client, app):
        """Lines 36-37: user deleted between auth and request"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "shortlived", "email": "short@test.com", "password": "Short1234",
        })
        token = resp.get_json()["data"]["access_token"]
        user_id = resp.get_json()["data"]["user"]["id"]
        with app.app_context():
            u = User.query.get(user_id)
            db.session.delete(u)
            db.session.commit()
        resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_update_profile_validation_error(self, client, auth_header):
        """Lines 47-48: invalid data sent to update endpoint"""
        resp = client.put("/api/v1/users/me", json={"avatar_url": "not-a-url"},
                          headers=auth_header)
        assert resp.status_code == 422

    def test_admin_update_validation_error(self, client, admin_auth_header):
        """Lines 118-119: invalid data in admin update"""
        resp = client.put("/api/v1/users/1", json={"role": "superadmin"},
                          headers=admin_auth_header)
        assert resp.status_code == 422


class TestErrorHandlers:
    """Cover every error handler in app/utils/errors.py"""

    def test_all_http_errors(self, client, app):
        """Trigger abort-based error handlers (400, 401, 403, 404, 405, 422, 500)."""
        @app.route("/_test_abort/<int:code>")
        def _abort(code):
            abort(code)

        with app.test_client() as c:
            for code in (400, 401, 403, 404, 405, 422, 500):
                resp = c.get(f"/_test_abort/{code}")
                assert resp.status_code == code
                data = resp.get_json()
                assert data["success"] is False

    def test_validation_error_handler(self, client, app):
        """Line 41: marshmallow ValidationError handler."""
        @app.route("/_test_validation")
        def _val():
            raise MarshError({"field": ["invalid"]}, field="invalid")
        with app.test_client() as c:
            resp = c.get("/_test_validation")
            assert resp.status_code == 422
            assert resp.get_json()["message"] == "数据校验失败"

    def test_integrity_error_handler(self, client, app):
        """Line 45: SQLAlchemy IntegrityError handler."""
        @app.route("/_test_integrity")
        def _int():
            raise IntegrityError("INSERT", None, "UNIQUE constraint")
        with app.test_client() as c:
            resp = c.get("/_test_integrity")
            assert resp.status_code == 409
            assert resp.get_json()["message"] == "数据冲突"

    def test_expired_token_handler(self, client, app):
        """Line 53: ExpiredSignatureError handler."""
        from jwt.exceptions import ExpiredSignatureError
        @app.route("/_test_expired")
        def _exp():
            raise ExpiredSignatureError("Signature has expired")
        with app.test_client() as c:
            resp = c.get("/_test_expired")
            assert resp.status_code == 401
            assert resp.get_json()["message"] == "Token 已过期"

    def test_invalid_token_handler(self, client, app):
        """Line 57: InvalidTokenError handler."""
        from jwt.exceptions import InvalidTokenError
        @app.route("/_test_invalid_token")
        def _inv():
            raise InvalidTokenError("Invalid token")
        with app.test_client() as c:
            resp = c.get("/_test_invalid_token")
            assert resp.status_code == 401
            assert resp.get_json()["message"] == "无效的 Token"
