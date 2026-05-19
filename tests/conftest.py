"""pytest fixtures — function-scoped app for isolated test databases."""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User


@pytest.fixture(scope="function")
def app():
    """Function-scoped app — fresh in-memory SQLite per test."""
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Give tests access to the db session (still within app context)."""
    with app.app_context():
        yield _db


# ── Helper: create user directly in DB (not via API) ──────────

def _create_user_in_db(username="testuser", email="test@example.com",
                       password="Test1234", role="user"):
    """Create a User model instance and commit."""
    u = User(username=username, email=email)
    u.password = password
    u.role = role
    _db.session.add(u)
    _db.session.commit()
    return u


# ── Token fixtures ────────────────────────────────────────────

@pytest.fixture(scope="function")
def user_token(client):
    """Register a normal user and return (access, refresh)."""
    resp = client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test1234",
    })
    data = resp.get_json()["data"]
    return data["access_token"], data["refresh_token"]


@pytest.fixture(scope="function")
def auth_header(user_token):
    """Auth header for a normal user."""
    access, _ = user_token
    return {"Authorization": f"Bearer {access}"}


@pytest.fixture(scope="function")
def admin_auth_header(client, app):
    """Auth header for an admin user (created directly)."""
    with app.app_context():
        _create_user_in_db(username="admin", email="admin@example.com",
                           password="Admin1234", role="admin")
    resp = client.post("/api/v1/auth/login", json={
        "login": "admin", "password": "Admin1234",
    })
    token = resp.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
