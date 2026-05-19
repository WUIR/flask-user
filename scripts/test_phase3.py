"""Phase 3 end-to-end API tests — single client block."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db

app = create_app("testing")

with app.app_context():
    db.create_all()

with app.test_client() as c:
    print("=" * 50)
    print("1. REGISTER")
    print("=" * 50)

    r = c.post("/api/v1/auth/register", json={
        "username": "testuser", "email": "test@example.com", "password": "Pass1234",
    })
    data = r.get_json()
    assert r.status_code == 201
    assert data["success"] is True
    assert data["data"]["user"]["username"] == "testuser"
    _access = data["data"]["access_token"]
    _refresh = data["data"]["refresh_token"]
    print(f"   Register: {r.status_code} OK")

    # Duplicate checks
    r = c.post("/api/v1/auth/register", json={
        "username": "testuser", "email": "other@example.com", "password": "Pass1234",
    })
    assert r.status_code == 409
    print(f"   Duplicate username: {r.status_code}")

    r = c.post("/api/v1/auth/register", json={
        "username": "other", "email": "test@example.com", "password": "Pass1234",
    })
    assert r.status_code == 409
    print(f"   Duplicate email: {r.status_code}")

    # Validation
    r = c.post("/api/v1/auth/register", json={
        "username": "weak", "email": "w@t.com", "password": "12345678",
    })
    assert r.status_code == 422
    print(f"   Weak password: {r.status_code}")

    r = c.post("/api/v1/auth/register", json={"username": "abc"})
    assert r.status_code == 422
    print(f"   Missing fields: {r.status_code}")

    # ── Login ─────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("2. LOGIN")
    print("=" * 50)

    r = c.post("/api/v1/auth/login", json={"login": "testuser", "password": "Pass1234"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["data"]["user"]["role"] == "user"
    _access = data["data"]["access_token"]
    _refresh = data["data"]["refresh_token"]
    print(f"   Login by username: {r.status_code} OK")

    r = c.post("/api/v1/auth/login", json={"login": "test@example.com", "password": "Pass1234"})
    assert r.status_code == 200
    print(f"   Login by email: {r.status_code} OK")

    r = c.post("/api/v1/auth/login", json={"login": "testuser", "password": "wrongpass"})
    assert r.status_code == 401
    assert r.get_json()["message"] == "密码错误"
    print(f"   Wrong password: {r.status_code}")

    r = c.post("/api/v1/auth/login", json={"login": "nobody", "password": "Pass1234"})
    assert r.status_code == 401
    print(f"   No user: {r.status_code}")

    # ── Refresh ───────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("3. REFRESH TOKEN")
    print("=" * 50)

    r = c.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {_refresh}"})
    assert r.status_code == 200
    assert "access_token" in r.get_json()["data"]
    print(f"   Refresh with refresh token: {r.status_code} OK")

    r = c.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {_access}"})
    assert r.status_code == 422
    print(f"   Refresh with access token: {r.status_code} (expected)")

    # ── Profile ───────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("4. PROFILE")
    print("=" * 50)

    r = c.get("/api/v1/users/me", headers={"Authorization": f"Bearer {_access}"})
    assert r.status_code == 200
    assert r.get_json()["data"]["username"] == "testuser"
    print(f"   Get profile: {r.status_code} OK")

    r = c.get("/api/v1/users/me")
    assert r.status_code == 401
    print(f"   No auth: {r.status_code}")

    r = c.put("/api/v1/users/me", json={"nickname": "TestNick"},
              headers={"Authorization": f"Bearer {_access}"})
    assert r.status_code == 200
    assert r.get_json()["data"]["nickname"] == "TestNick"
    print(f"   Update nickname: {r.status_code} OK")

    r = c.put("/api/v1/users/me/password", json={
        "old_password": "Pass1234", "new_password": "NewPass567",
    }, headers={"Authorization": f"Bearer {_access}"})
    assert r.status_code == 200
    print(f"   Change password: {r.status_code} OK")

    r = c.post("/api/v1/auth/login", json={"login": "testuser", "password": "NewPass567"})
    assert r.status_code == 200
    _access = r.get_json()["data"]["access_token"]
    print(f"   Login with new password: {r.status_code} OK")

    r = c.put("/api/v1/users/me/password", json={
        "old_password": "wrong", "new_password": "Ignored1",
    }, headers={"Authorization": f"Bearer {_access}"})
    assert r.status_code == 400
    print(f"   Wrong old password: {r.status_code}")

    # ── Admin ─────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("5. ADMIN")
    print("=" * 50)

    # Promote testuser to admin via service
    from app.extensions import db as _db
    with app.app_context():
        u = __import__("app.models", fromlist=["User"]).User.query.filter_by(username="testuser").first()
        u.role = "admin"
        _db.session.commit()

    r = c.post("/api/v1/auth/login", json={"login": "testuser", "password": "NewPass567"})
    assert r.status_code == 200
    _admin_access = r.get_json()["data"]["access_token"]

    r = c.get("/api/v1/users", headers={"Authorization": f"Bearer {_admin_access}"})
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["total"] >= 1
    print(f"   List users: {r.status_code} - {data['total']} users, page {data['page']}")

    # Get specific user
    r = c.get("/api/v1/users/1", headers={"Authorization": f"Bearer {_admin_access}"})
    assert r.status_code == 200
    print(f"   Get user 1: {r.status_code} - {r.get_json()['data']['username']}")

    # Register a disposable user for admin operations
    c.post("/api/v1/auth/register", json={
        "username": "disposable", "email": "discard@t.com", "password": "Pass1234",
    })

    # Admin update
    r = c.put("/api/v1/users/2", json={"is_active": False},
              headers={"Authorization": f"Bearer {_admin_access}"})
    assert r.status_code == 200
    assert r.get_json()["data"]["is_active"] is False
    print(f"   Admin update: {r.status_code} OK")

    # Admin delete (disposable user)
    r = c.delete("/api/v1/users/2", headers={"Authorization": f"Bearer {_admin_access}"})
    assert r.status_code == 200
    print(f"   Admin delete: {r.status_code} OK")

    # Non-admin check (demote first)
    with app.app_context():
        u = __import__("app.models", fromlist=["User"]).User.query.filter_by(username="testuser").first()
        u.role = "user"
        _db.session.commit()

    r = c.post("/api/v1/auth/login", json={"login": "testuser", "password": "NewPass567"})
    _user_access = r.get_json()["data"]["access_token"]

    r = c.get("/api/v1/users", headers={"Authorization": f"Bearer {_user_access}"})
    assert r.status_code == 403
    print(f"   Non-admin denied: {r.status_code}")

    # ── Logout ────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("6. LOGOUT")
    print("=" * 50)

    r = c.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {_user_access}"})
    assert r.status_code == 200
    print(f"   Logout: {r.status_code} OK")

    # ── Search ────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("7. SEARCH")
    print("=" * 50)

    # Re-login as admin to search
    with app.app_context():
        u = __import__("app.models", fromlist=["User"]).User.query.filter_by(username="testuser").first()
        u.role = "admin"
        _db.session.commit()

    r = c.post("/api/v1/auth/login", json={"login": "testuser", "password": "NewPass567"})
    _admin_access = r.get_json()["data"]["access_token"]

    r = c.get("/api/v1/users?search=test",
              headers={"Authorization": f"Bearer {_admin_access}"})
    assert r.status_code == 200
    data = r.get_json()["data"]
    print(f"   Search 'test': {r.status_code} - {data['total']} result(s)")

    r = c.get("/api/v1/users?search=nonexistent",
              headers={"Authorization": f"Bearer {_admin_access}"})
    assert r.status_code == 200
    data = r.get_json()["data"]
    print(f"   Search 'nonexistent': {r.status_code} - {data['total']} result(s)")

print("\n" + "=" * 50)
print("阶段三 ALL TESTS PASSED!")
print("=" * 50)
