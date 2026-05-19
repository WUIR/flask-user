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
    """获取当前用户信息
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: 返回用户详情（不含 password_hash）
      401:
        description: 未提供 Token 或 Token 无效
      404:
        description: 用户不存在
    """
    user_id = int(get_jwt_identity())
    try:
        user = user_service.get_user_by_id(user_id)
    except ValueError as e:
        return error_response(str(e), status_code=404)
    return success_response(user.to_dict())


@api_bp.route("/users/me", methods=["PUT"])
@jwt_required()
def update_my_profile():
    """更新当前用户信息
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            nickname:
              type: string
              example: Alice
              maxLength: 80
            avatar_url:
              type: string
              format: url
              example: https://example.com/avatar.jpg
            phone:
              type: string
              example: "13800138000"
              maxLength: 20
    responses:
      200:
        description: 个人信息已更新
      401:
        description: 未认证
      422:
        description: 数据校验失败
    """
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
    """修改密码
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [old_password, new_password]
          properties:
            old_password:
              type: string
              example: OldPass123
            new_password:
              type: string
              example: NewPass456
              description: 至少8位，包含字母和数字
    responses:
      200:
        description: 密码已修改
      400:
        description: 旧密码不正确
      401:
        description: 未认证
      422:
        description: 新密码强度不足
    """
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
    """注销当前账户
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: 账户已注销
      401:
        description: 未认证
    """
    user_id = int(get_jwt_identity())
    user = user_service.get_user_by_id(user_id)
    user_service.delete_user(user)
    return success_response(message="账户已注销")


# ── Admin endpoints ────────────────────────────────────────────

@api_bp.route("/users", methods=["GET"])
@admin_required
def list_all_users():
    """管理员：用户列表（分页/搜索/排序）
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 20
      - in: query
        name: search
        type: string
        description: 按用户名/邮箱/昵称搜索
      - in: query
        name: sort
        type: string
        default: created_at
        description: 排序字段
    responses:
      200:
        description: 返回分页用户列表
      401:
        description: 未认证
      403:
        description: 非管理员
    """
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
    """管理员：查看指定用户
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: 用户 ID
    responses:
      200:
        description: 返回用户详情
      401:
        description: 未认证
      403:
        description: 非管理员
      404:
        description: 用户不存在
    """
    try:
        user = user_service.get_user_by_id(user_id)
    except ValueError as e:
        return error_response(str(e), status_code=404)
    return success_response(user.to_dict())


@api_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    """管理员：更新用户信息
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            nickname:
              type: string
            role:
              type: string
              enum: [user, admin]
            is_active:
              type: boolean
            is_verified:
              type: boolean
    responses:
      200:
        description: 用户信息已更新
      401:
        description: 未认证
      403:
        description: 非管理员
      404:
        description: 用户不存在
      422:
        description: 数据校验失败
    """
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
    """管理员：删除用户
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: 用户已删除
      401:
        description: 未认证
      403:
        description: 非管理员
      404:
        description: 用户不存在
    """
    try:
        user_service.admin_delete_user(user_id)
    except ValueError as e:
        return error_response(str(e), status_code=404)
    return success_response(message="用户已删除")
