from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_core import PydanticCustomError

from app.config import Settings


POLICY = Settings()


class LoginInput(BaseModel):
    model_config = ConfigDict(strict=True)

    username: str
    password: str

    @model_validator(mode="before")
    @classmethod
    def validate_credentials(cls, data):
        if not isinstance(data, dict):
            raise PydanticCustomError("parameters", "请求体必须是 JSON 对象")
        values = [data.get("username"), data.get("password")]
        if any(v is None or (isinstance(v, str) and not v.strip()) for v in values):
            raise PydanticCustomError("parameters", "用户名/密码不能为空")
        if any(not isinstance(v, str) for v in values):
            raise PydanticCustomError("parameters", "用户名/密码必须为字符串")
        username = data["username"].strip()
        if len(username) > POLICY.username_max_length:
            raise PydanticCustomError(
                "parameters", f"用户名长度应为 1–{POLICY.username_max_length} 个字符"
            )
        # 用户名规范化，密码保留原始空格，避免改变用户设置的密码。
        return {**data, "username": username}


class RegisterInput(LoginInput):
    @model_validator(mode="after")
    def validate_password_length(self):
        if not POLICY.password_min_length <= len(self.password) <= POLICY.password_max_length:
            raise PydanticCustomError(
                "parameters",
                f"密码长度应为 {POLICY.password_min_length}-{POLICY.password_max_length} 个字符",
            )
        return self
