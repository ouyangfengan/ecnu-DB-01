from fastapi import APIRouter, Depends, Query, Request

from app.auth import AuthenticatedRoute, require_user
from app.errors import success
from app.question_resource_schemas import ResourceCreate, VersionDerive, VersionRestore
from app.question_resource_service import QuestionResourceService
from app.question_statistics_service import QuestionStatisticsService
from app.question_usage_service import QuestionUsageService


router = APIRouter(
    prefix="/question-resources", tags=["题目资源"], route_class=AuthenticatedRoute
)


@router.post("")
def create_resource(
    data: ResourceCreate, request: Request, user_id=Depends(require_user),
):
    return success(QuestionResourceService(request).create(data, user_id))


@router.get("")
def list_resources(
    request: Request, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(
        QuestionResourceService(request).list_owned(user_id, page, page_size)
    )


@router.get("/{resource_id}")
def resource_detail(
    resource_id: str, request: Request, user_id=Depends(require_user),
):
    return success(QuestionResourceService(request).detail(resource_id, user_id))


@router.get("/{resource_id}/versions/{version_id}")
def version_detail(
    resource_id: str, version_id: str, request: Request, user_id=Depends(require_user),
):
    return success(
        QuestionResourceService(request).version_detail(resource_id, version_id, user_id)
    )


@router.get("/{resource_id}/usage")
def resource_usage(
    resource_id: str, request: Request, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(QuestionUsageService(request).query(
        resource_id, user_id, page, page_size
    ))


@router.get("/{resource_id}/versions/{version_id}/usage")
def version_usage(
    resource_id: str, version_id: str, request: Request,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user_id=Depends(require_user),
):
    return success(QuestionUsageService(request).query(
        resource_id, user_id, page, page_size, version_id
    ))


@router.get("/{resource_id}/versions/{version_id}/statistics")
def version_statistics(
    resource_id: str, version_id: str, request: Request,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user_id=Depends(require_user),
):
    return success(QuestionStatisticsService(request).statistics(
        resource_id, version_id, user_id, page, page_size
    ))


@router.post("/{resource_id}/versions")
def derive_version(
    resource_id: str, data: VersionDerive,
    request: Request, user_id=Depends(require_user),
):
    return success(
        QuestionResourceService(request).derive(resource_id, data, user_id)
    )


@router.post("/{resource_id}/versions/{version_id}/restore")
def restore_version(
    resource_id: str, version_id: str, data: VersionRestore,
    request: Request, user_id=Depends(require_user),
):
    return success(
        QuestionResourceService(request).restore(resource_id, version_id, data, user_id)
    )
