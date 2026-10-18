import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from app.auth import router
from app.config import Settings
from app.database import create_indexes
from app.errors import APIError, failure
from app.filling import router as filling_router
from app.security import new_token, password_hasher, utc_now
from app.statistics import router as statistics_router
from app.surveys import router as survey_router


logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, clock=utc_now):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application):
        client = MongoClient(
            settings.mongo_uri,
            tz_aware=True,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        try:
            await run_in_threadpool(client.admin.command, "ping")
            db = client[settings.mongo_database]
            await run_in_threadpool(create_indexes, db)
            application.state.db = db
            application.state.dummy_password_hash = await run_in_threadpool(
                password_hasher.hash, new_token()
            )
            yield
        finally:
            client.close()

    application = FastAPI(title="问卷系统 API", version="0.4.0", lifespan=lifespan)
    application.state.settings = settings
    application.state.clock = clock
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    @application.exception_handler(APIError)
    async def handle_api_error(request: Request, error: APIError):
        return failure(error.code, error.message, error.status)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError):
        errors = error.errors()
        message = "参数校验失败"
        if any(e["type"] == "json_invalid" for e in errors):
            message = "请求体必须是有效的 JSON"
        elif any(e["type"] == "missing" and e["loc"] == ("body",) for e in errors):
            message = (
                "用户名/密码不能为空"
                if request.url.path in ("/auth/register", "/auth/login")
                else "请求体不能为空"
            )
        else:
            custom = next((e for e in errors if e["type"] == "parameters"), None)
            if custom:
                message = custom["msg"]
            elif request.url.path.startswith("/surveys"):
                first = errors[0]
                field = ".".join(str(part) for part in first["loc"][1:])
                descriptions = {
                    "missing": "缺少必填字段",
                    "extra_forbidden": "不支持的字段",
                    "bool_type": "必须为布尔值",
                    "string_type": "必须为字符串",
                    "string_too_long": "字符串长度超出限制",
                    "literal_error": "不支持的取值",
                    "list_type": "必须为列表",
                    "dict_type": "必须为对象",
                    "model_type": "请求体必须为 JSON 对象",
                }
                message = descriptions.get(first["type"], "参数校验失败")
                if field:
                    message = f"{field}：{message}"
        return failure(4001, message, 400)

    @application.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException):
        if error.status_code == 404:
            return failure(4040, "不存在", 404)
        if error.status_code == 405:
            return failure(4001, "请求方法不允许", 405)
        return failure(4001, "请求无效", error.status_code)

    @application.exception_handler(PyMongoError)
    async def handle_database_error(request: Request, error: PyMongoError):
        logger.error("MongoDB 请求失败：%s", type(error).__name__)
        return failure(5000, "服务暂不可用，请稍后重试", 503)

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception):
        logger.error("请求处理异常：%s", type(error).__name__)
        return failure(5000, "服务器内部错误", 500)

    application.include_router(router)
    application.include_router(survey_router)
    application.include_router(filling_router)
    application.include_router(statistics_router)

    @application.get("/", include_in_schema=False)
    @application.get("/ui", include_in_schema=False)
    @application.get("/ui/", include_in_schema=False)
    def frontend():
        return FileResponse(frontend_dir / "index.html")

    application.mount(
        "/ui-assets", StaticFiles(directory=frontend_dir, check_dir=True),
        name="frontend-assets",
    )
    return application


app = create_app()
