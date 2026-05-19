"""Business logic layer for user operations.

All methods are stateless and do not depend on Flask request context,
making them easy to unit test.
"""
from datetime import datetime

from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import or_

from app.extensions import db
from app.models.user import User


def register_user(data: dict) -> User:
    """Create a new user. Raises ValueError on duplicates."""
    if User.query.filter_by(username=data["username"]).first():
        raise ValueError("用户名已存在")
    if User.query.filter_by(email=data["email"]).first():
        raise ValueError("邮箱已被注册")

    user = User(
        username=data["username"],
        email=data["email"],
    )
    user.password = data["password"]
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(login: str, password: str) -> User:
    """Validate credentials. Raises ValueError on failure."""
    user = User.query.filter(
        or_(User.username == login, User.email == login)
    ).first()

    if user is None:
        raise ValueError("用户名或邮箱不存在")
    if not user.is_active:
        raise ValueError("账户已被禁用")
    if not user.check_password(password):
        raise ValueError("密码错误")

    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return user


def get_user_by_id(user_id: int) -> User:
    user = User.query.get(user_id)
    if user is None:
        raise ValueError("用户不存在")
    return user


def update_profile(user: User, data: dict) -> User:
    """Update mutable profile fields."""
    for field in ("nickname", "avatar_url", "phone"):
        if field in data:
            setattr(user, field, data[field])
    db.session.commit()
    return user


def change_password(user: User, old_password: str, new_password: str) -> None:
    if not user.check_password(old_password):
        raise ValueError("旧密码不正确")
    user.password = new_password
    db.session.commit()


def delete_user(user: User) -> None:
    db.session.delete(user)
    db.session.commit()


# ── Token helpers ──────────────────────────────────────────────

def build_tokens(user: User) -> dict:
    """Generate access & refresh tokens for a user."""
    identity = str(user.id)
    additional = {"role": user.role}
    return {
        "access_token": create_access_token(identity=identity, additional_claims=additional),
        "refresh_token": create_refresh_token(identity=identity, additional_claims=additional),
    }


# ── Admin helpers ──────────────────────────────────────────────

def list_users(page: int = 1, per_page: int = 20, search: str = "", sort: str = "created_at") -> tuple:
    """Return (paginated query, total_count)."""
    query = User.query
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.nickname.ilike(f"%{search}%"),
            )
        )
    sort_column = getattr(User, sort, User.created_at)
    query = query.order_by(sort_column.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination.items, pagination.total


def admin_update_user(user_id: int, data: dict) -> User:
    user = get_user_by_id(user_id)
    for field in ("nickname", "role", "is_active", "is_verified"):
        if field in data:
            setattr(user, field, data[field])
    db.session.commit()
    return user


def admin_delete_user(user_id: int) -> None:
    user = get_user_by_id(user_id)
    db.session.delete(user)
    db.session.commit()
