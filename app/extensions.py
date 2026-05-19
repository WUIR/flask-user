"""Extensions & JWT callbacks."""
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()


# ── JWT callbacks ─────────────────────────────────────────────

@jwt.user_identity_loader
def user_identity_lookup(identity):
    return str(identity)


@jwt.additional_claims_loader
def add_claims_to_access_token(identity):
    return {"role": "user"}
