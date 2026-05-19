"""Auth API: register, login, refresh, logout."""
from flask import request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import ValidationError

from app.api import api_bp
from app.extensions import limiter
from app.schemas.user import LoginSchema, RegisterSchema
from app.services import user_service
from app.utils.response import error_response, success_response


@api_bp.route("/auth/register", methods=["POST"])
@limiter.limit("10/minute")
def register():
    """用户注册
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, email, password]
          properties:
            username:
              type: string
              example: alice
              description: 3-80位字母/数字/下划线
            email:
              type: string
              format: email
              example: alice@example.com
            password:
              type: string
              example: Pass1234
              description: 至少8位，包含字母和数字
    responses:
      201:
        description: 注册成功，返回用户信息 + JWT
      409:
        description: 用户名或邮箱已存在
      422:
        description: 数据校验失败
    """
    schema = RegisterSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return error_response("数据校验失败", e.messages, 422)

    try:
        user = user_service.register_user(data)
    except ValueError as e:
        return error_response(str(e), status_code=409)

    tokens = user_service.build_tokens(user)
    return success_response({
        "user": user.to_dict(),
        **tokens,
    }, "注册成功", 201)


@api_bp.route("/auth/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    """用户登录
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [login, password]
          properties:
            login:
              type: string
              example: alice
              description: 用户名或邮箱
            password:
              type: string
              example: Pass1234
    responses:
      200:
        description: 登录成功，返回 JWT
      401:
        description: 用户名/密码错误 或 账户被禁用
      422:
        description: 数据校验失败
    """
    schema = LoginSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return error_response("数据校验失败", e.messages, 422)

    try:
        user = user_service.authenticate(data["login"], data["password"])
    except ValueError as e:
        return error_response(str(e), status_code=401)

    tokens = user_service.build_tokens(user)
    return success_response({
        "user": user.to_dict(),
        **tokens,
    }, "登录成功")


@api_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """刷新 Access Token
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Refresh Token，格式: Bearer &lt;token&gt;
    responses:
      200:
        description: 返回新的 access_token
      401:
        description: 未提供 Token
      422:
        description: 使用了 Access Token 而非 Refresh Token
    """
    identity = get_jwt_identity()
    additional = {"role": get_jwt().get("role", "user")}
    new_access = create_access_token(identity=identity, additional_claims=additional)
    return success_response({"access_token": new_access}, "Token 已刷新")


@api_bp.route("/auth/logout", methods=["POST"])
@jwt_required(verify_type=False)
def logout():
    """用户登出
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: 登出成功
      401:
        description: 未提供 Token
    """
    return success_response(message="已登出")
