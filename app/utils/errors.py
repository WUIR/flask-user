"""全局异常处理。"""

from flask import jsonify
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"success": False, "message": "请求参数错误", "data": None, "errors": str(error)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"success": False, "message": "未授权", "data": None, "errors": str(error)}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"success": False, "message": "权限不足", "data": None, "errors": str(error)}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "message": "资源不存在", "data": None, "errors": str(error)}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"success": False, "message": "请求方法不允许", "data": None, "errors": str(error)}), 405

    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({"success": False, "message": "请求无法处理", "data": None, "errors": str(error)}), 422

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "message": "服务器内部错误", "data": None, "errors": str(error)}), 500

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({"success": False, "message": "数据校验失败", "data": None, "errors": error.messages}), 422

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        return jsonify({"success": False, "message": "数据冲突", "data": None, "errors": str(error.orig)}), 409

    @app.errorhandler(NoAuthorizationError)
    def handle_no_auth(error):
        return jsonify({"success": False, "message": "缺少认证信息", "data": None, "errors": str(error)}), 401

    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(error):
        return jsonify({"success": False, "message": "Token 已过期", "data": None, "errors": str(error)}), 401

    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token(error):
        return jsonify({"success": False, "message": "无效的 Token", "data": None, "errors": str(error)}), 401
