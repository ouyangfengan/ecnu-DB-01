from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


def invalid(message):
    raise PydanticCustomError("parameters", message)


def clean_title(value):
    if not isinstance(value, str) or not value.strip():
        invalid("标题必须是非空字符串")
    return value.strip()


class StrictInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class SurveyCreate(StrictInput):
    title: str = Field(max_length=200)
    description: str = ""
    allow_anonymous: bool = False
    allow_multiple_submissions: bool = False

    _title = field_validator("title", mode="before")(clean_title)


class DeadlineInput(StrictInput):
    deadline: datetime | None

    @field_validator("deadline", mode="before")
    @classmethod
    def parse_deadline(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            invalid("截止时间必须是带时区的 ISO 8601 字符串或 null")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            invalid("截止时间格式无效")
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            invalid("截止时间必须包含时区")
        parsed = parsed.astimezone(timezone.utc)
        # MongoDB Date 精度为毫秒，在校验未来时间前统一精度。
        return parsed.replace(microsecond=parsed.microsecond // 1000 * 1000)


class OptionInput(StrictInput):
    option_id: str | None = None
    text: str

    _text = field_validator("text", mode="before")(clean_title)


class JumpRule(StrictInput):
    condition: dict[str, Any]
    target: str


QuestionType = Literal["single", "multiple", "text", "number"]


class QuestionInput(StrictInput):
    title: str
    type: QuestionType
    options: list[OptionInput] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    jump_rules: list[JumpRule] = Field(default_factory=list)

    _title = field_validator("title", mode="before")(clean_title)


class QuestionPatch(StrictInput):
    title: str | None = None
    type: QuestionType | None = None
    options: list[OptionInput] | None = None
    validation: dict[str, Any] | None = None
    jump_rules: list[JumpRule] | None = None

    @model_validator(mode="after")
    def nonempty_patch(self):
        if not self.model_fields_set:
            invalid("至少提供一个要修改的题目字段")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            invalid("题目字段不能为 null；清空列表请使用 []")
        return self
