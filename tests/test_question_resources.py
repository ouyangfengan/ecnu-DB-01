from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from bson import ObjectId
from pymongo.collection import Collection

from app.errors import APIError


ROOT = "/question-resources"


def ok(response):
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 0, response.text
    return response.json()["data"]


def error(response, code):
    assert response.status_code == {
        4001: 400, 4010: 401, 4030: 403, 4040: 404, 4090: 409,
    }[code], response.text
    assert response.json()["code"] == code, response.text
    assert response.json()["data"] == {}


def create(env, request_id="new-resource", headers=None, **fields):
    return env.client.post(
        ROOT, headers=headers or env.owner,
        json={"requestId": request_id, "title": " 年龄 ", "type": "number",
              "validation": {"min_value": 0, "max_value": 120, "integer_only": True},
              **fields},
    )


def version(env, resource_id, version_id, headers=None):
    return env.client.get(
        f"{ROOT}/{resource_id}/versions/{version_id}",
        headers=headers or env.owner,
    )


def derive(env, resource_id, parent_id, request_id="derive", headers=None, **fields):
    return env.client.post(
        f"{ROOT}/{resource_id}/versions", headers=headers or env.owner,
        json={"requestId": request_id, "parent_version_id": parent_id,
              "title": "新年龄", "type": "number",
              "validation": {"min_value": 0, "max_value": 130, "integer_only": True},
              **fields},
    )


def restore(env, resource_id, version_id, request_id="restore", headers=None):
    return env.client.post(
        f"{ROOT}/{resource_id}/versions/{version_id}/restore",
        headers=headers or env.owner, json={"requestId": request_id},
    )


def test_create_read_list_and_indexes_do_not_touch_old_collections(survey_env):
    e = survey_env
    first = ok(create(e))
    assert first["version_number"] == 1
    assert first["parent_version_id"] is None
    assert first["change_type"] == "create"
    assert ObjectId.is_valid(first["resource_id"])
    assert ObjectId.is_valid(first["version_id"])
    detail = ok(version(e, first["resource_id"], first["version_id"]))
    assert detail["content"] == {
        "title": "年龄", "type": "number", "options": [],
        "validation": {"min_value": 0, "max_value": 120, "integer_only": True},
    }
    stored = e.db.Question_versions.find_one({"_id": ObjectId(first["version_id"])})
    assert "required" not in stored["content"]["validation"]
    assert "jump_rules" not in stored["content"]
    assert e.db.Questions.count_documents({}) == 0
    assert e.db.Responses.count_documents({}) == 0
    assert e.db.Question_forms.count_documents({}) == 0
    assert e.db.Question_versions.index_information()["unique_resource_version"]["unique"]
    assert e.db.Question_operations.index_information()["unique_question_operation"]["unique"]

    e.clock.now += timedelta(seconds=1)
    second = ok(create(e, request_id="another", title="姓名", type="text", validation={}))
    listed = ok(e.client.get(f"{ROOT}?page=1&page_size=1", headers=e.owner))
    assert listed["total"] == 2
    assert listed["items"][0]["resource_id"] == second["resource_id"]
    assert listed["items"][0]["title"] == "姓名"
    next_page = ok(e.client.get(f"{ROOT}?page=2&page_size=1", headers=e.owner))
    assert next_page["items"][0]["resource_id"] == first["resource_id"]
    assert [item["version_id"] for item in ok(e.client.get(
        f"{ROOT}/{first['resource_id']}", headers=e.owner
    ))["versions"]] == [first["version_id"]]


@pytest.mark.parametrize("changes", [
    {"title": ""}, {"type": "unknown"},
    {"validation": {"required": False}},
    {"validation": {"min_value": 5, "max_value": 2}},
    {"validation": {"min_value": 0.1, "max_value": 0.9, "integer_only": True}},
    {"validation": {"min_length": 1}},
    {"options": [{"text": "不适用"}]},
    {"jump_rules": []}, {"order": 1},
    {"requestId": "invalid space"},
])
def test_invalid_create_rolls_back_without_using_request_id(survey_env, changes):
    e = survey_env
    error(create(e, **changes), 4001)
    assert e.db.Question_resources.count_documents({}) == 0
    assert e.db.Question_versions.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({}) == 0


@pytest.mark.parametrize("kind,options,validation", [
    ("single", [{"text": "甲"}, {"text": "乙"}], {}),
    ("multiple", [{"text": "甲"}, {"text": "乙"}], {"min_selected": 1, "max_selected": 2}),
    ("text", [], {"min_length": 0, "max_length": 100}),
    ("number", [], {"min_value": 0, "integer_only": True}),
])
def test_independent_versions_reuse_first_stage_question_validation(
    survey_env, kind, options, validation,
):
    e = survey_env
    created = ok(create(e, type=kind, options=options, validation=validation))
    content = ok(version(e, created["resource_id"], created["version_id"]))["content"]
    assert content["type"] == kind
    assert content["validation"] == ({"integer_only": False, **validation} if kind == "number" else validation)
    assert all(ObjectId.is_valid(o["option_id"]) for o in content["options"])
    if options:
        error(create(e, request_id="custom-ids", type=kind, options=[
            {"option_id": str(ObjectId()), "text": "甲"}, {"text": "乙"},
        ], validation=validation), 4001)


def test_branch_restore_preserve_history_and_option_identity(survey_env):
    e = survey_env
    initial = ok(create(e, type="single", validation={},
                        options=[{"text": "甲"}, {"text": "乙"}]))
    rid, original_id = initial["resource_id"], initial["version_id"]
    original = ok(version(e, rid, original_id))["content"]
    options = original["options"]
    second = ok(derive(
        e, rid, original_id, type="single", validation={}, title="修改后",
        options=[options[0], {"text": "丙"}],
    ))
    new_content = ok(version(e, rid, second["version_id"]))["content"]
    assert new_content["options"][0] == options[0]
    assert new_content["options"][1]["option_id"] not in {
        item["option_id"] for item in options
    }
    assert second["version_number"] == 2
    assert second["parent_version_id"] == original_id
    error(derive(
        e, rid, original_id, request_id="changed-choice", type="single",
        validation={}, options=[{**options[0], "text": "改名"}, options[1]],
    ), 4001)
    assert e.db.Question_versions.count_documents({"resource_id": ObjectId(rid)}) == 2

    fork = ok(derive(
        e, rid, original_id, request_id="fork", type="single",
        validation={}, options=options, title="另一分支",
    ))
    recovered = ok(restore(e, rid, original_id))
    assert [second["version_number"], fork["version_number"], recovered["version_number"]] == [2, 3, 4]
    assert fork["parent_version_id"] == recovered["parent_version_id"] == original_id
    assert recovered["change_type"] == "restore"
    assert ok(version(e, rid, recovered["version_id"]))["content"] == original
    assert ok(version(e, rid, original_id))["content"] == original
    versions = ok(e.client.get(f"{ROOT}/{rid}", headers=e.owner))["versions"]
    assert [item["version_number"] for item in versions] == [1, 2, 3, 4]
    assert [item["parent_version_id"] for item in versions] == [
        None, original_id, original_id, original_id,
    ]


def test_idempotent_creates_retries_and_conflicting_reuse(survey_env):
    e = survey_env
    first = ok(create(e))
    assert ok(create(e)) == first
    error(create(e, title="其他标题"), 4090)
    error(derive(e, first["resource_id"], first["version_id"],
                 request_id="new-resource"), 4090)
    assert e.db.Question_resources.count_documents({}) == 1
    assert e.db.Question_versions.count_documents({}) == 1

    second = ok(derive(e, first["resource_id"], first["version_id"]))
    assert ok(derive(e, first["resource_id"], first["version_id"])) == second
    error(derive(e, first["resource_id"], first["version_id"],
                 title="换一个内容"), 4090)
    recovered = ok(restore(e, first["resource_id"], first["version_id"]))
    assert ok(restore(e, first["resource_id"], first["version_id"])) == recovered
    assert e.db.Question_versions.count_documents({}) == 3
    assert e.db.Question_operations.count_documents({}) == 3

    other = ok(create(e, headers=e.reader))
    assert other["resource_id"] != first["resource_id"]
    assert e.db.Question_operations.count_documents({"request_id": "new-resource"}) == 2


def test_concurrent_same_request_and_distinct_branches(survey_env):
    e = survey_env
    with ThreadPoolExecutor(max_workers=4) as pool:
        creations = list(pool.map(lambda _: create(e), range(4)))
    ids = {ok(response)["resource_id"] for response in creations}
    assert len(ids) == 1
    assert e.db.Question_resources.count_documents({}) == 1
    rid = ids.pop()
    parent = ok(creations[0])["version_id"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        derived = list(pool.map(
            lambda index: derive(e, rid, parent, request_id=f"branch-{index}"),
            range(4),
        ))
    assert sorted(ok(response)["version_number"] for response in derived) == [2, 3, 4, 5]
    assert e.db.Question_versions.count_documents({"resource_id": ObjectId(rid)}) == 5


def test_concurrent_same_request_with_different_content_has_one_winner(survey_env):
    e = survey_env
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(create, e, "shared", title="第一种内容")
        second = pool.submit(create, e, "shared", title="第二种内容")
        responses = [first.result(), second.result()]
    assert sorted(response.json()["code"] for response in responses) == [0, 4090]
    assert e.db.Question_resources.count_documents({}) == 1
    assert e.db.Question_versions.count_documents({}) == 1
    assert e.db.Question_operations.count_documents({}) == 1


def test_auth_owner_scope_and_missing_targets(survey_env):
    e = survey_env
    first = ok(create(e))
    rid, vid = first["resource_id"], first["version_id"]
    paths = [
        (e.client.get, ROOT, {}),
        (e.client.get, f"{ROOT}/{rid}", {}),
        (e.client.get, f"{ROOT}/{rid}/versions/{vid}", {}),
        (e.client.post, ROOT, {"json": {"requestId": "unauth", "title": "t", "type": "text"}}),
        (e.client.post, f"{ROOT}/{rid}/versions", {
            "json": {"requestId": "unauth", "parent_version_id": vid, "title": "t", "type": "text"},
        }),
        (e.client.post, f"{ROOT}/{rid}/versions/{vid}/restore", {
            "json": {"requestId": "unauth"},
        }),
    ]
    for method, path, kwargs in paths:
        error(method(path, **kwargs), 4010)
    assert ok(e.client.get(ROOT, headers=e.reader))["total"] == 0
    error(e.client.get(f"{ROOT}/{rid}", headers=e.reader), 4030)
    error(version(e, rid, vid, e.reader), 4030)
    error(derive(e, rid, vid, headers=e.reader), 4030)
    error(restore(e, rid, vid, headers=e.reader), 4030)
    error(e.client.get(f"{ROOT}/{ObjectId()}", headers=e.owner), 4040)
    error(version(e, rid, str(ObjectId())), 4040)
    error(derive(e, rid, str(ObjectId()), request_id="bad-parent"), 4040)
    error(restore(e, rid, str(ObjectId()), request_id="bad-restore"), 4040)
    error(e.client.get(f"{ROOT}/bad-id", headers=e.owner), 4001)
    assert e.db.Question_operations.count_documents({}) == 1


def test_failed_transaction_does_not_leave_resource_or_dedupe_marker(survey_env, monkeypatch):
    e = survey_env
    original = Collection.insert_one

    def fail_version_insert(collection, *args, **kwargs):
        if collection.name == "Question_versions":
            raise APIError(4090, "模拟版本写入失败", 409)
        return original(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "insert_one", fail_version_insert)
        error(create(e), 4090)
    assert e.db.Question_resources.count_documents({}) == 0
    assert e.db.Question_versions.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({}) == 0
    assert ok(create(e))["version_number"] == 1


def test_invalid_derive_rolls_back_sequence_and_does_not_use_request_id(survey_env):
    e = survey_env
    created = ok(create(e))
    rid, vid = created["resource_id"], created["version_id"]
    error(derive(e, rid, vid, validation={"min_value": 10, "max_value": 2}), 4001)
    assert e.db.Question_resources.find_one({"_id": ObjectId(rid)})["last_version_number"] == 1
    assert e.db.Question_operations.count_documents({}) == 1
    assert ok(derive(e, rid, vid))["version_number"] == 2


def test_unstorable_validation_integer_is_a_parameter_error(survey_env):
    e = survey_env
    error(create(
        e, type="text", validation={"min_length": 2**100},
    ), 4001)
    assert e.db.Question_resources.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({}) == 0


def test_failed_version_insert_rolls_back_sequence_and_request_id(survey_env, monkeypatch):
    e = survey_env
    created = ok(create(e))
    rid, vid = created["resource_id"], created["version_id"]
    original = Collection.insert_one

    def fail_version_insert(collection, *args, **kwargs):
        if collection.name == "Question_versions":
            raise APIError(4090, "模拟派生写入失败", 409)
        return original(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "insert_one", fail_version_insert)
        error(derive(e, rid, vid), 4090)
    assert e.db.Question_resources.find_one({"_id": ObjectId(rid)})["last_version_number"] == 1
    assert e.db.Question_versions.count_documents({}) == 1
    assert e.db.Question_operations.count_documents({}) == 1
    assert ok(derive(e, rid, vid))["version_number"] == 2
