import os
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def survey_env():
    uri = os.getenv("TEST_MONGODB_URI", "mongodb://127.0.0.1:27017")
    name = "questionnaire_test_" + uuid4().hex
    mongo = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    hello = mongo.admin.command("hello")
    if "setName" not in hello and hello.get("msg") != "isdbgrid":
        pytest.fail("问卷测试需要 MongoDB 副本集，请按 README 配置 TEST_MONGODB_URI")
    clock = SimpleNamespace(now=datetime(2100, 1, 1, tzinfo=timezone.utc))
    settings = Settings(
        mongo_uri=uri, mongo_database=name, public_base_url="https://forms.example.test"
    )
    app = create_app(settings, clock=lambda: clock.now)
    try:
        with TestClient(app) as client:
            auth = {}
            for username in ("owner", "reader"):
                credentials = {"username": username, "password": "secret"}
                assert client.post("/auth/register", json=credentials).json()["code"] == 0
                token = client.post("/auth/login", json=credentials).json()["data"]["token"]
                auth[username] = {"Authorization": "Bearer " + token}
            yield SimpleNamespace(
                client=client, db=mongo[name], clock=clock, app=app,
                owner=auth["owner"], reader=auth["reader"],
            )
    finally:
        mongo.drop_database(name)
        mongo.close()
