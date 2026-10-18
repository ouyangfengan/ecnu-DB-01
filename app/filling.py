from fastapi import APIRouter, Depends, Request

from app.auth import AuthenticatedRoute, require_user
from app.errors import success
from app.filling_schemas import ProgressInput, SubmissionInput
from app.filling_service import FillingService


router = APIRouter(
    prefix="/surveys/access", tags=["问卷填写"], route_class=AuthenticatedRoute
)


@router.post("/{access_token}/progress")
def filling_progress(
    access_token: str, data: ProgressInput, request: Request, user_id=Depends(require_user),
):
    return success(FillingService(request).progress(
        access_token, user_id, [answer.model_dump() for answer in data.answers]
    ))


@router.post("/{access_token}/submit")
def submit_answers(
    access_token: str, data: SubmissionInput, request: Request, user_id=Depends(require_user),
):
    return success(FillingService(request).submit(
        access_token, user_id, data.request_id,
        [answer.model_dump() for answer in data.answers],
    ))
