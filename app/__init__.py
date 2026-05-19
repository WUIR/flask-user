import os
from typing import Optional

from flask import Flask

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

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # Register error handlers
    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    # Health check
    @app.route("/api/v1/health")
    def health():
        return {"status": "ok"}

    return app
