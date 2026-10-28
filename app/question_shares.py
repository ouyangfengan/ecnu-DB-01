from fastapi import APIRouter, Depends, Query, Request

from app.auth import AuthenticatedRoute, require_user
from app.errors import success
from app.question_resource_schemas import ResourceCreate, ShareGrant, VersionRestore
from app.question_shares_service import QuestionSharesService


router = APIRouter(tags=["题目共享"], route_class=AuthenticatedRoute)
version_path = "/question-resources/{resource_id}/versions/{version_id}"


@router.post(version_path + "/shares")
def grant(
    resource_id: str, version_id: str, data: ShareGrant,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionSharesService(request).grant(
        resource_id, version_id, data, user_id
    ))


@router.get(version_path + "/shares")
def list_sent(
    resource_id: str, version_id: str, request: Request,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user_id=Depends(require_user),
):
    return success(QuestionSharesService(request).list_sent(
        resource_id, version_id, user_id, page, page_size
    ))


@router.post(version_path + "/shares/{share_id}/revoke")
def revoke(
    resource_id: str, version_id: str, share_id: str, data: VersionRestore,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionSharesService(request).revoke(
        resource_id, version_id, share_id, data, user_id
    ))


@router.get("/question-shares/received")
def list_received(
    request: Request, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(QuestionSharesService(request).list_received(
        user_id, page, page_size
    ))


@router.post(version_path + "/fork")
def fork(
    resource_id: str, version_id: str, data: ResourceCreate,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionSharesService(request).fork(
        resource_id, version_id, data, user_id
    ))
