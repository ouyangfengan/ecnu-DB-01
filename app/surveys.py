from fastapi import APIRouter, Depends, Query, Request

from app.auth import AuthenticatedRoute, require_user
from app.errors import success
from app.question_bank_schemas import BankImport
from app.question_banks_service import QuestionBanksService
from app.question_links_service import QuestionLinksService
from app.question_resource_schemas import (
    DeriveAndSwitch, LinkExisting, RequiredSetting, SaveAndLink, SaveQuestion,
    VersionImport, VersionSwitch,
)
from app.question_switch_service import QuestionSwitchService
from app.survey_schemas import DeadlineInput, QuestionInput, QuestionPatch, SurveyCreate
from app.survey_service import SurveyService


router = APIRouter(prefix="/surveys", tags=["问卷管理"], route_class=AuthenticatedRoute)


@router.post("")
def create_survey(data: SurveyCreate, request: Request, user_id=Depends(require_user)):
    return success(SurveyService(request).create(data, user_id))


@router.get("")
def list_surveys(
    request: Request, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(SurveyService(request).list_owned(user_id, page, page_size))


@router.get("/access/{access_token}")
def access_survey(access_token: str, request: Request, user_id=Depends(require_user)):
    return success(SurveyService(request).detail(user_id, access_token=access_token))


@router.get("/{form_id}")
def survey_detail(form_id: str, request: Request, user_id=Depends(require_user)):
    return success(SurveyService(request).detail(user_id, form_id=form_id))


@router.get("/{form_id}/responses")
def survey_responses(
    form_id: str, request: Request, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(SurveyService(request).responses(form_id, user_id, page, page_size))


@router.post("/{form_id}/questions")
def add_question(
    form_id: str, data: QuestionInput, request: Request, user_id=Depends(require_user),
):
    return success(SurveyService(request).add_question(form_id, user_id, data))


@router.post("/{form_id}/questions/from-version")
def import_version(
    form_id: str, data: VersionImport,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionLinksService(request).import_version(form_id, data, user_id))


@router.post("/{form_id}/questions/from-bank")
def import_bank_member(
    form_id: str, data: BankImport, request: Request, user_id=Depends(require_user),
):
    return success(QuestionBanksService(request).import_member(form_id, data, user_id))


@router.patch("/{form_id}/questions/{question_id}")
def edit_question(
    form_id: str, question_id: str, data: QuestionPatch,
    request: Request, user_id=Depends(require_user),
):
    return success(SurveyService(request).edit_question(form_id, question_id, user_id, data))


@router.patch("/{form_id}/questions/{question_id}/required")
def set_question_required(
    form_id: str, question_id: str, data: RequiredSetting,
    request: Request, user_id=Depends(require_user),
):
    return success(SurveyService(request).set_question_required(
        form_id, question_id, user_id, data.required
    ))


@router.post("/{form_id}/questions/{question_id}/save")
def save_question(
    form_id: str, question_id: str, data: SaveQuestion,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionLinksService(request).save(
        form_id, question_id, data, user_id
    ))


@router.post("/{form_id}/questions/{question_id}/save-and-link")
def save_and_link_question(
    form_id: str, question_id: str, data: SaveAndLink,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionLinksService(request).save(
        form_id, question_id, data, user_id, with_link=True
    ))


@router.post("/{form_id}/questions/{question_id}/link")
def link_question(
    form_id: str, question_id: str, data: LinkExisting,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionLinksService(request).link(form_id, question_id, data, user_id))


@router.get("/{form_id}/questions/{question_id}/source")
def question_source(
    form_id: str, question_id: str, request: Request, user_id=Depends(require_user),
):
    return {
        "code": 0, "msg": "ok",
        "data": QuestionLinksService(request).source(form_id, question_id, user_id),
    }


@router.post("/{form_id}/questions/{question_id}/switch-version")
def switch_question_version(
    form_id: str, question_id: str, data: VersionSwitch,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionSwitchService(request).switch(
        form_id, question_id, data, user_id
    ))


@router.post("/{form_id}/questions/{question_id}/derive-and-switch")
def derive_and_switch_question(
    form_id: str, question_id: str, data: DeriveAndSwitch,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionSwitchService(request).switch(
        form_id, question_id, data, user_id, derive=True
    ))


@router.post("/{form_id}/publish")
def publish_survey(form_id: str, request: Request, user_id=Depends(require_user)):
    return success(SurveyService(request).publish(form_id, user_id))


@router.put("/{form_id}/deadline")
def set_deadline(
    form_id: str, data: DeadlineInput, request: Request, user_id=Depends(require_user),
):
    return success(SurveyService(request).set_deadline(form_id, user_id, data.deadline))


@router.post("/{form_id}/close")
def close_survey(form_id: str, request: Request, user_id=Depends(require_user)):
    return success(SurveyService(request).close(form_id, user_id))
