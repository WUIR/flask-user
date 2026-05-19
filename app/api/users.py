"""Users API: profile management & admin CRUD."""
from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.api import api_bp
from app.schemas.user import AdminUpdateUserSchema, ChangePasswordSchema, UpdateProfileSchema
from app.services import user_service
from app.utils.response import error_response, success_response


# ── Helper: admin-only decorator ───────────────────────────────

def admin_required(fn):
    """Decorator that rejects non-admin users."""
    from functools import wraps

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return error_response("权限不足", status_code=403)
        return fn(*args, **kwargs)
    return wrapper


# ── Current user (self) endpoints ─────────────────────────────

@api_bp.route("/users/me", methods=["GET"])
@jwt_required()
def get_my_profile():
    user_id = int(get_jwt_identity())
    try:
        user = user_service.get_user_by_id(user_id)
    except ValueError as e:
        return error_response(str(e), status_code=404)
    return success_response(user.to_dict())


@api_bp.route("/users/me", methods=["PUT"])
@jwt_required()
def update_my_profile():
    schema = UpdateProfileSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return error_response("数据校验失败", e.messages, 422)

    user_id = int(get_jwt_identity())
    user = user_service.get_user_by_id(user_id)
    user = user_service.update_profile(user, data)
    return success_response(user.to_dict(), "个人信息已更新")


@api_bp.route("/users/me/password", methods=["PUT"])
@jwt_required()
def change_my_password():
    schema = ChangePasswordSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return error_response("数据校验失败", e.messages, 422)

    user_id = int(get_jwt_identity())
    user = user_service.get_user_by_id(user_id)
    try:
        user_service.change_password(user, data["old_password"], data["new_password"])
    except ValueError as e:
        return error_response(str(e), status_code=400)
    return success_response(message="密码已修改")


@api_bp.route("/users/me", methods=["DELETE"])
@jwt_required()
def delete_my_account():
    user_id = int(get_jwt_identity())
    user = user_service.get_user_by_id(user_id)
    user_service.delete_user(user)
    return success_response(message="账户已注销")


# ── Admin endpoints ────────────────────────────────────────────

@api_bp.route("/users", methods=["GET"])
@admin_required
def list_all_users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    sort = request.args.get("sort", "created_at", type=str)

    users, total = user_service.list_users(page=page, per_page=per_page, search=search, sort=sort)
    return success_response({
        "items": [u.to_dict() for u in users],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    try:
        user = user_service.get_user_by_id(user_id)
    except ValueError as e:
        return error_response(str(e), status_code=404)
    return success_response(user.to_dict())


@api_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    schema = AdminUpdateUserSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return error_response("数据校验失败", e.messages, 422)

    try:
        user = user_service.admin_update_user(user_id, data)
    except ValueError as e:
        return error_response(str(e), status_code=404)
    return success_response(user.to_dict(), "用户信息已更新")


@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    try:
        user_service.admin_delete_user(user_id)
    except ValueError as e:
        return error_response(str(e), status_code=404)
    return success_response(message="用户已删除")
