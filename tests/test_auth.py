import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import AutoReconnect

from app.auth import AuthenticatedRoute, require_user
from app.config import Settings
from app.errors import APIError, success
from app.main import create_app
from app.security import password_hasher, token_hash


@pytest.fixture
def env():
    uri = os.getenv("TEST_MONGODB_URI", "mongodb://127.0.0.1:27017")
    name = "questionnaire_test_" + uuid4().hex
    mongo = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=3000)
    mongo.admin.command("ping")
    # 使用未来时钟，让过期校验测试不受 MongoDB 后台 TTL 清理影响。
    clock = SimpleNamespace(now=datetime(2100, 1, 1, tzinfo=timezone.utc))
    app = create_app(Settings(mongo_uri=uri, mongo_database=name), clock=lambda: clock.now)
    entered, release = Event(), Event()
    probes = APIRouter(prefix="/_test", route_class=AuthenticatedRoute)

    @probes.get("/success")
    def protected(user=Depends(require_user)):
        return success({"user_id": str(user)})

    @probes.get("/failure")
    def rejected(user=Depends(require_user)):
        raise APIError(4030, "无权限", 403)

    @probes.get("/business-failure")
    def business_failure(user=Depends(require_user)):
        return {"code": 4090, "msg": "状态冲突", "data": {}}

    @probes.get("/database-failure")
    def database_failure(user=Depends(require_user)):
        raise AutoReconnect("内部数据库连接详情")

    @probes.get("/validation")
    def validation(number: int, user=Depends(require_user)):
        return success()

    @probes.get("/wait")
    def wait(user=Depends(require_user)):
        entered.set()
        if not release.wait(10):
            raise RuntimeError("测试同步超时")
        return success()

    app.include_router(probes)
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(
                client=client, db=mongo[name], clock=clock,
                entered=entered, release=release,
            )
    finally:
        release.set()
        # 仅删除本次测试生成的随机数据库，绝不清空配置中的业务数据库。
        mongo.drop_database(name)
        mongo.close()


def register(env, username="alice", password="secret"):
    return env.client.post(
        "/auth/register", json={"username": username, "password": password}
    )


def login(env, username="alice", password="secret"):
    return env.client.post(
        "/auth/login", json={"username": username, "password": password}
    )


def logged_in(env):
    assert register(env).json()["code"] == 0
    response = login(env)
    assert response.json()["code"] == 0
    return response.json()["data"]["token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def assert_error(response, code, msg, status):
    assert response.status_code == status
    assert response.json() == {"code": code, "msg": msg, "data": {}}


def test_registration_storage_and_indexes(env):
    response = register(env, "  用户甲  ", "密码有六个字")
    assert response.status_code == 200
    data = response.json()["data"]
    assert ObjectId.is_valid(data["user_id"])
    assert datetime.fromisoformat(data["created_at"]) == env.clock.now
    user = env.db.Users.find_one()
    assert user["username"] == "用户甲"
    assert password_hasher.verify(user["password_hash"], "密码有六个字")
    assert "password" not in user and "form_list" not in user
    assert env.db.Users.index_information()["unique_username"]["unique"]
    indexes = env.db.Sessions.index_information()
    assert indexes["one_session_per_user"]["unique"]
    assert indexes["unique_token_hash"]["unique"]
    assert indexes["expired_sessions"]["expireAfterSeconds"] == 0


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login"])
@pytest.mark.parametrize("payload", [
    {}, {"username": "alice"}, {"password": "secret"},
    {"username": None, "password": "secret"},
    {"username": "alice", "password": None},
    {"username": "", "password": "secret"},
    {"username": "alice", "password": ""},
    {"username": " \t ", "password": "secret"},
    {"username": "alice", "password": "      "},
])
def test_missing_or_empty_credentials(env, path, payload):
    assert_error(
        env.client.post(path, json=payload),
        4001, "用户名/密码不能为空", 400,
    )


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login"])
@pytest.mark.parametrize("value", [123456, False, [], {"$ne": None}])
def test_non_string_credentials(env, path, value):
    for field in ("username", "password"):
        data = {"username": "alice", "password": "secret", field: value}
        assert_error(
            env.client.post(path, json=data),
            4001, "用户名/密码必须为字符串", 400,
        )


@pytest.mark.parametrize("length,accepted", [(5, False), (6, True), (12, True), (13, False)])
def test_registration_password_boundaries(env, length, accepted):
    result = register(env, password="x" * length)
    if accepted:
        assert result.json()["code"] == 0
    else:
        assert_error(result, 4001, "密码长度应为 6-12 个字符", 400)


def test_username_normalization_length_and_case(env):
    assert register(env, "x" * 50).json()["code"] == 0
    for path in ("/auth/register", "/auth/login"):
        assert_error(
            env.client.post(path, json={"username": "x" * 51, "password": "secret"}),
            4001, "用户名长度应为 1–50 个字符", 400,
        )
    assert register(env, "alice").json()["code"] == 0
    assert_error(register(env, " alice "), 4090, "该用户名已被注册", 409)
    assert register(env, "Alice").json()["code"] == 0
    assert login(env, " alice ").json()["data"]["username"] == "alice"


def test_password_spaces_are_preserved(env):
    assert register(env, password=" secret ").json()["code"] == 0
    assert login(env, password=" secret ").json()["code"] == 0
    assert_error(login(env, password="secret"), 4011, "用户名或密码错误", 401)


def test_wrong_password_and_unknown_user_are_identical(env):
    logged_in(env)
    for username, password in [("unknown", "secret"), ("alice", "x"), ("alice", "x" * 13)]:
        assert_error(login(env, username, password), 4011, "用户名或密码错误", 401)
    assert env.db.Sessions.count_documents({}) == 1


def test_login_hashes_token_and_replaces_old_session(env):
    old = logged_in(env)
    stored = env.db.Sessions.find_one()
    assert stored["token_hash"] == token_hash(old)
    assert old not in str(stored)
    assert stored["expires_at"] == env.clock.now + timedelta(days=3)
    new = login(env).json()["data"]["token"]
    assert new != old
    assert env.db.Sessions.count_documents({}) == 1
    assert_error(
        env.client.get("/_test/success", headers=headers(old)), 4010, "请先登录", 401
    )
    assert_error(
        env.client.post("/auth/logout", headers=headers(old)), 4010, "请先登录", 401
    )
    assert env.client.get("/_test/success", headers=headers(new)).json()["code"] == 0


def test_failed_login_does_not_revoke_current_session(env):
    token = logged_in(env)
    before = env.db.Sessions.find_one()
    env.clock.now += timedelta(hours=1)
    assert login(env, password="bad").json()["code"] == 4011
    assert env.db.Sessions.find_one() == before
    assert env.client.get("/_test/success", headers=headers(token)).json()["code"] == 0


@pytest.mark.parametrize("authorization", [None, "", "Basic abc", "Bearer", "Bearer unknown"])
def test_logout_requires_valid_token(env, authorization):
    supplied = {} if authorization is None else {"Authorization": authorization}
    assert_error(env.client.post("/auth/logout", headers=supplied), 4010, "请先登录", 401)


def test_logout_revokes_immediately(env):
    token = logged_in(env)
    result = env.client.post("/auth/logout", headers=headers(token))
    assert result.json() == {"code": 0, "msg": "退出成功", "data": {}}
    assert env.db.Sessions.count_documents({}) == 0
    assert_error(
        env.client.get("/_test/success", headers=headers(token)), 4010, "请先登录", 401
    )
    assert_error(
        env.client.post("/auth/logout", headers=headers(token)), 4010, "请先登录", 401
    )


def test_sliding_expiry_and_exact_expiry_boundary(env):
    token = logged_in(env)
    env.clock.now += timedelta(days=2)
    result = env.client.get("/_test/success", headers=headers(token))
    assert result.json()["code"] == 0
    expires = env.clock.now + timedelta(days=3)
    assert env.db.Sessions.find_one()["expires_at"] == expires
    env.clock.now = expires
    assert_error(
        env.client.get("/_test/success", headers=headers(token)), 4010, "请先登录", 401
    )
    assert env.db.Sessions.find_one()["expires_at"] == expires
    assert_error(
        env.client.post("/auth/logout", headers=headers(token)), 4010, "请先登录", 401
    )
    assert login(env).json()["code"] == 0
    assert env.db.Sessions.count_documents({}) == 1


@pytest.mark.parametrize("path", [
    "/_test/failure", "/_test/business-failure", "/_test/validation?number=bad",
    "/_test/database-failure",
])
def test_failed_request_does_not_renew(env, path):
    token = logged_in(env)
    expires = env.db.Sessions.find_one()["expires_at"]
    env.clock.now += timedelta(days=1)
    response = env.client.get(path, headers=headers(token))
    assert response.json()["code"] != 0
    assert env.db.Sessions.find_one()["expires_at"] == expires
    if path == "/_test/database-failure":
        assert_error(response, 5000, "服务暂不可用，请稍后重试", 503)


def test_public_requests_do_not_renew(env):
    token = logged_in(env)
    before = env.db.Sessions.find_one()
    env.clock.now += timedelta(days=1)
    result = env.client.post(
        "/auth/register", headers=headers(token),
        json={"username": "bob", "password": "secret"},
    )
    assert result.json()["code"] == 0
    assert env.db.Sessions.find_one() == before


def test_concurrent_registration_is_unique(env):
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: register(env), range(3)))
    assert sorted(r.json()["code"] for r in results) == [0, 4090, 4090]
    assert env.db.Users.count_documents({"username": "alice"}) == 1


def test_concurrent_logins_leave_one_valid_token(env):
    register(env)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: login(env), range(3)))
    assert all(r.json()["code"] == 0 for r in results)
    tokens = [r.json()["data"]["token"] for r in results]
    assert len(set(tokens)) == 3
    assert env.db.Sessions.count_documents({}) == 1
    outcomes = [
        env.client.get("/_test/success", headers=headers(t)).json()["code"] for t in tokens
    ]
    assert sorted(outcomes) == [0, 4010, 4010]


def test_concurrent_logout_succeeds_only_once(env):
    token = logged_in(env)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(
            lambda _: env.client.post("/auth/logout", headers=headers(token)), range(3)
        ))
    assert sorted(r.json()["code"] for r in results) == [0, 4010, 4010]
    assert env.db.Sessions.count_documents({}) == 0


def test_users_have_independent_sessions(env):
    alice = logged_in(env)
    register(env, "bob")
    bob = login(env, "bob").json()["data"]["token"]
    assert env.db.Sessions.count_documents({}) == 2
    assert env.client.post("/auth/logout", headers=headers(alice)).json()["code"] == 0
    assert env.client.get("/_test/success", headers=headers(bob)).json()["code"] == 0


@pytest.mark.parametrize("action", ["logout", "login"])
def test_inflight_request_cannot_restore_revoked_session(env, action):
    old = logged_in(env)
    env.clock.now += timedelta(days=1)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(env.client.get, "/_test/wait", headers=headers(old))
        assert env.entered.wait(5)
        try:
            if action == "logout":
                assert env.client.post("/auth/logout", headers=headers(old)).json()["code"] == 0
            else:
                assert login(env).json()["code"] == 0
            after = env.db.Sessions.find_one()
            env.clock.now += timedelta(hours=1)
        finally:
            env.release.set()
        assert future.result().json()["code"] == 0
    assert env.db.Sessions.find_one() == after
    assert_error(
        env.client.get("/_test/success", headers=headers(old)), 4010, "请先登录", 401
    )


def test_renewal_never_shortens_expiry(env):
    token = logged_in(env)
    later = env.clock.now + timedelta(days=5)
    env.db.Sessions.update_one({}, {"$set": {"expires_at": later}})
    env.clock.now += timedelta(days=1)
    assert env.client.get("/_test/success", headers=headers(token)).json()["code"] == 0
    assert env.db.Sessions.find_one()["expires_at"] == later


def test_invalid_body_and_framework_errors_use_envelope(env):
    for path in ("/auth/register", "/auth/login"):
        assert_error(env.client.post(path), 4001, "用户名/密码不能为空", 400)
        assert_error(
            env.client.post(path, content="{", headers={"Content-Type": "application/json"}),
            4001, "请求体必须是有效的 JSON", 400,
        )
        assert_error(
            env.client.post(path, json=["alice", "secret"]),
            4001, "请求体必须是 JSON 对象", 400,
        )
    assert_error(env.client.get("/missing"), 4040, "不存在", 404)
    assert_error(env.client.get("/auth/login"), 4001, "请求方法不允许", 405)


def test_test_routes_are_not_in_production_app():
    paths = {route.path for route in create_app().routes}
    assert not any(path.startswith("/_test") for path in paths)
    assert {"/auth/register", "/auth/login", "/auth/logout"} <= paths
