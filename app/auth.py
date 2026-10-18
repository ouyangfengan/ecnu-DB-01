import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

from app.errors import APIError, success
from app.schemas import LoginInput, RegisterInput
from app.security import new_token, password_hasher, token_hash, verify_password


bearer = HTTPBearer(auto_error=False)


def renew_session(request: Request):
    session = request.state.auth_session
    now = request.app.state.clock()
    # 仅更新仍有效的同一凭证；禁止 upsert，避免退出或新登录后旧会话复活。
    request.app.state.db.Sessions.update_one(
        {
            "_id": session["_id"],
            "token_hash": session["token_hash"],
            "expires_at": {"$gt": now},
        },
        {"$max": {"expires_at": now + request.app.state.settings.session_lifetime}},
    )


class AuthenticatedRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def handler(request: Request):
            response = await original_handler(request)
            if (
                getattr(request.state, "auth_session", None)
                and not getattr(request.state, "skip_renewal", False)
                and 200 <= response.status_code < 300
                and isinstance(getattr(response, "body", None), bytes)
            ):
                try:
                    body = json.loads(response.body)
                except (ValueError, UnicodeDecodeError):
                    body = None
                if isinstance(body, dict) and body.get("code") == 0:
                    await run_in_threadpool(renew_session, request)
            return response

        return handler


def require_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    if credentials is None:
        raise APIError(4010, "请先登录", 401)
    session = request.app.state.db.Sessions.find_one(
        {
            "token_hash": token_hash(credentials.credentials),
            "expires_at": {"$gt": request.app.state.clock()},
        }
    )
    if session is None:
        raise APIError(4010, "请先登录", 401)
    request.state.auth_session = session
    return session["user_id"]


router = APIRouter(prefix="/auth", tags=["账号"], route_class=AuthenticatedRoute)


@router.post("/register")
def register(data: RegisterInput, request: Request):
    now = request.app.state.clock()
    document = {
        "username": data.username,
        "password_hash": password_hasher.hash(data.password),
        "created_at": now,
    }
    try:
        result = request.app.state.db.Users.insert_one(document)
    except DuplicateKeyError:
        raise APIError(4090, "该用户名已被注册", 409) from None
    return success({"user_id": str(result.inserted_id), "created_at": now.isoformat()})


@router.post("/login")
def login(data: LoginInput, request: Request):
    db = request.app.state.db
    user = db.Users.find_one({"username": data.username})
    encoded = user["password_hash"] if user else request.app.state.dummy_password_hash
    # 不存在的账号也执行密码哈希验证，减少通过耗时判断账号存在性的差异。
    valid = verify_password(encoded, data.password)
    if user is None or not valid:
        raise APIError(4011, "用户名或密码错误", 401)
    for _ in range(3):
        token = new_token()
        now = request.app.state.clock()
        try:
            # 单文档原子替换凭证，最后一次写入生效；不能先删除再插入。
            db.Sessions.update_one(
                {"user_id": user["_id"]},
                {
                    "$set": {
                        "token_hash": token_hash(token),
                        "created_at": now,
                        "expires_at": now + request.app.state.settings.session_lifetime,
                    }
                },
                upsert=True,
            )
        except DuplicateKeyError:
            # 首次并发登录可能竞争唯一索引，重新按用户匹配并写入。
            continue
        return success({"token": token, "username": user["username"]})
    raise APIError(5000, "服务暂不可用，请稍后重试", 503)


@router.post("/logout")
def logout(request: Request, user_id=Depends(require_user)):
    session = request.state.auth_session
    result = request.app.state.db.Sessions.delete_one(
        {
            "_id": session["_id"],
            "user_id": user_id,
            "token_hash": session["token_hash"],
            "expires_at": {"$gt": request.app.state.clock()},
        }
    )
    if result.deleted_count == 0:
        raise APIError(4010, "请先登录", 401)
    request.state.skip_renewal = True
    return success(message="退出成功")
