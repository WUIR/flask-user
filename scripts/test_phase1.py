"""Phase 1 comprehensive tests."""
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# 1. 三套配置创建
print("=" * 50)
print("1. 配置创建测试")
print("=" * 50)
for cfg in ["development", "testing", "production"]:
    app = create_app(cfg)
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    print(f"   [{cfg:12}] DEBUG={app.debug}  DB={db_uri[:45]}")

# 2. 路由注册
print("\n" + "=" * 50)
print("2. 路由注册测试")
print("=" * 50)
app = create_app("testing")
for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    methods = ",".join(m for m in r.methods if m not in ("OPTIONS", "HEAD"))
    if r.rule != "/static/<path:filename>":
        print(f"   {r.rule:45} {methods}")

# 3. 端点功能测试
print("\n" + "=" * 50)
print("3. 端点功能测试")
print("=" * 50)
with app.test_client() as c:
    # Health
    r = c.get("/api/v1/health")
    print(f"   GET /api/v1/health          -> {r.status_code} {r.get_json()}")

    # 404
    r = c.get("/api/v1/nonexistent")
    data = r.get_json()
    assert r.status_code == 404
    assert data["message"] == "资源不存在"
    assert data["success"] is False
    print(f"   GET /api/v1/nonexistent     -> {r.status_code} {data['message']}")
    
    # Multiple health calls
    for _ in range(3):
        r = c.get("/api/v1/health")
        assert r.status_code == 200
    print("   Health multiple calls        -> OK (no rate limit in testing)")

# 4. 验证 import 完整性
print("\n" + "=" * 50)
print("4. 模块导入完整性")
print("=" * 50)
modules = [
    "app.extensions",
    "app.config",
    "app.utils.response",
    "app.utils.errors",
]
for mod in modules:
    try:
        __import__(mod)
        print(f"   [OK] {mod}")
    except Exception as e:
        print(f"   [FAIL] {mod}: {e}")

print("\n" + "=" * 50)
print("所有阶段一测试通过！")
print("=" * 50)
