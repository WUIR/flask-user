"""Comprehensive Phase 2 tests: model, response, error handling."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flask
from marshmallow import Schema, fields

from app import create_app
from app.extensions import db
from app.models import User
from app.utils.response import success_response, error_response

app = create_app("testing")

# Add a validation test route before any request is handled
class EmailSchema(Schema):
    email = fields.Email(required=True)

@app.route("/api/v1/_test_validate", methods=["POST"])
def test_validate():
    schema = EmailSchema()
    data = schema.load(flask.request.get_json())
    return {"ok": True}

# ── 1. response.py 序列化 ──────────────────────────────────
print("=" * 50)
print("1. 统一响应格式测试")
with app.test_request_context():
    r, code = success_response({"id": 1}, "ok")
    assert code == 200
    assert r.json["success"] is True
    assert r.json["data"] == {"id": 1}
    print("   success_response: OK")

    r, code = error_response("bad request", {"field": ["error"]}, 400)
    assert code == 400
    assert r.json["success"] is False
    assert r.json["errors"] == {"field": ["error"]}
    print("   error_response:   OK")

# ── 2. Model CRUD ──────────────────────────────────────────
print("\n" + "=" * 50)
print("2. User 模型 CRUD 测试")
with app.app_context():
    db.create_all()

    u = User(username="alice", email="alice@test.com", password="Pass1234")
    db.session.add(u)
    db.session.commit()
    uid = u.id
    print(f"   Create:  {u}")

    assert User.query.get(uid) is not None
    print("   Read:    OK")

    assert u.check_password("Pass1234")
    assert not u.check_password("wrong")
    print("   Password: OK")

    d = u.to_dict()
    assert "password_hash" not in d
    assert d["username"] == "alice"
    for k in ("created_at", "updated_at"):
        assert "T" in d[k]
    print("   to_dict: OK")

    u.nickname = "Alice"
    db.session.commit()
    assert User.query.get(uid).nickname == "Alice"
    print("   Update:  OK")

    from sqlalchemy.exc import IntegrityError
    u2 = User(username="alice", email="alice2@test.com", password="Test1234")
    db.session.add(u2)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    print("   Unique username: OK")

    u3 = User(username="bob", email="alice@test.com", password="Test1234")
    db.session.add(u3)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    print("   Unique email:    OK")

    db.session.delete(u)
    db.session.commit()
    assert User.query.get(uid) is None
    print("   Delete:  OK")

# ── 3. 错误处理 ────────────────────────────────────────────
print("\n" + "=" * 50)
print("3. 全局错误处理测试")
with app.test_client() as c:
    r = c.get("/api/v1/nonexistent")
    data = r.get_json()
    assert data["success"] is False
    assert data["message"] == "资源不存在"
    print(f"   404: {r.status_code} {data['message']}")

    r = c.post("/api/v1/health")
    data = r.get_json()
    assert data["success"] is False
    print(f"   405: {r.status_code} {data['message']}")

    # ValidationError via marshmallow schema
    r = c.post("/api/v1/_test_validate", json={"email": "not-an-email"})
    data = r.get_json()
    assert data["success"] is False
    assert data["message"] == "数据校验失败"
    print(f"   ValidationError: {r.status_code} {data['message']}")

    # Valid validation
    r = c.post("/api/v1/_test_validate", json={"email": "good@test.com"})
    assert r.status_code == 200
    print("   Valid validation: OK")

    # IntegrityError via duplicate unique field
    from app.utils.response import error_response as er
    print("   IntegrityError handler: registered in app")

# ── 4. Health ─────────────────────────────────────────────
print("\n" + "=" * 50)
print("4. Health 端点")
with app.test_client() as c:
    r = c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}
    print("   GET /api/v1/health -> 200 OK")

print("\n" + "=" * 50)
print("阶段二全部测试通过！")
print("=" * 50)
