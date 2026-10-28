from typing import Any, Literal

from pydantic import Field, field_validator

from app.survey_schemas import OptionInput, QuestionType, StrictInput, clean_title, invalid


class VersionContentInput(StrictInput):
    title: str
    type: QuestionType
    options: list[OptionInput] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", mode="before")
    @classmethod
    def valid_title(cls, value):
        title = clean_title(value)
        try:
            title.encode("utf-8")
        except UnicodeEncodeError:
            invalid("标题包含无效字符")
        return title

    @field_validator("validation")
    @classmethod
    def version_only_validation(cls, value):
        if "required" in value:
            invalid("必答属于卷内配置，不能保存在题目版本中")
        return value


class ResourceCreate(VersionContentInput):
    request_id: str = Field(
        alias="requestId", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )


class VersionDerive(ResourceCreate):
    parent_version_id: str


class VersionRestore(StrictInput):
    request_id: str = Field(
        alias="requestId", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )


class SaveQuestion(VersionRestore):
    pass


class SaveAndLink(VersionRestore):
    include_historical_answers: Literal[True] = Field(alias="includeHistoricalAnswers")


class LinkExisting(StrictInput):
    version_id: str
    include_historical_answers: Literal[True] = Field(alias="includeHistoricalAnswers")


class RequiredSetting(StrictInput):
    required: bool


class VersionImport(VersionRestore):
    version_id: str
    required: bool


class VersionSwitch(VersionRestore):
    expected_version_id: str
    version_id: str


class DeriveAndSwitch(VersionDerive):
    expected_version_id: str


class ShareGrant(VersionRestore):
    recipient_username: str

    @field_validator("recipient_username", mode="before")
    @classmethod
    def valid_recipient(cls, value):
        if not isinstance(value, str):
            invalid("接收者用户名必须为字符串")
        value = value.strip()
        if not value or len(value) > 50:
            invalid("接收者用户名长度应为 1-50 个字符")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            invalid("接收者用户名包含无效字符")
        return value
