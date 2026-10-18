from typing import Any

from bson import ObjectId
from pydantic import Field, field_validator

from app.survey_schemas import StrictInput, invalid


class AnswerInput(StrictInput):
    question_id: str
    value: Any = None

    @field_validator("question_id")
    @classmethod
    def valid_question_id(cls, value):
        if not ObjectId.is_valid(value):
            invalid("答案中的 question_id 格式无效")
        return str(ObjectId(value))


class ProgressInput(StrictInput):
    answers: list[AnswerInput] = Field(default_factory=list)


class SubmissionInput(ProgressInput):
    request_id: str = Field(
        alias="requestId", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )
