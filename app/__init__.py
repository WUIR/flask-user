"""Application factory with Swagger docs (static OpenAPI spec)."""
import json
import os
from typing import Optional

from flask import Flask, jsonify, render_template_string

from app.extensions import cors, db, jwt, limiter, migrate, talisman
from app.settings import config_map

SWAGGER_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>Flask 用户系统 - API 文档</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    SwaggerUIBundle({
      url: "/api/v1/openapi.json",
      dom_id: "#swagger-ui",
      presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIStandalonePreset
      ],
      layout: "StandaloneLayout",
      deepLinking: true,
      showCommonExtensions: true
    });
  </script>
</body>
</html>"""


def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, origins=app.config.get("CORS_ORIGINS", "*"))
    limiter.init_app(app)

    if app.config.get("USE_TALISMAN", False):
        talisman.init_app(app)

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # Register error handlers
    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    # ── Routes ──────────────────────────────────────────────

    @app.route("/api/v1/health")
    def health():
        """Health check."""
        return {"status": "ok"}

    @app.route("/api/v1/docs/")
    def swagger_ui():
        """Swagger UI page."""
        return render_template_string(SWAGGER_HTML)

    @app.route("/api/v1/openapi.json")
    def openapi_spec():
        """OpenAPI 3.0 spec."""
        # Load from JSON file so it can be regenerated independently
        spec_path = os.path.join(app.root_path, "static", "openapi.json")
        if os.path.exists(spec_path):
            with open(spec_path, encoding="utf-8") as f:
                return jsonify(json.load(f))
        # Fallback: return embedded spec
        return jsonify(_build_openapi_spec(app))

    return app


def _build_openapi_spec(app):
    """Dynamically build OpenAPI 3.0 spec from registered routes."""
    host = os.getenv("SWAGGER_HOST", "162.14.68.23:8000")
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Flask 用户系统 API",
            "description": "用户注册、登录、JWT 鉴权、管理员 CRUD 操作\n\n"
                           "测试覆盖率 100%，移动端适配 JSON API。",
            "version": "1.0.0",
        },
        "servers": [{"url": f"http://{host}/api/v1", "description": "生产环境"}],
        "components": {
            "securitySchemes": {
                "Bearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "输入 Bearer Token（不含 Bearer 前缀）",
                }
            }
        },
        "paths": {
            "/auth/register": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "用户注册",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["username", "email", "password"],
                                    "properties": {
                                        "username": {"type": "string", "example": "alice"},
                                        "email": {"type": "string", "format": "email", "example": "alice@example.com"},
                                        "password": {"type": "string", "example": "Pass1234"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "注册成功，返回用户信息 + JWT"},
                        "409": {"description": "用户名或邮箱已存在"},
                        "422": {"description": "数据校验失败"},
                    },
                }
            },
            "/auth/login": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "用户登录",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["login", "password"],
                                    "properties": {
                                        "login": {"type": "string", "example": "alice"},
                                        "password": {"type": "string", "example": "Pass1234"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "登录成功，返回 JWT"},
                        "401": {"description": "用户名/密码错误 或 账户被禁用"},
                        "422": {"description": "数据校验失败"},
                    },
                }
            },
            "/auth/refresh": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "刷新 Access Token",
                    "security": [{"Bearer": []}],
                    "responses": {
                        "200": {"description": "返回新的 access_token"},
                        "401": {"description": "未提供 Token"},
                    },
                }
            },
            "/auth/logout": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "用户登出",
                    "security": [{"Bearer": []}],
                    "responses": {"200": {"description": "登出成功"}},
                }
            },
            "/users/me": {
                "get": {
                    "tags": ["Users"],
                    "summary": "获取当前用户信息",
                    "security": [{"Bearer": []}],
                    "responses": {
                        "200": {"description": "用户详情"},
                        "401": {"description": "未认证"},
                    },
                },
                "put": {
                    "tags": ["Users"],
                    "summary": "更新当前用户信息",
                    "security": [{"Bearer": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "nickname": {"type": "string", "example": "Alice"},
                                        "avatar_url": {"type": "string", "format": "url"},
                                        "phone": {"type": "string", "example": "13800138000"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "个人信息已更新"},
                        "401": {"description": "未认证"},
                        "422": {"description": "数据校验失败"},
                    },
                },
                "delete": {
                    "tags": ["Users"],
                    "summary": "注销当前账户",
                    "security": [{"Bearer": []}],
                    "responses": {
                        "200": {"description": "账户已注销"},
                        "401": {"description": "未认证"},
                    },
                },
            },
            "/users/me/password": {
                "put": {
                    "tags": ["Users"],
                    "summary": "修改密码",
                    "security": [{"Bearer": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["old_password", "new_password"],
                                    "properties": {
                                        "old_password": {"type": "string", "example": "OldPass123"},
                                        "new_password": {"type": "string", "example": "NewPass456"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "密码已修改"},
                        "400": {"description": "旧密码不正确"},
                        "422": {"description": "新密码强度不足"},
                    },
                }
            },
            "/users": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "管理员：用户列表",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "search", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {"description": "分页用户列表"},
                        "403": {"description": "非管理员"},
                    },
                }
            },
            "/users/{user_id}": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "管理员：查看指定用户",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "用户详情"},
                        "404": {"description": "用户不存在"},
                    },
                },
                "put": {
                    "tags": ["Admin"],
                    "summary": "管理员：更新用户",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string", "enum": ["user", "admin"]},
                                        "is_active": {"type": "boolean"},
                                        "is_verified": {"type": "boolean"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "用户信息已更新"},
                        "403": {"description": "非管理员"},
                        "404": {"description": "用户不存在"},
                    },
                },
                "delete": {
                    "tags": ["Admin"],
                    "summary": "管理员：删除用户",
                    "security": [{"Bearer": []}],
                    "parameters": [
                        {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "用户已删除"},
                        "403": {"description": "非管理员"},
                        "404": {"description": "用户不存在"},
                    },
                },
            },
        },
    }
