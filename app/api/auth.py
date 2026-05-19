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
    identity = get_jwt_identity()
    additional = {"role": get_jwt().get("role", "user")}
    new_access = create_access_token(identity=identity, additional_claims=additional)
    return success_response({"access_token": new_access}, "Token 已刷新")


@api_bp.route("/auth/logout", methods=["POST"])
@jwt_required(verify_type=False)
def logout():
    return success_response(message="已登出")
