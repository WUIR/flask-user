"""统一 JSON 响应格式。"""

from typing import Any, Optional

from flask import jsonify


def success_response(data: Any = None, message: str = "操作成功", status_code: int = 200):
    return jsonify({"success": True, "message": message, "data": data, "errors": None}), status_code


def error_response(message: str = "操作失败", errors: Optional[Any] = None, status_code: int = 400):
    return jsonify({"success": False, "message": message, "data": None, "errors": errors}), status_code
