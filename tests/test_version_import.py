from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from bson import ObjectId
from pymongo.collection import Collection

from app.errors import APIError
from test_filling import item, submit
from test_question_links import content, save, save_and_link, source
from test_surveys import add, create, deadline, detail, error, ok, patch, publish


def import_version(env, form, version_id, key="import-key", required=False, headers=None):
    return env.client.post(
        f"/surveys/{form['form_id']}/questions/from-version",
        headers=env.owner if headers is None else headers,
        json={"requestId": key, "version_id": version_id, "required": required},
    )


def resource(env, kind="text", headers=None, key="resource-key"):
    body = {
        "requestId": key, "title": "可复用题", "type": kind, "validation": {},
    }
    if kind in ("single", "multiple"):
        body["options"] = [{"text": "甲"}, {"text": "乙"}]
    if kind == "number":
        body["validation"] = {"min_value": 0, "max_value": 120}
    return ok(env.client.post(
        "/question-resources", headers=headers or env.owner, json=body,
    ))


@pytest.mark.parametrize("kind", ["single", "multiple", "text", "number"])
def test_import_copies_fixed_content_preserves_options_and_creates_new_id(survey_env, kind):
    e = survey_env
    selected = resource(e, kind)
    original = content(e, selected)
    form = create(e)
    old = ok(add(e, form))
    before = e.db.Questions.find_one({"_id": ObjectId(old["question_id"])})
    imported = ok(import_version(e, form, selected["version_id"], required=True))
    assert imported["question_id"] not in (
        old["question_id"], selected["resource_id"], selected["version_id"],
    )
    assert imported["order"] == 2
    assert imported["resource_id"] == selected["resource_id"]
    assert imported["version_id"] == selected["version_id"]
    assert imported["options"] == original["options"]
    assert imported["validation"] == {**original["validation"], "required": True}
    assert imported["jump_rules"] == []
    assert source(e, form, imported).json()["data"]["version_id"] == selected["version_id"]
    assert e.db.Questions.find_one({"_id": before["_id"]}) == before
    assert content(e, selected) == original
    error(patch(e, form, imported, title="直接改版本内容"), 4090)
    assert e.db.Responses.count_documents({}) == 0


def test_saved_version_does_not_copy_source_jump_and_answers_use_new_question_id(survey_env):
    e = survey_env
    original_form = create(e)
    original = ok(add(e, original_form, "single"))
    target = ok(add(e, original_form))
    option = original["options"][0]["option_id"]
    ok(patch(e, original_form, original, jump_rules=[
        {"condition": {"op": "eq", "value": option}, "target": target["question_id"]},
    ]))
    selected = ok(save(e, original_form, original))
    form = create(e)
    imported = ok(import_version(e, form, selected["version_id"]))
    assert imported["question_id"] != original["question_id"]
    assert imported["jump_rules"] == []
    assert imported["options"] == original["options"]
    first = ok(add(e, form, "number"))
    # A previously existing question can point to the newly appended import.
    another_form = create(e)
    prior = ok(add(e, another_form, "number"))
    another = ok(import_version(
        e, another_form, selected["version_id"], key="other-import",
    ))
    ok(patch(e, another_form, prior, jump_rules=[
        {"condition": {"op": "eq", "value": 1}, "target": another["question_id"]},
    ]))
    ok(publish(e, form))
    ok(submit(e, form, [item(imported, option), item(first, None)]))
    response = e.db.Responses.find_one({"form_id": ObjectId(form["form_id"])})
    assert response["answers"] == [item(imported, option)]


def test_retries_replay_before_state_and_duplicate_checks(survey_env, monkeypatch):
    e = survey_env
    selected = resource(e)
    form = create(e)
    first = ok(import_version(e, form, selected["version_id"]))
    revision = e.db.Question_forms.find_one()["revision"]
    actual = Collection.find_one

    def no_current_state_read(collection, *args, **kwargs):
        if collection.name in ("Questions", "Question_links", "Question_versions", "Question_forms"):
            raise AssertionError("成功重试应直接返回首次结果")
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Collection, "find_one", no_current_state_read)
        assert ok(import_version(e, form, selected["version_id"])) == first
    assert e.db.Question_forms.find_one()["revision"] == revision
    error(import_version(e, form, selected["version_id"], key="new-key"), 4090,
          "该版本已存在于当前问卷，不能重复入卷")
    error(import_version(e, form, selected["version_id"], required=True), 4090)
    ok(publish(e, form))
    assert ok(import_version(e, form, selected["version_id"])) == first
    ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
    assert ok(import_version(e, form, selected["version_id"])) == first
    assert e.db.Questions.count_documents({}) == 1
    assert e.db.Question_links.count_documents({}) == 1


def test_new_versions_do_not_update_import_and_different_versions_can_coexist(survey_env):
    e = survey_env
    selected = resource(e)
    form = create(e)
    first = ok(import_version(e, form, selected["version_id"]))
    second = ok(e.client.post(
        f"/question-resources/{selected['resource_id']}/versions", headers=e.owner,
        json={"requestId": "derive", "parent_version_id": selected["version_id"],
              "title": "新版本题干", "type": "text", "validation": {}},
    ))
    assert detail(e, form)["questions"][0]["title"] == "可复用题"
    assert source(e, form, first).json()["data"]["version_id"] == selected["version_id"]
    imported_second = ok(import_version(
        e, form, second["version_id"], key="import-second", required=True,
    ))
    assert imported_second["question_id"] != first["question_id"]
    assert imported_second["order"] == 2
    assert imported_second["title"] == "新版本题干"
    assert imported_second["resource_id"] == first["resource_id"]
    other_form = create(e)
    other = ok(import_version(e, other_form, selected["version_id"], key="other-form"))
    assert other["question_id"] != first["question_id"]


def test_duplicate_check_includes_preexisting_associations(survey_env):
    e = survey_env
    form = create(e)
    old = ok(add(e, form))
    selected = ok(save_and_link(e, form, old))
    before = e.db.Question_forms.find_one()
    error(import_version(e, form, selected["version_id"]), 4090,
          "该版本已存在于当前问卷，不能重复入卷")
    assert e.db.Question_forms.find_one() == before
    assert e.db.Questions.count_documents({}) == 1


@pytest.mark.parametrize("state", ["published", "closed", "expired"])
def test_first_import_rejects_non_draft_and_keeps_data(survey_env, state):
    e = survey_env
    selected = resource(e)
    form = create(e)
    ok(add(e, form))
    if state == "expired":
        limit = e.clock.now + timedelta(hours=1)
        ok(deadline(e, form, limit.isoformat()))
    ok(publish(e, form))
    if state == "closed":
        ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
    if state == "expired":
        e.clock.now = limit
    before = e.db.Question_forms.find_one()
    error(import_version(e, form, selected["version_id"]), 4090)
    assert e.db.Question_forms.find_one() == before
    assert e.db.Question_links.count_documents({}) == 0
    assert e.db.Questions.count_documents({}) == 1
    assert e.db.Question_operations.count_documents({}) == 1


def test_expired_draft_can_import_but_not_publish(survey_env):
    e = survey_env
    selected = resource(e)
    form = create(e)
    ok(deadline(e, form, (e.clock.now + timedelta(hours=1)).isoformat()))
    e.clock.now += timedelta(hours=1)
    ok(import_version(e, form, selected["version_id"]))
    error(publish(e, form), 4090)


def test_permissions_validation_and_missing_targets(survey_env):
    e = survey_env
    form = create(e)
    selected = resource(e)
    foreign = resource(e, headers=e.reader, key="foreign")
    error(e.client.post(
        f"/surveys/{form['form_id']}/questions/from-version",
        json={"requestId": "key", "version_id": selected["version_id"], "required": False},
    ), 4010)
    error(import_version(e, form, selected["version_id"], headers=e.reader), 4030)
    error(import_version(e, form, foreign["version_id"]), 4030)
    error(import_version(e, form, str(ObjectId())), 4040)
    error(import_version(e, {"form_id": str(ObjectId())}, selected["version_id"]), 4040)
    error(import_version(e, form, "invalid"), 4001)
    for body in [
        {"requestId": "key", "version_id": selected["version_id"]},
        {"requestId": "key", "version_id": selected["version_id"], "required": "true"},
        {"requestId": "key", "version_id": selected["version_id"], "required": False,
         "jump_rules": []},
    ]:
        error(e.client.post(
            f"/surveys/{form['form_id']}/questions/from-version",
            headers=e.owner, json=body,
        ), 4001)
    assert e.db.Questions.count_documents({}) == 0
    assert e.db.Question_links.count_documents({}) == 0


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_import_only_creates_one_occurrence(survey_env, same_key):
    e = survey_env
    selected = resource(e)
    form = create(e)
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(
            lambda i: import_version(
                e, form, selected["version_id"],
                key="shared" if same_key else f"import-{i}",
            ), range(3),
        ))
    if same_key:
        assert len({ok(r)["question_id"] for r in responses}) == 1
    else:
        assert sorted(r.json()["code"] for r in responses) == [0, 4090, 4090]
        for response in responses:
            if response.json()["code"] == 4090:
                assert response.json()["data"] == {}
    assert e.db.Questions.count_documents({}) == 1
    assert e.db.Question_links.count_documents({}) == 1
    assert e.db.Question_forms.find_one()["revision"] == 1


def test_import_failure_rolls_back_question_link_marker_and_revision(survey_env, monkeypatch):
    e = survey_env
    selected = resource(e)
    form = create(e)
    before = e.db.Question_forms.find_one()
    actual = Collection.insert_one

    def fail_link(collection, *args, **kwargs):
        if collection.name == "Question_links":
            raise APIError(4090, "模拟关联写入失败", 409)
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Collection, "insert_one", fail_link)
        error(import_version(e, form, selected["version_id"]), 4090)
    assert e.db.Question_forms.find_one() == before
    assert e.db.Questions.count_documents({}) == 0
    assert e.db.Question_links.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({}) == 1
    assert ok(import_version(e, form, selected["version_id"]))["order"] == 1


def test_import_revalidates_whole_form_without_partial_writes(survey_env):
    e = survey_env
    selected = resource(e)
    form = create(e)
    old = ok(add(e, form, "number"))
    e.db.Questions.update_one({"_id": ObjectId(old["question_id"])}, {"$set": {
        "jump_rules": [{"condition": {"op": "eq", "value": 1}, "target": str(ObjectId())}],
    }})
    before = e.db.Question_forms.find_one()
    error(import_version(e, form, selected["version_id"]), 4001)
    assert e.db.Question_forms.find_one() == before
    assert e.db.Questions.count_documents({}) == 1
    assert e.db.Question_links.count_documents({}) == 0


def test_import_racing_with_publish_keeps_coherent_frozen_form(survey_env):
    e = survey_env
    selected = resource(e)
    form = create(e)
    ok(add(e, form))
    with ThreadPoolExecutor(max_workers=2) as pool:
        importing = pool.submit(import_version, e, form, selected["version_id"])
        publication = pool.submit(publish, e, form)
        ok(publication.result())
        response = importing.result()
    assert response.json()["code"] in (0, 4090)
    questions = detail(e, form)["questions"]
    assert len(questions) == (2 if response.json()["code"] == 0 else 1)
    assert e.db.Question_links.count_documents({}) == (
        1 if response.json()["code"] == 0 else 0
    )
    assert detail(e, form)["status"] == "published"


def test_distinct_versions_import_with_manual_add_and_edit_have_unique_order(survey_env):
    e = survey_env
    selected = resource(e)
    second = ok(e.client.post(
        f"/question-resources/{selected['resource_id']}/versions", headers=e.owner,
        json={"requestId": "derive", "parent_version_id": selected["version_id"],
              "title": "第二版", "type": "text", "validation": {}},
    ))
    form = create(e)
    old = ok(add(e, form))
    with ThreadPoolExecutor(max_workers=4) as pool:
        first_import = pool.submit(import_version, e, form, selected["version_id"])
        second_import = pool.submit(
            import_version, e, form, second["version_id"], key="second-import",
        )
        manual = pool.submit(add, e, form)
        editing = pool.submit(patch, e, form, old, title="原题编辑")
        created = [ok(task.result()) for task in (first_import, second_import, manual)]
        assert ok(editing.result())["title"] == "原题编辑"
    assert sorted(q["order"] for q in created) == [2, 3, 4]
    assert detail(e, form)["questions"][0]["title"] == "原题编辑"
    assert e.db.Question_links.count_documents({}) == 2
