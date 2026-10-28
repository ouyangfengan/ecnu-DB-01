from fastapi import APIRouter, Depends, Query, Request

from app.auth import AuthenticatedRoute, require_user
from app.errors import success
from app.question_bank_schemas import BankCreate, BankMemberAdd, BankMemberSwitch, BankPatch
from app.question_banks_service import QuestionBanksService
from app.question_resource_schemas import VersionRestore


router = APIRouter(
    prefix="/question-banks", tags=["个人题库"], route_class=AuthenticatedRoute
)


@router.post("")
def create(data: BankCreate, request: Request, user_id=Depends(require_user)):
    return success(QuestionBanksService(request).create(data, user_id))


@router.get("")
def list_banks(
    request: Request, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(QuestionBanksService(request).list_banks(user_id, page, page_size))


@router.get("/{bank_id}")
def detail(bank_id: str, request: Request, user_id=Depends(require_user)):
    return success(QuestionBanksService(request).detail(bank_id, user_id))


@router.patch("/{bank_id}")
def patch(bank_id: str, data: BankPatch, request: Request, user_id=Depends(require_user)):
    return success(QuestionBanksService(request).patch(bank_id, data, user_id))


@router.get("/{bank_id}/members")
def list_members(
    bank_id: str, request: Request, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), user_id=Depends(require_user),
):
    return success(QuestionBanksService(request).list_members(bank_id, user_id, page, page_size))


@router.post("/{bank_id}/members")
def add_member(
    bank_id: str, data: BankMemberAdd, request: Request, user_id=Depends(require_user),
):
    return success(QuestionBanksService(request).add_member(bank_id, data, user_id))


@router.post("/{bank_id}/members/{member_id}/switch-version")
def switch_member(
    bank_id: str, member_id: str, data: BankMemberSwitch,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionBanksService(request).switch_member(bank_id, member_id, data, user_id))


@router.post("/{bank_id}/members/{member_id}/remove")
def remove_member(
    bank_id: str, member_id: str, data: VersionRestore,
    request: Request, user_id=Depends(require_user),
):
    return success(QuestionBanksService(request).remove_member(bank_id, member_id, data, user_id))


@router.post("/{bank_id}/delete")
def delete(bank_id: str, data: VersionRestore, request: Request, user_id=Depends(require_user)):
    return success(QuestionBanksService(request).delete(bank_id, data, user_id))
