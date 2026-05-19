"""Application factory with Swagger docs."""
import os
from typing import Optional

from flask import Flask
from flasgger import Swagger

from app.extensions import cors, db, jwt, limiter, migrate, talisman
from app.settings import config_map


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

    # Swagger / OpenAPI docs
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/api/v1/apispec.json",
            }
        ],
        "static_url_path": "/api/v1/flasgger_static",
        "specs_route": "/api/v1/docs/",
    }
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Flask 用户系统 API",
            "description": "用户注册、登录、JWT 鉴权、管理员 CRUD 操作",
            "version": "1.0.0",
            "contact": {"email": "admin@example.com"},
        },
        "host": os.getenv("SWAGGER_HOST", "162.14.68.23:8000"),
        "basePath": "/api/v1",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Bearer Token，格式: Bearer &lt;token&gt;",
            }
        },
    }
    Swagger(app, config=swagger_config, template=swagger_template)

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # Register error handlers
    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    # Health check
    @app.route("/api/v1/health")
    def health():
        """Health check endpoint.
        ---
        tags:
          - System
        responses:
          200:
            description: Service is healthy
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
        """
        return {"status": "ok"}

    return app
