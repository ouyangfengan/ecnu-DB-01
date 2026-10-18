from fastapi import APIRouter, Depends, Query, Request

from app.auth import AuthenticatedRoute, require_user
from app.errors import success
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


@router.post("/{form_id}/questions")
def add_question(
    form_id: str, data: QuestionInput, request: Request, user_id=Depends(require_user),
):
    return success(SurveyService(request).add_question(form_id, user_id, data))


@router.patch("/{form_id}/questions/{question_id}")
def edit_question(
    form_id: str, question_id: str, data: QuestionPatch,
    request: Request, user_id=Depends(require_user),
):
    return success(SurveyService(request).edit_question(form_id, question_id, user_id, data))


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
