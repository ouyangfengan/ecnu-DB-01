from pydantic import field_validator, model_validator

from app.question_resource_schemas import VersionRestore, VersionSwitch
from app.survey_schemas import invalid


def bank_name(value):
    if not isinstance(value, str):
        invalid("题库名称必须为字符串")
    value = value.strip()
    if not 1 <= len(value) <= 100:
        invalid("题库名称裁剪后长度应为 1-100 个字符")
    valid_text(value)
    return value


def bank_description(value):
    if not isinstance(value, str) or len(value) > 1000:
        invalid("题库说明必须为不超过 1000 字符的字符串")
    valid_text(value)
    return value


def valid_text(value):
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        invalid("题库文本包含无效字符")


class BankCreate(VersionRestore):
    name: str
    description: str = ""

    _name = field_validator("name", mode="before")(bank_name)
    _description = field_validator("description", mode="before")(bank_description)


class BankPatch(VersionRestore):
    name: str | None = None
    description: str | None = None

    _name = field_validator("name", mode="before")(bank_name)
    _description = field_validator("description", mode="before")(bank_description)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set.intersection({"name", "description"}):
            invalid("至少提供名称或说明中的一个字段")
        return self


class BankMemberAdd(VersionRestore):
    version_id: str


class BankMemberSwitch(VersionSwitch):
    pass


class BankImport(VersionRestore):
    bank_id: str
    member_id: str
    expected_member_version_id: str
    required: bool
