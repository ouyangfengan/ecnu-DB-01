from fastapi import APIRouter, Depends, Query, Request

from app.auth import AuthenticatedRoute, require_user
from app.errors import success
from app.statistics_service import StatisticsService


router = APIRouter(prefix="/surveys", tags=["统计结果"], route_class=AuthenticatedRoute)
MAX_PAGE = (2**63 - 1) // 100


@router.get("/{form_id}/statistics")
def survey_statistics(form_id: str, request: Request, user_id=Depends(require_user)):
    return success(StatisticsService(request).whole_form(form_id, user_id))


@router.get("/{form_id}/questions/{question_id}/statistics")
def question_statistics(
    form_id: str, question_id: str, request: Request,
    page: int = Query(1, ge=1, le=MAX_PAGE),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(StatisticsService(request).one_question(
        form_id, question_id, user_id, page, page_size
    ))
