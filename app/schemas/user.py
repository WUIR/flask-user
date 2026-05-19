"""Marshmallow schemas for request validation & deserialization."""
import re

from marshmallow import Schema, fields, validates
from marshmallow.validate import Length, Regexp, ValidationError

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$")
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,80}$")


class RegisterSchema(Schema):
    username = fields.String(required=True, validate=[
        Length(min=3, max=80),
        Regexp(USERNAME_PATTERN, error="用户名只能包含字母、数字和下划线"),
    ])
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=[
        Length(min=8, error="密码至少 8 位"),
    ])

    @validates("password")
    def validate_password(self, value):
        if not PASSWORD_PATTERN.match(value):
            raise ValidationError("密码必须包含字母和数字")


class LoginSchema(Schema):
    login = fields.String(required=True, error="请输入用户名或邮箱")
    password = fields.String(required=True, error="请输入密码")


class UpdateProfileSchema(Schema):
    nickname = fields.String(validate=Length(max=80))
    avatar_url = fields.URL()
    phone = fields.String(validate=Length(max=20))


class ChangePasswordSchema(Schema):
    old_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=[
        Length(min=8, error="新密码至少 8 位"),
    ])

    @validates("new_password")
    def validate_new_password(self, value):
        if not PASSWORD_PATTERN.match(value):
            raise ValidationError("新密码必须包含字母和数字")


class AdminUpdateUserSchema(Schema):
    nickname = fields.String(validate=Length(max=80))
    role = fields.String(validate=Regexp(r"^(user|admin)$"))
    is_active = fields.Boolean()
    is_verified = fields.Boolean()
