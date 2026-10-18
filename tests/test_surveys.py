from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlsplit

import pytest
from bson import ObjectId
from pymongo.collection import Collection

from app.survey_service import SurveyService


def ok(response):
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 0, response.text
    return response.json()["data"]


def error(response, code, message=None):
    assert response.json()["code"] == code, response.text
    assert response.status_code == {4001: 400, 4010: 401, 4030: 403, 4040: 404, 4090: 409}[code]
    if message is not None:
        assert response.json()["msg"] == message
    assert response.json()["data"] == {}


def create(env, **fields):
    return ok(env.client.post("/surveys", headers=env.owner, json={"title": "问卷", **fields}))


def add(env, form, kind="text", **fields):
    data = {"title": "题目", "type": kind}
    if kind in ("single", "multiple"):
        data["options"] = [{"text": "选项甲"}, {"text": "选项乙"}, {"text": "选项丙"}]
    data.update(fields)
    return env.client.post(
        f"/surveys/{form['form_id']}/questions", headers=env.owner, json=data
    )


def patch(env, form, q, **fields):
    return env.client.patch(
        f"/surveys/{form['form_id']}/questions/{q['question_id']}",
        headers=env.owner, json=fields,
    )


def publish(env, form):
    return env.client.post(f"/surveys/{form['form_id']}/publish", headers=env.owner)


def deadline(env, form, value):
    return env.client.put(
        f"/surveys/{form['form_id']}/deadline", headers=env.owner, json={"deadline": value}
    )


def detail(env, form):
    return ok(env.client.get(f"/surveys/{form['form_id']}", headers=env.owner))


def test_create_defaults_link_storage_and_indexes(survey_env):
    e = survey_env
    form = create(e, title="  中文问卷  ")
    assert ObjectId.is_valid(form["form_id"])
    assert form["access_link"].startswith("https://forms.example.test/surveys/access/")
    stored = e.db.Question_forms.find_one()
    assert stored["title"] == "中文问卷"
    assert stored["status"] == "draft"
    assert stored["deadline"] is None
    assert stored["description"] == ""
    assert stored["allow_anonymous"] is False
    assert stored["allow_multiple_submissions"] is False
    assert stored["owner_id"] == e.db.Users.find_one({"username": "owner"})["_id"]
    assert stored["created_at"] == e.clock.now
    assert e.db.Question_forms.index_information()["unique_access_token"]["unique"]
    assert e.db.Questions.index_information()["unique_form_order"]["unique"]
    assert "questions" not in stored
    assert detail(e, form)["questions"] == []
    error(e.client.get(urlsplit(form["access_link"]).path, headers=e.reader), 4090, "问卷尚未发布")


@pytest.mark.parametrize("data", [
    {}, {"title": ""}, {"title": " \t "}, {"title": "a" * 201},
    {"title": 123}, {"title": "q", "description": None},
    {"title": "q", "allow_anonymous": "false"},
    {"title": "q", "allow_multiple_submissions": 0},
    {"title": "q", "status": "published"},
])
def test_create_validation(survey_env, data):
    error(survey_env.client.post("/surveys", headers=survey_env.owner, json=data), 4001)
    assert survey_env.db.Question_forms.count_documents({}) == 0


def test_list_is_owner_only_paginated_and_does_not_query_questions(survey_env, monkeypatch):
    e = survey_env
    first = create(e, title="第一份")
    e.clock.now += timedelta(seconds=1)
    second = create(e, title="第二份")
    ok(e.client.post("/surveys", headers=e.reader, json={"title": "其他用户的问卷"}))
    actual_find = Collection.find

    def no_question_query(collection, *args, **kwargs):
        assert collection.name != "Questions"
        return actual_find(collection, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "find", no_question_query)
        result = ok(e.client.get("/surveys?page=1&page_size=1", headers=e.owner))
        assert result["total"] == 2
        assert result["items"][0]["form_id"] == second["form_id"]
        assert "questions" not in result["items"][0]
        result = ok(e.client.get("/surveys?page=2&page_size=1", headers=e.owner))
        assert result["items"][0]["form_id"] == first["form_id"]
    for query in ("page=0", "page_size=101", "page_size=0", "page=abc"):
        error(e.client.get("/surveys?" + query, headers=e.owner), 4001)


def test_all_routes_require_login(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form))
    fid, qid = form["form_id"], q["question_id"]
    for method, path, payload in [
        ("post", "/surveys", {"title": "q"}),
        ("get", "/surveys", None),
        ("get", f"/surveys/{fid}", None),
        ("get", urlsplit(form["access_link"]).path, None),
        ("post", f"/surveys/{fid}/questions", {"title": "q", "type": "text"}),
        ("patch", f"/surveys/{fid}/questions/{qid}", {"title": "q"}),
        ("put", f"/surveys/{fid}/deadline", {"deadline": None}),
        ("post", f"/surveys/{fid}/publish", None),
        ("post", f"/surveys/{fid}/close", None),
    ]:
        error(e.client.request(method, path, json=payload), 4010)


def test_management_routes_enforce_ownership_and_not_found(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form))
    fid, qid = form["form_id"], q["question_id"]
    for method, suffix, payload in [
        ("get", "", None),
        ("post", "/questions", {"title": "题目", "type": "text"}),
        ("patch", f"/questions/{qid}", {"title": "修改"}),
        ("put", "/deadline", {"deadline": None}),
        ("post", "/publish", None),
        ("post", "/close", None),
    ]:
        error(e.client.request(
            method, f"/surveys/{fid}{suffix}", headers=e.reader, json=payload
        ), 4030)
        error(e.client.request(
            method, f"/surveys/{ObjectId()}{suffix}", headers=e.owner, json=payload
        ), 4040)
    error(e.client.get("/surveys/bad-id", headers=e.owner), 4001)
    error(e.client.get("/surveys/access/missing", headers=e.reader), 4040)
    assert e.db.Questions.find_one()["title"] == "题目"


def test_question_types_and_detail_visibility(survey_env):
    e = survey_env
    form = create(e, allow_anonymous=True, allow_multiple_submissions=True, description="说明")
    for kind in ("single", "multiple", "text", "number"):
        q = ok(add(e, form, kind))
        assert q["validation"]["required"] is False
        if kind in ("single", "multiple"):
            assert all(ObjectId.is_valid(o["option_id"]) for o in q["options"])
    owner_view = detail(e, form)
    assert [q["order"] for q in owner_view["questions"]] == [1, 2, 3, 4]
    ok(publish(e, form))
    reader_view = ok(e.client.get(urlsplit(form["access_link"]).path, headers=e.reader))
    assert reader_view["questions"] == owner_view["questions"]
    assert reader_view["status"] == "published"
    assert reader_view["allow_anonymous"] is True
    assert "owner_id" not in reader_view and "access_token" not in reader_view
    assert "revision" not in reader_view and "access_link" not in reader_view
    assert e.db.Questions.count_documents({"form_id": ObjectId(form["form_id"])}) == 4


@pytest.mark.parametrize("data", [
    {"title": "q", "type": "unsupported"},
    {"title": " ", "type": "text"},
    {"title": "q", "type": "single"},
    {"title": "q", "type": "multiple", "options": [{"text": "a"}]},
    {"title": "q", "type": "single", "options": [{"text": ""}, {"text": "b"}]},
    {"title": "q", "type": "text", "options": [{"text": "a"}, {"text": "b"}]},
    {"title": "q", "type": "text", "validation": {"min_length": 3, "max_length": 1}},
    {"title": "q", "type": "number", "validation": {"integer_only": True, "min_value": 0.1, "max_value": 0.9}},
    {"title": "q", "type": "number", "validation": {"min_value": True}},
    {"title": "q", "type": "text", "validation": {"required": "true"}},
    {"title": "q", "type": "text", "order": 100},
])
def test_invalid_question_is_not_saved_and_revision_rolls_back(survey_env, data):
    e = survey_env
    form = create(e)
    before = e.db.Question_forms.find_one()
    error(e.client.post(
        f"/surveys/{form['form_id']}/questions", headers=e.owner, json=data
    ), 4001)
    assert e.db.Questions.count_documents({}) == 0
    assert e.db.Question_forms.find_one() == before


def test_required_multiple_default_and_exact_count(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form, "multiple", validation={"required": True}))
    assert q["validation"]["required"] is True
    error(patch(e, form, q, validation={"required": True, "max_selected": 0}), 4001)
    result = ok(patch(e, form, q, validation={"required": True, "min_selected": 2, "max_selected": 2}))
    assert result["validation"]["min_selected"] == result["validation"]["max_selected"] == 2
    assert detail(e, form)["questions"][0]["validation"] == result["validation"]


def test_patch_preserves_option_ids_and_revalidates_references(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form, "single"))
    target = ok(add(e, form))
    option = q["options"][0]["option_id"]
    rules = [{"condition": {"op": "eq", "value": option}, "target": target["question_id"]}]
    ok(patch(e, form, q, jump_rules=rules))
    edited = ok(patch(e, form, q, title=" 改后的标题 "))
    assert edited["options"] == q["options"]
    assert edited["title"] == "改后的标题"
    error(patch(e, form, q, options=q["options"][1:]), 4001)
    assert detail(e, form)["questions"][0]["options"] == q["options"]
    renamed = [{**o, "text": "新文本"} for o in q["options"]]
    assert ok(patch(e, form, q, options=renamed))["options"][0]["option_id"] == option
    error(patch(e, form, q, options=[
        {"option_id": str(ObjectId()), "text": "a"}, {"text": "b"},
    ]), 4001)
    error(patch(e, form, q, title=None), 4001)
    error(patch(e, form, q), 4001)


def test_patch_rejects_question_from_another_form(survey_env):
    e = survey_env
    first, second = create(e), create(e)
    q = ok(add(e, first))
    error(patch(e, second, q, title="修改"), 4040)


def test_jump_target_and_rule_conflicts(survey_env):
    e = survey_env
    form, other = create(e), create(e)
    q = ok(add(e, form, "number", validation={"min_value": 0, "max_value": 10}))
    target = ok(add(e, form))
    foreign = ok(add(e, other))
    for bad in (q["question_id"], foreign["question_id"], str(ObjectId())):
        error(patch(e, form, q, jump_rules=[
            {"condition": {"op": "eq", "value": 1}, "target": bad}
        ]), 4001)
    error(patch(e, form, q, jump_rules=[
        {"condition": {"op": "lte", "value": 5}, "target": target["question_id"]},
        {"condition": {"op": "gte", "value": 5}, "target": "end"},
    ]), 4001)
    rules = [
        {"condition": {"op": "lt", "value": 5}, "target": target["question_id"]},
        {"condition": {"op": "gte", "value": 5}, "target": "end"},
    ]
    assert ok(patch(e, form, q, jump_rules=rules))["jump_rules"] == rules
    ok(publish(e, form))


def test_forward_jump_can_skip_required_questions_in_definition(survey_env):
    e = survey_env
    form = create(e)
    first = ok(add(e, form, "single"))
    ok(add(e, form, validation={"required": True}))
    ok(add(e, form, validation={"required": True}))
    fourth = ok(add(e, form))
    rules = [{
        "condition": {"op": "eq", "value": first["options"][0]["option_id"]},
        "target": fourth["question_id"],
    }]
    ok(patch(e, form, first, jump_rules=rules))
    ok(publish(e, form))
    assert detail(e, form)["questions"][0]["jump_rules"] == rules
    # 本轮只验证定义可保存，提交时的路径校验由后续填写模块实现。


def test_lifecycle_and_freeze(survey_env):
    e = survey_env
    form = create(e)
    error(publish(e, form), 4090, "请先添加题目")
    error(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner), 4090)
    q = ok(add(e, form))
    assert ok(publish(e, form)) == {"status": "published"}
    published = e.db.Question_forms.find_one()
    error(add(e, form), 4090)
    error(patch(e, form, q, title="禁止修改"), 4090)
    error(deadline(e, form, None), 4090)
    error(publish(e, form), 4090)
    assert e.db.Question_forms.find_one() == published
    assert ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner)) == {"status": "closed"}
    assert detail(e, form)["status"] == "closed"
    error(e.client.get(urlsplit(form["access_link"]).path, headers=e.reader), 4090, "问卷已关闭")
    error(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner), 4090)
    error(publish(e, form), 4090)


@pytest.mark.parametrize("value", [
    "2099-12-31T23:59:59Z", "2100-01-01T00:00:00Z", "2100-01-02",
    "2100-01-02T00:00:00", "not-a-date", 4102444800,
])
def test_invalid_deadlines(survey_env, value):
    e = survey_env
    form = create(e)
    error(deadline(e, form, value), 4001)
    assert e.db.Question_forms.find_one()["deadline"] is None


def test_deadline_normalization_and_clearing(survey_env):
    e = survey_env
    form = create(e)
    result = ok(deadline(e, form, "2100-01-02T08:00:00+08:00"))
    assert result["deadline"].startswith("2100-01-02T00:00:00")
    assert e.db.Question_forms.find_one()["deadline"] == e.clock.now + timedelta(days=1)
    assert ok(deadline(e, form, None)) == {"deadline": None}


def test_expired_published_storage_is_closed_everywhere(survey_env):
    e = survey_env
    form = create(e)
    ok(add(e, form))
    limit = e.clock.now + timedelta(hours=1)
    ok(deadline(e, form, limit.isoformat()))
    ok(publish(e, form))
    e.clock.now = limit
    assert e.db.Question_forms.find_one()["status"] == "published"
    assert detail(e, form)["status"] == "closed"
    assert ok(e.client.get("/surveys", headers=e.owner))["items"][0]["status"] == "closed"
    error(e.client.get(urlsplit(form["access_link"]).path, headers=e.reader), 4090, "问卷已截止")
    error(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner), 4090, "问卷已截止")
    assert e.db.Question_forms.find_one()["status"] == "published"


def test_expired_draft_cannot_publish_but_deadline_can_be_fixed(survey_env):
    e = survey_env
    form = create(e)
    ok(add(e, form))
    ok(deadline(e, form, (e.clock.now + timedelta(hours=1)).isoformat()))
    e.clock.now += timedelta(hours=1)
    error(publish(e, form), 4090)
    assert detail(e, form)["status"] == "draft"
    ok(deadline(e, form, None))
    ok(publish(e, form))


def test_publish_revalidates_stored_rules(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form, "number"))
    e.db.Questions.update_one({"_id": ObjectId(q["question_id"])}, {"$set": {
        "jump_rules": [{"condition": {"op": "eq", "value": 1}, "target": str(ObjectId())}]
    }})
    before = e.db.Question_forms.find_one()
    error(publish(e, form), 4001)
    assert e.db.Question_forms.find_one() == before


def test_concurrent_additions_have_unique_order(survey_env):
    e = survey_env
    form = create(e)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: add(e, form), range(4)))
    assert sorted(ok(r)["order"] for r in results) == [1, 2, 3, 4]
    assert len(detail(e, form)["questions"]) == 4


def test_concurrent_publish_only_succeeds_once(survey_env):
    e = survey_env
    form = create(e)
    ok(add(e, form))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: publish(e, form), range(3)))
    assert sorted(r.json()["code"] for r in results) == [0, 4090, 4090]
    assert detail(e, form)["status"] == "published"


def test_publish_racing_with_edit_leaves_coherent_frozen_form(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form))
    with ThreadPoolExecutor(max_workers=2) as pool:
        publication = pool.submit(publish, e, form)
        edit = pool.submit(patch, e, form, q, title="并发修改")
        ok(publication.result())
        response = edit.result()
    expected_title = "并发修改" if response.json()["code"] == 0 else "题目"
    assert response.json()["code"] in (0, 4090)
    assert detail(e, form)["questions"][0]["title"] == expected_title
    error(patch(e, form, q, title="发布后的修改"), 4090)


def test_expiry_rechecked_inside_close_transaction(survey_env, monkeypatch):
    e = survey_env
    form = create(e)
    ok(add(e, form))
    limit = e.clock.now + timedelta(hours=1)
    ok(deadline(e, form, limit.isoformat()))
    ok(publish(e, form))
    original = SurveyService.mutate

    def delayed(service, fid, uid, expected, operation):
        def move_clock_then_operate(document, session):
            e.clock.now = limit
            return operation(document, session)
        return original(service, fid, uid, expected, move_clock_then_operate)

    monkeypatch.setattr(SurveyService, "mutate", delayed)
    before = e.db.Question_forms.find_one()
    error(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner), 4090)
    assert e.db.Question_forms.find_one() == before


def test_surveys_reuse_sliding_auth_and_failed_requests_do_not_renew(survey_env):
    e = survey_env
    owner_id = e.db.Users.find_one({"username": "owner"})["_id"]
    before = e.db.Sessions.find_one({"user_id": owner_id})["expires_at"]
    e.clock.now += timedelta(hours=1)
    error(e.client.post("/surveys", headers=e.owner, json={}), 4001)
    assert e.db.Sessions.find_one({"user_id": owner_id})["expires_at"] == before
    create(e)
    assert e.db.Sessions.find_one({"user_id": owner_id})["expires_at"] == e.clock.now + timedelta(days=3)


def test_missing_body_does_not_use_account_error_message(survey_env):
    response = survey_env.client.post("/surveys", headers=survey_env.owner)
    error(response, 4001, "请求体不能为空")
