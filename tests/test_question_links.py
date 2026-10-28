from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from urllib.parse import urlsplit

import pytest
from bson import ObjectId
from pymongo.collection import Collection

from app.errors import APIError
from app.question_links_service import QuestionLinksService
from test_filling import item, submit
from test_surveys import add, create, deadline, detail, error, ok, patch, publish


def path(form, question):
    return f"/surveys/{form['form_id']}/questions/{question['question_id']}"


def save(env, form, question, key="save-key", headers=None):
    return env.client.post(
        path(form, question) + "/save", headers=headers or env.owner,
        json={"requestId": key},
    )


def save_and_link(env, form, question, key="save-link-key", headers=None,
                  confirm=True):
    return env.client.post(
        path(form, question) + "/save-and-link", headers=headers or env.owner,
        json={"requestId": key, "includeHistoricalAnswers": confirm},
    )


def link(env, form, question, version_id, headers=None, confirm=True):
    return env.client.post(
        path(form, question) + "/link", headers=headers or env.owner,
        json={"version_id": version_id, "includeHistoricalAnswers": confirm},
    )


def source(env, form, question, headers=None):
    return env.client.get(
        path(form, question) + "/source", headers=headers or env.owner,
    )


def required(env, form, question, value, headers=None):
    return env.client.patch(
        path(form, question) + "/required", headers=headers or env.owner,
        json={"required": value},
    )


def content(env, saved):
    return ok(env.client.get(
        f"/question-resources/{saved['resource_id']}/versions/{saved['version_id']}",
        headers=env.owner,
    ))["content"]


def test_save_only_snapshots_question_and_retries_without_reading_edited_source(
    survey_env, monkeypatch,
):
    e = survey_env
    form = create(e)
    question = ok(add(e, form, "number", title="原题",
                      validation={"required": True, "min_value": 0}))
    original = e.db.Questions.find_one({"_id": ObjectId(question["question_id"])})
    first = ok(save(e, form, question))
    assert content(e, first) == {
        "title": "原题", "type": "number", "options": [],
        "validation": {"min_value": 0, "integer_only": False},
    }
    assert first["source_question_id"] == question["question_id"]
    assert e.db.Questions.find_one({"_id": original["_id"]}) == original
    assert source(e, form, question).json()["data"] is None
    assert "source_question_id" not in detail(e, form)["questions"][0]

    ok(patch(e, form, question, title="编辑后的题"))
    original_find = Collection.find_one

    def fail_question_read(collection, *args, **kwargs):
        if collection.name == "Questions":
            raise AssertionError("重试不应重新读取后来编辑的卷内题目")
        return original_find(collection, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Collection, "find_one", fail_question_read)
        assert ok(save(e, form, question)) == first
    assert content(e, first)["title"] == "原题"
    second = ok(save(e, form, question, "intentionally-new"))
    assert second["resource_id"] != first["resource_id"]
    assert content(e, second)["title"] == "编辑后的题"
    assert source(e, form, question).json()["data"] is None
    assert e.db.Question_links.count_documents({}) == 0


@pytest.mark.parametrize("state", ["draft", "published", "closed", "expired"])
def test_save_and_link_preserves_question_response_and_old_statistics(survey_env, state):
    e = survey_env
    form = create(e)
    question = ok(add(e, form, "text", title="旧题",
                      validation={"required": True, "max_length": 20}))
    if state != "draft":
        if state == "expired":
            limit = e.clock.now + timedelta(hours=1)
            ok(deadline(e, form, limit.isoformat()))
        ok(publish(e, form))
        ok(submit(e, form, [item(question, "历史回答")]))
        if state == "closed":
            ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
        elif state == "expired":
            e.clock.now = limit
    before_q = e.db.Questions.find_one({"_id": ObjectId(question["question_id"])})
    before_responses = list(e.db.Responses.find({"form_id": ObjectId(form["form_id"])}))
    before_detail = detail(e, form)
    before_stats = ok(e.client.get(
        f"/surveys/{form['form_id']}/statistics", headers=e.owner
    ))
    before_revision = e.db.Question_forms.find_one()["revision"]
    result = ok(save_and_link(e, form, question))
    assert result["question_id"] == question["question_id"]
    assert result["include_historical_answers"] is True
    assert e.db.Question_forms.find_one()["revision"] == before_revision + 1
    assert e.db.Questions.find_one({"_id": before_q["_id"]}) == before_q
    assert list(e.db.Responses.find({"form_id": ObjectId(form["form_id"])})) == before_responses
    assert detail(e, form) == before_detail
    assert ok(e.client.get(
        f"/surveys/{form['form_id']}/statistics", headers=e.owner
    )) == before_stats
    assert source(e, form, question).json()["data"]["version_id"] == result["version_id"]
    assert content(e, result)["validation"] == {"max_length": 20}
    assert ok(save_and_link(e, form, question)) == result
    error(save_and_link(e, form, question, key="new-association"), 4090)
    assert e.db.Question_resources.count_documents({}) == 1
    assert e.db.Question_links.count_documents({}) == 1
    if state == "published":
        reader = ok(e.client.get(
            urlsplit(form["access_link"]).path, headers=e.reader
        ))
        assert reader["questions"] == before_detail["questions"]


def test_link_existing_checks_exact_version_content_and_existing_association(survey_env):
    e = survey_env
    form = create(e)
    first = ok(add(e, form, "single", validation={"required": True}))
    second = ok(add(e, form, "single", validation={"required": False}))
    saved = ok(save(e, form, first))
    assert [o["option_id"] for o in content(e, saved)["options"]] == [
        o["option_id"] for o in first["options"]
    ]
    error(link(e, form, second, saved["version_id"]), 4090)
    error(link(e, form, first, saved["version_id"], confirm=False), 4001)
    linked = ok(link(e, form, first, saved["version_id"]))
    assert linked["resource_id"] == saved["resource_id"]
    revision = e.db.Question_forms.find_one()["revision"]
    assert ok(link(e, form, first, saved["version_id"])) == linked
    assert e.db.Question_forms.find_one()["revision"] == revision
    other = ok(save(e, form, first, key="another-resource"))
    error(link(e, form, first, other["version_id"]), 4090)
    assert e.db.Question_links.count_documents({}) == 1
    assert first["question_id"] in [
        str(q["_id"]) for q in e.db.Questions.find()
    ]


def test_same_version_can_link_questions_with_different_required_settings(survey_env):
    e = survey_env
    first_form, second_form = create(e), create(e)
    first = ok(add(e, first_form, "text", title="同一题",
                   validation={"required": True, "max_length": 20}))
    second = ok(add(e, second_form, "text", title="同一题",
                    validation={"required": False, "max_length": 20}))
    saved = ok(save_and_link(e, first_form, first))
    linked = ok(link(e, second_form, second, saved["version_id"]))
    assert linked["version_id"] == saved["version_id"]
    assert first["question_id"] != second["question_id"]
    assert detail(e, first_form)["questions"][0]["validation"]["required"] is True
    assert detail(e, second_form)["questions"][0]["validation"]["required"] is False
    assert e.db.Question_links.count_documents({
        "version_id": ObjectId(saved["version_id"]),
    }) == 2


def test_save_and_link_retry_skips_question_and_link_reads(survey_env, monkeypatch):
    e = survey_env
    form = create(e)
    question = ok(add(e, form))
    saved = ok(save_and_link(e, form, question))
    actual = Collection.find_one

    def no_current_question_or_link_read(collection, *args, **kwargs):
        if collection.name in ("Questions", "Question_links"):
            raise AssertionError("成功重试必须直接回放首次结果")
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Collection, "find_one", no_current_question_or_link_read)
        assert ok(save_and_link(e, form, question)) == saved
    assert e.db.Question_links.count_documents({}) == 1


def test_linked_draft_can_change_required_and_jump_but_not_version_content(survey_env):
    e = survey_env
    form = create(e)
    first = ok(add(e, form, "single", validation={"required": True}))
    target = ok(add(e, form, "text"))
    saved = ok(save_and_link(e, form, first))
    assert ok(required(e, form, first, False))["validation"]["required"] is False
    jump = [{"condition": {"op": "eq", "value": first["options"][0]["option_id"]},
             "target": target["question_id"]}]
    assert ok(patch(e, form, first, jump_rules=jump))["jump_rules"] == jump
    assert ok(patch(e, form, first, validation={"required": True}))["validation"]["required"]
    for attempted in [
        {"title": "不同的标题"},
        {"options": [{**first["options"][0], "text": "改名"}, *first["options"][1:]]},
        {"validation": {"required": True, "min_selected": 1}},
    ]:
        before = e.db.Questions.find_one({"_id": ObjectId(first["question_id"])})
        response = patch(e, form, first, **attempted)
        assert response.json()["code"] in (4001, 4090)
        assert e.db.Questions.find_one({"_id": before["_id"]}) == before
    assert content(e, saved)["options"] == first["options"]
    assert detail(e, form)["questions"][0]["jump_rules"] == jump


def test_linked_required_endpoint_keeps_existing_version_limits(survey_env):
    e = survey_env
    form = create(e)
    question = ok(add(e, form, "number", validation={
        "min_value": 0, "max_value": 10, "integer_only": True,
    }))
    saved = ok(save_and_link(e, form, question))
    error(patch(e, form, question, validation={"required": True}), 4090)
    assert ok(required(e, form, question, True))["validation"] == {
        "required": True, "min_value": 0, "max_value": 10, "integer_only": True,
    }
    assert content(e, saved)["validation"] == {
        "min_value": 0, "max_value": 10, "integer_only": True,
    }
    error(required(e, form, question, "true"), 4001)
    ok(publish(e, form))
    error(required(e, form, question, False), 4090)
    error(patch(e, form, question, title="不得修改"), 4090)


def test_confirmation_permissions_and_request_id_conflicts(survey_env):
    e = survey_env
    form = create(e)
    question = ok(add(e, form))
    error(save_and_link(e, form, question, confirm=False), 4001)
    error(e.client.post(
        path(form, question) + "/save-and-link", headers=e.owner,
        json={"requestId": "missing-confirm"},
    ), 4001)
    for method, endpoint, body in [
        ("post", "save", {"requestId": "unauthorized"}),
        ("post", "save-and-link", {
            "requestId": "unauthorized", "includeHistoricalAnswers": True,
        }),
        ("post", "link", {
            "version_id": str(ObjectId()), "includeHistoricalAnswers": True,
        }),
        ("get", "source", None), ("patch", "required", {"required": True}),
    ]:
        error(e.client.request(
            method, path(form, question) + "/" + endpoint, json=body
        ), 4010)
        error(e.client.request(
            method, path(form, question) + "/" + endpoint,
            headers=e.reader, json=body,
        ), 4030)
    first = ok(save(e, form, question))
    error(save_and_link(e, form, question, key="save-key"), 4090)
    error(save(e, form, question, key="save-link-key", headers=e.reader), 4030)
    error(link(e, form, question, str(ObjectId())), 4040)
    error(source(e, form, {"question_id": str(ObjectId())}), 4040)
    assert e.db.Question_links.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({}) == 1
    assert first["version_id"]


def test_save_and_link_failure_rolls_back_resource_version_revision_and_marker(
    survey_env, monkeypatch,
):
    e = survey_env
    form = create(e)
    question = ok(add(e, form))
    before = e.db.Question_forms.find_one()
    original = Collection.insert_one

    def fail_insert(collection, *args, **kwargs):
        if collection.name == "Question_links":
            raise APIError(4090, "模拟关联写入失败", 409)
        return original(collection, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Collection, "insert_one", fail_insert)
        error(save_and_link(e, form, question), 4090)
    assert e.db.Question_forms.find_one() == before
    for collection in ("Question_resources", "Question_versions",
                       "Question_operations", "Question_links"):
        assert e.db[collection].count_documents({}) == 0
    assert ok(save_and_link(e, form, question))["question_id"] == question["question_id"]


def test_save_only_uses_consistent_snapshot_while_draft_changes(survey_env, monkeypatch):
    e = survey_env
    form = create(e)
    question = ok(add(e, form, title="快照前"))
    entered, release = Event(), Event()
    original = QuestionLinksService.question

    def paused(service, *args, **kwargs):
        selected = original(service, *args, **kwargs)
        entered.set()
        assert release.wait(10)
        return selected

    with monkeypatch.context() as patcher:
        patcher.setattr(QuestionLinksService, "question", paused)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(save, e, form, question)
            assert entered.wait(5)
            try:
                ok(patch(e, form, question, title="快照后"))
            finally:
                release.set()
            saved = ok(future.result())
    assert content(e, saved)["title"] == "快照前"
    assert detail(e, form)["questions"][0]["title"] == "快照后"


def test_link_racing_with_edit_leaves_consistent_version(survey_env, monkeypatch):
    e = survey_env
    form = create(e)
    question = ok(add(e, form, title="原题"))
    saved = ok(save(e, form, question))
    entered, release = Event(), Event()
    original = QuestionLinksService.coordinate_form

    def paused(service, *args, **kwargs):
        original(service, *args, **kwargs)
        entered.set()
        assert release.wait(10)

    with monkeypatch.context() as patcher:
        patcher.setattr(QuestionLinksService, "coordinate_form", paused)
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(link, e, form, question, saved["version_id"])
            assert entered.wait(5)
            editing = pool.submit(patch, e, form, question, title="并发改题")
            release.set()
            linked = future.result()
            response = editing.result()
    assert {response.json()["code"], linked.json()["code"]} in (
        {0, 4090}, {4090},
    )
    actual = source(e, form, question).json()["data"]
    if actual:
        assert content(e, saved)["title"] == detail(e, form)["questions"][0]["title"]
    else:
        assert detail(e, form)["questions"][0]["title"] == "并发改题"


def test_published_link_and_submission_coordinate_without_changing_content(survey_env):
    e = survey_env
    form = create(e)
    question = ok(add(e, form, "text"))
    ok(publish(e, form))
    saved = ok(save(e, form, question))
    before = e.db.Questions.find_one({"_id": ObjectId(question["question_id"])})
    with ThreadPoolExecutor(max_workers=2) as pool:
        linking = pool.submit(link, e, form, question, saved["version_id"])
        submitting = pool.submit(submit, e, form, [item(question, "同时提交")])
        assert ok(linking.result())["version_id"] == saved["version_id"]
        assert ok(submitting.result())["response_id"]
    assert e.db.Questions.find_one({"_id": before["_id"]}) == before
    assert e.db.Responses.count_documents({"form_id": ObjectId(form["form_id"])}) == 1
    assert e.db.Question_links.count_documents({"question_id": before["_id"]}) == 1


def test_save_and_link_racing_with_publish_keeps_frozen_question(survey_env):
    e = survey_env
    form = create(e)
    question = ok(add(e, form, "text"))
    before = e.db.Questions.find_one({"_id": ObjectId(question["question_id"])})
    with ThreadPoolExecutor(max_workers=2) as pool:
        association = pool.submit(save_and_link, e, form, question)
        publication = pool.submit(publish, e, form)
        saved = ok(association.result())
        assert ok(publication.result()) == {"status": "published"}
    assert e.db.Question_forms.find_one()["status"] == "published"
    assert e.db.Questions.find_one({"_id": before["_id"]}) == before
    assert source(e, form, question).json()["data"]["version_id"] == saved["version_id"]
    assert e.db.Question_resources.count_documents({}) == 1
    assert e.db.Question_versions.count_documents({}) == 1
    error(patch(e, form, question, title="发布后不能编辑"), 4090)
