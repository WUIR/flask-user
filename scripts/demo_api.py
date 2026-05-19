"""API Demo — shows every endpoint with request & response."""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db

app = create_app("testing")

def j(data):
    return json.dumps(data, indent=2, ensure_ascii=False)

with app.app_context():
    db.create_all()

with app.test_client() as c:
    print("=" * 65)
    print("FLASK 用户系统 — API 完整演示")
    print("=" * 65)

    # ── 1. Health ──────────────────────────────────────────
    print("\n─── 1. Health ──────────────────────────────────────")
    r = c.get("/api/v1/health")
    print(f"  GET  /api/v1/health  →  {r.status_code}")
    print(f"  {j(r.get_json())}")

    # ── 2. Register ────────────────────────────────────────
    print("\n─── 2. Register ────────────────────────────────────")
    payload = {"username": "alice", "email": "alice@example.com", "password": "Alice1234"}
    r = c.post("/api/v1/auth/register", json=payload)
    data = r.get_json()
    print(f"  POST /api/v1/auth/register  →  {r.status_code}")
    print(f"  Payload: {j(payload)}")
    print(f"  Response: {j({'success': data['success'], 'message': data['message'], 'user': data['data']['user']})}")
    _access = data["data"]["access_token"]
    _refresh = data["data"]["refresh_token"]

    # Register failure — duplicate
    r = c.post("/api/v1/auth/register", json={"username": "alice", "email": "b@t.com", "password": "Xxx12345"})
    print(f"\n  Duplicate user → {r.status_code}: {r.get_json()['message']}")

    # Register failure — weak password
    r = c.post("/api/v1/auth/register", json={"username": "bob", "email": "b@t.com", "password": "12345678"})
    print(f"  Weak password → {r.status_code}: {r.get_json()['message']}")

    # ── 3. Login ───────────────────────────────────────────
    print("\n─── 3. Login ───────────────────────────────────────")
    r = c.post("/api/v1/auth/login", json={"login": "alice", "password": "Alice1234"})
    data = r.get_json()
    print(f"  POST /api/v1/auth/login  →  {r.status_code}")
    print(f"  Response: {j({'success': data['success'], 'message': data['message'], 'user': data['data']['user']})}")
    _access = data["data"]["access_token"]

    # Login failure
    r = c.post("/api/v1/auth/login", json={"login": "alice", "password": "wrong"})
    print(f"\n  Wrong password → {r.status_code}: {r.get_json()['message']}")
    r = c.post("/api/v1/auth/login", json={"login": "nobody", "password": "Xxx12345"})
    print(f"  No user → {r.status_code}: {r.get_json()['message']}")

    # ── 4. Refresh ─────────────────────────────────────────
    print("\n─── 4. Refresh Token ───────────────────────────────")
    r = c.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {_refresh}"})
    print(f"  POST /api/v1/auth/refresh  →  {r.status_code}")
    print(f"  {j(r.get_json())}")

    r = c.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {_access}"})
    print(f"\n  Refresh with ACCESS token → {r.status_code}: {r.get_json()['msg']}")

    # ── 5. Get Profile ─────────────────────────────────────
    print("\n─── 5. Get Profile ────────────────────────────────")
    r = c.get("/api/v1/users/me", headers={"Authorization": f"Bearer {_access}"})
    print(f"  GET  /api/v1/users/me  →  {r.status_code}")
    print(f"  {j(r.get_json()['data'])}")

    # ── 6. Update Profile ──────────────────────────────────
    print("\n─── 6. Update Profile ─────────────────────────────")
    payload = {"nickname": "AliceInWonderland"}
    r = c.put("/api/v1/users/me", json=payload, headers={"Authorization": f"Bearer {_access}"})
    print(f"  PUT  /api/v1/users/me  →  {r.status_code}")
    print(f"  Payload: {j(payload)}")
    print(f"  Response: {j({'message': r.get_json()['message'], 'nickname': r.get_json()['data']['nickname']})}")

    # ── 7. Change Password ─────────────────────────────────
    print("\n─── 7. Change Password ────────────────────────────")
    payload = {"old_password": "Alice1234", "new_password": "NewPass789"}
    r = c.put("/api/v1/users/me/password", json=payload, headers={"Authorization": f"Bearer {_access}"})
    print(f"  PUT  /api/v1/users/me/password  →  {r.status_code}")
    print(f"  {j(r.get_json())}")

    # ── 8. Admin Operations ────────────────────────────────
    print("\n─── 8. Admin Operations ───────────────────────────")

    # Register a second user + promote to admin
    c.post("/api/v1/auth/register", json={"username": "bob", "email": "bob@t.com", "password": "Bob12345"})
    c.post("/api/v1/auth/register", json={"username": "charlie", "email": "charlie@t.com", "password": "Cha12345"})

    with app.app_context():
        u = __import__("app.models", fromlist=["User"]).User.query.filter_by(username="alice").first()
        u.role = "admin"
        db.session.commit()

    r = c.post("/api/v1/auth/login", json={"login": "alice", "password": "NewPass789"})
    _admin_access = r.get_json()["data"]["access_token"]

    # List users
    r = c.get("/api/v1/users", headers={"Authorization": f"Bearer {_admin_access}"})
    print(f"  GET  /api/v1/users  →  {r.status_code}")
    print(f"  {j({k: v for k, v in r.get_json()['data'].items() if k != 'items'})}")
    print(f"  Users: {[u['username'] for u in r.get_json()['data']['items']]}")

    # Search
    r = c.get("/api/v1/users?search=bob", headers={"Authorization": f"Bearer {_admin_access}"})
    print(f"\n  GET  /api/v1/users?search=bob  →  {r.status_code}")
    print(f"  Found: {r.get_json()['data']['total']} user(s)")

    # Get user by ID
    r = c.get("/api/v1/users/2", headers={"Authorization": f"Bearer {_admin_access}"})
    print(f"\n  GET  /api/v1/users/2  →  {r.status_code}")
    print(f"  {j(r.get_json()['data'])}")

    # Admin update user
    r = c.put("/api/v1/users/2", json={"is_active": False, "role": "admin"},
              headers={"Authorization": f"Bearer {_admin_access}"})
    print(f"\n  PUT  /api/v1/users/2  →  {r.status_code}")
    print(f"  {j({'message': r.get_json()['message'], 'is_active': r.get_json()['data']['is_active'], 'role': r.get_json()['data']['role']})}")

    # Admin delete user
    r = c.delete("/api/v1/users/3", headers={"Authorization": f"Bearer {_admin_access}"})
    print(f"\n  DELETE /api/v1/users/3  →  {r.status_code}: {r.get_json()['message']}")

    # Non‑admin check
    with app.app_context():
        u2 = __import__("app.models", fromlist=["User"]).User.query.filter_by(username="alice").first()
        u2.role = "user"
        db.session.commit()
    r = c.post("/api/v1/auth/login", json={"login": "alice", "password": "NewPass789"})
    _user_access = r.get_json()["data"]["access_token"]
    r = c.get("/api/v1/users", headers={"Authorization": f"Bearer {_user_access}"})
    print(f"\n  Non‑admin GET /api/v1/users  →  {r.status_code}: {r.get_json()['message']}")

    # ── 9. Logout ──────────────────────────────────────────
    print("\n─── 9. Logout ─────────────────────────────────────")
    r = c.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {_user_access}"})
    print(f"  POST /api/v1/auth/logout  →  {r.status_code}: {r.get_json()['message']}")

    print("\n" + "=" * 65)
    print("ALL 12 API ENDPOINTS DEMONSTRATED SUCCESSFULLY")
    print("=" * 65)
